import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { C, FONT, GS } from "../constants/theme";
import { useActivePlan } from "../contexts/PlanContext";
import { fetchEvents, generateCourses } from "../api/course";
import type { RecommendedEvent } from "../api/course";
import { coupleBudget } from "../utils/budget";
import { LOADING_STEPS } from "../constants/course";
import PageHeader from "../components/common/PageHeader";
import AiBubble from "../components/common/AiBubble";
import LoadingScreen from "../components/onboarding/LoadingScreen";

const CAT_ICON: Record<string, string> = { 전시: "🎨", 공연: "🎭", 영화: "🎬", 팝업: "🛍️", 체험: "🧶" };

/** 메인 이벤트 선택 — 선택한 지역 근처에 실제로 있는 장소만 AI가 추천 (가짜 목록 없음) */
export default function EventSelectPage() {
  const navigate = useNavigate();
  const { plan, setCourses } = useActivePlan();
  const { region, date, tagsA, tagsB, budgetA, budgetB, weather } = plan.input;

  const [events,   setEvents]   = useState<RecommendedEvent[]>([]);
  const [message,  setMessage]  = useState("");
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(false);
  const [moreBusy, setMoreBusy] = useState(false);
  const [noMore,   setNoMore]   = useState(false);
  const [selected, setSelected] = useState<string | null>(plan.selectedEvent?.name ?? null);
  const [genMsg,   setGenMsg]   = useState("");
  const [genError, setGenError] = useState(false);
  const started = useRef(false);

  const base = { region: region.name, lat: region.lat, lon: region.lon, date, tagsA, tagsB };

  const load = async () => {
    setLoading(true); setError(false);
    try {
      const r = await fetchEvents(base);
      setEvents(r.events); setMessage(r.message);
    } catch (e) {
      console.warn("이벤트 추천 실패", e);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (started.current) return;      // StrictMode 이중 실행 방지 (AI 호출은 한 번만)
    started.current = true;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadMore = async () => {
    setMoreBusy(true);
    try {
      const r = await fetchEvents({ ...base, more: true, exclude: events.map(e => e.name) });
      if (r.events.length === 0) setNoMore(true);
      setEvents(prev => [...prev, ...r.events]);
    } catch {
      setNoMore(true);
    } finally {
      setMoreBusy(false);
    }
  };

  const handleNext = async () => {
    const ev = events.find(e => e.name === selected) ?? null;
    setGenMsg(LOADING_STEPS[3]);
    const budget = coupleBudget(budgetA, budgetB);
    try {
      const courses = await generateCourses({
        sessionId: plan.sessionId, region: region.name, lat: region.lat, lon: region.lon, date,
        weather: weather.type, temp: weather.temp, budgetMin: budget.min, budgetMax: budget.max,
        tagsA, tagsB, selectedEvent: ev, noEvent: !ev,
      });
      setCourses(courses, ev);
      navigate("/courses");
    } catch (e) {
      console.warn("코스 생성 실패", e);
      setGenMsg(""); setGenError(true);
    }
  };

  if (genMsg) return <LoadingScreen message={genMsg} />;

  const card = (ev: RecommendedEvent, i: number) => {
    const isSel = selected === ev.name;
    return (
      <div key={ev.name} onClick={() => setSelected(isSel ? null : ev.name)} style={{
        background:   isSel ? C.mainDim : C.card,
        border:       `2px solid ${isSel ? C.mainDark : C.cardBorder}`,
        borderRadius: 18, padding: "16px 14px", cursor: "pointer",
        transition: "all 0.2s ease", position: "relative",
        boxShadow:  isSel ? "0 4px 16px rgba(122,92,189,0.25)" : "0 2px 8px rgba(0,0,0,0.05)",
        animation:  `popIn 0.35s ease ${Math.min(i, 6) * 0.06}s both`,
      }}>
        {isSel && <div style={{ position: "absolute", top: 10, right: 12, fontSize: 14, color: C.mainDark, fontWeight: 700 }}>✓</div>}
        <div style={{ fontSize: 26, marginBottom: 6 }}>{CAT_ICON[ev.category] ?? "✨"}</div>
        <div style={{ fontSize: 13, fontWeight: 700, color: isSel ? C.mainDark : C.text, marginBottom: 4, lineHeight: 1.35 }}>{ev.name}</div>
        <div style={{ fontSize: 11, color: C.textDim, background: isSel ? C.card : C.inputBg, padding: "2px 8px", borderRadius: 999, display: "inline-block", marginBottom: 6 }}>
          {ev.category}
        </div>
        {ev.reason && <div style={{ fontSize: 11, color: C.text, lineHeight: 1.45, marginBottom: 4 }}>{ev.reason}</div>}
        {ev.address && <div style={{ fontSize: 10.5, color: C.textMuted, lineHeight: 1.4 }}>{ev.address}</div>}
      </div>
    );
  };

  const nextLabel = selected ? `'${selected}' 중심으로 코스 짜줘 →`
    : events.length ? "이벤트 없이 코스 짜줘 →" : "카페·식당 중심으로 코스 짜줘 →";

  return (
    <div style={{ minHeight: "100vh", background: C.bg, padding: "32px 20px 60px", fontFamily: FONT }}>
      <style>{GS}</style>
      <PageHeader label="이벤트 추천" />

      {loading && (
        <div style={{ textAlign: "center", padding: "60px 0" }}>
          <div style={{ fontSize: 40, animation: "spin 1.6s linear infinite", display: "inline-block", color: C.main, marginBottom: 18 }}>◎</div>
          <p style={{ color: C.text, fontSize: 15, fontWeight: 600, marginBottom: 6 }}>{region.name} 근처 이벤트를 찾는 중</p>
          <p style={{ color: C.textDim, fontSize: 13 }}>두 분의 취향에 맞는 실제 장소만 골라요 (20~40초)</p>
        </div>
      )}

      {!loading && error && (
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <p style={{ color: C.text, fontSize: 14, marginBottom: 14 }}>이벤트를 불러오지 못했어요.</p>
          <button onClick={load} style={{ padding: "10px 18px", borderRadius: 12, border: `1px solid ${C.cardBorder}`, background: C.card, color: C.mainDark, fontWeight: 700, cursor: "pointer", fontFamily: FONT }}>
            다시 시도
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          <AiBubble
            message={events.length ? `${region.name} 근처에서 두 분께 맞는 이벤트를 찾았어요!` : message}
            hint={events.length ? "하나를 고르면 그 장소를 중심으로 코스를 짜요" : undefined}
          />

          {events.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
              {events.map(card)}
            </div>
          )}

          {events.length > 0 && !noMore && (
            <button onClick={loadMore} disabled={moreBusy} style={{ width: "100%", padding: 12, marginBottom: 22, background: C.card, color: C.mainDark, border: `1.5px dashed ${C.main}`, borderRadius: 14, fontSize: 13, fontWeight: 700, cursor: moreBusy ? "default" : "pointer", fontFamily: FONT }}>
              {moreBusy ? "주변 장소를 더 찾는 중..." : "+ 더 보기"}
            </button>
          )}
          {noMore && events.length > 0 && (
            <p style={{ textAlign: "center", fontSize: 12, color: C.textDim, marginBottom: 22 }}>주변에서 더 찾을 수 있는 장소가 없어요.</p>
          )}

          {genError && (
            <p style={{ textAlign: "center", fontSize: 13, color: C.error, marginBottom: 12 }}>
              코스를 만들지 못했어요. 잠시 후 다시 눌러 주세요.
            </p>
          )}
          <button onClick={() => { setGenError(false); handleNext(); }} style={{ width: "100%", padding: 16, background: C.mainDark, color: "#fff", border: "none", borderRadius: 14, fontSize: 15, fontWeight: 700, cursor: "pointer", boxShadow: "0 4px 20px rgba(90,68,128,0.3)", fontFamily: FONT }}>
            {nextLabel}
          </button>
        </>
      )}
    </div>
  );
}
