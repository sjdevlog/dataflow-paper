import { useEffect, useState } from "react";
import type { CoursePlace } from "../types/course";
import { fetchCrowd } from "../api/course";
import type { CrowdResult } from "../api/course";
import { GoogleAttribution } from "./GooglePlaceInfo";

const DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const DAY_KO: Record<string, string> = { sunday: "일", monday: "월", tuesday: "화", wednesday: "수", thursday: "목", friday: "금", saturday: "토" };

// 같은 장소는 한 번만 조회 (SerpApi 무료 월 250회 절약, StrictMode 이중 호출 방지). 새로고침하면 비워진다
const cache = new Map<string, Promise<CrowdResult>>();
const getCrowd = (key: string, p: { name: string; lat: number; lon: number }) => {
    if (!cache.has(key)) cache.set(key, fetchCrowd(p).catch(e => { cache.delete(key); throw e; }));
    return cache.get(key)!;
};

const hourOf = (t: string) => { const m = /^(\d{1,2})/.exec(t || ""); return m ? Number(m[1]) : null; };
const label = (h: number) => (h === 0 ? "자정" : h < 12 ? `오전 ${h}시` : h === 12 ? "정오" : `오후 ${h - 12}시`);

/** 방문 요일의 시간대별 혼잡도 (구글맵 '인기 시간대') — 방문 시각 막대를 강조 */
export default function CrowdBars({ place, visitDate }: { place: CoursePlace; visitDate?: string }) {
    const key = `${place.name}|${place.lat}|${place.lon}`;
    const [res, setRes] = useState<{ key: string; c: CrowdResult | null } | null>(null);
    useEffect(() => {
        let cancelled = false;
        getCrowd(key, { name: place.name, lat: place.lat, lon: place.lon })
            .then(c => { if (!cancelled) setRes({ key, c }); })
            .catch(() => { if (!cancelled) setRes({ key, c: null }); });
        return () => { cancelled = true; };
    }, [key, place.name, place.lat, place.lon]);

    const loading = res?.key !== key;
    const c = loading ? null : res?.c;
    const day = visitDate ? DAYS[new Date(`${visitDate}T00:00:00`).getDay()] : DAYS[new Date().getDay()];
    const rows = (c?.found && c.days?.[day]) || [];
    const visitHour = hourOf(place.time);
    const atVisit = rows.find(r => r.hour === visitHour);

    return (
        <div>
            <p style={{ fontSize: 13, fontWeight: 600, color: "#3d3d3d", marginBottom: 8 }}>
                시간대별 혼잡도 <span style={{ fontSize: 11, color: "#999", fontWeight: 400 }}>({DAY_KO[day]}요일 기준)</span>
            </p>
            {loading && <p style={{ fontSize: 12, color: "#bbb", margin: 0 }}>불러오는 중...</p>}
            {!loading && !rows.length && <p style={{ fontSize: 12, color: "#999", margin: 0 }}>정보 없음</p>}
            {rows.length > 0 && (
                <>
                    {(atVisit?.info || c?.live_info) && (
                        <p style={{ fontSize: 12, color: "#5a4480", margin: "0 0 8px" }}>
                            {c?.live_info ? `지금: ${c.live_info}` : `${label(atVisit!.hour)}: ${atVisit!.info}`}
                        </p>
                    )}
                    <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 64 }}>
                        {rows.map(r => (
                            <div key={r.hour} title={`${label(r.hour)} ${r.info || ""}`} style={{
                                flex: 1, height: `${Math.max(r.score, 3)}%`, borderRadius: 3,
                                background: r.hour === visitHour ? "#5a4480" : "#d8d0ee",
                            }} />
                        ))}
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#aaa", marginTop: 4 }}>
                        <span>{label(rows[0].hour)}</span>
                        {visitHour != null && atVisit && <span style={{ color: "#5a4480" }}>■ 방문 예정 {label(visitHour)}</span>}
                        <span>{label(rows[rows.length - 1].hour)}</span>
                    </div>
                    <GoogleAttribution />
                </>
            )}
        </div>
    );
}
