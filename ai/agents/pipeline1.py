import json
import re

from deepagents import create_deep_agent
from agents.shared import get_llm
from tools.event import search_events
from tools.logger import new_session, end_session

SYSTEM_PROMPT = """당신은 커플 데이트의 메인 이벤트를 추천하는 전문가입니다.

[입력으로 받는 정보]
- 사용자의 자연어 요청 (예: "성수동에서 토요일 데이트 할만한 거")
- 지역, 날짜, 통합 취향 (가능한 경우)

[당신의 역할]
1. search_events 툴을 호출하여 공연, 전시, 영화, 팝업 등 메인 이벤트를 검색한다.
2. 검색 결과를 바탕으로 최대 6개의 이벤트를 추천한다.
   - 반드시 search_events 결과에 실제로 나온 장소만 쓴다. 지어내지 않는다.
   - 그 지역 근처에 해당 유형(예: 공연장)이 없으면 그 유형은 넣지 않는다. 개수를 억지로 채우지 않는다.
   - 검색어에는 지역명을 붙인다 (예: "양평 전시", "양평 공방 체험").
3. 각 이벤트별로 짧은 추천 이유를 함께 제시한다.

[출력 형식 — 반드시 준수]
최종 응답은 아래 JSON 형식으로만 출력하라. 자연어 설명·마크다운은 절대 포함하지 말 것.
JSON 외 어떠한 추가 텍스트도 허용되지 않는다.

{
  "events": [
    {
      "name": "OO 갤러리 〈도시의 빛〉 전시",
      "place_id": "kakao:145791269",
      "category": "전시",
      "reason": "두 분 다 좋아하시는 감성 공간",
      "address": "서울 성동구 ...",
      "place_url": "http://place.map.kakao.com/..."
    }
  ]
}

규칙:
- 이벤트는 1~6개 (실제로 찾은 만큼만)
- category는 "전시" / "공연" / "팝업" / "영화" / "체험" 중 적절한 것
- 모르는 값은 빈 문자열 ""
- 응답 전체가 위 JSON 객체 하나여야 한다 (코드블록 X, 멘트 X)
"""


def build_pipeline1_agent():
    llm = get_llm()
    return create_deep_agent(
        model=llm,
        tools=[search_events],
        system_prompt=SYSTEM_PROMPT,
    )


def _compose_pipeline1_message(natural_language, merged_preferences, weather, area, visit_date) -> str:
    """입력 dict들을 자연어 메시지로 합친다."""
    parts = [natural_language or ""]

    if area:
        parts.append(f"지역: {area}")
    if visit_date:
        parts.append(f"방문 예정일: {visit_date}")
    if weather:
        cond = weather.get("condition", "")
        temp = weather.get("temp_celsius", "")
        if cond or temp != "":
            parts.append(f"날씨: {cond} {temp}도")
    if merged_preferences:
        atms = ", ".join(merged_preferences.get("atmospheres", []))
        cats = ", ".join(merged_preferences.get("categories", []))
        areas = ", ".join(merged_preferences.get("areas_preferred", []))
        budget = merged_preferences.get("budget_max")
        if atms:
            parts.append(f"통합 취향 분위기: {atms}")
        if cats:
            parts.append(f"통합 취향 카테고리: {cats}")
        if areas:
            parts.append(f"선호 지역: {areas}")
        if budget:
            parts.append(f"1인 예산 상한: {budget:,}원")
    return "\n".join(p for p in parts if p)


def _parse_json_output(text: str) -> dict:
    """LLM 응답에서 JSON 객체를 추출해 이벤트 리스트로 반환한다.

    추출 경로(_parse_status)는 디버그용:
    - "empty"             : 응답 텍스트가 비어 있음
    - "codeblock_ok"      : ```json``` 블록 안의 JSON 파싱 성공
    - "brace_ok"          : 텍스트에서 { ... } 추출해 파싱 성공
    - "json_failed"       : JSON 후보를 찾았지만 파싱 실패
    - "no_json_found"     : JSON 후보 자체가 없음
    """
    if not text:
        return {"events": [], "_parse_status": "empty"}

    # 1) ```json ... ``` 코드블록 우선
    code_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            return {
                "events": data.get("events", []),
                "_parse_status": "codeblock_ok",
            }
        except json.JSONDecodeError:
            return {"events": [], "_parse_status": "json_failed"}

    # 2) 텍스트 안에서 가장 외곽의 { ... }
    brace = re.search(r"\{[\s\S]*\}", text)
    if not brace:
        return {"events": [], "_parse_status": "no_json_found"}

    try:
        data = json.loads(brace.group(0))
        return {
            "events": data.get("events", []),
            "_parse_status": "brace_ok",
        }
    except json.JSONDecodeError:
        return {"events": [], "_parse_status": "json_failed"}


def _extract_final_text(result) -> str:
    """에이전트 응답의 마지막 메시지에서 텍스트를 추출한다."""
    messages = result.get("messages", [])
    for msg in reversed(messages):
        content = getattr(msg, "content", None)
        if not content:
            continue
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
                elif isinstance(item, str):
                    texts.append(item)
            if texts:
                return "\n".join(texts)
    return ""


def recommend_events(
    natural_language: str,
    merged_preferences: dict = None,
    weather: dict = None,
    area: str = None,
    visit_date: str = None,
) -> dict:
    """Pipeline 1 진입점 — 메인 이벤트 최대 6개 추천 (실제 검색된 장소만).

    API_SPEC.md §2 참조.

    Args:
        natural_language: 사용자 자연어 요청 (필수)
        merged_preferences: 두 사람 통합 취향
        weather: 날씨 정보 (condition, temp_celsius)
        area: 지역명
        visit_date: YYYY-MM-DD

    Returns:
        dict — 성공 시 {session_id, events_raw, events, _parse_status},
               실패 시 {session_id, error, events}
    """
    sid = new_session()

    if not natural_language:
        end_session("failed", note="natural_language 누락")
        return {
            "session_id": sid,
            "error": "natural_language is required",
            "events": [],
        }

    try:
        agent = build_pipeline1_agent()
        user_msg = _compose_pipeline1_message(
            natural_language, merged_preferences, weather, area, visit_date
        )

        result = agent.invoke({"messages": [{"role": "user", "content": user_msg}]})
        text = _extract_final_text(result)
        parsed = _parse_json_output(text)

        end_session("success")
        return {
            "session_id": sid,
            "events_raw": text,
            "events": parsed["events"],
            "_parse_status": parsed["_parse_status"],
        }
    except Exception as e:
        end_session("failed", note=str(e))
        return {
            "session_id": sid,
            "error": f"{type(e).__name__}: {e}",
            "events": [],
        }
