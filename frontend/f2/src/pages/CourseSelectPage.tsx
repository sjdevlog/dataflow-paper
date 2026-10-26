import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { CourseKey, CoursePlace } from "../types/course";
import { C, FONT, GS } from "../constants/theme";
import { CAT_EMOJI, COURSE_LABEL } from "../constants/course";
import { useActivePlan } from "../contexts/PlanContext";
import PageHeader from "../components/common/PageHeader";
import AiBubble from "../components/common/AiBubble";
import SampleDataNotice from "../components/common/SampleDataNotice";

function PlaceRow({ place, last }: { place: CoursePlace; last: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 0", borderBottom: last ? "none" : "1px solid rgba(0,0,0,0.06)" }}>
      <span style={{ fontSize: 11, color: "#999", fontFamily: "monospace", width: 40, flexShrink: 0 }}>{place.time}</span>
      <span style={{ fontSize: 14 }}>{CAT_EMOJI[place.category] || "📍"}</span>
      <span style={{ fontSize: 13, color: "#333", fontWeight: 500 }}>{place.name}</span>
    </div>
  );
}

const CARD_STYLE: Record<CourseKey, { icon: string; bg: string; accent: string; textColor: string }> = {
  A: { icon: "🌿", bg: "#FFFDE7", accent: "#8BC34A", textColor: "#5a7a3a" },
  B: { icon: "⚡", bg: "#FFF3E0", accent: "#FF9800", textColor: "#a05800" },
};

export default function CourseSelectPage() {
  const navigate = useNavigate();
  const { plan, selectCourse } = useActivePlan();

  const [showAI, setShowAI] = useState(false);
  const [selected, setSelected] = useState<CourseKey | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setShowAI(true), 500);
    return () => clearTimeout(t);
  }, []);

  const handlePick = (key: CourseKey) => {
    if (selected) return;
    setSelected(key);
    selectCourse(key);
    setTimeout(() => navigate("/result"), 700);
  };

  return (
    <div style={{ minHeight: "100vh", background: C.bg, padding: "32px 20px 60px", fontFamily: FONT }}>
      <style>{GS}</style>

      <PageHeader label="코스 선택" />
      <SampleDataNotice source={plan.courses.A.source} />

      {showAI && <AiBubble message="두 가지로 짜봤어요!" hint="마음에 드는 코스를 선택해보세요" />}

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {(["A", "B"] as const).map((id) => {
          const { icon, bg, accent, textColor } = CARD_STYLE[id];
          const course = plan.courses[id];
          const isSelected = selected === id;
          const isUnselected = selected !== null && !isSelected;
          return (
            <div
              key={id}
              onClick={() => handlePick(id)}
              style={{
                background: isUnselected ? "#f5f5f5" : bg,
                border: `2px solid ${isSelected ? accent : C.cardBorder}`,
                borderRadius: 16,
                padding: "16px 18px",
                cursor: selected ? "default" : "pointer",
                opacity: isUnselected ? 0.45 : 1,
                transition: "all 0.22s ease",
                boxShadow: isSelected ? `0 6px 24px ${accent}40` : "0 2px 8px rgba(0,0,0,0.05)",
                animation: "fadeUp 0.4s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <span style={{ fontSize: 18 }}>{icon}</span>
                <span style={{ fontSize: 14, fontWeight: 700, color: textColor }}>{COURSE_LABEL[id]}</span>
                {isSelected && (
                  <span style={{ marginLeft: "auto", fontSize: 11, background: accent, color: "#fff", padding: "2px 10px", borderRadius: "999px", fontWeight: 700 }}>
                    선택됨 ✓
                  </span>
                )}
              </div>
              {course.places.map((p, i) => (
                <PlaceRow key={i} place={p} last={i === course.places.length - 1} />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
