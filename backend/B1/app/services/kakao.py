import math
import os
import httpx
from dotenv import load_dotenv

load_dotenv()
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")

LOCAL_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
DIRECTIONS_URL   = "https://apis-navi.kakaomobility.com/v1/directions"

# 평균 보행 속도 (m/min) — 경로 API 실패 시 직선거리 환산용
WALK_METERS_PER_MIN = 67


def _headers() -> dict:
    return {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}


async def geocode(query: str) -> tuple[float | None, float | None]:
    """카카오 키워드 검색으로 (위도, 경도) 조회. 실패 시 (None, None)"""
    if not KAKAO_REST_API_KEY or not query.strip():
        return None, None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(LOCAL_SEARCH_URL, headers=_headers(), params={"query": query, "size": 1})
            docs = res.json().get("documents", [])
            if docs:
                return float(docs[0]["y"]), float(docs[0]["x"])
    except Exception as e:
        print(f">>> 좌표 조회 실패: {query} ({e})")
    return None, None


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _route_minutes(client: httpx.AsyncClient, origin: str, dest: str, priority: str) -> int | None:
    try:
        res = await client.get(
            DIRECTIONS_URL,
            headers=_headers(),
            params={"origin": origin, "destination": dest, "priority": priority},
        )
        return round(res.json()["routes"][0]["summary"]["duration"] / 60)
    except Exception:
        return None


async def transport_minutes(lat1, lon1, lat2, lon2) -> tuple[int | None, int | None]:
    """카카오 모빌리티 API로 (자동차, 도보) 이동 시간(분) 계산. 도보는 직선거리로 폴백"""
    if not all([lat1, lon1, lat2, lon2]):
        return None, None

    origin, dest = f"{lon1},{lat1}", f"{lon2},{lat2}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        car_minutes  = await _route_minutes(client, origin, dest, "RECOMMEND")
        walk_minutes = await _route_minutes(client, origin, dest, "WALK")

    if walk_minutes is None:
        walk_minutes = round(haversine_meters(lat1, lon1, lat2, lon2) / WALK_METERS_PER_MIN)
    return car_minutes, walk_minutes
