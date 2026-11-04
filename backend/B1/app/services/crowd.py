"""시간대별 혼잡도 — SerpApi의 Google Maps 결과에 들어 있는 '인기 시간대(popular_times)'를 쓴다.

Google 공식 Places API에는 이 정보가 없어, 구글맵 화면 정보를 대신 받아 주는 SerpApi(무료 월 250회)를 사용한다.
- 장소 1곳당 최대 2회 호출(검색 → 상세)이라, 결과 화면 전체가 아니라 상세 카드를 열 때만 부른다.
- 카카오 장소와 150 m 안에 있는 결과만 인정한다.
- 웨이팅(대기 팀 수)은 공개된 API가 없어 제공하지 않는다.

환경 변수: SERPAPI_API_KEY (코드에 넣지 않음)
"""
import os
import re

import httpx
from dotenv import load_dotenv

from app.services.kakao import haversine_meters

load_dotenv()

SERPAPI_URL = "https://serpapi.com/search.json"
MATCH_RADIUS_M = 150
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _key() -> str:
    return os.getenv("SERPAPI_API_KEY", "")


def parse_hour(label: str) -> int | None:
    """'8 PM', '8 PM', '오후 8시', '20시' → 20"""
    t = (label or "").replace(" ", " ").strip().upper()
    m = re.search(r"(\d{1,2})", t)
    if not m:
        return None
    h = int(m.group(1)) % 24
    if "PM" in t or "오후" in t:
        h = h % 12 + 12
    elif "AM" in t or "오전" in t:
        h = h % 12
    return h


def parse_popular_times(pt: dict) -> dict:
    days = {}
    for day, items in (pt.get("graph_results") or {}).items():
        rows = []
        for it in items or []:
            h = parse_hour(it.get("time", ""))
            if h is None:
                continue
            rows.append({"hour": h, "score": int(it.get("busyness_score") or 0), "info": it.get("info", "")})
        if rows:
            days[day.lower()] = sorted(rows, key=lambda r: r["hour"])
    live = pt.get("live_hash") or {}
    return {"days": days, "live_info": live.get("info", "") if isinstance(live, dict) else ""}


def _near(r: dict, lat: float, lon: float) -> bool:
    g = r.get("gps_coordinates") or {}
    if "latitude" not in g:
        return False
    return haversine_meters(lat, lon, g["latitude"], g["longitude"]) <= MATCH_RADIUS_M


async def popular_times(name: str, lat: float, lon: float) -> dict:
    if not _key():
        return {"found": False, "reason": "no_key"}
    base = {"engine": "google_maps", "hl": "ko", "gl": "kr", "api_key": _key()}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            data = (await client.get(SERPAPI_URL, params={**base, "type": "search", "q": name,
                                                          "ll": f"@{lat},{lon},17z"})).json()
            place = data.get("place_results")
            if not place or not _near(place, lat, lon):
                cand = next((r for r in data.get("local_results") or [] if _near(r, lat, lon)), None)
                if not cand:
                    return {"found": False, "reason": "not_matched"}
                place = cand
                if not place.get("popular_times") and cand.get("place_id"):
                    detail = (await client.get(SERPAPI_URL, params={**base, "place_id": cand["place_id"]})).json()
                    place = detail.get("place_results") or place
    except Exception as e:
        return {"found": False, "reason": f"error: {type(e).__name__}"}

    pt = place.get("popular_times")
    if not pt:
        return {"found": False, "reason": "no_popular_times"}
    return {"found": True, **parse_popular_times(pt)}
