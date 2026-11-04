"""논문 2.4절 비교 실험 — 시나리오 × 시스템(R / L / LV / LVF) 배치 실행.

실행 (repo 루트에서):
    python experiments/run.py --reps 1 --limit 5      # 시험 실행 (시나리오 5개)
    python experiments/run.py --reps 2                # 전체 실행
    python experiments/run.py --regions 성수,홍대,강남  # 무료 한도용 축소 실행 (36개 시나리오)
    python experiments/run.py --mock --limit 4        # API 키 없이 하네스만 점검
    python experiments/summarize.py                   # 표 8·9 집계

API 키는 ai/.env 에서 읽는다 (GOOGLE_API_KEY = Gemini, KAKAO_KEY).
키를 코드나 결과 파일에 쓰지 않는다.

결과:
    experiments/results/runs.csv     시나리오·반복·시스템별 1행
    experiments/results/lambda.csv   LVF 후보 집합에서 λ별 선택 결과 (표 9)
이미 기록된 (scenario_id, rep) 는 건너뛰므로 중단 후 다시 실행해도 이어서 진행된다.

시스템 정의 (논문 표 5):
    R    카테고리별 카카오 검색 1순위를 고정 시간대에 배치 (영업시간 검증 X, 공정성 X)
    L    Pipeline 2, check_hours 미사용, 코스 1개
    LV   Pipeline 2, 더블체크 사용, 코스 후보 3개 → λ = 0 으로 선택
    LVF  LV와 같은 후보 집합 → λ = FAIR_LAMBDA 로 선택 (제안 방법)
LV와 LVF는 같은 후보에서 선택만 달리하므로, 차이는 공정성 선택의 효과만 반영한다.

평가: 생성이 끝난 뒤 영업시간 캐시를 비우고 모든 추천 장소를 다시 조회해 위반을 판정한다.
"""

import argparse
import csv
import importlib.util
import itertools
import json
import math
import os
import random
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))
os.chdir(ROOT / "ai")                       # ai/.env, ai/logs 기준 경로

from dotenv import load_dotenv               # noqa: E402
load_dotenv(ROOT / "ai" / ".env")

# backend/B1 의 점수 함수(논문 식 (1)~(5))를 그대로 사용 — app 패키지 초기화 없이 파일만 로드
_spec = importlib.util.spec_from_file_location("scoring", ROOT / "backend/B1/app/services/scoring.py")
scoring = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scoring)

RESULTS = Path(__file__).resolve().parent / "results"
FAIR_LAMBDA = float(os.getenv("FAIR_LAMBDA", "1.0"))
LAMBDAS = [0.0, 0.5, 1.0, 2.0]
N_CANDIDATES = 3
WALK_M_PER_MIN = 67                          # 도보 4 km/h

# ── 시나리오 (논문 표 6) ─────────────────────────────────────────
REGIONS = ["성수", "홍대", "강남", "종로", "잠실"]
PAIRS = [  # (id, 겹침 여부, A 태그, B 태그)
    ("P1", "overlap", ["감성 카페", "조용한 분위기"], ["감성 카페", "전시·문화"]),
    ("P2", "overlap", ["맛집 탐방", "활기찬 분위기"], ["맛집 탐방", "핫플 방문"]),
    ("P3", "overlap", ["로맨틱", "고급스러운"], ["로맨틱", "맛집 탐방"]),
    ("P4", "disjoint", ["감성 카페", "조용한 분위기"], ["활기찬 분위기", "핫플 방문"]),
    ("P5", "disjoint", ["전시·문화", "로맨틱"], ["활동적인 코스", "캐주얼"]),
    ("P6", "disjoint", ["브런치", "디저트 맛집"], ["산책·자연", "활동적인 코스"]),
]
R_PLAN = [("카페", "13:00"), ("식당", "18:00"), ("바", "20:00")]   # 백엔드 B2 폴백과 같은 구성


