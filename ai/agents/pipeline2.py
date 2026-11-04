import json
import re
import time

from deepagents import create_deep_agent
from agents.shared import get_llm
from tools.search import search_places
from tools.hours import get_place_info
from tools.check_hours import check_hours
from tools.logger import new_session, end_session, session_tool_counts

_ROLE_VERIFY = """1. search_places 툴로 메인 이벤트 주변의 카페, 식당, 산책 코스 등을 검색한다.
2. get_place_info 툴로 후보 장소의 상세 정보(주소, 전화, 카카오맵 링크)를 확인한다.
3. 코스를 구성하기 전에, 넣으려는 후보 장소마다 check_hours 툴을 호출하여
   방문 예정 날짜(visit_date: YYYY-MM-DD)와 방문 시각(visit_time: HH:MM)에 영업하는지 확인한다.
4. 판정이 closed인 장소는 코스에서 빼고 search_places로 대체 장소를 찾아 다시 확인한다.
5. 메인 이벤트를 중심으로 시간대별 코스를 구성한다."""

_ROLE_NO_VERIFY = """1. search_places 툴로 메인 이벤트 주변의 카페, 식당, 산책 코스 등을 검색한다.
2. get_place_info 툴로 후보 장소의 상세 정보(주소, 전화, 카카오맵 링크)를 확인한다.
3. 메인 이벤트를 중심으로 시간대별 코스를 구성한다."""

_COURSE_NAMES = ["A안", "B안", "C안", "D안", "E안"]


def build_system_prompt(n_courses: int = 2, verify: bool = True) -> str:
    names = " / ".join(_COURSE_NAMES[:n_courses])
    hours_rule = '- status는 "ok" / "closed" / "outside_hours" / "unknown" 중 하나' if verify else '- hours_check는 빈 배열 []로 둔다'
    return f"""당신은 선택된 메인 이벤트를 중심으로 데이트 코스를 설계하는 전문가입니다.

[입력으로 받는 정보]
- 선택된 메인 이벤트 (이름, 장소, 시간 등)
- 두 사람(A, B) 각각의 취향 태그와 통합 취향 (가능한 경우)
- 지역, 날씨, 방문 날짜 (가능한 경우)

[당신의 역할]
{_ROLE_VERIFY if verify else _ROLE_NO_VERIFY}
- 코스 후보끼리는 장소 구성이 서로 다르게 만든다. 한 후보는 A의 취향을, 다른 후보는 B의 취향을,
  또 다른 후보는 두 사람의 공통 취향을 더 반영하는 식으로 다양하게 구성한다.

[출력 형식 — 반드시 준수]
최종 응답은 아래 JSON 형식으로만 출력하라. 자연어 설명·마크다운은 절대 포함하지 말 것.

{{
  "courses": [
    {{
      "name": "A안",
      "theme": "여유로운 오후 데이트",
      "places": [
        {{
          "order": 1,
          "time": "11:30",
          "duration_min": 60,
          "name": "어니언 성수",
          "category": "카페",
          "address": "서울 성동구 ...",
          "phone": "070-...",
          "place_url": "http://place.map.kakao.com/...",
          "is_main": false,
          "memo": "감성 카페, 빵과 커피로 시작"
        }}
      ]
    }}
  ],
  "hours_check": [
    {{"name": "어니언 성수", "visit_day": "토요일", "hours": "09:00 ~ 22:00", "status": "ok"}}
  ]
}}

규칙:
- 정확히 {n_courses}개의 코스({names}) 생성
- 메인 이벤트는 모든 코스에 포함하고 is_main: true
- category는 "카페" / "식당" / "레스토랑" / "바" / "전시" / "공연" / "체험" / "산책" 중 가장 가까운 것
{hours_rule}
- 모르는 값은 빈 문자열 ""
- 응답 전체가 위 JSON 객체 하나여야 한다 (배열 X, 코드블록 X)
"""


# 기존 import 호환용 (기본값: 2개 코스, 검증 사용)
SYSTEM_PROMPT = build_system_prompt()


def build_pipeline2_agent(n_courses: int = 2, verify: bool = True):
    llm = get_llm()
    tools = [search_places, get_place_info] + ([check_hours] if verify else [])
    return create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=build_system_prompt(n_courses, verify),
    )


def _compose_pipeline2_message(selected_event, merged_preferences, weather, visit_date,
                               tags_a=None, tags_b=None) -> str:
    """입력 dict들을 자연어 메시지로 합친다."""
    parts = []
    ev_name = selected_event.get("name", "")
    ev_cat = selected_event.get("category", "")
    ev_time = selected_event.get("time", "")
    parts.append(f"선택된 메인 이벤트: {ev_name} ({ev_cat}, 예상 시간 {ev_time})")
    parts.append("이 이벤트를 중심으로 시간대별 데이트 코스를 짜주세요.")

    if selected_event.get("address"):
        parts.append(f"이벤트 주소: {selected_event['address']}")
    if visit_date:
        parts.append(f"방문 예정일: {visit_date} (check_hours의 visit_date로 이 값을 그대로 사용)")
    if weather:
        cond = weather.get("condition", "")
        temp = weather.get("temp_celsius", "")
        if cond or temp != "":
            parts.append(f"날씨: {cond} {temp}도")
    if tags_a:
        parts.append(f"A의 취향: {', '.join(tags_a)}")
    if tags_b:
        parts.append(f"B의 취향: {', '.join(tags_b)}")
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
    return "\n".join(parts)


