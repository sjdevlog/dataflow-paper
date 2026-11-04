/** 화면 표시용 두 사람 이름 — 비어 있으면 A·B */
export const personNames = (input?: { nameA?: string; nameB?: string }) => ({
  a: input?.nameA?.trim() || "A",
  b: input?.nameB?.trim() || "B",
});
