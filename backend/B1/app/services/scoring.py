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


# ── 장소 카테고리 정규화 ─────────────────────────────────────────
# LLM·카카오가 주는 자유 형식 카테고리("음식점 > 카페", "이탈리안 레스토랑")를
# CATEGORY_TAG_MATCH의 키로 맞춘다. 앞쪽 규칙이 우선한다.
_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("카페",     ("카페", "디저트", "베이커리", "커피", "찻집")),
    ("바",       ("바", "술집", "펍", "와인", "칵테일", "포차", "호프")),
    ("레스토랑", ("레스토랑", "양식", "이탈리안", "프렌치", "파인다이닝", "스테이크")),
    ("식당",     ("식당", "음식점", "한식", "일식", "중식", "맛집", "분식", "고기", "브런치")),
    ("전시",     ("전시", "미술관", "갤러리", "박물관")),
    ("공연",     ("공연", "뮤지컬", "콘서트", "연극", "극장", "영화")),
    ("체험",     ("체험", "공방", "클래스", "방탈출", "팝업")),
]


def normalize_category(raw: str | None) -> str:
    text = (raw or "").replace(" ", "")
    for category, keywords in _CATEGORY_RULES:
        if any(k in text for k in keywords):
            return category
    return "기타"


# ── 공정성 기반 코스 선택 (논문 식 (2)~(5)) ──────────────────────
#   J(C)  = (S̄_A(C) + S̄_B(C)) / 2 − λ · G(C)
#   C*    = argmax_{C ∈ 𝒞, V(C) = 0} J(C)
#   V(C)  : 방문 시각에 영업하지 않는 장소 수. 모든 후보가 V>0이면 V가 가장 작은 후보 중 J 최대.

def course_scores(categories: list[str], tags_a: list[str], tags_b: list[str], lam: float) -> dict:
    """코스(장소 카테고리 목록)의 평균 만족도·격차·목적함수 J를 계산"""
    cats = [normalize_category(c) for c in categories]
    scores_a = [satisfaction(tags_a, c) for c in cats]
    scores_b = [satisfaction(tags_b, c) for c in cats]
    m = course_metrics(scores_a, scores_b)
    if m["fairness_gap"] is None:
        return {**m, "avg_satisfaction": None, "objective": None}
    avg = (m["avg_satisfaction_a"] + m["avg_satisfaction_b"]) / 2
    return {**m, "avg_satisfaction": round(avg, 2), "objective": round(avg - lam * m["fairness_gap"], 2)}


def select_fair_course(candidates: list[dict], tags_a: list[str], tags_b: list[str], lam: float = 1.0) -> tuple[int, list[dict]]:
    """후보 코스 중 C*의 인덱스와 후보별 점수를 반환.

    candidates: [{"categories": [...], "violations": int}, ...]
    lam = 0 이면 평균 만족도만으로 선택 (공정성 미고려 기준선).
    """
    if not candidates:
        raise ValueError("candidates is empty")
    scored = []
    for i, cand in enumerate(candidates):
        s = course_scores(cand.get("categories", []), tags_a, tags_b, lam)
        scored.append({"index": i, "violations": int(cand.get("violations", 0)), **s})
    valid = [s for s in scored if s["objective"] is not None] or scored
    min_v = min(s["violations"] for s in valid)
    pool = [s for s in valid if s["violations"] == min_v]
    # 동점이면 앞선 후보(에이전트가 먼저 제시한 안)를 유지
    best = max(pool, key=lambda s: (s["objective"] if s["objective"] is not None else float("-inf"), -s["index"]))
    return best["index"], scored
