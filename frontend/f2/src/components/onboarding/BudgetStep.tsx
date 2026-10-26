import type { ReactNode } from "react";
import { C } from "../../constants/theme";
import type { BudgetRange } from "../../utils/budget";
import BudgetSlider from "./BudgetSlider";
import { NavButtons, StepHeading } from "./controls";

/** Step 2(A님) / Step 4(B님) — 1인 예산 범위 */
export default function BudgetStep({ step, who, value, onChange, onBack, onNext, nextLabel, children }: {
  step: number; who: "A" | "B"; value: BudgetRange; onChange: (v: BudgetRange) => void;
  onBack: () => void; onNext: () => void; nextLabel: string; children?: ReactNode;
}) {
  const color = who === "A" ? C.main : C.point;
  return (
    <>
      <StepHeading step={step} who={who} color={color} title="의 1인 예산 범위는요?" hint="슬라이더 조정 또는 직접 입력하세요" />
      <p style={{ fontSize:12, color:C.textMuted, margin:"0 0 20px", background:C.inputBg, padding:"8px 12px", borderRadius:8 }}>
        💡 조정하지 않으면 기본값 <strong style={{ color:C.text }}>3만원 ~ 10만원</strong>으로 코스가 생성돼요
      </p>
      <div style={{ background:C.card, border:`1px solid ${C.cardBorder}`, borderRadius:20, padding:"20px 20px 24px", marginBottom:20, boxShadow:"0 2px 12px #B8A9D912" }}>
        <BudgetSlider value={value} onChange={onChange} color={color} label={`${who}님 예산`} />
      </div>
      {children}
      <NavButtons onBack={onBack} onNext={onNext} nextLabel={nextLabel} />
    </>
  );
}