def _parse_json_output(text: str) -> dict:
    """LLM 응답에서 JSON 객체를 추출해 코스/영업시간 검증 결과를 분리한다.

    추출 경로(_parse_status)는 디버그용으로 함께 반환:
    - "empty"             : 응답 텍스트가 비어 있음
    - "codeblock_ok"      : ```json``` 블록 안의 JSON 파싱 성공
    - "brace_ok"          : 텍스트에서 { ... } 추출해 파싱 성공
    - "json_failed"       : JSON 후보를 찾았지만 파싱 실패 (잘못된 JSON)
    - "no_json_found"     : JSON 후보 자체가 없음 (마크다운 응답)
    """
    if not text:
        return {"courses": [], "hours_check": [], "_parse_status": "empty"}

    # 1) ```json ... ``` 코드블록 우선 추출
    code_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            return {
                "courses": data.get("courses", []),
                "hours_check": data.get("hours_check", []),
                "_parse_status": "codeblock_ok",
            }
        except json.JSONDecodeError:
            return {"courses": [], "hours_check": [], "_parse_status": "json_failed"}

    # 2) 텍스트 안에서 가장 외곽의 { ... } 추출
    brace = re.search(r"\{[\s\S]*\}", text)
    if not brace:
        return {"courses": [], "hours_check": [], "_parse_status": "no_json_found"}

    try:
        data = json.loads(brace.group(0))
        return {
            "courses": data.get("courses", []),
            "hours_check": data.get("hours_check", []),
            "_parse_status": "brace_ok",
        }
    except json.JSONDecodeError:
        return {"courses": [], "hours_check": [], "_parse_status": "json_failed"}


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


def final_check(courses: list[dict], visit_date: str | None) -> dict:
    """check ② — 코드 단의 최종 영업시간 재검증 (논문 2.2.3절).

    check ①에서 조회한 장소는 30분 캐시에 있으므로 추가 크롤링 없이 판정된다.
    각 장소에 open_status를 붙이고, 코스별 violations(closed 개수)를 계산한다.
    """
    from tools.hours_judge import judge, parse_visit

    t0 = time.time()
    n_checked = n_hit = 0
    for course in courses:
        violations = 0
        for place in course.get("places", []):
            when = parse_visit(visit_date or "", place.get("time", ""))
            if not when or not place.get("name"):
                place["open_status"] = "unknown"
                continue
            r = judge(place["name"], when)
            place["open_status"] = r["status"]
            n_checked += 1
            n_hit += int(r["cache_hit"])
            violations += int(r["status"] == "closed")
        course["violations"] = violations
    return {"checked": n_checked, "cache_hits": n_hit, "seconds": round(time.time() - t0, 2)}


def generate_course(
    selected_event: dict,
    merged_preferences: dict = None,
    weather: dict = None,
    visit_date: str = None,
    n_courses: int = 2,
    verify: bool = True,
    tags_a: list = None,
    tags_b: list = None,
) -> dict:
    """Pipeline 2 진입점 — 선택된 메인 이벤트 기반으로 코스 후보를 생성한다.

    API_SPEC.md §3 참조.

    Args:
        selected_event: Pipeline 1 응답의 events[i] 객체 (필수)
        merged_preferences: 두 사람 통합 취향
        weather: 날씨 정보 (condition, temp_celsius)
        visit_date: YYYY-MM-DD
        n_courses: 생성할 코스 후보 수 (A안, B안, C안 …)
        verify: True면 check_hours 툴 사용(check ①) + 최종 재검증(check ②)
        tags_a, tags_b: 두 사람 각각의 취향 태그

    Returns:
        dict — 성공 시 {session_id, courses, hours_check, final_check, timing, tool_calls, _parse_status},
               실패 시 {session_id, error, courses: []}
    """
    sid = new_session()

    if not selected_event:
        end_session("failed", note="selected_event 누락")
        return {
            "session_id": sid,
            "error": "selected_event is required",
            "courses": [],
        }

    t0 = time.time()
    try:
        agent = build_pipeline2_agent(n_courses, verify)
        user_msg = _compose_pipeline2_message(
            selected_event, merged_preferences, weather, visit_date, tags_a, tags_b
        )

        result = agent.invoke({"messages": [{"role": "user", "content": user_msg}]})
        agent_sec = round(time.time() - t0, 2)
        text = _extract_final_text(result)
        parsed = _parse_json_output(text)

        check2 = final_check(parsed["courses"], visit_date) if verify else None

        end_session("success")
        return {
            "session_id": sid,
            "courses_raw": text,                       # 원본 마크다운/JSON 백업
            "courses": parsed["courses"],              # 파싱된 코스 리스트 (verify면 violations 포함)
            "hours_check": parsed["hours_check"],      # 에이전트가 보고한 영업시간 검증
            "final_check": check2,                     # check ② 통계
            "timing": {"agent_sec": agent_sec, "total_sec": round(time.time() - t0, 2)},
            "tool_calls": session_tool_counts(sid),
            "_parse_status": parsed["_parse_status"],  # 디버그: 파싱 경로
        }
    except Exception as e:
        end_session("failed", note=str(e))
        return {
            "session_id": sid,
            "error": f"{type(e).__name__}: {e}",
            "courses": [],
            "timing": {"total_sec": round(time.time() - t0, 2)},
            "tool_calls": session_tool_counts(sid),
        }
