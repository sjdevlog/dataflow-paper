import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# backend/B1/app/services/ai_bridge.py → repo 루트의 ai/
AI_PATH = Path(os.getenv("AI_PATH", Path(__file__).resolve().parents[4] / "ai"))

if str(AI_PATH) not in sys.path:
    sys.path.insert(0, str(AI_PATH))
load_dotenv(AI_PATH / ".env")


def recommend_events(natural_language: str, weather: dict, area: str, visit_date: str | None = None) -> list[dict]:
    """AI Pipeline 1 호출. 실패하면 빈 리스트 (호출 측에서 B2로 폴백)"""
    try:
        from agents.pipeline1 import recommend_events as _recommend
    except Exception as e:
        print(f">>> AI 모듈 import 실패 ({AI_PATH}): {e}")
        return []

    result = _recommend(natural_language=natural_language, weather=weather, area=area, visit_date=visit_date)
    if result.get("error"):
        print(f">>> AI 추천 실패: {result['error']}")
    return result.get("events", [])


def generate_course(selected_event: dict, weather: dict, visit_date: str | None,
                    tags_a: list[str], tags_b: list[str],
                    n_courses: int = 3, verify: bool = True) -> dict:
    """AI Pipeline 2 호출 (코스 후보 생성 + 영업시간 더블체크).

    실패하면 {"courses": [], "error": ...} — 호출 측에서 B2로 폴백.
    """
    try:
        from agents.pipeline2 import generate_course as _generate
    except Exception as e:
        print(f">>> AI 모듈 import 실패 ({AI_PATH}): {e}")
        return {"courses": [], "error": f"import: {e}"}

    result = _generate(
        selected_event=selected_event,
        weather=weather,
        visit_date=visit_date,
        n_courses=n_courses,
        verify=verify,
        tags_a=tags_a,
        tags_b=tags_b,
    )
    if result.get("error"):
        print(f">>> AI 코스 생성 실패: {result['error']}")
    return result
