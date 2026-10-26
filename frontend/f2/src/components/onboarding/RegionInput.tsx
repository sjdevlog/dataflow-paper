import { useState, useRef, useEffect, useCallback } from "react";
import { C, FONT } from "../../constants/theme";
import { KAKAO_JS_KEY } from "../../config";
import { searchKakaoPlaces } from "../../api/kakaoPlaces";
import type { PlaceSearchResult } from "../../api/kakaoPlaces";
import type { RegionValue } from "../../contexts/PlanContext";

export default function RegionInput({ value, onChange }: { value: RegionValue | null; onChange: (v: RegionValue | null) => void }) {
  const [query,    setQuery]   = useState(value?.name || "");
  const [results,  setResults] = useState<PlaceSearchResult[]>([]);
  const [loading,  setLoading] = useState(false);
  const [open,     setOpen]    = useState(false);
  const ref        = useRef<HTMLDivElement>(null);
  const debRef     = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasKey     = !!KAKAO_JS_KEY;

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); setOpen(false); return; }
    setLoading(true);
    try {
      const list = await searchKakaoPlaces(q);
      setResults(list);
      setOpen(list.length > 0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setQuery(q);
    onChange(null);
    if (hasKey) {
      if (debRef.current) clearTimeout(debRef.current);
      debRef.current = setTimeout(() => doSearch(q), 350);
    }
  };

  const handleFreeForm = () => {
    // 확정 후 늦게 도착한 검색 결과가 드롭다운을 다시 열지 않도록
    if (debRef.current) clearTimeout(debRef.current);
    if (query.trim() && !value?.name) {
      onChange({ name: query.trim(), lat: null, lon: null });
    }
  };

  const handleSelect = (result: PlaceSearchResult) => {
    setQuery(result.name);
    setOpen(false);
    onChange(result);
  };

  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  return (
    <div ref={ref} style={{ position:"relative", marginBottom:8 }}>
      <div style={{ position:"relative" }}>
        <input
          value={query}
          onChange={handleInput}
          onFocus={() => results.length > 0 && setOpen(true)}
          onBlur={handleFreeForm}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); handleFreeForm(); setOpen(false); } }}
          placeholder={hasKey ? "지역·장소 검색 (예: 홍대, 해운대, 한옥마을)" : "지역명 직접 입력 후 Enter (예: 성수동)"}
          style={{ width:"100%", padding:"14px 16px", paddingRight:40, background:C.card, border:`1.5px solid ${C.inputBorder}`, borderRadius:14, color:C.text, fontSize:15, fontFamily:FONT }}
        />
        {loading && (
          <span style={{ position:"absolute", right:14, top:"50%", transform:"translateY(-50%)", fontSize:11, color:C.textMuted, animation:"pulse 1s ease infinite" }}>검색 중</span>
        )}
      </div>

      {!hasKey && (
        <p style={{ fontSize:11, color:C.textMuted, margin:"6px 0 0 4px", lineHeight:1.5 }}>
          💡 <code style={{ background:C.inputBg, padding:"1px 5px", borderRadius:4, fontSize:10 }}>VITE_KAKAO_MAPS_API_KEY</code> 설정 시 자동완성 활성화
        </p>
      )}

      {open && results.length > 0 && (
        <div style={{ position:"absolute", top:"calc(100% + 4px)", left:0, right:0, background:C.card, border:`1px solid ${C.cardBorder}`, borderRadius:14, zIndex:200, overflow:"hidden", boxShadow:"0 8px 24px #B8A9D930", animation:"fadeIn 0.15s ease" }}>
          {results.map((r, i) => (
            <button
              key={i}
              // mousedown 에서 input blur → 직접입력 확정 → 레이아웃 이동으로 클릭이 빗나가는 것 방지
              onMouseDown={e => e.preventDefault()}
              onClick={() => handleSelect(r)}
              style={{ width:"100%", padding:"11px 16px", background:"transparent", border:"none", borderBottom: i < results.length-1 ? `1px solid ${C.cardBorder}` : "none", color:C.text, fontSize:14, textAlign:"left", cursor:"pointer", fontFamily:FONT }}
              onMouseEnter={e => (e.currentTarget.style.background = C.mainDim)}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              <div style={{ fontWeight:600, marginBottom:2 }}>📍 {r.name}</div>
              <div style={{ fontSize:11, color:C.textMuted }}>{r.address}</div>
            </button>
          ))}
        </div>
      )}

      {value?.name && (
        <p style={{ fontSize:11, color:C.main, margin:"6px 0 0 4px", fontWeight:600 }}>
          ✓ {value.name} 선택됨 {value.lat != null && value.lon != null && <span style={{ color:C.textMuted }}>({value.lat.toFixed(3)}, {value.lon.toFixed(3)})</span>}
        </p>
      )}
    </div>
  );
}
