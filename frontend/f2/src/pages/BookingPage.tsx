import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { CoursePlace } from "../types/course";
import { C, FONT, GS } from "../constants/theme";
import { useActivePlan } from "../contexts/PlanContext";
import { formatDateShort } from "../utils/date";
import ActionButtonGroup from "../components/ActionButtonGroup";
import PageHeader from "../components/common/PageHeader";
import AiBubble from "../components/common/AiBubble";

function bookingButton(place: CoursePlace) {
  const naverSearch = (q: string) =>
    `https://search.naver.com/search.naver?query=${encodeURIComponent(q)}`;

  if (place.reservationAvailable) {
    const url =
      place.naverReservationUrl ??
      place.reservationUrl ??
      naverSearch(place.name + " 예약");
    return { label: "예약하기", url };
  }
  if ((place.admissionFee ?? 0) > 0) {
    return { label: "입장권", url: naverSearch(place.name + " 입장권") };
  }
  return null;
}

export default function BookingPage() {
  const navigate = useNavigate();
  const { plan } = useActivePlan();
  const { input } = plan;

  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const places = plan.courses[plan.selectedCourse].places;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: C.bg,
        padding: "32px 20px 60px",
        fontFamily: FONT,
      }}
    >
      <style>{GS}</style>

      <PageHeader label="예약 안내" showBack subtitle={`📍 ${input.region.name} · 📅 ${formatDateShort(input.date)}`} />
      <AiBubble message="각 장소에서 바로 예매하실 수 있어요!" maxWidth={280} />

      {/* 장소 예약 목록 */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 10,
          marginBottom: 28,
        }}
      >
        {places.map((place, i) => {
          const btn = bookingButton(place);
          const isOpen = expandedIdx === i;
          return (
            <div
              key={i}
              style={{
                background: isOpen ? C.mainDim : C.card,
                border: `1px solid ${isOpen ? C.main : C.cardBorder}`,
                borderRadius: 14,
                padding: "14px 16px",
                boxShadow: "0 1px 4px rgba(184,169,217,0.12)",
                animation: `fadeUp 0.3s ease ${i * 0.07}s both`,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onClick={() => setExpandedIdx(isOpen ? null : i)}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 8 }}
                  >
                    <span
                      style={{
                        fontSize: 11,
                        color: C.main,
                        fontFamily: "monospace",
                      }}
                    >
                      {place.time}
                    </span>
                    <span
                      style={{ fontSize: 14, fontWeight: 600, color: C.text }}
                    >
                      {place.name}
                    </span>
                  </div>
                  {place.openingHours && (
                    <div
                      style={{
                        fontSize: 11,
                        color: C.textMuted,
                        marginTop: 2,
                        marginLeft: 36,
                      }}
                    >
                      {place.openingHours}
                      {place.closedDays &&
                        place.closedDays !== "없음" &&
                        ` · 휴무 ${place.closedDays}`}
                    </div>
                  )}
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    flexShrink: 0,
                  }}
                >
                  {btn ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        window.open(btn.url, "_blank");
                      }}
                      style={{
                        padding: "6px 14px",
                        background: C.mainDark,
                        color: C.card,
                        border: "none",
                        borderRadius: "999px",
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      {btn.label}
                    </button>
                  ) : (
                    <span style={{ fontSize: 11, color: C.textMuted }}>
                      {place.openingHours === "상시 개방"
                        ? "상시 개방"
                        : "예약 불필요"}
                    </span>
                  )}
                </div>
              </div>

              {/* 액션 버튼 (펼쳐졌을 때) */}
              {isOpen && (
                <div onClick={(e) => e.stopPropagation()}>
                  <ActionButtonGroup place={place} hideNavigation />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <button
        onClick={() => navigate("/complete")}
        style={{
          width: "100%",
          padding: 16,
          background: C.mainDark,
          color: C.card,
          border: "none",
          borderRadius: 14,
          fontSize: 16,
          fontWeight: 700,
          cursor: "pointer",
          boxShadow: "0 4px 20px rgba(90,68,128,0.3)",
          fontFamily: FONT,
        }}
      >
        코스 확정하기 →
      </button>
    </div>
  );
}
