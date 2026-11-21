"""experiments/results/*.csv → 논문 표 집계 (markdown 출력 + summary.json)

실행: python experiments/summarize.py
      RESULTS_DIR=experiments/results_v2 python experiments/summarize.py

출력 (교수님 피드백 반영):
- 시스템별 표: 위반 '건수/전체 장소 수', unknown 건수·비율, unknown을 위반으로 쳤을 때의 비율
- 반복(rep)별 평균을 구한 뒤 반복 간 평균 ± 표준편차
- Fisher 정확 검정(위반율), Wilcoxon 부호순위 검정(같은 시나리오·반복끼리 짝지은 만족도·격차)
- 취향 겹침 여부별 fairness gap, λ별 결과, LV/LVF 예시 사례
외부 패키지 없이 표준 라이브러리만 사용한다.
"""
import csv
import json
import math
import os
import statistics as st
from pathlib import Path

RESULTS = Path(os.getenv("RESULTS_DIR", Path(__file__).resolve().parent / "results"))
ALL_SYSTEMS = ["R", "L", "L3", "LV", "LVF"]


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


def ints(rows, key):
    return sum(int(float(r[key])) for r in rows if r.get(key) not in ("", None))


# ── 검정 (표준 라이브러리 구현) ───────────────────────────────────

def fisher_exact(a, b, c, d):
    """2×2 표 [[a, b], [c, d]]의 양측 Fisher 정확 검정 p값"""
    r1, c1, n = a + b, a + c, a + b + c + d

    def p_of(x):
        return math.comb(c1, x) * math.comb(n - c1, r1 - x) / math.comb(n, r1)

    p_obs = p_of(a)
    lo, hi = max(0, r1 - (n - c1)), min(r1, c1)
    return min(1.0, sum(p_of(x) for x in range(lo, hi + 1) if p_of(x) <= p_obs * (1 + 1e-9)))


def wilcoxon(xs, ys):
    """짝지은 표본의 Wilcoxon 부호순위 검정 (정규근사, 차이 0 제외, 동순위 평균). (n, p) 반환"""
    d = [x - y for x, y in zip(xs, ys) if abs(x - y) > 1e-12]
    n = len(d)
    if n < 6:
        return n, None
    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    i = 0
    tie_term = 0.0
    while i < n:
        j = i
        while j + 1 < n and abs(abs(d[order[j + 1]]) - abs(d[order[i]])) < 1e-12:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        t = j - i + 1
        tie_term += t ** 3 - t
        i = j + 1
    w_plus = sum(r for r, v in zip(ranks, d) if v > 0)
    mu = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24 - tie_term / 48)
    z = (w_plus - mu) / sigma if sigma else 0.0
    p = math.erfc(abs(z) / math.sqrt(2))
    return n, p


