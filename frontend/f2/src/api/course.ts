import { postJson } from "./http";
import { DEFAULT_LAT, DEFAULT_LON } from "../config";
import type {
  BackendCourse, BackendCourseResponse, BackendPlace,
  CourseKey, CoursePlace, GeneratedCourse, WeatherType,
} from "../types/course";

export interface GenerateCourseInput {
  sessionId: string;
  region: string;
  lat: number;
  lon: number;
  date: string;            // YYYY-MM-DD
  weather: WeatherType;
  temp: number | null;
  budgetMin: number;
  budgetMax: number;
  tagsA: string[];
  tagsB: string[];
  selectedEvent?: RecommendedEvent | null;   // 사용자가 고른 메인 이벤트
  noEvent?: boolean;                         // 주변에 이벤트 장소가 없어 이벤트 없이 짜는 경우
}

/** 백엔드가 추천한 메인 이벤트 (지역 반경 안에 실제로 있는 장소) */
export interface RecommendedEvent {
  name: string;
  category: string;
  address: string;
  place_url: string;
  latitude: number | null;
  longitude: number | null;
  reason: string;
  source: "ai" | "kakao";
}

export interface EventsResult {
  events: RecommendedEvent[];
  source: "ai" | "kakao" | "ai+kakao" | "none";
  message: string;
}

/** POST /course/events — 메인 이벤트 추천. more=true 면 AI 없이 주변 장소를 더 불러옴 */
export function fetchEvents(input: {
  region: string; lat: number; lon: number; date: string;
  tagsA: string[]; tagsB: string[]; exclude?: string[]; more?: boolean;
}): Promise<EventsResult> {
  return postJson<EventsResult>("/course/events", {
    region: input.region, lat: input.lat, lon: input.lon, date: input.date,
    tags_a: input.tagsA, tags_b: input.tagsB,
    exclude: input.exclude ?? [], more: input.more ?? false,
  }, input.more ? 20000 : 150000);   // AI 추천은 20~60초, 더 보기는 카카오 검색만
}

const FALLBACK_TIMES = ["13:00", "15:30", "18:00", "20:00"];

export function mapCategory(cat: string): CoursePlace["category"] {
  if (cat.includes("카페")) return "cafe";
  if (["식당", "레스토랑", "바", "펍"].some(k => cat.includes(k))) return "restaurant";
  if (cat.includes("쇼핑") || cat.includes("팝업")) return "shopping";
  if (["전시", "갤러리", "공연", "영화"].some(k => cat.includes(k))) return "culture";
  return "activity";
}

const toNumber = (v: number | string | null | undefined, fallback: number) => {
  const n = typeof v === "string" ? parseFloat(v) : v;
  return n != null && Number.isFinite(n) ? n : fallback;
};

/** 백엔드 장소 → 화면용 CoursePlace */
export function adaptPlace(p: BackendPlace, i: number, budget: number): CoursePlace {
  const cost = p.price || 0;
  return {
    time:  p.time || FALLBACK_TIMES[i] || "13:00",
    name:  p.name,
    desc:  p.category || "",
    category:  mapCategory(p.category || ""),
    spaceType: "indoor",
    satisfactionA: p.satisfaction_a ?? 0,
    satisfactionB: p.satisfaction_b ?? 0,
    lat: toNumber(p.latitude,  DEFAULT_LAT),
    lon: toNumber(p.longitude, DEFAULT_LON),
    estimatedCost: cost,
    budgetRatio:   budget > 0 ? Math.round((cost / budget) * 100) : 0,
    isOverBudget:  cost > budget,
    recommendedMenus: [],
    reservationAvailable: false,
    relationKeywords: [],
    travelTimeToNext: p.walk_minutes_to_next ?? undefined,
    travelModeToNext: "walk",
    carTimeToNext:    p.car_minutes_to_next ?? undefined,
  };
}

function adaptCourse(c: BackendCourse, budget: number): GeneratedCourse {
  return {
    title:  c.title,
    places: c.places.map((p, i) => adaptPlace(p, i, budget)),
    source: c.source ?? "b2",
    avgSatisfactionA: c.avg_satisfaction_a ?? undefined,
    avgSatisfactionB: c.avg_satisfaction_b ?? undefined,
    fairnessGap:      c.fairness_gap ?? undefined,
  };
}

/** POST /course/generate — A안/B안을 한 번에 생성 */
export async function generateCourses(input: GenerateCourseInput): Promise<Record<CourseKey, GeneratedCourse>> {
  const data = await postJson<BackendCourseResponse>("/course/generate", {
    user_id:    `${input.sessionId}_A`,
    region:     input.region,
    lat:        input.lat,
    lon:        input.lon,
    date:       input.date,
    weather:    input.weather,
    temp:       input.temp,
    budget_min: input.budgetMin,
    budget_max: input.budgetMax,
    tags_a:     input.tagsA,
    tags_b:     input.tagsB,
    selected_event: input.selectedEvent ?? null,
    no_event:   input.noEvent ?? false,
  }, 240000);   // AI 에이전트(Gemini + 툴 호출)가 혼잡 시 2분 이상 걸림

  const [a, b] = data.courses ?? [];
  if (!a?.places?.length || !b?.places?.length) throw new Error("코스 응답이 비어 있어요");
  return { A: adaptCourse(a, data.budget_max), B: adaptCourse(b, data.budget_max) };
}
