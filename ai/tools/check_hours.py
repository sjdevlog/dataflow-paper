"""카카오맵 페이지를 Playwright로 크롤링해서 영업시간을 확인하는 툴.

설계:
- 카카오 Local API로 place_url 조회 → Playwright로 페이지 로딩 → 영업시간 텍스트 추출 (_scrape_hours)
- 판정·캐시는 tools/hours_judge.py
"""

import os
import re
import time
from typing import Optional

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

from tools.logger import log_tool

load_dotenv()

# 캐시(30분 TTL)와 영업 여부 판정은 tools/hours_judge.py 에 있다.

# 카카오맵 영업시간 셀렉터 후보 (페이지 구조 변경 대응)
KAKAO_HOURS_SELECTORS = [
    ".openhour_wrap",
    ".openhour_list",
    ".OpenHour",
    "[class*='OpenHour']",
    "[class*='openhour']",
    "[class*='operating']",
    ".location_detail",
]


def _get_kakao_url(place_name: str) -> Optional[str]:
    """카카오 Local API로 장소 검색 → place_url 반환."""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_KEY')}"}
    params = {"query": place_name, "size": 1}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        items = res.json().get("documents", [])
        if not items:
            return None
        return items[0].get("place_url")
    except Exception:
        return None


DAY_HOURS_PATTERN = re.compile(
    r"([월화수목금토일])\(([0-9/]+)\)\s*([0-9:]+|영업종료|휴무)\s*(?:~\s*([0-9:]+|영업종료|휴무))?"
)

EXPAND_TRIGGERS = [
    "text=영업정보 전체보기",
    "text=펼치기",
    "[aria-label*='펼치기']",
    "[aria-expanded='false']",
    "[class*='unfold']",
    "[class*='Unfold']",
]


def _try_expand(page) -> None:
    """영업시간 섹션의 펼치기 버튼을 시도해본다 (실패해도 무시)."""
    for selector in EXPAND_TRIGGERS:
        try:
            locator = page.locator(selector).first
            if locator.is_visible(timeout=500):
                locator.click(timeout=1000)
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def _scrape_hours(place_url: str) -> str:
    """Playwright로 카카오맵 페이지에서 영업시간 추출."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(place_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)

            _try_expand(page)

            body_text = page.locator("body").inner_text()

            # 1차 시도: 요일별 시간 패턴 추출 (가장 정확)
            matches = DAY_HOURS_PATTERN.findall(body_text)
            if matches:
                lines = []
                for day, date, open_t, close_t in matches:
                    if close_t:
                        lines.append(f"{day}({date}) {open_t} ~ {close_t}")
                    else:
                        lines.append(f"{day}({date}) {open_t}")
                # 영업 상태 헤더 함께 잡기
                status_match = re.search(r"영업\s*[중마감](?:[^\n]{0,30})", body_text)
                status = status_match.group(0).strip() if status_match else ""
                header = f"[{status}]\n" if status else ""
                return header + "\n".join(lines)

            # 2차 시도: 기존 셀렉터들
            for selector in KAKAO_HOURS_SELECTORS:
                try:
                    el = page.query_selector(selector)
                    if el:
                        text = el.inner_text().strip()
                        if text and ("영업" in text or ":" in text):
                            return text
                except Exception:
                    continue

            # 3차 폴백: "영업시간" 키워드 근처 텍스트
            match = re.search(r"영업시간[^\n]{0,200}", body_text)
            if match:
                return match.group(0).strip()

            return "영업시간 정보를 페이지에서 찾을 수 없음"
        finally:
            browser.close()


@tool
@log_tool
def check_hours(place_name: str, visit_date: str = "", visit_time: str = "") -> str:
    """장소가 방문 예정 날짜·시각에 영업 중인지 확인합니다.

    카카오맵 페이지에서 영업시간을 읽어 판정합니다.
    같은 장소를 30분 안에 다시 조회하면 캐시를 사용합니다.

    Args:
        place_name: 확인할 장소 이름 (예: "어니언 성수")
        visit_date: 방문 날짜 YYYY-MM-DD (예: "2026-11-08")
        visit_time: 방문 시각 HH:MM (예: "15:30")

    Returns:
        판정(open / closed / unknown), 영업시간 원문, 출처, 링크.
    """
    from tools.hours_judge import get_hours, is_open_at, parse_visit

    info, hit = get_hours(place_name)
    when = parse_visit(visit_date, visit_time)
    verdict = is_open_at(info, when) if when else "unknown"
    lines = [
        f"[{place_name}]{' (캐시)' if hit else ''}",
        f"판정: {verdict}" + ("" if when else " (방문 날짜·시각을 YYYY-MM-DD, HH:MM으로 주면 판정 가능)"),
        f"출처: {info.source}",
    ]
    if info.place_url:
        lines.append(f"링크: {info.place_url}")
    if info.text:
        lines += ["", info.text[:500]]
    if info.error:
        lines.append(f"참고: {info.error}")
    return "\n".join(lines)
