import os
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.database import get_db
from app.models.user import UserPreference
from app.schemas.course import CourseRequest, CourseResponse, CourseItem, PlaceItem, EventRequest, EventResponse
from app.services.weather import get_weather
from app.services.kakao import geocode, transport_minutes
from app.services.places import fetch_places
from app.services.scoring import satisfaction, course_metrics, normalize_category, select_fair_course
from app.services import ai_bridge, events as event_service

router = APIRouter()

MIN_BUDGET    = 10000
AI_N_CANDIDATES = 3                                      # Pipeline 2가 만드는 코스 후보 수 |𝒞|
FAIR_LAMBDA     = float(os.getenv("FAIR_LAMBDA", "1.0"))  # 식 (4)의 λ (0이면 공정성 미고려)

# B2 폴백 코스 구성: (카테고리, 후보 인덱스, 시간, 예산 비율)
COURSE_A_PLAN = [("카페", 0, "13:00", 0.15), ("식당", 0, "18:00", 0.50), ("바", 0, "20:00", 0.35)]
COURSE_B_PLAN = [("카페", 1, "13:00", 0.15), ("바", 0, "17:00", 0.35), ("식당", 1, "20:00", 0.50)]

DEFAULT_TAGS_A = ["감성 카페", "로맨틱"]
DEFAULT_TAGS_B = ["맛집 탐방", "활기찬 분위기"]


def resolve_tags(req: CourseRequest, prefs: UserPreference | None) -> tuple[list[str], list[str]]:
    """요청 태그 > DB 저장 취향 > 기본값 순으로 A/B 취향 태그 결정"""
    tags_a = req.tags_a or req.tags_m
    tags_b = req.tags_b or req.tags_f
    if not tags_a and prefs and prefs.mood:
        tags_a = prefs.mood.split(",")
    return tags_a or DEFAULT_TAGS_A, tags_b or DEFAULT_TAGS_B


async def fetch_b2_candidates(region: str, lat: float, lon: float) -> dict[str, list[dict]]:
    near = {"lat": lat, "lon": lon}
    bars = await fetch_places("바/펍", region, **near) or await fetch_places("기타", region, **near)
    return {
        "카페": await fetch_places("카페", region, **near),
        "식당": await fetch_places("레스토랑", region, **near),
        "바":   bars,
    }


def pick(candidates: list[dict], idx: int) -> dict | None:
    if not candidates:
        return None
    return candidates[idx] if idx < len(candidates) else candidates[0]


async def make_place(data: dict | None, category: str, time: str, price: int,
                     region: str, tags_a: list[str], tags_b: list[str]) -> PlaceItem:
    fallback_names = {"카페": "카페", "식당": "레스토랑", "바": "바"}
    name = data["name"] if data else f"{region} {fallback_names.get(category, category)}"
    lat = float(data["latitude"]) if data and data.get("latitude") else None
    lon = float(data["longitude"]) if data and data.get("longitude") else None
    if not lat or not lon:
        lat, lon = await geocode(f"{region} {name}")

    return PlaceItem(
        name=name,
        category=category,
        region=region,
        time=time,
        price=price,
        is_open=True,
        latitude=lat,
        longitude=lon,
        satisfaction_a=satisfaction(tags_a, category),
        satisfaction_b=satisfaction(tags_b, category),
    )


async def fill_transport(places: list[PlaceItem]) -> None:
    for cur, nxt in zip(places, places[1:]):
        car_min, walk_min = await transport_minutes(cur.latitude, cur.longitude, nxt.latitude, nxt.longitude)
        cur.walk_minutes_to_next = walk_min
        cur.car_minutes_to_next = car_min


def build_course(title: str, places: list[PlaceItem], budget: int, source: str,
                 violations: int | None = None) -> CourseItem:
    metrics = course_metrics(
        [p.satisfaction_a for p in places if p.satisfaction_a is not None],
        [p.satisfaction_b for p in places if p.satisfaction_b is not None],
    )
    return CourseItem(title=title, total_price=budget, places=places, source=source,
                      violations=violations, **metrics)