def next_weekday(target: int, start: date) -> date:
    """start 다음 날부터 처음 오는 요일(월=0). 영업시간 판정을 위해 7일 이내 날짜를 쓴다."""
    d = start + timedelta(days=1)
    while d.weekday() != target:
        d += timedelta(days=1)
    return d


def build_scenarios(weekday: str, weekend: str, regions: list[str] = REGIONS) -> list[dict]:
    out = []
    for region, (pid, kind, ta, tb), (day_kind, d) in itertools.product(
            regions, PAIRS, [("weekday", weekday), ("weekend", weekend)]):
        out.append({"scenario_id": f"{region}-{pid}-{day_kind}", "region": region, "pair": pid,
                    "pair_kind": kind, "day_kind": day_kind, "date": d, "tags_a": ta, "tags_b": tb})
    return out


# ── 외부 호출 (실제 / mock) ──────────────────────────────────────

class Real:
    def __init__(self):
        from agents.pipeline1 import recommend_events
        from agents.pipeline2 import generate_course
        from tools import hours_judge
        self._rec, self._gen, self.hj = recommend_events, generate_course, hours_judge

    def main_event(self, sc):
        r = self._rec(natural_language=f"{sc['region']}에서 데이트할 만한 전시나 공연", area=sc["region"],
                      visit_date=sc["date"])
        ev = r.get("events", [])
        self.last_error = r.get("error") or f"이벤트 0개 (parse={r.get('_parse_status', '')})"
        return ev[0] if ev else None

    def generate(self, sc, event, n, verify):
        return self._gen(selected_event=event, visit_date=sc["date"], n_courses=n, verify=verify,
                         tags_a=sc["tags_a"], tags_b=sc["tags_b"])

    def search(self, query):
        doc = self.hj.kakao_lookup(query)
        if not doc:
            return None
        return {"name": doc.get("place_name", query), "category": doc.get("category_name", ""),
                "x": float(doc["x"]), "y": float(doc["y"])}

    def judge(self, name, when):
        return self.hj.judge(name, when)["status"]

    def clear_cache(self):
        self.hj.clear_cache()


class Mock(Real):
    """API 없이 하네스 흐름만 점검 (수치는 의미 없음)"""
    CATS = ["카페", "식당", "바", "전시", "레스토랑", "체험"]

    def __init__(self, seed=0):
        from tools import hours_judge
        self.hj, self.rng = hours_judge, random.Random(seed)

    def main_event(self, sc):
        return {"name": f"{sc['region']} 전시", "category": "전시"}

    def generate(self, sc, event, n, verify):
        courses = []
        for i in range(n):
            places = [{"name": event["name"], "category": "전시", "time": "14:00"}]
            for t in ("16:00", "18:30"):
                places.append({"name": f"{sc['region']} 장소{self.rng.randint(1, 99)}",
                               "category": self.rng.choice(self.CATS), "time": t})
            c = {"places": places}
            if verify:
                c["violations"] = 0
                for p in places:
                    p["open_status"] = "open"
            courses.append(c)
        return {"courses": courses, "timing": {"total_sec": round(self.rng.uniform(20, 60), 1)},
                "tool_calls": {"search_places": 3, "check_hours": 4 if verify else 0},
                "final_check": {"checked": 9, "cache_hits": 9} if verify else None, "_parse_status": "brace_ok"}

    def search(self, query):
        return {"name": query, "category": query.split()[-1], "x": 127.0 + self.rng.random() / 100,
                "y": 37.5 + self.rng.random() / 100}

    def judge(self, name, when):
        return self.rng.choices(["open", "closed", "unknown"], [0.8, 0.1, 0.1])[0]

    def clear_cache(self):
        pass


# ── 지표 ─────────────────────────────────────────────────────────

