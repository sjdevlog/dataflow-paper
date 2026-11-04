"""POST /course/generate — 외부 API(기상청·B2·카카오·AI)를 목으로 대체해 라우터 로직만 검증

실행: backend/B1 에서 `python -m pytest tests`
"""
import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/dateflow_test.db")

import pytest
from fastapi.testclient import TestClient

import app.routers.course as course
from app.main import app
from app.services.scoring import satisfaction, course_metrics

REQUEST = {
    "user_id": "t_A", "region": "성수", "lat": 37.54, "lon": 127.05,
    "budget_max": 80000, "date": "2026-11-01",
    "tags_a": ["전시·문화", "감성 카페"], "tags_b": ["맛집 탐방"],
}


@pytest.fixture
def client(monkeypatch):
    async def weather(*a, **k):
        return {"description": "맑음", "temperature": 20}

    async def places(category, area, size=5, lat=None, lon=None):
        return [{"name": f"{area} {category}{i}", "latitude": 37.5 + i * 0.001, "longitude": 127.0} for i in range(2)]

    async def geocode(q, near=None):
        return 37.5, 127.0

    async def transport(*a):
        return 5, 12

    monkeypatch.setattr(course, "get_weather", weather)
    monkeypatch.setattr(course, "fetch_places", places)
    monkeypatch.setattr(course, "geocode", geocode)
    monkeypatch.setattr(course, "transport_minutes", transport)
    return TestClient(app)


def test_ai_success_builds_both_courses(client, monkeypatch):
    # 리팩터링 전에는 AI 성공 시 B안에서 make_place NameError → 500
    events = [{"name": "전시A", "category": "전시"}]
    gen = {"courses": [{"places": [
        {"name": "전시A", "category": "전시", "time": "14:00", "open_status": "open"},
        {"name": "카페B", "category": "음식점 > 카페", "time": "16:00", "open_status": "open"},
    ], "violations": 0}]}
    monkeypatch.setattr(course.ai_bridge, "recommend_events", lambda **k: events)
    monkeypatch.setattr(course.ai_bridge, "generate_course", lambda **k: gen)

    res = client.post("/course/generate", json=REQUEST)
    assert res.status_code == 200
    a, b = res.json()["courses"]
    assert a["source"] == "ai" and [p["name"] for p in a["places"]] == ["전시A", "카페B"]
    assert a["places"][1]["category"] == "카페" and a["violations"] == 0
    assert b["source"] == "b2" and len(b["places"]) == 3


def test_ai_picks_fair_course_and_skips_closed(client, monkeypatch):
    # 후보 0: 영업 위반 있음 / 후보 1: A만 만족 / 후보 2: 두 사람 균형 → λ=1이면 2번 선택
    req = {**REQUEST, "tags_a": ["감성 카페", "조용한 분위기"], "tags_b": ["활기찬 분위기", "핫플 방문"],
           "selected_event": {"name": "전시X", "category": "전시"}}
    def place(name, cat, status="open"):
        return {"name": name, "category": cat, "time": "15:00", "open_status": status}
    gen = {"courses": [
        {"places": [place("바1", "바", "closed"), place("카페1", "카페")], "violations": 1},
        {"places": [place("카페2", "카페"), place("카페3", "카페")], "violations": 0},
        {"places": [place("카페4", "카페"), place("바2", "바")], "violations": 0},
    ]}
    called = {}
    def fake_gen(**k):
        called.update(k)
        return gen
    monkeypatch.setattr(course.ai_bridge, "recommend_events", lambda **k: (_ for _ in ()).throw(AssertionError("이벤트를 받았으면 Pipeline 1 호출 안 함")))
    monkeypatch.setattr(course.ai_bridge, "generate_course", fake_gen)

    a, b = client.post("/course/generate", json=req).json()["courses"]
    assert [p["name"] for p in a["places"]] == ["카페4", "바2"]
    assert called["selected_event"]["name"] == "전시X" and called["verify"] is True
    # 고른 이벤트는 B안에도 두 번째 장소로 들어간다
    assert b["places"][1]["name"] == "전시X" and b["places"][1]["category"] == "전시"