async def ai_course_places(req: CourseRequest, mood: str, weather: dict, budget: int,
                           tags_a: list[str], tags_b: list[str]) -> tuple[list[PlaceItem], int | None]:
    """AI 경로: 메인 이벤트 → Pipeline 2 코스 후보 + 영업시간 더블체크 → 공정성 기반 선택 (논문 식 (5)).

    실패하면 ([], None) — 호출 측에서 B2로 폴백.
    """
    wx = {"condition": weather.get("description", ""), "temp_celsius": weather.get("temperature", 20)}
    event = req.selected_event
    if not event and req.no_event:
        # 근처에 전시·공연이 없을 때: 산책을 중심 일정으로 두고 카페·식당 위주로 구성
        event = {"name": f"{req.region} 산책", "category": "산책"}
    if not event:
        events = await run_in_threadpool(
            ai_bridge.recommend_events,
            natural_language=req.natural_input or f"{req.region}에서 {mood} 데이트",
            weather=wx, area=req.region, visit_date=req.date,
        )
        if not events:
            return [], None
        event = events[0]

    result = await run_in_threadpool(
        ai_bridge.generate_course,
        selected_event=event, weather=wx, visit_date=req.date,
        tags_a=tags_a, tags_b=tags_b, n_courses=AI_N_CANDIDATES, verify=True,
    )
    courses = [c for c in result.get("courses", []) if c.get("places")]
    if not courses:
        return [], None

    candidates = [
        {"categories": [p.get("category", "") for p in c["places"]], "violations": c.get("violations", 0)}
        for c in courses
    ]
    idx, _ = select_fair_course(candidates, tags_a, tags_b, lam=FAIR_LAMBDA)
    chosen = courses[idx]

    raw = chosen["places"]
    places = []
    for p in raw:
        category = normalize_category(p.get("category"))
        lat, lon = await geocode(f"{req.region} {p.get('name', '')}")
        status = p.get("open_status")
        places.append(PlaceItem(
            name=p.get("name", ""),
            category=category,
            region=req.region,
            time=p.get("time", ""),
            price=int(budget / len(raw)),
            is_open=status != "closed",
            open_status=status,
            latitude=lat,
            longitude=lon,
            satisfaction_a=satisfaction(tags_a, category),
            satisfaction_b=satisfaction(tags_b, category),
        ))
    return places, chosen.get("violations")


@router.post("/events", response_model=EventResponse)
async def recommend_events(req: EventRequest):
    """메인 이벤트 추천 — 선택한 지역 반경 안에 실제로 있는 장소만 반환 (개수를 억지로 채우지 않음)"""
    if req.more:
        found = await event_service.search_nearby(req.lat, req.lon, set(req.exclude), event_service.MORE_SIZE)
        msg = "" if found else "주변에서 더 찾을 수 있는 장소가 없어요."
        return EventResponse(events=found, source="kakao" if found else "none", message=msg)

    found, source = await event_service.recommend(req.region, req.lat, req.lon, req.date,
                                                  req.tags_a, req.tags_b, req.natural_input)
    msg = "" if found else f"{req.region} 근처에서 전시·공연·체험 장소를 찾지 못했어요. 카페·식당 중심으로 코스를 짤게요."
    return EventResponse(events=found, source=source, message=msg)


@router.post("/generate", response_model=CourseResponse)
async def generate_course(req: CourseRequest, db: Session = Depends(get_db)):
    if req.budget_max < MIN_BUDGET:
        raise HTTPException(status_code=400, detail="예산은 최소 10,000원 이상이어야 합니다.")

    prefs = db.query(UserPreference).filter(UserPreference.user_id == req.user_id).first()
    mood   = prefs.mood if prefs and prefs.mood else "감성적"
    budget = req.budget_max
    tags_a, tags_b = resolve_tags(req, prefs)

    target_date = req.date.replace("-", "") if req.date else None
    weather = await get_weather(req.lat, req.lon, req.region, target_date)
    wx_desc = weather["description"]

    candidates = await fetch_b2_candidates(req.region, req.lat, req.lon)

    async def b2_places(plan) -> list[PlaceItem]:
        return [
            await make_place(pick(candidates[cat], idx), cat, time, int(budget * ratio), req.region, tags_a, tags_b)
            for cat, idx, time, ratio in plan
        ]

    # A안: AI 추천 성공 시 AI 코스, 실패 시 B2 폴백
    places_a, violations_a = await ai_course_places(req, mood, weather, budget, tags_a, tags_b)
    source_a = "ai" if places_a else "b2"
    if not places_a:
        places_a = await b2_places(COURSE_A_PLAN)
    await fill_transport(places_a)

    # B안: B2 장소로 순서·후보를 바꿔 구성
    places_b = await b2_places(COURSE_B_PLAN)
    await fill_transport(places_b)

    return CourseResponse(
        course_id=str(uuid.uuid4()),
        user_id=req.user_id,
        region=req.region,
        budget_max=budget,
        weather=wx_desc,
        courses=[
            build_course(f"차분한 감성 코스 ({wx_desc})", places_a, budget, source_a, violations_a),
            build_course(f"액티브 핫플 코스 ({wx_desc})", places_b, budget, "b2"),
        ],
    )


@router.get("/{course_id}")
def get_course(course_id: str):
    return {"course_id": course_id, "message": "코스 조회 기능 구현 예정"}
