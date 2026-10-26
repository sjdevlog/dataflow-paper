import { C } from "../../constants/theme";
import { PREF_TAGS } from "../../utils/tags";
import { NavButtons, StepHeading, TagButton } from "./controls";

/** Step 1(A님) / Step 3(B님) — 취향 태그 선택 */
export default function PreferenceStep({ step, who, tags, onToggle, onBack, onNext, nextLabel }: {
  step: number; who: "A" | "B"; tags: string[]; onToggle: (tag: string) => void;
  onBack: () => void; onNext: () => void; nextLabel: string;
}) {
  const color = who === "A" ? C.main : C.point;
  const dim   = who === "A" ? C.mainDim : C.pointDim;
  return (
    <>
      <StepHeading step={step} who={who} color={color} title="의 취향을 알려주세요" hint="여러 개 선택 가능해요" />
      <div style={{ height: 18 }} />
      {Object.entries(PREF_TAGS).map(([cat, list]) => (
        <div key={cat} style={{ marginBottom:22 }}>
          <div style={{ fontSize:11, color:C.textMuted, marginBottom:8, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:600 }}>{cat}</div>
          <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
            {list.map(t => <TagButton key={t} label={t} selected={tags.includes(t)} onClick={() => onToggle(t)} color={color} />)}
          </div>
        </div>
      ))}
      {tags.length > 0 && (
        <div style={{ background:dim, border:`1px solid ${C.cardBorder}`, borderRadius:14, padding:"12px 16px", marginBottom:20 }}>
          <div style={{ fontSize:11, color, marginBottom:6, fontWeight:600 }}>선택됨</div>
          <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
            {tags.map(t => <span key={t} style={{ fontSize:12, background:color, color:"#fff", padding:"3px 10px", borderRadius:"999px" }}>{t}</span>)}
          </div>
        </div>
      )}
      <NavButtons onBack={onBack} onNext={onNext} nextLabel={nextLabel} />
    </>
  );
}
