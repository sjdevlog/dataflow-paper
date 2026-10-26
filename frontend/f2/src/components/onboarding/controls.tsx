import { C, FONT } from "../../constants/theme";

export function TagButton({ label, selected, onClick, color = C.main }: { label: string; selected: boolean; onClick: () => void; color?: string }) {
  return (
    <button onClick={onClick} style={{
      padding:"8px 16px", borderRadius:"999px",
      border: selected ? "none" : `1.5px solid ${C.cardBorder}`,
      background: selected ? color : C.card,
      color: selected ? "#fff" : C.textDim,
      fontSize:13, fontFamily:FONT,
      fontWeight: selected ? 700 : 400, cursor:"pointer",
      transition:"all 0.18s",
      boxShadow: selected ? "0 2px 8px #B8A9D940" : "none",
    }}>{label}</button>
  );
}

export function ProgressBar({ step, total = 4 }: { step: number; total?: number }) {
  return (
    <div style={{ display:"flex", gap:6, marginBottom:32 }}>
      {Array.from({ length: total }, (_, i) => (
        <div key={i} style={{ flex:1, height:4, borderRadius:"999px", background:i<step?C.main:C.cardBorder, transition:"background 0.3s" }} />
      ))}
    </div>
  );
}

export function NavButtons({ onBack, onNext, nextLabel, nextDisabled }: { onBack: () => void; onNext: () => void; nextLabel: string; nextDisabled?: boolean }) {
  return (
    <div style={{ display:"flex", gap:10 }}>
      <button className="df-nav-btn" onClick={onBack} style={{ flex:1, padding:14, background:C.card, border:`1.5px solid ${C.cardBorder}`, borderRadius:14, color:C.textDim, fontSize:14, cursor:"pointer", fontFamily:FONT }}>← 이전</button>
      <button className="df-nav-btn" onClick={onNext} disabled={nextDisabled} style={{ flex:2, padding:14, background:nextDisabled?C.inputBg:C.main, border:"none", borderRadius:14, color:nextDisabled?C.textMuted:"#fff", fontSize:15, fontWeight:700, cursor:nextDisabled?"not-allowed":"pointer", fontFamily:FONT, boxShadow:nextDisabled?"none":"0 4px 14px #B8A9D940", transition:"all 0.2s" }}>{nextLabel}</button>
    </div>
  );
}

/** 단계 상단: 진행바 + "Step n / 4 · A님" + 제목 */
export function StepHeading({ step, who, color, title, hint }: { step: number; who: "A" | "B"; color: string; title: string; hint: string }) {
  return (
    <>
      <ProgressBar step={step} />
      <div style={{ fontSize:11, color, marginBottom:10, letterSpacing:"0.1em", textTransform:"uppercase", fontWeight:600 }}>Step {step} / 4 · {who}님</div>
      <h2 className="df-step-title" style={{ fontSize:26, fontWeight:700, color:C.text, margin:"0 0 4px" }}><span style={{ color }}>{who}님</span>{title}</h2>
      <p style={{ fontSize:13, color:C.textMuted, margin:"0 0 6px" }}>{hint}</p>
    </>
  );
}