def fmt_p(p):
    if p is None:
        return "-"
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def main():
    runs = load("runs.csv")
    lam = load("lambda.csv")
    if not runs:
        print(f"{RESULTS}/runs.csv 가 없습니다. 먼저 experiments/run.py 를 실행하세요.")
        return
    systems = [s for s in ALL_SYSTEMS if any(r["system"] == s for r in runs)]
    reps = sorted({r["rep"] for r in runs})

    errors = {}
    for r in runs:
        if r.get("error"):
            errors[r["error"][:160]] = errors.get(r["error"][:160], 0) + 1
    if errors:
        print("### 오류 (상위 5개)\n")
        for e, n in sorted(errors.items(), key=lambda x: -x[1])[:5]:
            print(f"- {n}회: {e}")
        print()

    ok = {s: [r for r in runs if r["system"] == s and r.get("success") == "1"] for s in systems}
    summary = {"reps": reps, "systems": {}}

    # ── 표 8: 시스템별 (전체 반복 통합) ──
    print(f"### 표 8. 시스템별 성능 비교 (시나리오 × 반복 {len(reps)}회 통합, 평균 ± 표준편차)\n")
    print("| 시스템 | 성공 | 위반 (closed) | unknown | unknown 포함 위반 | 평균 만족도 | Fairness gap | 이동시간(분) | 응답 시간(초) | 툴 호출 수 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for s in systems:
        rows = [r for r in runs if r["system"] == s]
        o = ok[s]
        n_pl, n_cl, n_un = ints(o, "n_places"), ints(o, "violations"), ints(o, "unknown")
        summary["systems"][s] = {
            "success": f"{len(o)}/{len(rows)}", "n_places": n_pl, "closed": n_cl, "unknown": n_un,
            "violation_rate": n_cl / n_pl if n_pl else None,
            "unknown_rate": n_un / n_pl if n_pl else None,
            "violation_rate_with_unknown": (n_cl + n_un) / n_pl if n_pl else None,
            "avg_satisfaction": st.mean(num(o, "avg_satisfaction")) if o else None,
            "fairness_gap": st.mean(num(o, "fairness_gap")) if o else None,
            "walk_min": st.mean(num(o, "walk_min_straight")) if num(o, "walk_min_straight") else None,
            "gen_sec": st.mean(num(rows, "gen_sec")) if num(rows, "gen_sec") else None,
        }
        pct = lambda k, x: f"{x}/{n_pl} ({x / n_pl * 100:.1f}%)" if n_pl else "-"   # noqa: E731
        print(f"| {s} | {len(o)}/{len(rows)} | {pct('c', n_cl)} | {pct('u', n_un)} | {pct('cu', n_cl + n_un)} | "
              f"{mean_sd(num(o, 'avg_satisfaction'))} | {mean_sd(num(o, 'fairness_gap'))} | "
              f"{mean_sd(num(o, 'walk_min_straight'), 1)} | {mean_sd(num(rows, 'gen_sec'), 1)} | "
              f"{mean_sd(num(rows, 'tool_calls'), 1)} |")
    print("\n위반 = 평가 시점 재조회에서 closed 판정된 장소 수 / 전체 추천 장소 수. "
          "unknown 포함 위반 = (closed + unknown) / 전체 (가장 보수적인 가정).")

    # ── 반복 간 평균 ± 표준편차 ──
    if len(reps) > 1:
        print(f"\n### 반복 {len(reps)}회의 반복별 평균 → 반복 간 평균 ± 표준편차\n")
        print("| 시스템 | 위반율(%) | 평균 만족도 | Fairness gap | 응답 시간(초) |")
        print("|---|---|---|---|---|")
        for s in systems:
            vr, sat, gap, sec = [], [], [], []
            for rep in reps:
                o = [r for r in ok[s] if r["rep"] == rep]
                n_pl = ints(o, "n_places")
                if n_pl:
                    vr.append(ints(o, "violations") / n_pl * 100)
                if o:
                    sat.append(st.mean(num(o, "avg_satisfaction")))
                    gap.append(st.mean(num(o, "fairness_gap")))
                g = num([r for r in runs if r["system"] == s and r["rep"] == rep], "gen_sec")
                if g:
                    sec.append(st.mean(g))
            print(f"| {s} | {mean_sd(vr)} | {mean_sd(sat)} | {mean_sd(gap)} | {mean_sd(sec, 1)} |")

    # ── 검정 ──
    print("\n### 통계 검정\n")
    print("| 비교 | 지표 | 결과 | p |")
    print("|---|---|---|---|")
    tests = {}

    def fisher_row(s1, s2, with_unknown=False):
        if s1 not in ok or s2 not in ok:
            return
        def counts(s):
            n = ints(ok[s], "n_places")
            v = ints(ok[s], "violations") + (ints(ok[s], "unknown") if with_unknown else 0)
            return v, n - v, n
        v1, o1, n1 = counts(s1)
        v2, o2, n2 = counts(s2)
        if not n1 or not n2:
            return
        p = fisher_exact(v1, o1, v2, o2)
        label = "위반율 (unknown 포함)" if with_unknown else "위반율"
        tests[f"fisher {s1} vs {s2}{' +unknown' if with_unknown else ''}"] = p
        print(f"| {s1} vs {s2} | {label} | {v1}/{n1} vs {v2}/{n2} | {fmt_p(p)} (Fisher) |")

    def paired(s1, s2, key, label):
        if s1 not in ok or s2 not in ok:
            return
        a = {(r["scenario_id"], r["rep"]): float(r[key]) for r in ok[s1] if r.get(key)}
        b = {(r["scenario_id"], r["rep"]): float(r[key]) for r in ok[s2] if r.get(key)}
        keys = sorted(a.keys() & b.keys())
        xs, ys = [a[k] for k in keys], [b[k] for k in keys]
        n_nz, p = wilcoxon(xs, ys)
        tests[f"wilcoxon {s1} vs {s2} {key}"] = p
        print(f"| {s1} vs {s2} | {label} | {st.mean(xs):.2f} vs {st.mean(ys):.2f} (짝 {len(keys)}개, 차이 있는 짝 {n_nz}개) | "
              f"{fmt_p(p)} (Wilcoxon) |")

    for s1, s2 in (("L", "LV"), ("L3", "LV"), ("L", "L3")):
        fisher_row(s1, s2)
        fisher_row(s1, s2, with_unknown=True)
    paired("LV", "LVF", "fairness_gap", "Fairness gap")
    paired("LV", "LVF", "avg_satisfaction", "평균 만족도")
    paired("L", "L3", "avg_satisfaction", "평균 만족도 (후보 3개 선택 효과)")
    paired("L3", "LV", "avg_satisfaction", "평균 만족도 (검증 효과)")
    paired("L", "LVF", "fairness_gap", "Fairness gap")
    paired("LV", "LVF", "walk_min_straight", "이동시간")
    summary["tests"] = tests

    # ── 표 9: 취향 겹침 여부별 ──
    print("\n### 표 9. 취향 겹침 여부별 fairness gap\n")
    print("| 시스템 | 겹침 있음 | 겹침 없음 |")
    print("|---|---|---|")
    for s in systems:
        print(f"| {s} | {mean_sd(num([r for r in ok[s] if r['pair_kind'] == 'overlap'], 'fairness_gap'))} | "
              f"{mean_sd(num([r for r in ok[s] if r['pair_kind'] == 'disjoint'], 'fairness_gap'))} |")

    parse = [r for r in runs if r["system"] in ("L", "L3", "LV")]
    if parse:
        good = sum(1 for r in parse if r.get("parse_status") in ("codeblock_ok", "brace_ok"))
        print(f"\n파싱 성공률 (L·L3·LV 생성 {len(parse)}회): {good}/{len(parse)}")
    lv = [r for r in runs if r["system"] == "LV" and r.get("cache_hits") not in ("", None)]
    if lv:
        print(f"check ② 평균 캐시 적중 수: {st.mean(num(lv, 'cache_hits')):.1f}")

    # ── 표 10: λ ──
    if lam:
        print("\n### 표 10. 공정성 가중치 λ에 따른 결과 (LV 후보 집합)\n")
        lams = sorted({float(r["lambda"]) for r in lam})
        print("| λ | " + " | ".join(f"{x:g}" for x in lams) + " |")
        print("|---|" + "---|" * len(lams))
        for key, label in (("avg_satisfaction", "평균 만족도"), ("fairness_gap", "Fairness gap")):
            print(f"| {label} | " + " | ".join(mean_sd(num([r for r in lam if float(r['lambda']) == x], key))
                                              for x in lams) + " |")
        summary["lambda"] = {x: {k: st.mean(num([r for r in lam if float(r["lambda"]) == x], k))
                                 for k in ("avg_satisfaction", "fairness_gap")} for x in lams}

    # ── 예시 사례: 취향이 겹치지 않는 쌍에서 LV와 LVF가 다른 코스를 고른 경우 ──
    lvm = {(r["scenario_id"], r["rep"]): r for r in ok.get("LV", [])}
    print("\n### 예시 사례 (취향 겹침 없음, LV와 LVF의 선택이 다른 경우 — 격차 차이가 큰 순 3개)\n")
    cands = []
    for r in ok.get("LVF", []):
        v = lvm.get((r["scenario_id"], r["rep"]))
        if v and r["pair_kind"] == "disjoint" and v["places"] != r["places"]:
            cands.append((float(v["fairness_gap"]) - float(r["fairness_gap"]), v, r))
    for diff, v, f in sorted(cands, key=lambda x: -x[0])[:3]:
        print(f"- {f['scenario_id']} rep{f['rep']}")
        for tag, r in (("LV ", v), ("LVF", f)):
            print(f"  {tag}: {', '.join(json.loads(r['places']))} | A {r['sat_a']} / B {r['sat_b']} | "
                  f"평균 {r['avg_satisfaction']} | 격차 {r['fairness_gap']} | 이동 {r['walk_min_straight']}분")

    (RESULTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {RESULTS / 'summary.json'}")


if __name__ == "__main__":
    main()
