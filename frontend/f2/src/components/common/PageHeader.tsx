import { useNavigate } from "react-router-dom";
import { C } from "../../constants/theme";

/** DateFlow 로고 + 페이지 라벨 (+ 선택적으로 뒤로가기 버튼) */
export default function PageHeader({ label, showBack = false, subtitle }: { label: string; showBack?: boolean; subtitle?: string }) {
  const navigate = useNavigate();
  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: subtitle ? 6 : 0 }}>
        {showBack && (
          <button onClick={() => navigate(-1)} style={{ background: C.mainDim, border: "none", borderRadius: 8, padding: "6px 12px", color: C.mainDark, fontSize: 13, cursor: "pointer", flexShrink: 0 }}>
            ← 뒤로
          </button>
        )}
        <span style={{ fontSize: 20, fontWeight: 900, color: C.mainDark }}>
          Date<span style={{ color: C.main }}>Flow</span>
        </span>
        <span style={{ fontSize: 11, color: C.main, letterSpacing: "0.1em" }}>{label}</span>
      </div>
      {subtitle && <p style={{ fontSize: 13, color: C.textMuted, margin: 0, paddingLeft: 4 }}>{subtitle}</p>}
    </div>
  );
}
