"""experiments/results/*.csv → 논문 표 8·9 집계 (markdown 출력 + summary.json)

실행: python experiments/summarize.py
"""
import csv
import json
import statistics as st
from pathlib import Path

RESULTS = Path(__import__("os").getenv("RESULTS_DIR", Path(__file__).resolve().parent / "results"))
SYSTEMS = ["R", "L", "LV", "LVF"]


def load(name):
    p = RESULTS / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(rows, key):
    return [float(r[key]) for r in rows if r.get(key) not in ("", None)]


def mean_sd(xs, nd=2):
    if not xs:
        return "-"
    if len(xs) == 1:
        return f"{xs[0]:.{nd}f}"
    return f"{st.mean(xs):.{nd}f} ± {st.stdev(xs):.{nd}f}"


def main():
    runs = load("runs.csv")
    lam = load("lambda.csv")
    if not runs:
        print("results/runs.csv 가 없습니다. 먼저 experiments/run.py 를 실행하세요.")
        return

    errors = {}
    for r in runs:
        if r.get("error"):
            errors[r["error"][:160]] = errors.get(r["error"][:160], 0) + 1
    if errors:
        print("### 오류 (상위 5개)\n")
        for e, n in sorted(errors.items(), key=lambda x: -x[1])[:5]:
            print(f"- {n}회: {e}")
        print()

    summary = {}
    print("### 표 8. 시스템별 성능 비교 (평균 ± 표준편차)\n")
    print("| 시스템 | 성공률 | 위반율 | 평균 만족도 | Fairness gap | 이동시간(분, 직선) | 응답 시간(초) | 툴 호출 수 |")
    print("|---|---|---|---|---|---|---|---|")
    for s in SYSTEMS:
        rows = [r for r in runs if r["system"] == s]
        ok = [r for r in rows if r.get("success") == "1"]
        total_places = sum(int(r["n_places"]) for r in ok if r.get("n_places"))
        total_viol = sum(int(r["violations"]) for r in ok if r.get("violations"))
        vrate = total_viol / total_places if total_places else None
        summary[s] = {
            "n": len(rows), "success_rate": len(ok) / len(rows) if rows else None,
            "violation_rate": vrate,
            "avg_satisfaction": st.mean(num(ok, "avg_satisfaction")) if num(ok, "avg_satisfaction") else None,
            "fairness_gap": st.mean(num(ok, "fairness_gap")) if num(ok, "fairness_gap") else None,
        }
        print(f"| {s} | {len(ok)}/{len(rows)} | {vrate:.3f} | " if vrate is not None else f"| {s} | {len(ok)}/{len(rows)} | - | ",
              end="")
        print(f"{mean_sd(num(ok, 'avg_satisfaction'))} | {mean_sd(num(ok, 'fairness_gap'))} | "
              f"{mean_sd(num(ok, 'walk_min_straight'), 1)} | {mean_sd(num(rows, 'gen_sec'), 1)} | "
              f"{mean_sd(num(rows, 'tool_calls'), 1)} |")

    print("\n위반율 = 전체 추천 장소 중 평가 시점 재조회에서 closed 판정 비율 (unknown 제외 안 함)")
    unk = {s: sum(int(r['unknown']) for r in runs if r['system'] == s and r.get('unknown')) for s in SYSTEMS}
    print(f"unknown 판정 수: {unk}")

    print("\n### 취향 겹침 여부별 fairness gap\n")
    print("| 시스템 | 겹침 있음 | 겹침 없음 |")
    print("|---|---|---|")
    for s in SYSTEMS:
        ok = [r for r in runs if r["system"] == s and r.get("success") == "1"]
        print(f"| {s} | {mean_sd(num([r for r in ok if r['pair_kind'] == 'overlap'], 'fairness_gap'))} | "
              f"{mean_sd(num([r for r in ok if r['pair_kind'] == 'disjoint'], 'fairness_gap'))} |")

    parse = [r for r in runs if r["system"] in ("L", "LV")]
    if parse:
        good = sum(1 for r in parse if r.get("parse_status") in ("codeblock_ok", "brace_ok"))
        print(f"\n파싱 성공률 (L·LV 생성 {len(parse)}회): {good / len(parse):.3f}")
    lv = [r for r in runs if r["system"] == "LV" and r.get("cache_hits") not in ("", None)]
    if lv:
        print(f"check ② 평균 캐시 적중 수: {st.mean(num(lv, 'cache_hits')):.1f}")

    if lam:
        print("\n### 표 9. 공정성 가중치 λ에 따른 결과 (LVF 후보 집합)\n")
        lams = sorted({float(r["lambda"]) for r in lam})
        print("| λ | " + " | ".join(f"{l:g}" for l in lams) + " |")
        print("|---|" + "---|" * len(lams))
        for key, label in (("avg_satisfaction", "평균 만족도"), ("fairness_gap", "Fairness gap")):
            print(f"| {label} | " + " | ".join(mean_sd(num([r for r in lam if float(r['lambda']) == l], key))
                                              for l in lams) + " |")
        summary["lambda"] = {l: {k: st.mean(num([r for r in lam if float(r["lambda"]) == l], k))
                                 for k in ("avg_satisfaction", "fairness_gap")} for l in lams}

    (RESULTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {RESULTS / 'summary.json'}")


if __name__ == "__main__":
    main()
