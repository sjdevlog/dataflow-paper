import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { C, FONT, GS } from "../constants/theme";
import { usePlan } from "../contexts/PlanContext";
import PageHeader from "../components/common/PageHeader";
import AiBubble from "../components/common/AiBubble";

type Event = { icon: string; name: string; sub: string; category: string };

const REGION_EVENTS: { keywords: string[]; events: Event[] }[] = [
  {
    keywords: ["성수", "뚝섬"],
    events: [
      { icon: "🎨", name: "OO 갤러리",    sub: "도시의 빛",       category: "전시" },
      { icon: "👟", name: "무신사 X 팝업", sub: "마케팅 팝업",      category: "팝업" },
      { icon: "🎬", name: "성수 시네마",   sub: "나의 아름다운",     category: "영화" },
      { icon: "🎭", name: "소극장 행복",   sub: "연극",             category: "공연" },
    ],
  },
  {
    keywords: ["홍대", "합정", "상수"],
    events: [
      { icon: "🎵", name: "인디 공연",     sub: "버스킹 위크",      category: "공연" },
      { icon: "🖼️", name: "갤러리 홍",    sub: "청년 작가전",       category: "전시" },
      { icon: "🧁", name: "디저트 팝업",   sub: "베이킹 클래스",     category: "팝업" },
      { icon: "🃏", name: "보드게임 카페", sub: "주말 토너먼트",      category: "활동" },
    ],
  },
  {
    keywords: ["강남", "신사", "압구정"],
    events: [
      { icon: "🛍️", name: "럭셔리 팝업", sub: "신상 컬렉션",       category: "팝업" },
      { icon: "🎭", name: "예술의전당",   sub: "클래식 공연",        category: "공연" },
      { icon: "🍷", name: "와인 페어",    sub: "가로수길 와인&푸드", category: "푸드" },
      { icon: "🧖", name: "뷰티 팝업",   sub: "체험 이벤트",        category: "팝업" },
    ],
  },
];

const DEFAULT_EVENTS: Event[] = [
  { icon: "🎨", name: "갤러리 전시",  sub: "현대 미술전",    category: "전시" },
  { icon: "🎵", name: "공연·콘서트", sub: "주말 라이브",     category: "공연" },
  { icon: "🛍️", name: "팝업 스토어", sub: "한정판 컬렉션",  category: "팝업" },
  { icon: "🍽️", name: "푸드 페스타", sub: "지역 맛집 행사", category: "푸드" },
];

function getEventsForRegion(region: string): Event[] {
  const match = REGION_EVENTS.find(r => r.keywords.some(k => region.includes(k)));
  return match ? match.events : DEFAULT_EVENTS;
}

export default function EventSelectPage() {
  const navigate = useNavigate();
  const { plan, setEvents } = usePlan();
  const region   = plan?.input.region.name || "성수동";

  const [events]                = useState<Event[]>(() => getEventsForRegion(region));
  const [selected, setSelected] = useState<number[]>(
    () => (plan?.events ?? []).map(name => events.findIndex(e => e.name === name)).filter(i => i >= 0)
  );
  const [showAI,   setShowAI]   = useState(false);
  const [showCards, setShowCards] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setShowAI(true),    400);
    const t2 = setTimeout(() => setShowCards(true), 800);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  const toggle = (i: number) => {
    setSelected(prev => prev.includes(i) ? prev.filter(x => x !== i) : [...prev, i]);
  };

  const handleNext = () => {
    setEvents(selected.map(i => events[i].name));
    navigate("/courses");
  };

  return (
    <div style={{ minHeight: "100vh", background: C.bg, padding: "32px 20px 60px", fontFamily: FONT }}>
      <style>{GS}</style>

      <PageHeader label="이벤트 추천" />

      {showAI && <AiBubble message={`지금 ${region}에서 이런 이벤트들이 진행 중이에요!`} hint="관심 있는 이벤트를 골라보세요" />}

      {/* 이벤트 카드 2×2 그리드 */}
      {showCards && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 28 }}>
          {events.map((ev, i) => {
            const isSel = selected.includes(i);
            return (
              <div key={i} onClick={() => toggle(i)} style={{
                background:   isSel ? C.mainDim : C.card,
                border:       `2px solid ${isSel ? C.mainDark : C.cardBorder}`,
                borderRadius: 18, padding: "18px 14px", cursor: "pointer",
                textAlign: "center", transition: "all 0.2s ease", position: "relative",
                boxShadow:  isSel ? "0 4px 16px rgba(122,92,189,0.25)" : "0 2px 8px rgba(0,0,0,0.05)",
                animation:  `popIn 0.35s ease ${i * 0.08}s both`,
              }}>
                {isSel && <div style={{ position: "absolute", top: 10, right: 12, fontSize: 14, color: C.mainDark, fontWeight: 700 }}>✓</div>}
                <div style={{ fontSize: 30, marginBottom: 8 }}>{ev.icon}</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: isSel ? C.mainDark : C.text, marginBottom: 3 }}>{ev.name}</div>
                <div style={{ fontSize: 11, color: C.textDim, background: isSel ? C.mainDim : C.inputBg, padding: "2px 8px", borderRadius: "999px", display: "inline-block" }}>
                  {ev.sub}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selected.length > 0 && (
        <div style={{ background: C.mainDim, borderRadius: 12, padding: "10px 16px", marginBottom: 16, fontSize: 12, color: C.mainDark, fontWeight: 600, animation: "fadeUp 0.3s ease" }}>
          선택됨: {selected.map(i => events[i]?.name).join(", ")}
        </div>
      )}

      {showCards && (
        <button onClick={handleNext} style={{ width: "100%", padding: 16, background: C.mainDark, color: "#fff", border: "none", borderRadius: 14, fontSize: 15, fontWeight: 700, cursor: "pointer", boxShadow: "0 4px 20px rgba(90,68,128,0.3)", fontFamily: FONT, animation: "fadeUp 0.4s ease 0.4s both" }}>
          {selected.length > 0 ? `${selected.length}개 이벤트 포함해서 코스 짜줘 →` : "이벤트 없이 코스 짜줘 →"}
        </button>
      )}
    </div>
  );
}
