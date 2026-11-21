"""영업시간 판정 정확도 확인용 시트 만들기 (교수님 피드백: 50~100곳 수동 확인)

실행: python experiments/make_check_sheet.py [--n 100] [--seed 0]
      RESULTS_DIR=experiments/results_v2 python experiments/make_check_sheet.py

places.csv(평가한 장소 1곳당 1행)에서 같은 장소·방문 시각 중복을 없애고,
closed와 unknown은 모두 넣고 나머지는 open에서 무작위로 채워 n곳을 뽑는다.
→ results/check_sheet.csv : 카카오맵 링크를 열어 '사람 판정' 칸에 open / closed / unknown 을 적는다.

다 채운 뒤 정확도 계산:
      python experiments/make_check_sheet.py --score
"""
import argparse
import csv
import os
import random
from collections import Counter
from pathlib import Path

RESULTS = Path(os.getenv("RESULTS_DIR", Path(__file__).resolve().parent / "results"))
WEEKDAY_KO = "월화수목금토일"
FIELDS = ["번호", "장소", "카테고리", "방문일", "요일", "방문 시각", "도구 판정", "카카오맵 링크",
          "사람 판정 (open/closed/unknown)", "메모"]


def make(n, seed):
    from datetime import date
    with (RESULTS / "places.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    uniq = {}
    for r in rows:
        uniq.setdefault((r["name"], r["date"], r["time"]), r)
    pool = list(uniq.values())
    rng = random.Random(seed)
    must = [r for r in pool if r["status"] in ("closed", "unknown")]
    rest = [r for r in pool if r["status"] == "open"]
    rng.shuffle(must)
    rng.shuffle(rest)
    pick = (must + rest)[:n] if len(must) < n else must[: n // 2] + rest[: n - n // 2]
    rng.shuffle(pick)
    out = RESULTS / "check_sheet.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:       # 엑셀에서 한글이 깨지지 않게 BOM
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, r in enumerate(pick, 1):
            d = date.fromisoformat(r["date"])
            w.writerow({"번호": i, "장소": r["name"], "카테고리": r["category"], "방문일": r["date"],
                        "요일": WEEKDAY_KO[d.weekday()], "방문 시각": r["time"], "도구 판정": r["status"],
                        "카카오맵 링크": r["place_url"]})
    print(f"{len(pick)}곳 → {out}  (도구 판정 분포: {dict(Counter(r['status'] for r in pick))})")


def score():
    with (RESULTS / "check_sheet.csv").open(encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["사람 판정 (open/closed/unknown)"].strip()]
    if not rows:
        print("사람 판정이 비어 있습니다.")
        return
    pairs = [(r["도구 판정"], r["사람 판정 (open/closed/unknown)"].strip().lower()) for r in rows]
    agree = sum(t == h for t, h in pairs)
    print(f"확인한 장소 {len(pairs)}곳, 일치 {agree}곳 ({agree / len(pairs) * 100:.1f}%)\n")
    labels = ["open", "closed", "unknown"]
    print("| 도구 \\ 사람 | " + " | ".join(labels) + " |")
    print("|---|" + "---|" * len(labels))
    for t in labels:
        print(f"| {t} | " + " | ".join(str(sum(1 for a, b in pairs if a == t and b == h)) for h in labels) + " |")
    known = [(t, h) for t, h in pairs if t != "unknown" and h != "unknown"]
    if known:
        ok = sum(t == h for t, h in known)
        print(f"\n둘 다 open/closed로 판정한 {len(known)}곳의 정확도: {ok / len(known) * 100:.1f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    score() if a.score else make(a.n, a.seed)
