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
    events = [{"name": "전시A", "category": "전시"}, {"name": "카페B", "category": "카페"}]
    monkeypatch.setattr(course.ai_bridge, "recommend_events", lambda **k: events)

    res = client.post("/course/generate", json=REQUEST)
    assert res.status_code == 200
    a, b = res.json()["courses"]
    assert a["source"] == "ai" and [p["name"] for p in a["places"]] == ["전시A", "카페B"]
    assert b["source"] == "b2" and len(b["places"]) == 3


def test_ai_failure_falls_back_to_b2(client, monkeypatch):
    monkeypatch.setattr(course.ai_bridge, "recommend_events", lambda **k: [])
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
