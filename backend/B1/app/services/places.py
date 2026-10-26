import os
import httpx

B2_URL = os.getenv("B2_URL", "http://localhost:8001")


def _clean_area(area: str) -> str:
    return area.replace("공원", "").replace("입구", "").replace("역", "").strip()


async def fetch_places(category: str, area: str, size: int = 5) -> list[dict]:
    """B2 API에서 실제 장소 데이터 가져오기 (없으면 실시간 수집 후 재조회)"""
    area = _clean_area(area)
    params = {"category": category, "area": area, "size": size}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            places = (await client.get(f"{B2_URL}/places", params=params)).json().get("places", [])
            if not places:
                await client.post(
                    f"{B2_URL}/places/collect",
                    json={"query": f"{area} {category}", "crawl_supplement": False},
                )
                places = (await client.get(f"{B2_URL}/places", params=params)).json().get("places", [])
            return places
    except Exception:
        return []
