"""취향 태그 ↔ 장소 카테고리 매칭 기반 만족도/공정성 계산

S_u(p) = clip(BASE + STEP × |T_u ∩ M(c_p)|, MIN, MAX)
  T_u    : 사용자 u의 취향 태그 집합
  M(c_p) : 장소 p의 카테고리 c_p 에 매칭되는 태그 집합
"""

BASE_SCORE = 60
STEP       = 10
MIN_SCORE  = 55
MAX_SCORE  = 95

CATEGORY_TAG_MATCH: dict[str, list[str]] = {
    "카페":     ["감성 카페", "여유로운 카페", "디저트 맛집", "브런치", "조용한 분위기"],
    "식당":     ["맛집 탐방", "디저트 맛집", "브런치", "활기찬 분위기"],
    "레스토랑": ["맛집 탐방", "로맨틱", "고급스러운", "조용한 분위기"],
    "바":       ["활기찬 분위기", "핫플 방문", "캐주얼"],
    "전시":     ["전시·문화", "조용한 분위기", "감성 카페", "로맨틱"],
    "공연":     ["전시·문화", "활기찬 분위기", "활동적인 코스"],
    "체험":     ["활동적인 코스", "핫플 방문"],
    "기타":     ["핫플 방문", "산책·자연"],
}


def satisfaction(tags: list[str], category: str) -> int:
    matches = CATEGORY_TAG_MATCH.get(category, [])
    hits = sum(1 for tag in tags if tag in matches)
    return min(MAX_SCORE, max(MIN_SCORE, BASE_SCORE + STEP * hits))


def course_metrics(scores_a: list[int], scores_b: list[int]) -> dict:
    """코스 단위 평균 만족도와 두 사람 간 격차(공정성 지표)"""
    if not scores_a or not scores_b:
        return {"avg_satisfaction_a": None, "avg_satisfaction_b": None, "fairness_gap": None}
    avg_a = sum(scores_a) / len(scores_a)
    avg_b = sum(scores_b) / len(scores_b)
    return {
        "avg_satisfaction_a": round(avg_a, 1),
        "avg_satisfaction_b": round(avg_b, 1),
        "fairness_gap":       round(abs(avg_a - avg_b), 1),
    }
