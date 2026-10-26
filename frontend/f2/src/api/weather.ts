import { requestJson } from "./http";
import type { WeatherType } from "../types/course";

export interface WeatherSnapshot {
  type: WeatherType;
  temp: number | null;
  cityName: string;
  source: "kma" | "openmeteo";
  humidity?: number;
  windSpeed?: number;
  pop?: number;
  skyDesc?: string;
  description?: string;
  isOutdoorOk?: boolean;
}

export const WEATHER_META: Record<WeatherType, { icon: string; label: string; note: string }> = {
  sunny:  { icon: "☀️", label: "맑음",    note: "실외 코스 포함" },
  cloudy: { icon: "⛅",  label: "흐림",    note: "실내·외 혼합 코스" },
  rainy:  { icon: "🌧️", label: "비",      note: "실내 중심 코스" },
  snow:   { icon: "❄️", label: "눈·추위", note: "따뜻한 실내 코스" },
};

// open-meteo WMO weathercode → WeatherType
const wmoToType = (c: number): WeatherType => {
  if ([0, 1].includes(c))                               return "sunny";
  if ([51, 53, 55, 61, 63, 65, 80, 81, 82].includes(c)) return "rainy";
  if ([71, 73, 75, 77, 85, 86].includes(c))             return "snow";
  return "cloudy";
};

// 기상청 PTY(강수형태)/SKY(하늘상태) → WeatherType
const kmaToType = (pty: number, sky: number): WeatherType => {
  if (pty > 0) return pty === 3 ? "snow" : [1, 2, 4].includes(pty) ? "rainy" : "cloudy";
  return sky === 1 ? "sunny" : "cloudy";
};

type KmaResponse = {
  error?: string; region?: string;
  pty_code: number | null; sky_code: number; temperature: number | null;
  humidity?: number; wind_speed?: number; pop?: number; sky_desc?: string;
  description?: string; is_outdoor_ok?: boolean;
};

async function fetchKma(lat: number, lon: number, cityName: string, targetDate?: string): Promise<WeatherSnapshot | null> {
  const qs = new URLSearchParams({ lat: String(lat), lon: String(lon), region: cityName });
  if (targetDate) qs.set("target_date", targetDate.replace(/-/g, ""));
  const d = await requestJson<KmaResponse>(`/weather?${qs}`, {}, 4000);
  if (d.error || d.pty_code === null || d.pty_code === undefined) return null;
  return {
    type:        kmaToType(d.pty_code, d.sky_code),
    temp:        d.temperature !== null ? Math.round(d.temperature) : null,
    cityName:    cityName || d.region || "선택 지역",
    source:      "kma",
    humidity:    d.humidity,
    windSpeed:   d.wind_speed,
    pop:         d.pop,
    skyDesc:     d.sky_desc,
    description: d.description,
    isOutdoorOk: d.is_outdoor_ok,
  };
}

async function fetchOpenMeteo(lat: number, lon: number, cityName: string, targetDate?: string): Promise<WeatherSnapshot> {
  const base = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&timezone=Asia%2FSeoul`;
  const name = cityName || "선택 지역";

  const today = new Date(); today.setHours(0, 0, 0, 0);
  const tgt   = targetDate ? new Date(targetDate + "T00:00:00") : null;
  if (tgt && tgt >= today) {
    const days = Math.min(Math.ceil((tgt.getTime() - today.getTime()) / 86400000) + 2, 16);
    const w = await requestJson<{ daily?: { time: string[]; weathercode: number[]; temperature_2m_max: number[]; temperature_2m_min: number[] } }>(
      `${base}&daily=weathercode,temperature_2m_max,temperature_2m_min&forecast_days=${days}`
    );
    const idx = (w.daily?.time || []).indexOf(targetDate!);
    if (idx >= 0) {
      const avg = Math.round((w.daily!.temperature_2m_max[idx] + w.daily!.temperature_2m_min[idx]) / 2);
      return { type: wmoToType(w.daily!.weathercode[idx]), temp: avg, cityName: name, source: "openmeteo" };
    }
  }

  const w = await requestJson<{ current: { weathercode: number; temperature_2m: number } }>(
    `${base}&current=weathercode,temperature_2m`
  );
  return { type: wmoToType(w.current.weathercode), temp: Math.round(w.current.temperature_2m), cityName: name, source: "openmeteo" };
}

/** 기상청(백엔드) 우선, 실패 시 open-meteo 폴백 */
export async function fetchWeather(lat: number, lon: number, cityName: string, targetDate?: string): Promise<WeatherSnapshot> {
  try {
    const kma = await fetchKma(lat, lon, cityName, targetDate);
    if (kma) return kma;
  } catch { /* 백엔드 미연결 → 폴백 */ }
  return fetchOpenMeteo(lat, lon, cityName, targetDate);
}

/** 지역명 → 좌표 (open-meteo geocoding) */
export async function geocodeCity(city: string): Promise<{ lat: number; lon: number; name: string } | null> {
  const g = await requestJson<{ results?: { latitude: number; longitude: number; name: string }[] }>(
    `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1&language=ko`
  );
  const r = g.results?.[0];
  return r ? { lat: r.latitude, lon: r.longitude, name: r.name } : null;
}