def test_ai_failure_falls_back_to_b2(client, monkeypatch):
    monkeypatch.setattr(course.ai_bridge, "recommend_events", lambda **k: [])
    monkeypatch.setattr(course.ai_bridge, "generate_course", lambda **k: {"courses": [], "error": "x"})
    a, _ = client.post("/course/generate", json=REQUEST).json()["courses"]
    assert a["source"] == "b2"
    assert [p["category"] for p in a["places"]] == ["카페", "식당", "바"]


def test_request_budget_and_tags_are_used(client, monkeypatch):
    monkeypatch.setattr(course.ai_bridge, "recommend_events", lambda **k: [])
    data = client.post("/course/generate", json=REQUEST).json()
    assert data["budget_max"] == 80000
    cafe = data["courses"][0]["places"][0]
    assert cafe["price"] == 12000                       # 15% 배분
    assert cafe["satisfaction_a"] == satisfaction(REQUEST["tags_a"], "카페")
    assert cafe["walk_minutes_to_next"] == 12


def test_budget_below_minimum_rejected(client):
    assert client.post("/course/generate", json={**REQUEST, "budget_max": 5000}).status_code == 400


def test_scoring():
    assert satisfaction(["감성 카페", "브런치"], "카페") == 80
    assert satisfaction([], "바") == 60
    assert satisfaction(["감성 카페"] * 10, "카페") == 95   # 상한
    assert course_metrics([80, 70], [60, 90]) == {"avg_satisfaction_a": 75.0, "avg_satisfaction_b": 75.0, "fairness_gap": 0.0}
    assert course_metrics([], [60])["fairness_gap"] is None


def test_normalize_category():
    from app.services.scoring import normalize_category
    assert normalize_category("음식점 > 카페 > 커피전문점") == "카페"
    assert normalize_category("이탈리안 레스토랑") == "레스토랑"
    assert normalize_category("와인바") == "바"
    assert normalize_category("미술관") == "전시"
    assert normalize_category("한강공원") == "기타"


def test_select_fair_course_prefers_small_gap():
    from app.services.scoring import select_fair_course
    tags_a, tags_b = ["감성 카페", "조용한 분위기"], ["활기찬 분위기", "핫플 방문"]
    cands = [
        {"categories": ["카페", "카페", "카페"], "violations": 0},   # A만 만족 (평균 높음, 격차 큼)
        {"categories": ["카페", "바", "전시"], "violations": 0},     # 균형
    ]
    i0, _ = select_fair_course(cands, tags_a, tags_b, lam=0)
    i1, scored = select_fair_course(cands, tags_a, tags_b, lam=1)
    assert i0 == 0 and i1 == 1
    assert scored[1]["fairness_gap"] < scored[0]["fairness_gap"]


def test_select_fair_course_avoids_closed_places():
    from app.services.scoring import select_fair_course
    cands = [
        {"categories": ["카페", "바"], "violations": 1},
        {"categories": ["기타", "기타"], "violations": 0},
    ]
    idx, _ = select_fair_course(cands, ["감성 카페"], ["핫플 방문"], lam=1)
    assert idx == 1


# ── 메인 이벤트 추천 (/course/events) ──────────────────────────────
import app.services.events as ev_svc

EV_REQ = {"region": "양평", "lat": 37.49, "lon": 127.49, "date": "2026-11-07",
          "tags_a": ["전시·문화"], "tags_b": ["산책·자연"]}


def _doc(name, cat="문화,예술 > 전시관"):
    return {"place_name": name, "category_name": cat, "address_name": "경기 양평군", "x": "127.49", "y": "37.49",
            "place_url": f"http://place.map.kakao.com/{abs(hash(name)) % 1000}"}


def test_events_keeps_only_ai_events_found_nearby(client, monkeypatch):
    # AI가 3개 추천 → 그중 '서울 콘서트홀'은 양평 반경에서 검색 안 됨 → 제외
    ai = [{"name": "양평 미술관", "category": "전시", "reason": "조용한 전시"},
          {"name": "서울 콘서트홀", "category": "공연"},
          {"name": "두물머리 공방", "category": "체험"}]
    monkeypatch.setattr(ev_svc.ai_bridge, "recommend_events", lambda **k: ai)
    near = {"양평 미술관": [_doc("양평 미술관")], "두물머리 공방": [_doc("두물머리 공방", "체험 > 공방")]}

    async def fake_kakao(client_, query, lat, lon, size):
        return near.get(query, [])
    monkeypatch.setattr(ev_svc, "_kakao", fake_kakao)

    data = client.post("/course/events", json=EV_REQ).json()
    names = [e["name"] for e in data["events"]]
    assert "서울 콘서트홀" not in names
    assert names[:2] == ["양평 미술관", "두물머리 공방"]
    assert data["events"][0]["source"] == "ai" and data["events"][0]["reason"] == "조용한 전시"


