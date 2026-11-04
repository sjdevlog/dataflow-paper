"""장소 상세 보강 — Google Places API (New)에서 별점·리뷰·사진·가격대·영업 상태를 가져온다.

- 카카오에서 고른 장소와 같은 곳인지 위치(150 m 이내)와 이름으로 확인하고, 아니면 보여주지 않는다.
- 구글 정책: 데이터를 저장·캐시하지 않는다(요청 때마다 조회), 화면에 "Google Maps" 출처와
  리뷰·사진 작성자를 표시한다, 결과를 구글 지도가 아닌 지도 위에 찍지 않는다.
- 혼잡도(인기 시간대)와 가격대 분포는 공식 API에 없어 제공하지 않는다.

환경 변수: GOOGLE_PLACES_API_KEY (Places API (New) 사용 설정된 키, 코드에 넣지 않음)
"""
import asyncio
import difflib
import os
import re

import httpx
from dotenv import load_dotenv

from app.services.kakao import haversine_meters

load_dotenv()

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PHOTO_URL = "https://places.googleapis.com/v1/{name}/media"
FIELD_MASK = ",".join(f"places.{f}" for f in (
    "id", "displayName", "location", "rating", "userRatingCount", "reviews", "priceRange",
    "photos", "primaryTypeDisplayName", "currentOpeningHours", "googleMapsUri",
))
MATCH_RADIUS_M = 150
MAX_PHOTOS = 3
MAX_REVIEWS = 5


def _key() -> str:
    return os.getenv("GOOGLE_PLACES_API_KEY", "")


def _norm(s: str) -> str:
    return re.sub(r"[\s\(\)\[\]·\-_.,]", "", s or "").lower()


def same_place(kakao_name: str, lat: float, lon: float, g: dict) -> bool:
    """카카오 장소와 구글 장소가 같은 곳인지: 150 m 이내 + 이름이 서로 포함되거나 충분히 비슷"""
    loc = g.get("location") or {}
    if "latitude" not in loc:
        return False
    if haversine_meters(lat, lon, loc["latitude"], loc["longitude"]) > MATCH_RADIUS_M:
        return False
    a, b = _norm(kakao_name), _norm((g.get("displayName") or {}).get("text", ""))
    if not a or not b:
        return False
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= 0.5


def _won(money: dict | None) -> int | None:
    if not money or money.get("currencyCode", "KRW") != "KRW":
        return None
    try:
        return int(money.get("units", 0))
    except (TypeError, ValueError):
        return None


def parse_place(g: dict) -> dict:
    pr = g.get("priceRange") or {}
    oh = g.get("currentOpeningHours") or {}
    reviews = []
    for r in (g.get("reviews") or [])[:MAX_REVIEWS]:
        au = r.get("authorAttribution") or {}
        text = (r.get("text") or r.get("originalText") or {}).get("text", "")
        reviews.append({
            "author": au.get("displayName", ""),
            "author_uri": au.get("uri", ""),
            "author_photo": au.get("photoUri", ""),
            "rating": r.get("rating"),
            "relative_time": r.get("relativePublishTimeDescription", ""),
            "text": text,
            "google_maps_uri": r.get("googleMapsUri") or g.get("googleMapsUri", ""),
        })
    return {
        "found": True,
        "name": (g.get("displayName") or {}).get("text", ""),
        "type_name": (g.get("primaryTypeDisplayName") or {}).get("text", ""),
        "rating": g.get("rating"),
        "rating_count": g.get("userRatingCount"),
        "price_min": _won(pr.get("startPrice")),
        "price_max": _won(pr.get("endPrice")),
        "open_now": oh.get("openNow"),
        "next_close_time": oh.get("nextCloseTime"),
        "next_open_time": oh.get("nextOpenTime"),
        "weekday_hours": oh.get("weekdayDescriptions", []),
        "google_maps_uri": g.get("googleMapsUri", ""),
        "reviews": reviews,
        "photos": [],
    }


async def _photo(client: httpx.AsyncClient, photo: dict) -> dict | None:
    """사진 URL만 받아온다 (skipHttpRedirect) — API 키는 서버에만 머문다"""
    try:
        res = await client.get(PHOTO_URL.format(name=photo["name"]),
                               params={"maxWidthPx": 480, "skipHttpRedirect": "true", "key": _key()})
        uri = res.json().get("photoUri")
    except Exception:
        return None
    if not uri:
        return None
    au = (photo.get("authorAttributions") or [{}])[0] if photo.get("authorAttributions") else {}
    return {"url": uri, "author": au.get("displayName", ""), "author_uri": au.get("uri", "")}


async def details(name: str, lat: float, lon: float) -> dict:
    """구글 장소 상세. 키가 없거나 같은 장소를 못 찾으면 {"found": False, "reason": ...}"""
    if not _key():
        return {"found": False, "reason": "no_key"}
    body = {"textQuery": name, "languageCode": "ko", "regionCode": "KR", "pageSize": 3,
            "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lon}, "radius": 300.0}}}
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": _key(), "X-Goog-FieldMask": FIELD_MASK}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(SEARCH_URL, json=body, headers=headers)
            places = res.json().get("places", [])
            match = next((g for g in places if same_place(name, lat, lon, g)), None)
            if not match:
                return {"found": False, "reason": "not_matched"}
            out = parse_place(match)
            photos = await asyncio.gather(*[_photo(client, p) for p in (match.get("photos") or [])[:MAX_PHOTOS]])
            out["photos"] = [p for p in photos if p]
            return out
    except Exception as e:
        return {"found": False, "reason": f"error: {type(e).__name__}"}
