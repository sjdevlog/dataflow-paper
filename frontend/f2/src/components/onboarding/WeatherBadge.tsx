import { C } from "../../constants/theme";
import { WEATHER_META } from "../../api/weather";
import type { WeatherSnapshot } from "../../api/weather";

export default function WeatherBadge({ wx, loading }: { wx: WeatherSnapshot | null; loading: boolean }) {
  if (loading) return (
    <div style={{ display:"flex", alignItems:"center", gap:8, padding:"10px 14px", background:C.inputBg, borderRadius:12, fontSize:13, color:C.textMuted, animation:"pulse 1.2s ease infinite" }}>
      <span style={{ animation:"spin 1.4s linear infinite", display:"inline-block" }}>◎</span> 날씨 확인 중...
    </div>
  );
  if (!wx) return null;
  const m     = WEATHER_META[wx.type];
  const isKMA = wx.source === "kma";
  const hasExtra = isKMA && (wx.humidity != null || wx.windSpeed != null || wx.pop != null || wx.skyDesc);
  return (
    <div style={{ padding:"12px 14px", background:C.skyDim, border:`1px solid ${C.sky}44`, borderRadius:14, animation:"fadeUp 0.3s ease" }}>
      <div style={{ display:"flex", alignItems:"center", gap:10 }}>
        <span style={{ fontSize:24 }}>{m.icon}</span>
        <div style={{ flex:1 }}>
          <div style={{ display:"flex", alignItems:"center", gap:7, flexWrap:"wrap", marginBottom:2 }}>
            <span style={{ fontSize:13, fontWeight:700, color:C.text }}>
              {wx.cityName} 현재 {wx.skyDesc || m.label}{wx.temp !== null ? ` · ${wx.temp}°C` : ""}
            </span>
            <span style={{ fontSize:10, padding:"1px 6px", borderRadius:4, fontWeight:700,
              background: isKMA ? C.greenBg : C.skyDim,
              color:      isKMA ? C.green   : C.sky }}>
              {isKMA ? "기상청" : "open-meteo"}
            </span>
          </div>
          <div style={{ fontSize:11, color:C.textDim }}>{m.note} · 코스 생성에 반영돼요</div>
        </div>
      </div>
      {hasExtra && (
        <div style={{ display:"flex", gap:14, marginTop:10, paddingTop:8, borderTop:`1px solid ${C.sky}33`, flexWrap:"wrap" }}>
          {wx.humidity != null && <span style={{ fontSize:12, color:C.textDim }}>💧 습도 <strong style={{ color:C.text }}>{wx.humidity}%</strong></span>}
          {wx.windSpeed != null && <span style={{ fontSize:12, color:C.textDim }}>💨 풍속 <strong style={{ color:C.text }}>{wx.windSpeed}m/s</strong></span>}
          {wx.pop != null && <span style={{ fontSize:12, color:C.textDim }}>🌂 강수확률 <strong style={{ color:C.text }}>{wx.pop}%</strong></span>}
          {wx.isOutdoorOk != null && (
            <span style={{ fontSize:12, padding:"1px 8px", borderRadius:"999px", fontWeight:600,
              background: wx.isOutdoorOk ? C.greenBg : C.errorBg,
              color:      wx.isOutdoorOk ? C.green   : C.error }}>
              {wx.isOutdoorOk ? "실외 활동 가능" : "실내 추천"}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