def test_events_falls_back_to_kakao_and_never_pads(client, monkeypatch):
    # AI 실패 + 반경 안에 갤러리 1곳뿐 → 1개만 반환 (억지로 6개 채우지 않음)
    monkeypatch.setattr(ev_svc.ai_bridge, "recommend_events", lambda **k: [])

    async def fake_kakao(client_, query, lat, lon, size):
        return [_doc("양평 갤러리")] if query == "갤러리" else []
    monkeypatch.setattr(ev_svc, "_kakao", fake_kakao)

    data = client.post("/course/events", json=EV_REQ).json()
    assert [e["name"] for e in data["events"]] == ["양평 갤러리"]
    assert data["source"] == "kakao"


def test_events_empty_region_gives_message(client, monkeypatch):
    monkeypatch.setattr(ev_svc.ai_bridge, "recommend_events", lambda **k: [])

    async def fake_kakao(*a, **k):
        return []
    monkeypatch.setattr(ev_svc, "_kakao", fake_kakao)
    data = client.post("/course/events", json=EV_REQ).json()
    assert data["events"] == [] and data["source"] == "none" and "찾지 못했어요" in data["message"]


def test_events_more_excludes_shown(client, monkeypatch):
    async def fake_kakao(client_, query, lat, lon, size):
        return [_doc(f"{query} A"), _doc(f"{query} B")]
    monkeypatch.setattr(ev_svc, "_kakao", fake_kakao)
    data = client.post("/course/events", json={**EV_REQ, "more": True, "exclude": ["전시 A"]}).json()
    names = [e["name"] for e in data["events"]]
    assert len(names) == 3 and "전시 A" not in names


def test_no_event_uses_walk_as_main(client, monkeypatch):
    called = {}
    def fake_gen(**k):
        called.update(k)
        return {"courses": []}
    monkeypatch.setattr(course.ai_bridge, "recommend_events", lambda **k: (_ for _ in ()).throw(AssertionError("호출 안 함")))
    monkeypatch.setattr(course.ai_bridge, "generate_course", fake_gen)
    client.post("/course/generate", json={**REQUEST, "no_event": True})
    assert called["selected_event"]["category"] == "산책"


# ── 다른 장소 추천 (/course/alternatives) ──────────────────────────
import app.services.alternatives as alt_svc


def test_alternatives_skip_closed_and_rank_by_fairness(client, monkeypatch):
    docs = [_doc("코스에 있는 카페", "음식점 > 카페"), _doc("닫은 카페", "음식점 > 카페"),
            _doc("와인바 겸 카페", "음식점 > 술집 > 와인바"), _doc("조용한 카페", "음식점 > 카페")]

    class FakeRes:
        def json(self):
            return {"documents": docs}

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k): return FakeRes()

    monkeypatch.setattr(alt_svc, "KAKAO_REST_API_KEY", "test")
    monkeypatch.setattr(alt_svc.httpx, "AsyncClient", lambda **k: FakeClient())
    monkeypatch.setattr(alt_svc, "_open_status", lambda name, d, t: "closed" if name == "닫은 카페" else "open")

    req = {"name": "원래 카페", "category": "카페", "lat": 37.54, "lon": 127.05, "time": "15:00", "date": "2026-11-07",
           "tags_a": ["감성 카페", "조용한 분위기"], "tags_b": ["활기찬 분위기", "핫플 방문"],
           "exclude": ["코스에 있는 카페"], "prev": {"lat": 37.541, "lon": 127.05}}
    data = client.post("/course/alternatives", json=req).json()
    names = [a["name"] for a in data["alternatives"]]
    assert "닫은 카페" not in names and "코스에 있는 카페" not in names
    # 바(B 취향 2개 일치 vs A 0개) 와 카페(A 2개 vs B 0개)는 격차가 같으면 평균으로 비교 → 둘 다 후보
    assert set(names) == {"와인바 겸 카페", "조용한 카페"}
    assert data["alternatives"][0]["walk_from_prev"] is not None


# ── 구글 장소 상세 (/course/place-details) ─────────────────────────
import app.services.google_places as gp

