// 예산 슬라이더 단계 (원)
export const BUDGET_VALUES = [10000, 20000, 30000, 50000, 70000, 100000, 150000, 200000, 300000, 500000, Infinity];
export const BUDGET_LABELS = ["1만", "2만", "3만", "5만", "7만", "10만", "15만", "20만", "30만", "50만", "∞"];

// 백엔드로 보낼 때 "제한없음"을 대신하는 값
export const UNLIMITED_BUDGET = 999999;

export const fmtBudget = (v: number) => v === Infinity ? "제한없음" : `${v / 10000}만원`;
export const fmtWon    = (v: number) => v >= UNLIMITED_BUDGET ? "제한없음" : `${Math.round(v / 10000)}만원`;

export const budgetAt = (idx: number) => {
  const v = BUDGET_VALUES[idx];
  return v === Infinity ? UNLIMITED_BUDGET : v;
};

/** 직접 입력한 금액을 가장 가까운 슬라이더 단계로 */
export function snapToBudgetIdx(rawValue: string | number): number {
  const num = parseInt(String(rawValue).replace(/[^0-9]/g, ""), 10);
  if (!num || num <= 0) return 0;
  let bestIdx = 0, bestDiff = Infinity;
  BUDGET_VALUES.forEach((v, i) => {
    const diff = Math.abs((v === Infinity ? 99999999 : v) - num);
    if (diff < bestDiff) { bestDiff = diff; bestIdx = i; }
  });
  return bestIdx;
}

export type BudgetRange = { minIdx: number; maxIdx: number };

/** 코스 전체(2인) 예산 = 두 사람 1인 예산의 합. 결과 화면의 'A+B 합산'과 같은 기준 */
export function coupleBudget(a: BudgetRange, b: BudgetRange): { min: number; max: number } {
  return {
    min: Math.min(UNLIMITED_BUDGET, budgetAt(a.minIdx) + budgetAt(b.minIdx)),
    max: Math.min(UNLIMITED_BUDGET, budgetAt(a.maxIdx) + budgetAt(b.maxIdx)),
  };
}

/** 두 사람 예산 범위의 교집합 (없으면 null) */
export function budgetOverlap(a: BudgetRange, b: BudgetRange): BudgetRange | null {
  const minIdx = Math.max(a.minIdx, b.minIdx);
  const maxIdx = Math.min(a.maxIdx, b.maxIdx);
  return minIdx <= maxIdx ? { minIdx, maxIdx } : null;
}
