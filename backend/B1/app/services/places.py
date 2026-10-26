import os
import httpx
from app.services.kakao import KAKAO_REST_API_KEY, LOCAL_SEARCH_URL

B2_URL = os.getenv("B2_URL", "http://localhost:8001")

# B2 카테고리 → 카카오 키워드 검색어 (B2 미연결 시 폴백)
KAKAO_QUERY = {"카페": "카페", "레스토랑": "레스토랑", "바/펍": "와인바", "기타": "칵테일바"}


def _clean_area(area: str) -> str:
    return area.replace("공원", "").replace("입구", "").replace("역", "").strip()


async def _fetch_b2(client: httpx.AsyncClient, category: str, area: str, size: int) -> list[dict]:
    params = {"category": category, "area": area, "size": size}
    places = (await client.get(f"{B2_URL}/places", params=params)).json().get("places", [])
    if not places:
        await client.post(f"{B2_URL}/places/collect", json={"query": f"{area} {category}", "crawl_supplement": False})
        places = (await client.get(f"{B2_URL}/places", params=params)).json().get("places", [])
    return places


SEARCH_RADIUS_M = 1500


async def _fetch_kakao(client: httpx.AsyncClient, category: str, area: str, size: int,
                       lat: float | None, lon: float | None) -> list[dict]:
    if not KAKAO_REST_API_KEY:
        return []
    keyword = KAKAO_QUERY.get(category, category)
    # 좌표가 있으면 '지역명 + 키워드' 대신 반경 검색 (지역명이 POI 이름일 때 엉뚱한 결과 방지)
    params = (
        {"query": keyword, "x": lon, "y": lat, "radius": SEARCH_RADIUS_M, "size": size}
        if lat is not None and lon is not None
        else {"query": f"{area} {keyword}", "size": size}
    )
    res = await client.get(LOCAL_SEARCH_URL, headers={"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}, params=params)
    return [
        {"name": d["place_name"], "latitude": d["y"], "longitude": d["x"], "source": "kakao"}
        for d in res.json().get("documents", [])
    ]


async def fetch_places(category: str, area: str, size: int = 5,
                       lat: float | None = None, lon: float | None = None) -> list[dict]:
    """B2 장소 DB 조회 (없으면 실시간 수집) → B2 미연결이면 카카오 키워드 검색으로 폴백"""
    area = _clean_area(area)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            places = await _fetch_b2(client, category, area, size)
            if places:
                return places
        except Exception:
            pass
        try:
            return await _fetch_kakao(client, category, area, size, lat, lon)
        except Exception:
            return []