def haversine_m(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[1], a[0], b[1], b[0]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def evaluate(api, sc, places, region):
    """선택된 코스 1개를 평가 (캐시를 비운 뒤 영업 여부 재조회)"""
    from tools.hours_judge import parse_visit
    statuses, coords, cats = [], [], []
    for p in places:
        when = parse_visit(sc["date"], p.get("time", ""))
        statuses.append(api.judge(p["name"], when) if when else "unknown")
        cats.append(p.get("category", ""))
        if p.get("x") is not None:
            coords.append((p["x"], p["y"]))
        else:
            hit = api.search(f"{region} {p['name']}")
            if hit:
                coords.append((hit["x"], hit["y"]))
    s = scoring.course_scores(cats, sc["tags_a"], sc["tags_b"], lam=0)
    dist = sum(haversine_m(a, b) for a, b in zip(coords, coords[1:]))
    n = len(places)
    return {
        "n_places": n,
        "violations": statuses.count("closed"),
        "unknown": statuses.count("unknown"),
        "violation_rate": round(statuses.count("closed") / n, 4) if n else None,
        "avg_satisfaction": s["avg_satisfaction"],
        "sat_a": s["avg_satisfaction_a"],
        "sat_b": s["avg_satisfaction_b"],
        "fairness_gap": s["fairness_gap"],
        "walk_min_straight": round(dist / WALK_M_PER_MIN, 1),
        "places": json.dumps([p["name"] for p in places], ensure_ascii=False),
    }


def rule_based(api, sc, event):
    places = [{"name": event["name"], "category": event.get("category", "전시"), "time": "15:00"}] if event else []
    for cat, t in R_PLAN:
        hit = api.search(f"{sc['region']} {cat}")
        if hit:
            places.append({"name": hit["name"], "category": cat, "time": t, "x": hit["x"], "y": hit["y"]})
    places.sort(key=lambda p: p["time"])
    return places


def select(courses, sc, lam):
    cands = [{"categories": [p.get("category", "") for p in c["places"]], "violations": c.get("violations", 0)}
             for c in courses]
    idx, scored = scoring.select_fair_course(cands, sc["tags_a"], sc["tags_b"], lam=lam)
    return idx, scored


# ── 실행 ─────────────────────────────────────────────────────────

RUN_FIELDS = ["scenario_id", "rep", "system", "region", "pair", "pair_kind", "day_kind", "date",
              "success", "parse_status", "gen_sec", "tool_calls", "check_hours_calls", "cache_hits",
              "n_places", "violations", "unknown", "violation_rate", "avg_satisfaction", "sat_a", "sat_b",
              "fairness_gap", "walk_min_straight", "places", "error"]
LAMBDA_FIELDS = ["scenario_id", "rep", "lambda", "chosen_index", "avg_satisfaction", "fairness_gap", "violations"]


def append(path, fields, row):
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def done_keys(path):
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by, failed = {}, set()
    for r in rows:
        key = (r["scenario_id"], r["rep"])
        by.setdefault(key, set()).add(r["system"])
        if r["system"] == "ERROR" or r.get("error", "").startswith("no main event"):
            failed.add(key)                      # 메인 이벤트 실패·예외는 다시 실행
    return {k for k, v in by.items() if {"R", "L", "LV", "LVF"} <= v and k not in failed}


def purge(path, key):
    """다시 실행할 (scenario_id, rep)의 이전 행을 지워 중복 집계를 막는다"""
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    keep = [r for r in rows if (r["scenario_id"], r["rep"]) != key]
    if len(keep) != len(rows):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(keep)


def run_one(api, sc, rep, runs_csv, lam_csv):
    base = {k: sc[k] for k in ("scenario_id", "region", "pair", "pair_kind", "day_kind", "date")}
    base["rep"] = rep
    event = api.main_event(sc)
    if not event:
        for system in ("R", "L", "LV", "LVF"):
            append(runs_csv, RUN_FIELDS, {**base, "system": system, "success": 0,
                                          "error": f"no main event: {getattr(api, 'last_error', '')}"[:300]})
        return

    # 생성 단계
    r_places = rule_based(api, sc, event)
    gen_l = api.generate(sc, event, n=1, verify=False)
    gen_v = api.generate(sc, event, n=N_CANDIDATES, verify=True)

    # 평가 단계 — 생성 때 쓴 영업시간 캐시를 비우고 다시 조회
    api.clear_cache()

    def meta(gen):
        tc = gen.get("tool_calls") or {}
        fc = gen.get("final_check") or {}
        return {"parse_status": gen.get("_parse_status", ""), "gen_sec": (gen.get("timing") or {}).get("total_sec"),
                "tool_calls": sum(tc.values()), "check_hours_calls": tc.get("check_hours", 0),
                "cache_hits": fc.get("cache_hits", ""), "error": gen.get("error", "")}

    append(runs_csv, RUN_FIELDS, {**base, "system": "R", "success": int(len(r_places) > 1),
                                  **evaluate(api, sc, r_places, sc["region"])})

    l_courses = [c for c in gen_l.get("courses", []) if c.get("places")]
    row = {**base, "system": "L", **meta(gen_l), "success": int(bool(l_courses))}
    if l_courses:
        row.update(evaluate(api, sc, l_courses[0]["places"], sc["region"]))
    append(runs_csv, RUN_FIELDS, row)

    v_courses = [c for c in gen_v.get("courses", []) if c.get("places")]
    for system, lam in (("LV", 0.0), ("LVF", FAIR_LAMBDA)):
        row = {**base, "system": system, **meta(gen_v), "success": int(bool(v_courses))}
        if v_courses:
            idx, _ = select(v_courses, sc, lam)
            row.update(evaluate(api, sc, v_courses[idx]["places"], sc["region"]))
        append(runs_csv, RUN_FIELDS, row)

    # 표 9 — 같은 후보 집합에서 λ만 바꿔 선택 (만족도·격차는 식 (2)~(3), 위반은 check ② 기준)
    if v_courses:
        for lam in LAMBDAS:
            idx, scored = select(v_courses, sc, lam)
            s = scored[idx]
            append(lam_csv, LAMBDA_FIELDS, {"scenario_id": sc["scenario_id"], "rep": rep, "lambda": lam,
                                            "chosen_index": idx, "avg_satisfaction": s["avg_satisfaction"],
                                            "fairness_gap": s["fairness_gap"], "violations": s["violations"]})


def main():
    today = date.today()
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="앞에서부터 시나리오 N개만")
    ap.add_argument("--weekday", default=next_weekday(2, today).isoformat(), help="평일 방문일 (기본: 다음 수요일)")
    ap.add_argument("--weekend", default=next_weekday(5, today).isoformat(), help="주말 방문일 (기본: 다음 토요일)")
    ap.add_argument("--regions", default=",".join(REGIONS), help="쉼표로 구분 (무료 한도에 맞춰 줄이기: 성수,홍대,강남)")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--out", default=str(RESULTS))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runs_csv, lam_csv = out / "runs.csv", out / "lambda.csv"
    api = Mock() if args.mock else Real()

    scenarios = build_scenarios(args.weekday, args.weekend, [r.strip() for r in args.regions.split(",") if r.strip()])
    if args.limit:
        scenarios = scenarios[:args.limit]
    skip = done_keys(runs_csv)
    todo = [(sc, rep) for rep in range(args.reps) for sc in scenarios if (sc["scenario_id"], str(rep)) not in skip]
    print(f"시나리오 {len(scenarios)}개 × 반복 {args.reps} — 남은 실행 {len(todo)}건 → {out}")

    for i, (sc, rep) in enumerate(todo, 1):
        t0 = time.time()
        for path in (runs_csv, lam_csv):
            purge(path, (sc["scenario_id"], str(rep)))
        try:
            run_one(api, sc, rep, runs_csv, lam_csv)
        except Exception as e:                      # 한 시나리오 실패가 전체를 멈추지 않도록
            append(runs_csv, RUN_FIELDS, {**sc, "rep": rep, "system": "ERROR", "success": 0,
                                          "error": f"{type(e).__name__}: {e}"})
        print(f"[{i}/{len(todo)}] {sc['scenario_id']} rep{rep} — {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
