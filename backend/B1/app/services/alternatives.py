"""'다른 장소 추천' — 코스의 한 장소를 같은 종류의 주변 장소로 바꿀 후보를 찾는다.

1) 원래 장소 반경 1 km 안에서 같은 종류를 카카오로 검색
2) 방문 시각에 영업 중인지 확인 (논문 check ①과 같은 판정 모듈, 30분 캐시)
3) 두 사람 만족도 평균 − λ·격차(논문 식 (4))가 높은 순으로 최대 3곳
"""
import asyncio
import os

import httpx
from starlette.concurrency import run_in_threadpool

from app.services import ai_bridge  # noqa: F401  (ai/ 경로를 sys.path에 올려 hours_judge를 import 가능하게 함)
from app.services.kakao import KAKAO_REST_API_KEY, LOCAL_SEARCH_URL, haversine_meters, WALK_METERS_PER_MIN
from app.services.scoring import normalize_category, satisfaction

RADIUS_M = 1000
MAX_CANDIDATES = 6        # 영업시간을 확인할 후보 수 (크롤링 시간 때문에 제한)
MAX_RESULTS = 3
FAIR_LAMBDA = float(os.getenv("FAIR_LAMBDA", "1.0"))

SEARCH_KEYWORD = {
    "카페": "카페", "식당": "맛집", "레스토랑": "레스토랑", "바": "와인바",
    "전시": "전시", "공연": "공연장", "체험": "체험", "기타": "산책",
}


def _walk(a: tuple | None, b: tuple | None) -> int | None:
    if not a or not b or None in a or None in b:
        return None
    return round(haversine_meters(a[0], a[1], b[0], b[1]) / WALK_METERS_PER_MIN)


def _open_status(name: str, date: str | None, time: str) -> str:
    try:
        from tools.hours_judge import judge, parse_visit
    except Exception:
        return "unknown"
    when = parse_visit(date or "", time or "")
    if not when:
        return "unknown"
    try:
        return judge(name, when)["status"]
    except Exception:
        return "unknown"


async def find_alternatives(name: str, category: str, lat: float, lon: float, time: str, date: str | None,
                            tags_a: list[str], tags_b: list[str], exclude: list[str],
                            prev: tuple | None = None, nxt: tuple | None = None) -> list[dict]:
    cat = normalize_category(category)
    keyword = SEARCH_KEYWORD.get(cat, category or "카페")
    if not KAKAO_REST_API_KEY:
        return []
    params = {"query": keyword, "x": lon, "y": lat, "radius": RADIUS_M, "size": 15}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(LOCAL_SEARCH_URL, headers={"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"},
                                   params=params)
            docs = res.json().get("documents", [])
    except Exception:
        return []

    skip = set(exclude) | {name}
    cands = [d for d in docs if d.get("place_name") and d["place_name"] not in skip][:MAX_CANDIDATES]

    statuses = await asyncio.gather(*[run_in_threadpool(_open_status, d["place_name"], date, time) for d in cands])

    out = []
    for d, status in zip(cands, statuses):
        if status == "closed":
            continue
        c = normalize_category(d.get("category_name") or cat)
        if c == "기타":
            c = cat
        sa, sb = satisfaction(tags_a, c), satisfaction(tags_b, c)
        pos = (float(d["y"]), float(d["x"]))
        out.append({
            "name": d["place_name"],
            "category": c,
            "address": d.get("road_address_name") or d.get("address_name", ""),
            "place_url": d.get("place_url", ""),
            "latitude": pos[0],
            "longitude": pos[1],
            "open_status": status,
            "satisfaction_a": sa,
            "satisfaction_b": sb,
            "objective": round((sa + sb) / 2 - FAIR_LAMBDA * abs(sa - sb), 2),
            "walk_from_prev": _walk(prev, pos),
            "walk_to_next": _walk(pos, nxt),
        })
    # 영업 확인된 곳 우선 → 목적함수 J 높은 순 → 원래 장소에서 가까운 순(카카오 정확도 순서 유지)
    out.sort(key=lambda x: (x["open_status"] != "open", -x["objective"]))
    return out[:MAX_RESULTS]