G_PLACE = {
    "displayName": {"text": "보나리체타"}, "location": {"latitude": 37.3381, "longitude": 127.2662},
    "rating": 5.0, "userRatingCount": 166, "primaryTypeDisplayName": {"text": "이탈리아 음식점"},
    "priceRange": {"startPrice": {"currencyCode": "KRW", "units": "20000"}, "endPrice": {"currencyCode": "KRW", "units": "30000"}},
    "currentOpeningHours": {"openNow": True, "weekdayDescriptions": ["월요일: 11:00~22:00"]},
    "googleMapsUri": "https://maps.google.com/?cid=1",
    "reviews": [{"rating": 5, "relativePublishTimeDescription": "3개월 전", "text": {"text": "분위기 좋아요"},
                 "authorAttribution": {"displayName": "김지윤", "uri": "u", "photoUri": "p"}}],
    "photos": [{"name": "places/x/photos/1", "authorAttributions": [{"displayName": "SH L", "uri": "u2"}]}],
}


def test_same_place_requires_nearby_and_similar_name():
    assert gp.same_place("보나리체타", 37.3381, 127.2662, G_PLACE)
    assert gp.same_place("보나리체타 외대점", 37.3382, 127.2663, G_PLACE)
    assert not gp.same_place("전혀다른식당", 37.3381, 127.2662, G_PLACE)       # 이름 다름
    assert not gp.same_place("보나리체타", 37.5665, 126.9780, G_PLACE)          # 서울시청 — 멀리 떨어짐


def test_place_details_parses_google_fields(client, monkeypatch):
    class FakeRes:
        def __init__(self, data): self._d = data
        def json(self): return self._d

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return FakeRes({"places": [G_PLACE]})
        async def get(self, *a, **k): return FakeRes({"photoUri": "https://lh3.googleusercontent.com/x"})

    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "test")
    monkeypatch.setattr(gp.httpx, "AsyncClient", lambda **k: FakeClient())
    d = client.post("/course/place-details", json={"name": "보나리체타", "lat": 37.3381, "lon": 127.2662}).json()
    assert d["found"] and d["rating"] == 5.0 and d["rating_count"] == 166
    assert (d["price_min"], d["price_max"]) == (20000, 30000) and d["type_name"] == "이탈리아 음식점"
    assert d["reviews"][0]["author"] == "김지윤" and d["reviews"][0]["relative_time"] == "3개월 전"
    assert d["photos"][0]["url"].startswith("https://") and "key" not in d["photos"][0]["url"]


def test_place_details_without_key(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    d = client.post("/course/place-details", json={"name": "x", "lat": 37.5, "lon": 127.0}).json()
    assert d == {"found": False, "reason": "no_key"}


# ── 시간대별 혼잡도 (/course/crowd) ───────────────────────────────
import app.services.crowd as crowd_svc


def test_parse_hour_formats():
    assert crowd_svc.parse_hour("8 PM") == 20 and crowd_svc.parse_hour("8 PM") == 20
    assert crowd_svc.parse_hour("오후 8시") == 20 and crowd_svc.parse_hour("오전 12시") == 0
    assert crowd_svc.parse_hour("12 PM") == 12 and crowd_svc.parse_hour("abc") is None


def test_crowd_matches_nearby_place(client, monkeypatch):
    pt = {"graph_results": {"saturday": [{"time": "오후 7시", "busyness_score": 60, "info": "보통 조금 붐빔"},
                                         {"time": "오후 6시", "busyness_score": 40}]}}
    calls = []

    class FakeRes:
        def __init__(self, d): self._d = d
        def json(self): return self._d

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params):
            calls.append(params)
            if "place_id" in params:
                return FakeRes({"place_results": {"popular_times": pt, "gps_coordinates": {"latitude": 37.5, "longitude": 127.0}}})
            return FakeRes({"local_results": [
                {"place_id": "far", "gps_coordinates": {"latitude": 37.6, "longitude": 127.0}},
                {"place_id": "near", "gps_coordinates": {"latitude": 37.5003, "longitude": 127.0}}]})

    monkeypatch.setenv("SERPAPI_API_KEY", "test")
    monkeypatch.setattr(crowd_svc.httpx, "AsyncClient", lambda **k: FakeClient())
    d = client.post("/course/crowd", json={"name": "카페", "lat": 37.5, "lon": 127.0}).json()
    assert d["found"] and [r["hour"] for r in d["days"]["saturday"]] == [18, 19]
    assert calls[-1]["place_id"] == "near"


