import { C, FONT, GS } from "../../constants/theme";
import { LOADING_STEPS } from "../../constants/course";

export default function LoadingScreen({ message }: { message: string }) {
  const stepIdx = LOADING_STEPS.indexOf(message);
  const isDone  = stepIdx < 0;
  const pct     = isDone ? 100 : Math.round(((stepIdx + 1) / LOADING_STEPS.length) * 100);
  return (
    <div style={{ minHeight:"100vh", background:C.bg, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", padding:"0 20px", fontFamily:FONT }}>
      <style>{GS}</style>
      <div style={{ textAlign:"center", width:"100%", maxWidth:320 }}>
        <div style={{ fontSize:44, animation:"spin 1.6s linear infinite", display:"inline-block", marginBottom:24, color:C.main }}>◎</div>
        <p style={{ color:C.text, fontSize:16, fontWeight:600, marginBottom:8 }}>{isDone ? "코스 완성! ✦" : "코스 생성 중"}</p>
        <p style={{ color:C.textDim, fontSize:14, animation:"pulse 1.5s ease infinite", marginBottom:28 }}>{message}</p>
        <div style={{ background:C.inputBg, borderRadius:"999px", height:6, overflow:"hidden", marginBottom:14 }}>
          <div style={{ width:`${pct}%`, height:"100%", background:`linear-gradient(90deg,${C.main},${C.point})`, borderRadius:"999px", transition:"width 0.5s ease" }} />
        </div>
        <div style={{ display:"flex", justifyContent:"space-between", padding:"0 4px" }}>
          {LOADING_STEPS.map((_, i) => (
            <div key={i} style={{ width:8, height:8, borderRadius:"50%", background:(isDone||i<=stepIdx)?C.main:C.inputBg, transition:"background 0.3s" }} />
          ))}
        </div>
      </div>
    </div>
  );
}
