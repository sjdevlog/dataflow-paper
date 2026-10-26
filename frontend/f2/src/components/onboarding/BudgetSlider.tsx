import { useState } from "react";
import { C, FONT } from "../../constants/theme";
import { BUDGET_LABELS, BUDGET_VALUES, fmtBudget, snapToBudgetIdx } from "../../utils/budget";
import type { BudgetRange } from "../../utils/budget";

const MAX_IDX = BUDGET_VALUES.length - 1;

export default function BudgetSlider({ value, onChange, color, label }: {
  value: BudgetRange; onChange: (v: BudgetRange) => void; color: string; label: string;
}) {
  const { minIdx, maxIdx } = value;
  const [showDirect, setShowDirect] = useState(false);
  const [dMin, setDMin] = useState("");
  const [dMax, setDMax] = useState("");
  const [topSlider, setTopSlider] = useState<"min" | "max">("max");

  const applyDirect = () => {
    let next = value;
    if (dMin.trim()) next = { ...next, minIdx: Math.min(snapToBudgetIdx(dMin), next.maxIdx) };
    if (dMax.trim()) next = { ...next, maxIdx: Math.max(snapToBudgetIdx(dMax), next.minIdx) };
    onChange(next);
    setDMin(""); setDMax("");
  };

  const leftPct  = (minIdx / MAX_IDX) * 100;
  const rightPct = (maxIdx / MAX_IDX) * 100;

  return (
    <div style={{ marginBottom:8 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:12 }}>
        <span style={{ fontSize:13, color, fontWeight:700, fontFamily:FONT }}>{label}</span>
        <span style={{ fontSize:13, color:C.text, fontFamily:FONT }}>
          {fmtBudget(BUDGET_VALUES[minIdx])} ~ {fmtBudget(BUDGET_VALUES[maxIdx])}
        </span>
      </div>
      <div style={{ position:"relative", height:4, background:C.inputBg, borderRadius:2, margin:"14px 0" }}
        onMouseDown={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const val  = Math.round(((e.clientX - rect.left) / rect.width) * MAX_IDX);
          setTopSlider(Math.abs(val - minIdx) <= Math.abs(val - maxIdx) ? "min" : "max");
        }}>
        <div style={{ position:"absolute", left:`${leftPct}%`, width:`${rightPct-leftPct}%`, height:"100%", background:color, borderRadius:2, opacity:0.7 }} />
        <input type="range" min={0} max={MAX_IDX} value={minIdx}
          onChange={e => { const v = Number(e.target.value); if (v <= maxIdx) onChange({ minIdx: v, maxIdx }); }}
          style={{ position:"absolute", width:"100%", top:-8, left:0, margin:0, accentColor:color, zIndex: topSlider==="min" ? 3 : 1 }} />
        <input type="range" min={0} max={MAX_IDX} value={maxIdx}
          onChange={e => { const v = Number(e.target.value); if (v >= minIdx) onChange({ minIdx, maxIdx: v }); }}
          style={{ position:"absolute", width:"100%", top:-8, left:0, margin:0, accentColor:color, zIndex: topSlider==="max" ? 3 : 1 }} />
      </div>
      <div style={{ display:"flex", justifyContent:"space-between", marginTop:6 }}>
        {BUDGET_LABELS.map((l, i) => (
          <span key={i} style={{ fontSize:9, color:i===minIdx||i===maxIdx?color:C.textMuted, fontFamily:"monospace", transition:"color 0.2s" }}>{l}</span>
        ))}
      </div>
      <button onClick={() => setShowDirect(v => !v)}
        style={{ marginTop:12, padding:"6px 14px", background:"transparent", border:`1px dashed ${C.inputBorder}`, borderRadius:8, color:C.textDim, fontSize:12, cursor:"pointer", fontFamily:FONT, display:"flex", alignItems:"center", gap:6 }}>
        <span>{showDirect ? "▲" : "⌨️"}</span>
        {showDirect ? "슬라이더로 돌아가기" : "금액 직접 입력"}
      </button>
      {showDirect && (
        <div style={{ marginTop:10, padding:"14px 16px", background:C.inputBg, borderRadius:12, animation:"fadeUp 0.2s ease" }}>
          <p style={{ fontSize:11, color:C.textMuted, margin:"0 0 10px" }}>금액 입력 후 Enter — 가장 가까운 단계로 자동 설정돼요</p>
          <div style={{ display:"flex", gap:8 }}>
            {[
              { label:"최솟값 (원)", val:dMin, set:setDMin, placeholder:BUDGET_VALUES[minIdx] === Infinity ? "∞" : BUDGET_VALUES[minIdx].toLocaleString() },
              { label:"최댓값 (원)", val:dMax, set:setDMax, placeholder:BUDGET_VALUES[maxIdx] === Infinity ? "∞" : BUDGET_VALUES[maxIdx].toLocaleString() },
            ].map(({ label: lbl, val, set, placeholder }) => (
              <div key={lbl} style={{ flex:1 }}>
                <label style={{ fontSize:11, color, fontWeight:600, display:"block", marginBottom:4 }}>{lbl}</label>
                <input type="number" value={val} onChange={e => set(e.target.value)} onBlur={applyDirect}
                  onKeyDown={e => e.key === "Enter" && applyDirect()} placeholder={placeholder}
                  style={{ width:"100%", padding:"10px 12px", background:C.card, border:`1.5px solid ${C.inputBorder}`, borderRadius:10, color:C.text, fontSize:14, fontFamily:FONT }} />
              </div>
            ))}
          </div>
          <p style={{ fontSize:11, color:C.textMuted, margin:"8px 0 0" }}>
            → 적용 결과: {fmtBudget(BUDGET_VALUES[minIdx])} ~ {fmtBudget(BUDGET_VALUES[maxIdx])}
          </p>
        </div>
      )}
    </div>
  );
}