def test_crowd_fetches_detail_when_search_place_lacks_popular_times(client, monkeypatch):
    pt = {"graph_results": {"monday": [{"time": "12 PM", "busyness_score": 30}]}}
    calls = []

    class FakeRes:
        def __init__(self, d): self._d = d
        def json(self): return self._d

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params):
            calls.append(params)
            loc = {"latitude": 37.5, "longitude": 127.0}
            if "place_id" in params:
                return FakeRes({"place_results": {"popular_times": pt, "gps_coordinates": loc}})
            return FakeRes({"place_results": {"place_id": "p1", "gps_coordinates": loc}})

    monkeypatch.setenv("SERPAPI_API_KEY", "test")
    monkeypatch.setattr(crowd_svc.httpx, "AsyncClient", lambda **k: FakeClient())
    d = client.post("/course/crowd", json={"name": "바", "lat": 37.5, "lon": 127.0}).json()
    assert d["found"] and d["days"]["monday"][0]["hour"] == 12
    assert calls[-1]["place_id"] == "p1"


def test_crowd_without_key(client, monkeypatch):
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    assert client.post("/course/crowd", json={"name": "x", "lat": 1, "lon": 1}).json()["reason"] == "no_key"


# ── 좌표 조회: 지역 반경 우선 ─────────────────────────────────────────────
def test_geocode_searches_near_region_first(monkeypatch):
    import asyncio
    from app.services import kakao

    calls = []

    class Resp:
        def __init__(self, docs): self._docs = docs
        def json(self): return {"documents": self._docs}

    class Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, headers=None, params=None):
            calls.append(params)
            return Resp([{"y": "37.54", "x": "127.04"}] if "x" in params else [])

    monkeypatch.setattr(kakao, "KAKAO_REST_API_KEY", "test")
    monkeypatch.setattr(kakao.httpx, "AsyncClient", Client)
    lat, lon = asyncio.run(kakao.geocode("차만다 성수", near=(37.5444, 127.0374)))
    assert (lat, lon) == (37.54, 127.04)
    assert calls[0]["radius"] == kakao.GEOCODE_RADIUS_M and calls[0]["query"] == "차만다 성수"


# ── 코스 이름: 반영된 취향 태그로 짓기 ───────────────────────────────
def test_course_title_uses_matched_tags_and_avoids_duplicates():
    from app.services.scoring import course_title
    a_tags = ["조용한 분위기", "전시·문화", "감성 카페"]
    b_tags = ["활기찬 분위기", "맛집 탐방"]
    t1 = course_title(["식당", "전시", "식당"], a_tags, b_tags)
    assert t1 == "맛집 탐방 · 전시·문화 코스"          # 반대 분위기 태그 둘을 붙이지 않음
    t2 = course_title(["식당", "전시", "식당"], a_tags, b_tags, avoid=t1)
    assert t2 != t1
    assert course_title(["기타"], [], [], fallback="추천 코스 1") == "추천 코스 1"


def test_generate_titles_follow_tags(client, monkeypatch):
    monkeypatch.setattr(course.ai_bridge, "recommend_events", lambda **k: [])
    monkeypatch.setattr(course.ai_bridge, "generate_course", lambda **k: {"courses": []})
    a, b = client.post("/course/generate", json=REQUEST).json()["courses"]
    assert "차분한" not in a["title"] and "액티브" not in b["title"]
    assert a["title"] != b["title"]


# ── 두 사람 이름 저장 ───────────────────────────────────────────────
def test_profile_names_saved_per_account(client):
    import uuid
    u = f"nm{uuid.uuid4().hex[:8]}"
    tok = client.post("/auth/register", json={"username": u, "password": "Abcd1234!", "nickname": "수정"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/auth/profile", headers=h).json() == {"my_name": "수정", "partner_name": ""}
    assert client.put("/auth/profile", headers=h, json={"my_name": " 수정 ", "partner_name": "민수"}).status_code == 200
    assert client.get("/auth/profile", headers=h).json() == {"my_name": "수정", "partner_name": "민수"}
    assert client.get("/auth/profile").status_code == 401
    assert client.put("/auth/profile", headers=h, json={"my_name": "가" * 21}).status_code == 422
