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

    async def geocode(q):
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

    a = client.post("/course/generate", json=req).json()["courses"][0]
    assert [p["name"] for p in a["places"]] == ["카페4", "바2"]
    assert called["selected_event"]["name"] == "전시X" and called["verify"] is True


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
