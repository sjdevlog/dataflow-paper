import { C } from "../../constants/theme";

/** "🌸 DateFlow AI" 말풍선 */
export default function AiBubble({ message, hint, maxWidth = 300 }: { message: string; hint?: string; maxWidth?: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", marginBottom: 20, animation: "fadeUp 0.4s ease" }}>
      <div style={{ fontSize: 11, color: C.main, marginBottom: 6, fontWeight: 600 }}>🌸 DateFlow AI</div>
      <div style={{ background: C.mainDark, color: C.card, borderRadius: "18px 18px 18px 4px", padding: "12px 20px", fontSize: 14, fontWeight: 600, maxWidth }}>
        {message}
      </div>
      {hint && <div style={{ marginTop: 6, fontSize: 12, color: C.main }}>{hint}</div>}
    </div>
  );
}
