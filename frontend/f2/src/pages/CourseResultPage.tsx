import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { CourseKey, CoursePlace } from "../types/course";
import { COURSE_LABEL } from "../constants/course";
import { useActivePlan } from "../contexts/PlanContext";
import PreferenceIntersection from "../components/PreferenceIntersection";
import CourseTimeline from "../components/CourseTimeline";
import PlaceDetailCard from "../components/PlaceDetailCard";
import KakaoMap from "../components/KakaoMap";
import SampleDataNotice from "../components/common/SampleDataNotice";
import { getWeatherEmoji } from "../utils/getWeatherEmoji";
import { coupleBudget, fmtWon } from "../utils/budget";
import { dayOfWeekKo, formatDateShort } from "../utils/date";
import { commonTags } from "../utils/tags";
import { fetchAlternatives, alternativeToPlace, fetchPlaceDetails } from "../api/course";
import type { AlternativePlace, GooglePlaceDetails } from "../api/course";
import { placeCost, placeKey, fmtRange } from "../utils/cost";

export default function CourseResultPage() {
  const navigate = useNavigate();
  const { plan, selectCourse, removePlace, replacePlace } = useActivePlan();
  const { input } = plan;

  const [selectedPlace, setSelectedPlace] = useState<CoursePlace | null>(null);
  // '다른 장소 추천' 패널
  const [altFor,  setAltFor]  = useState<CoursePlace | null>(null);
  const [alts,    setAlts]    = useState<AlternativePlace[]>([]);
  const [altBusy, setAltBusy] = useState(false);
  const [altMsg,  setAltMsg]  = useState("");

  const openAlternatives = async (place: CoursePlace) => {
    const list = plan.courses[plan.selectedCourse].places;
    const i = list.findIndex(p => p.name === place.name);
    setAltFor(place); setAlts([]); setAltMsg(""); setAltBusy(true);
    try {
      const r = await fetchAlternatives({
        place, date: input.date, tagsA: input.tagsA, tagsB: input.tagsB,
        exclude: list.map(p => p.name), prev: list[i - 1], next: list[i + 1],
      });
      setAlts(r.alternatives); setAltMsg(r.message);
    } catch {
      setAltMsg("다른 장소를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.");
    } finally {
      setAltBusy(false);
    }
  };

  const applyAlternative = (a: AlternativePlace) => {
    if (!altFor) return;
    const next = alternativeToPlace(a, altFor);
    replacePlace(plan.selectedCourse, altFor.name, next, a.walk_from_prev);
    setSelectedPlace(next); setAltFor(null);
  };
  const activeTab = plan.selectedCourse;
  const course = plan.courses[activeTab];
  const places = course.places;

  const budgetRange = coupleBudget(input.budgetA, input.budgetB);
  const budget = budgetRange.max;
  // 구글 상세(가격대 등) — 화면을 보는 동안만 메모리에 두고 저장하지 않음 (구글 정책)
  const [google, setGoogle] = useState<Record<string, GooglePlaceDetails | null>>({});
  const missing = places.filter(p => !(placeKey(p) in google)).map(placeKey).join(",");
  useEffect(() => {
    if (!missing) return;
    let cancelled = false;
    places.filter(p => missing.split(",").includes(placeKey(p))).forEach(p => {
      fetchPlaceDetails({ name: p.name, lat: p.lat, lon: p.lon })
        .then(d => { if (!cancelled) setGoogle(prev => ({ ...prev, [placeKey(p)]: d.found ? d : null })); })
        .catch(() => { if (!cancelled) setGoogle(prev => ({ ...prev, [placeKey(p)]: null })); });
    });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [missing]);

  const loaded = places.map(p => placeKey(p) in google);
  const costs = places.map(p => placeCost(google[placeKey(p)]));
  const known = costs.filter((c): c is Extract<typeof c, { known: true }> => c.known);
  const nUnknown = costs.length - known.length;
  const totalCost = known.reduce((s, c) => s + c.mid, 0);
  const totalRange = { known: true as const, min: known.reduce((s, c) => s + c.min, 0), max: known.reduce((s, c) => s + c.max, 0), mid: totalCost };
  const isOverBudget = known.length > 0 && totalCost > budget;

  // 선택한 날짜 기준 휴무 장소 체크
  const closedWarnings = places.filter((p) => {
    if (!p.closedDays || p.closedDays === "없음") return false;
    return p.closedDays.includes(dayOfWeekKo(input.date)) || p.possiblyClosedWarning;
  });

  const switchTab = (tab: CourseKey) => {
    selectCourse(tab);
    setSelectedPlace(null);
  };

  return (
    <div style={{ minHeight: "100vh", background: "#F5F3FB", padding: "24px 32px" }}>
      {/* 헤더 */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
        <button
          onClick={() => navigate(-1)}
          style={{ background: "#EAE5F5", border: "none", borderRadius: "8px", padding: "6px 12px", color: "#5a4480", fontSize: "13px", cursor: "pointer", flexShrink: 0 }}
        >
          ← 뒤로
        </button>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: "22px", fontWeight: "bold", color: "#5a4480", margin: 0 }}>
            {input.region.name} 데이트 코스 {getWeatherEmoji(input.weather.type)}
          </h1>
          <p style={{ fontSize: "13px", color: "#9B8EC4", margin: "4px 0 0" }}>
            📍 {input.region.name} · 📅 {formatDateShort(input.date)}
          </p>
        </div>
      </div>

      <SampleDataNotice source={course.source} />

      {/* A/B 코스 선택 탭 */}
      <div style={{ display: "flex", gap: "10px", marginBottom: "16px" }}>
        {(["A", "B"] as CourseKey[]).map((tab) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              onClick={() => switchTab(tab)}
              style={{
                padding: "10px 20px",
                borderRadius: "999px",
                border: isActive ? "none" : "1.5px solid #C9BCEB",
                background: isActive ? "#5a4480" : "#ffffff",
                color: isActive ? "#ffffff" : "#7a6aaa",
                fontSize: "14px",
                fontWeight: isActive ? 700 : 400,
                cursor: "pointer",
                transition: "all 0.2s ease",
                boxShadow: isActive ? "0 2px 8px rgba(90,68,128,0.25)" : "none",
              }}
            >
              {tab}안 · {COURSE_LABEL[tab]}
            </button>
          );
        })}
      </div>

      {/* 코스 만족도 · 공정성 */}
      {course.avgSatisfactionA != null && course.avgSatisfactionB != null && (
        <div style={{ display: "flex", gap: "14px", flexWrap: "wrap", fontSize: "12px", color: "#7B6FA0", marginBottom: "16px" }}>
          <span>A님 평균 만족도 <strong style={{ color: "#5a4480" }}>{course.avgSatisfactionA}%</strong></span>
          <span>B님 평균 만족도 <strong style={{ color: "#c0607a" }}>{course.avgSatisfactionB}%</strong></span>
          {course.fairnessGap != null && <span>만족도 격차 <strong style={{ color: "#3D3257" }}>{course.fairnessGap}%p</strong></span>}
          <span style={{ color: "#B0A8CC" }}>{course.source === "ai" ? "AI 추천" : course.source === "b2" ? "장소 DB 기반" : "샘플"}</span>
        </div>
      )}

      {/* 예산 진행 바 */}
      <div style={{ background: "#ffffff", borderRadius: "12px", padding: "14px 18px", marginBottom: "24px", border: `1px solid ${isOverBudget ? "#f5c0c0" : "#e8e4f4"}` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <span style={{ fontSize: "13px", color: "#888" }}>예상 총 비용</span>
          <div style={{ textAlign: "right" }}>
            <span style={{ fontSize: "14px", fontWeight: 700, color: isOverBudget ? "#e05555" : "#5a4480" }}>
              {known.length ? fmtRange(totalRange) : "정보 없음"}
            </span>
            <span style={{ fontSize: "11px", color: "#bbb", marginLeft: "6px" }}>
              A+B 합산 {fmtWon(budgetRange.min)} ~ {fmtWon(budgetRange.max)}
            </span>
          </div>
        </div>
        <div style={{ width: "100%", height: "8px", background: "#eee", borderRadius: "999px", overflow: "hidden" }}>
          <div
            style={{
              width: `${Math.min((totalCost / budget) * 100, 100)}%`,
              height: "100%",
              background: isOverBudget ? "#e05555" : "#b8a9d9",
              borderRadius: "999px",
              transition: "width 0.3s ease",
            }}
          />
        </div>
        <div style={{ marginTop: "6px", fontSize: "12px", color: isOverBudget ? "#e05555" : "#b8a9d9", textAlign: "right" }}>
          {!known.length ? "" : isOverBudget
            ? `⚠️ 중간값 기준 ${(totalCost - budget).toLocaleString()}원 초과`
            : `중간값 기준 ${(budget - totalCost).toLocaleString()}원 남음`}
        </div>
        <div style={{ marginTop: "2px", fontSize: "11px", color: "#bbb", textAlign: "right" }}>
          {loaded.every(Boolean)
            ? `Google Maps 1인 가격대 × 2명 기준${nUnknown ? ` · 가격 정보 없는 ${nUnknown}곳 제외` : ""}`
            : "가격 정보를 불러오는 중..."}
        </div>
      </div>

      {/* 메인 그리드 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "24px", alignItems: "start" }}>
        {/* 왼쪽 — 취향 교집합 + 지도 */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <PreferenceIntersection personA={input.tagsA} personB={input.tagsB} common={commonTags(input.tagsA, input.tagsB)} />
          <KakaoMap places={places} selectedPlace={selectedPlace} onSelectPlace={setSelectedPlace} />
        </div>

        {/* 오른쪽 — 코스 타임라인 */}
        <div style={{ background: "#FFFFFF", borderRadius: "16px", padding: "16px", border: "1px solid #E8E4F4", boxShadow: "0 1px 4px rgba(184,169,217,0.15)" }}>
          {/* 휴무 경고 */}
          {closedWarnings.length > 0 && (
            <div style={{ marginBottom: "14px", display: "flex", flexDirection: "column", gap: "6px" }}>
              {closedWarnings.map((p) => (
                <div key={p.name} style={{ background: "#FFF8E1", border: "1px solid #FFD54F", borderRadius: "10px", padding: "9px 14px", fontSize: "12px", color: "#a05800" }}>
                  ⚠ <strong>{p.name}</strong> — {p.closedDays} 휴무예요. 예약 전 확인하세요.
                </div>
              ))}
            </div>
          )}
          <CourseTimeline places={places} onSelectPlace={setSelectedPlace} costs={places.map((_, i) => (loaded[i] ? costs[i] : undefined))} />
        </div>
      </div>

      {/* 장소 상세 카드 */}
      {selectedPlace && (
        <div style={{ marginTop: "24px" }}>
          <PlaceDetailCard
            place={selectedPlace}
            onClose={() => setSelectedPlace(null)}
            onSkip={(place) => {
              removePlace(activeTab, place.name);
              setSelectedPlace(null);
            }}
            onRecommendOther={openAlternatives}
            google={placeKey(selectedPlace) in google ? google[placeKey(selectedPlace)] : undefined}
            visitDate={input.date}
            onWishlist={(place) => console.log("찜하기:", place.name)}
          />
        </div>
      )}

      {/* 다른 장소 추천 결과 */}
      {altFor && (
        <div style={{ marginTop: "16px", background: "#fff", borderRadius: "16px", padding: "18px", border: "1px solid #e8e4f4" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <p style={{ fontSize: "14px", fontWeight: 700, color: "#5a4480", margin: 0 }}>'{altFor.name}' 대신 갈 만한 곳</p>
            <button onClick={() => setAltFor(null)} style={{ background: "none", border: "none", color: "#b8a9d9", fontSize: "16px", cursor: "pointer" }}>✕</button>
          </div>
          {altBusy && <p style={{ fontSize: "13px", color: "#7B6FA0", margin: 0 }}>주변 1 km에서 영업 중인 곳을 찾는 중... (10~30초)</p>}
          {!altBusy && altMsg && <p style={{ fontSize: "13px", color: "#7B6FA0", margin: 0 }}>{altMsg}</p>}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {alts.map(a => (
              <button key={a.name} onClick={() => applyAlternative(a)} style={{ textAlign: "left", background: "#F5F3FB", border: "1px solid #e8e4f4", borderRadius: "12px", padding: "12px", cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
                  <span style={{ fontSize: "14px", fontWeight: 700, color: "#3D3257" }}>{a.name}</span>
                  <span style={{ fontSize: "11px", color: a.open_status === "open" ? "#388E3C" : "#999", whiteSpace: "nowrap" }}>
                    {a.open_status === "open" ? "방문 시각 영업 중" : "영업시간 확인 필요"}
                  </span>
                </div>
                <div style={{ fontSize: "12px", color: "#7B6FA0", marginTop: "4px" }}>
                  {a.category} · A {a.satisfaction_a}점 · B {a.satisfaction_b}점
                  {a.walk_from_prev != null && ` · 앞 장소에서 도보 ${a.walk_from_prev}분`}
                </div>
                {a.address && <div style={{ fontSize: "11px", color: "#B0A8CC", marginTop: "2px" }}>{a.address}</div>}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 다음 단계 */}
      <div style={{ marginTop: "32px" }}>
        <button
          onClick={() => navigate("/booking")}
          style={{ width: "100%", padding: "16px", background: "#5a4480", color: "#fff", border: "none", borderRadius: "14px", fontSize: "16px", fontWeight: 700, cursor: "pointer", boxShadow: "0 4px 20px rgba(90,68,128,0.3)" }}
        >
          {activeTab}안 선택 →
        </button>
      </div>
    </div>
  );
}
