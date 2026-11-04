import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { C, FONT, GS_FORM } from "../constants/theme";
import { DEFAULT_LAT, DEFAULT_LON, KAKAO_JS_KEY } from "../config";
import { fetchWeather, geocodeCity, WEATHER_META } from "../api/weather";
import type { WeatherSnapshot } from "../api/weather";
import { savePrefs } from "../api/prefs";
import { usePlan } from "../contexts/PlanContext";
import type { RegionValue } from "../contexts/PlanContext";
import type { GeneratedCourse } from "../types/course";
import { BUDGET_VALUES, budgetAt, budgetOverlap, fmtBudget } from "../utils/budget";
import type { BudgetRange } from "../utils/budget";
import { formatDateKo, todayStr } from "../utils/date";
import RegionInput from "../components/onboarding/RegionInput";
import WeatherBadge from "../components/onboarding/WeatherBadge";
import CalendarPicker from "../components/onboarding/CalendarPicker";
import LoadingScreen from "../components/onboarding/LoadingScreen";
import { LOADING_STEPS } from "../constants/course";
import PreferenceStep from "../components/onboarding/PreferenceStep";
import BudgetStep from "../components/onboarding/BudgetStep";

const DEFAULT_BUDGET: BudgetRange = { minIdx: 2, maxIdx: 5 };

// 코스는 이벤트 선택 뒤 생성 — 그 전까지 비워 둔다 (샘플 데이터를 보여주지 않음)
const EMPTY_COURSE: GeneratedCourse = { title: "", places: [], source: "ai" };
const EMPTY_COURSES = { A: EMPTY_COURSE, B: EMPTY_COURSE };

const toggle = (list: string[], tag: string) => list.includes(tag) ? list.filter(t => t !== tag) : [...list, tag];
const rangeLabel = (r: BudgetRange) => `${fmtBudget(BUDGET_VALUES[r.minIdx])} ~ ${fmtBudget(BUDGET_VALUES[r.maxIdx])}`;

