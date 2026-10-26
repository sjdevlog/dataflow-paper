export const KO_DAYS = ["일", "월", "화", "수", "목", "금", "토"];

const parse = (s: string) => new Date(s + "T00:00:00");

/** 로컬 기준 YYYY-MM-DD (toISOString 은 UTC 라 KST 오전 9시 전엔 어제가 됨) */
export function todayStr(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** "5월 20일 (화)" */
export function formatDateShort(s: string): string {
  if (!s) return "";
  const d = parse(s);
  return `${d.getMonth() + 1}월 ${d.getDate()}일 (${KO_DAYS[d.getDay()]})`;
}

/** "5월 20일 (오늘)" / "(내일)" / "(화요일)" */
export function formatDateKo(s: string): string {
  if (!s) return "";
  const d   = parse(s);
  const now = new Date(); now.setHours(0, 0, 0, 0);
  const diffDays = Math.round((d.getTime() - now.getTime()) / 86400000);
  const suffix = diffDays === 0 ? "(오늘)" : diffDays === 1 ? "(내일)" : `(${KO_DAYS[d.getDay()]}요일)`;
  return `${d.getMonth() + 1}월 ${d.getDate()}일 ${suffix}`;
}

export function isWeekendDate(s: string): boolean {
  if (!s) return false;
  const dow = parse(s).getDay();
  return dow === 0 || dow === 6;
}

export function dayOfWeekKo(s: string): string {
  return KO_DAYS[parse(s).getDay()];
}
