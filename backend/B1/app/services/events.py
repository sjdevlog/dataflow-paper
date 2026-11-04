"""메인 이벤트 추천 — AI(Pipeline 1) 추천을 지역 반경으로 검증하고, 부족하면 카카오 검색으로 채운다.

원칙: 그 지역 근처에 실제로 있는 장소만 보여준다. 개수를 억지로 채우지 않는다.
(예: 시골 지역에 공연장이 없으면 공연은 추천하지 않는다)
"""
import asyncio

import httpx
from starlette.concurrency import run_in_threadpool

from app.services import ai_bridge
from app.services.kakao import KAKAO_REST_API_KEY, LOCAL_SEARCH_URL

MAX_EVENTS = 6           # 첫 추천 최대 개수
MORE_SIZE = 3            # '더 보기' 한 번에 추가하는 개수
EVENT_RADIUS_M = 5000    # 선택한 지역 중심에서 이 거리 안의 장소만 인정

# 이벤트가 될 만한 장소 검색어 → 화면에 보일 분류
NEARBY_QUERIES = [
    ("전시", "전시"), ("갤러리", "전시"), ("미술관", "전시"),
    ("공연장", "공연"), ("소극장", "공연"),
    ("팝업스토어", "팝업"), ("체험", "체험"), ("공방", "체험"),
]


def guess_category(kakao_category: str, fallback: str = "체험") -> str:
    c = kakao_category or ""
    if any(k in c for k in ("미술관", "갤러리", "전시", "박물관")):
        return "전시"
    if any(k in c for k in ("공연", "극장", "콘서트", "소극장")):
        return "공연"
    if "영화" in c:
        return "영화"
    if "팝업" in c:
        return "팝업"
    return fallback


def _to_event(doc: dict, category: str, reason: str = "", source: str = "kakao") -> dict:
    return {
        "name": doc.get("place_name", ""),
        "category": category,
        "address": doc.get("road_address_name") or doc.get("address_name", ""),
        "place_url": doc.get("place_url", ""),
        "latitude": float(doc["y"]) if doc.get("y") else None,
        "longitude": float(doc["x"]) if doc.get("x") else None,
        "reason": reason,
        "source": source,
    }


async def _kakao(client: httpx.AsyncClient, query: str, lat: float, lon: float, size: int) -> list[dict]:
    if not KAKAO_REST_API_KEY:
        return []
    params = {"query": query, "x": lon, "y": lat, "radius": EVENT_RADIUS_M, "size": size}
    try:
        res = await client.get(LOCAL_SEARCH_URL, headers={"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"},
                               params=params)
        return res.json().get("documents", [])
    except Exception:
        return []


async def verify_nearby(client: httpx.AsyncClient, event: dict, lat: float, lon: float) -> dict | None:
    """AI가 추천한 장소가 지역 반경 안에 실제로 있는지 카카오로 확인 → 있으면 좌표·주소를 채워 반환"""
    name = (event.get("name") or "").strip()
    if not name:
        return None
    docs = await _kakao(client, name, lat, lon, 1)
    if not docs:
        return None
    category = event.get("category") or guess_category(docs[0].get("category_name", ""))
    return _to_event(docs[0], category, reason=event.get("reason", ""), source="ai")


async def search_nearby(lat: float, lon: float, exclude: set[str], size: int) -> list[dict]:
    """지역 반경 안의 전시·공연·체험 장소 (AI 없이 카카오 검색만)"""
    found: list[dict] = []
    seen = set(exclude)
    async with httpx.AsyncClient(timeout=8.0) as client:
        results = await asyncio.gather(*[_kakao(client, q, lat, lon, 5) for q, _ in NEARBY_QUERIES])
    for (q, cat), docs in zip(NEARBY_QUERIES, results):
        for d in docs:
            name = d.get("place_name", "")
            if name and name not in seen:
                seen.add(name)
                found.append(_to_event(d, guess_category(d.get("category_name", ""), cat)))
    # 검색어별로 돌아가며 섞이도록 정렬 (한 종류만 몰리지 않게)
    by_cat: dict[str, list[dict]] = {}
    for ev in found:
        by_cat.setdefault(ev["category"], []).append(ev)
    mixed = []
    while any(by_cat.values()) and len(mixed) < size:
        for cat in list(by_cat):
            if by_cat[cat] and len(mixed) < size:
                mixed.append(by_cat[cat].pop(0))
    return mixed


async def recommend(region: str, lat: float, lon: float, date: str | None,
                    tags_a: list[str], tags_b: list[str], natural_input: str | None) -> tuple[list[dict], str]:
    """(이벤트 목록, 출처 설명). AI 추천 중 반경 안에 실제로 있는 것만 남기고, 3개 미만이면 카카오 검색으로 보충"""
    tags = ", ".join(dict.fromkeys(tags_a + tags_b))
    nl = natural_input or f"{region}에서 데이트할 만한 전시·공연·체험 (두 사람 취향: {tags})"
    ai_events = await run_in_threadpool(
        ai_bridge.recommend_events, natural_language=nl, weather={}, area=region, visit_date=date,
    )

    events: list[dict] = []
    if ai_events:
        async with httpx.AsyncClient(timeout=8.0) as client:
            checked = await asyncio.gather(*[verify_nearby(client, ev, lat, lon) for ev in ai_events])
        names = set()
        for ev in checked:
            if ev and ev["name"] not in names:
                names.add(ev["name"])
                events.append(ev)
        events = events[:MAX_EVENTS]

    n_ai = len(events)
    if n_ai < 3:
        events += await search_nearby(lat, lon, {e["name"] for e in events}, MAX_EVENTS - n_ai)
    n_kakao = len(events) - n_ai
    source = "ai+kakao" if n_ai and n_kakao else "ai" if n_ai else "kakao" if n_kakao else "none"
    return events, source