export default function OnboardingPage() {
  const navigate = useNavigate();
  const { startPlan } = usePlan();

  const [region,     setRegion]     = useState<RegionValue | null>(null);
  const [dateStr,    setDateStr]    = useState(todayStr());
  const [tagsA,      setTagsA]      = useState<string[]>([]);
  const [tagsB,      setTagsB]      = useState<string[]>([]);
  const [budgetA,    setBudgetA]    = useState<BudgetRange>(DEFAULT_BUDGET);
  const [budgetB,    setBudgetB]    = useState<BudgetRange>(DEFAULT_BUDGET);

  const [step,       setStep]       = useState(0);
  const [loadingMsg, setLoadingMsg] = useState("");
  const [wxPreview,  setWxPreview]  = useState<WeatherSnapshot | null>(null);
  const [wxLoading,  setWxLoading]  = useState(false);
  const [isMobile,   setIsMobile]   = useState(window.innerWidth <= 480);

  const [sessionId] = useState(() => `df_${Date.now()}`);

  useEffect(() => {
    const h = () => setIsMobile(window.innerWidth <= 480);
    window.addEventListener("resize", h);
    return () => window.removeEventListener("resize", h);
  }, []);

  const overlap = budgetOverlap(budgetA, budgetB);

  // 지역·날짜가 바뀌면 날씨 미리보기 갱신
  useEffect(() => {
    let cancelled = false;
    const doFetch = async () => {
      if (!region?.name) {
        setWxPreview(null);
        setWxLoading(false);
        return;
      }
      setWxLoading(true);
      try {
        let { lat, lon, name } = region;
        if (lat == null || lon == null) {
          const g = await geocodeCity(region.name);
          if (!g) throw new Error("지역을 찾을 수 없어요");
          ({ lat, lon, name } = g);
        }
        const wx = await fetchWeather(lat, lon, name, dateStr);
        if (!cancelled) setWxPreview(wx);
      } catch {
        if (!cancelled) setWxPreview(null);
      } finally {
        if (!cancelled) setWxLoading(false);
      }
    };
    doFetch();
    return () => { cancelled = true; };
  }, [region, dateStr]);

  const handleGenerate = async () => {
    if (!region) return;

    setLoadingMsg(LOADING_STEPS[0]);
    let lat = region.lat ?? DEFAULT_LAT;
    let lon = region.lon ?? DEFAULT_LON;
    let cityName = region.name;
    if (region.lat == null || region.lon == null) {
      try {
        const g = await geocodeCity(cityName);
        if (g) ({ lat, lon, name: cityName } = g);
      } catch { /* 기본 좌표 사용 */ }
    }

    setLoadingMsg(LOADING_STEPS[1]);
    let weather: WeatherSnapshot = wxPreview ?? { type: "cloudy", temp: null, cityName, source: "openmeteo" };
    if (!wxPreview) {
      try { weather = await fetchWeather(lat, lon, cityName, dateStr); } catch { /* 흐림으로 가정 */ }
    }
    weather = { ...weather, cityName };

    setLoadingMsg(LOADING_STEPS[2]);
    await savePrefs(sessionId, tagsA, tagsB, budgetAt(overlap ? overlap.minIdx : budgetA.maxIdx));

    // 코스는 이벤트를 고른 뒤 EventSelectPage 에서 생성 (선택한 이벤트를 중심으로 짜기 위해)
    startPlan(sessionId, {
      region: { name: cityName, lat, lon }, date: dateStr, tagsA, tagsB, budgetA, budgetB, weather,
    }, EMPTY_COURSES);

    setLoadingMsg("이벤트를 추천하러 가요 ✦");
    await new Promise(r => setTimeout(r, 700));
    navigate("/events");
  };

  const wrap  = { minHeight:"100vh", background:C.bg, fontFamily:FONT, display:"flex" as const, flexDirection:"column" as const, alignItems:"center" as const, padding:"0 0 80px" };
  const inner = { maxWidth:"420px", width:"100%", padding: isMobile ? "28px 14px 0" : "48px 20px 0" };
  const areaName = region?.name || "";

  if (loadingMsg) return <LoadingScreen message={loadingMsg} />;

  // ── STEP 0: 랜딩 (날짜·지역) ──────────────────────────────
  if (step === 0) return (
    <div style={wrap}><style>{GS_FORM}</style>
      <div className="df-inner" style={{ ...inner, paddingTop: isMobile ? 40 : 64, animation:"fadeUp 0.5s ease" }}>
        <div style={{ fontSize:11, letterSpacing:"0.2em", color:C.main, marginBottom:16, textTransform:"uppercase", fontWeight:600 }}>Capstone 12조</div>
        <h1 className="df-title" style={{ fontSize:40, fontWeight:900, color:C.text, margin:"0 0 8px", lineHeight:1.15, letterSpacing:"-0.03em" }}>
          Date<span style={{ color:C.main }}>Flow</span>
        </h1>
        <p style={{ fontSize:15, color:C.textDim, margin:"0 0 28px", lineHeight:1.7 }}>두 사람의 취향을 분석해<br />딱 맞는 데이트 코스를 만들어드려요</p>
        {[
          { icon:"📍", text: KAKAO_JS_KEY ? "카카오 API 실시간 지역 검색" : "전국 어디든 지역명 입력" },
          { icon:"🌤", text:"선택 즉시 날씨 자동 확인" },
          { icon:"💰", text:"A/B 각자 예산 · 직접 입력 가능" },
          { icon:"✦",  text:"취향 교집합 코스 자동 생성" },
        ].map((x, i) => (
          <div key={i} style={{ display:"flex", alignItems:"center", gap:14, marginBottom:10, animation:`fadeUp 0.5s ease ${0.06+i*0.07}s both` }}>
            <span style={{ fontSize:16, width:22, textAlign:"center" }}>{x.icon}</span>
            <span style={{ fontSize:14, color:C.textDim }}>{x.text}</span>
          </div>
        ))}
        <div style={{ marginTop:24 }}>
          <label style={{ fontSize:12, color:C.textDim, display:"block", marginBottom:8, fontWeight:500 }}>데이트 날짜</label>
          <CalendarPicker value={dateStr} onChange={setDateStr} />
          <label style={{ fontSize:12, color:C.textDim, display:"block", marginBottom:8, fontWeight:500 }}>데이트 지역</label>
          <RegionInput value={region} onChange={setRegion} />
          <div style={{ marginTop:8, marginBottom:16, minHeight:wxLoading ? 48 : 0 }}>
            <WeatherBadge wx={wxPreview} loading={wxLoading && !wxPreview} />
          </div>
        </div>
        <button onClick={() => setStep(1)} disabled={!areaName}
          style={{ width:"100%", padding:16, background:areaName?C.main:C.inputBg, color:areaName?"#fff":C.textMuted, border:"none", borderRadius:14, fontSize:16, fontWeight:700, cursor:areaName?"pointer":"not-allowed", fontFamily:FONT, boxShadow:areaName?"0 4px 20px #B8A9D950":"none", transition:"all 0.2s" }}>
          시작하기 →
        </button>
      </div>
    </div>
  );

  return (
    <div style={wrap}><style>{GS_FORM}</style>
      <div className="df-inner" style={{ ...inner, animation:"fadeUp 0.35s ease" }} key={step}>
        {step === 1 && (
          <PreferenceStep step={1} who="A" tags={tagsA} onToggle={t => setTagsA(toggle(tagsA, t))}
            onBack={() => setStep(0)} onNext={() => setStep(2)} nextLabel="A님 예산 설정 →" />
        )}
        {step === 2 && (
          <BudgetStep step={2} who="A" value={budgetA} onChange={setBudgetA}
            onBack={() => setStep(1)} onNext={() => setStep(3)} nextLabel="B님 취향 입력 →" />
        )}
        {step === 3 && (
          <PreferenceStep step={3} who="B" tags={tagsB} onToggle={t => setTagsB(toggle(tagsB, t))}
            onBack={() => setStep(2)} onNext={() => setStep(4)} nextLabel="B님 예산 설정 →" />
        )}
        {step === 4 && (
          <BudgetStep step={4} who="B" value={budgetB} onChange={setBudgetB}
            onBack={() => setStep(3)} onNext={handleGenerate} nextLabel="날씨 확인 후 코스 생성 ✦">
            <div style={{ background:overlap?C.skyDim:C.errorBg, border:`1px solid ${overlap?C.sky:C.error}44`, borderRadius:12, padding:"14px 16px", marginBottom:20 }}>
              {overlap
                ? (<><div style={{ fontSize:13, color:C.sky, fontWeight:700, marginBottom:4 }}>✓ 예산 교집합</div><div style={{ fontSize:13, color:C.text }}>{rangeLabel(overlap)}</div><div style={{ fontSize:11, color:C.textMuted, marginTop:4 }}>이 범위 안의 장소로 코스를 구성해요</div></>)
                : (<><div style={{ fontSize:13, color:C.error, fontWeight:700, marginBottom:4 }}>⚠ 예산 범위가 겹치지 않아요</div><div style={{ fontSize:11, color:C.error, marginTop:4 }}>두 분 예산을 합산한 범위로 코스를 생성해요</div></>)}
            </div>
            <div style={{ background:C.card, border:`1px solid ${C.cardBorder}`, borderRadius:16, padding:16, marginBottom:20 }}>
              <div style={{ fontSize:11, color:C.main, marginBottom:10, fontWeight:600 }}>입력 요약</div>
              {[
                { k:"지역",     v: areaName },
                { k:"날짜",     v: dateStr ? formatDateKo(dateStr) : "미선택" },
                { k:"날씨",     v: wxPreview ? `${WEATHER_META[wxPreview.type].label} · ${wxPreview.temp ?? "?"}°C` : "생성 시 자동 확인" },
                { k:"A님 취향", v: tagsA.length ? tagsA.slice(0,3).join(", ") : "미선택" },
                { k:"A님 예산", v: rangeLabel(budgetA) },
                { k:"B님 취향", v: tagsB.length ? tagsB.slice(0,3).join(", ") : "미선택" },
                { k:"B님 예산", v: rangeLabel(budgetB) },
              ].map(({ k, v }) => (
                <div key={k} style={{ display:"flex", gap:10, fontSize:12, marginBottom:5 }}>
                  <span style={{ color:C.textMuted, width:64, flexShrink:0 }}>{k}</span>
                  <span style={{ color:k==="날씨"?C.sky:C.text }}>{v}</span>
                </div>
              ))}
            </div>
          </BudgetStep>
        )}
      </div>
    </div>
  );
}
