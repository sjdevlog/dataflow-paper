"""영업 여부 판정 — 카카오맵 장소 페이지 크롤링 기반.

check_hours 툴(에이전트용 텍스트)과 코드 단의 최종 검증(check ②)·실험 평가가
같은 판정 로직을 쓰도록 분리한 모듈이다.

판정 결과 status:
  "open"    : 방문 시각에 영업 중
  "closed"  : 휴무, 영업시간 밖, 또는 폐업/임시휴업
  "unknown" : 영업시간 정보를 얻지 못함

필요한 환경 변수 (.env, 코드에 키를 넣지 말 것):
  KAKAO_KEY              카카오 REST API 키
"""

import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

CACHE_TTL = 30 * 60  # 30분 — 논문 2.2.3절

KOR_DAYS = "월화수목금토일"          # datetime.weekday(): 월=0 … 일=6
DAY_LINE = re.compile(
    r"([월화수목금토일])\(([0-9/]+)\)\s*([0-9]{1,2}:[0-9]{2}|휴무|영업종료)\s*(?:~\s*([0-9]{1,2}:[0-9]{2}))?"
)


@dataclass
class HoursInfo:
    """한 장소의 영업시간 원자료 (캐시 단위)"""
    place_name: str
    source: str                                   # "kakao" | "none"
    # 요일(0=월…6=일) → [(open_min, close_min)], close_min이 open_min보다 작으면 자정 넘김
    weekly: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    closed_days: set[int] = field(default_factory=set)
    always_open: bool = False
    text: str = ""
    place_url: str = ""
    error: str = ""


_cache: dict[str, tuple[HoursInfo, float]] = {}


def clear_cache() -> None:
    _cache.clear()


def _hm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


# ── 카카오 ──────────────────────────────────────────────────────

def kakao_lookup(query: str, x: float | None = None, y: float | None = None) -> Optional[dict]:
    """카카오 키워드 검색 1건 (place_name, place_url, x, y, category_name)"""
    key = os.getenv("KAKAO_KEY")
    if not key:
        return None
    params = {"query": query, "size": 1}
    if x is not None and y is not None:
        params.update({"x": x, "y": y, "radius": 5000, "sort": "accuracy"})
    try:
        res = requests.get(KAKAO_SEARCH_URL, headers={"Authorization": f"KakaoAK {key}"}, params=params, timeout=5)
        docs = res.json().get("documents", [])
        return docs[0] if docs else None
    except Exception:
        return None


def parse_kakao_hours(text: str) -> tuple[dict[int, list[tuple[int, int]]], set[int]]:
    """'월(11/3) 11:00 ~ 22:00' / '화(11/4) 휴무' 형식의 줄을 요일별 구간으로 변환"""
    weekly: dict[int, list[tuple[int, int]]] = {}
    closed: set[int] = set()
    for day, _date, open_t, close_t in DAY_LINE.findall(text):
        d = KOR_DAYS.index(day)
        if open_t in ("휴무", "영업종료"):
            closed.add(d)
        elif close_t:
            weekly.setdefault(d, []).append((_hm(open_t), _hm(close_t)))
    return weekly, closed


def _kakao_hours(place_name: str, x=None, y=None) -> HoursInfo:
    doc = kakao_lookup(place_name, x, y)
    if not doc or not doc.get("place_url"):
        return HoursInfo(place_name, "none", error="kakao: 장소를 찾을 수 없음")
    url = doc["place_url"]
    try:
        from tools.check_hours import _scrape_hours   # Playwright 크롤러 재사용
        text = _scrape_hours(url)
    except Exception as e:
        return HoursInfo(place_name, "none", place_url=url, error=f"kakao: {type(e).__name__}: {e}")
    weekly, closed = parse_kakao_hours(text)
    if not weekly and not closed:
        return HoursInfo(place_name, "none", text=text, place_url=url, error="kakao: 영업시간 파싱 실패")
    return HoursInfo(place_name, "kakao", weekly=weekly, closed_days=closed, text=text, place_url=url)


# ── 판정 ────────────────────────────────────────────────────────

def get_hours(place_name: str, lat=None, lng=None, use_cache: bool = True) -> tuple[HoursInfo, bool]:
    """(영업시간 정보, 캐시 적중 여부)"""
    now = time.time()
    if use_cache:
        hit = _cache.get(place_name)
        if hit and now - hit[1] < CACHE_TTL:
            return hit[0], True
    info = _kakao_hours(place_name, lng, lat)
    _cache[place_name] = (info, now)
    return info, False


def is_open_at(info: HoursInfo, when: datetime) -> str:
    if info.always_open:
        return "open"
    if info.source == "none":
        return "unknown"
    minute = when.hour * 60 + when.minute
    d = when.weekday()
    if d in info.closed_days and d not in info.weekly:
        return "closed"
    # 당일 구간 + 전날 자정 넘김 구간
    for start, end in info.weekly.get(d, []):
        if (start <= end and start <= minute < end) or (end < start and minute >= start) or (start == end):
            return "open"
    for start, end in info.weekly.get((d - 1) % 7, []):
        if end < start and minute < end:
            return "open"
    if d not in info.weekly and d not in info.closed_days:
        return "unknown"
    return "closed"


def judge(place_name: str, visit: datetime, lat=None, lng=None, use_cache: bool = True) -> dict:
    info, hit = get_hours(place_name, lat, lng, use_cache)
    return {
        "name": place_name,
        "status": is_open_at(info, visit),
        "source": info.source,
        "cache_hit": hit,
        "hours_text": info.text[:300],
        "place_url": info.place_url,
        "error": info.error,
    }


def parse_visit(visit_date: str, hhmm: str = "") -> Optional[datetime]:
    """'2026-11-08' + '15:30' → datetime. 형식이 틀리면 None"""
    try:
        base = datetime.strptime(visit_date[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return None
    m = re.match(r"\s*(\d{1,2}):(\d{2})", hhmm or "")
    if m:
        base += timedelta(hours=int(m.group(1)), minutes=int(m.group(2)))
    return base
