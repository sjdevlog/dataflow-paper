"""영업 여부 판정 단위 테스트 (네트워크 없음). 실행: ai/ 에서 python -m pytest tests/test_hours_judge.py"""
from datetime import datetime

from tools.hours_judge import HoursInfo, is_open_at, parse_kakao_hours, parse_visit

KAKAO_TEXT = """[영업 중]
월(11/3) 11:00 ~ 22:00
화(11/4) 휴무
수(11/5) 11:00 ~ 22:00
금(11/7) 18:00 ~ 02:00
"""


def _info(text):
    weekly, closed = parse_kakao_hours(text)
    return HoursInfo("t", "kakao", weekly=weekly, closed_days=closed)


def test_kakao_parse_and_judge():
    info = _info(KAKAO_TEXT)
    assert is_open_at(info, datetime(2026, 11, 2, 13, 0)) == "open"      # 월 13:00
    assert is_open_at(info, datetime(2026, 11, 2, 23, 0)) == "closed"    # 월 23:00
    assert is_open_at(info, datetime(2026, 11, 3, 13, 0)) == "closed"    # 화 휴무
    assert is_open_at(info, datetime(2026, 11, 6, 23, 30)) == "open"     # 금 자정 넘김 구간
    assert is_open_at(info, datetime(2026, 11, 7, 1, 0)) == "open"       # 토 01:00 = 금요일 영업 연장
    assert is_open_at(info, datetime(2026, 11, 8, 13, 0)) == "unknown"   # 일요일 정보 없음


def test_parse_visit():
    assert parse_visit("2026-11-08", "15:30") == datetime(2026, 11, 8, 15, 30)
    assert parse_visit("bad", "15:30") is None
