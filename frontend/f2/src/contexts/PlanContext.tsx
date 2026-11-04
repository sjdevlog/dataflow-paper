import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { CourseKey, CoursePlace, GeneratedCourse } from "../types/course";
import type { WeatherSnapshot } from "../api/weather";
import type { BudgetRange } from "../utils/budget";
import type { RecommendedEvent } from "../api/course";

export type RegionValue = { name: string; lat: number | null; lon: number | null };

/** 온보딩에서 입력받은 값 */
export interface PlanInput {
  region: RegionValue & { lat: number; lon: number };
  date: string;
  tagsA: string[];
  tagsB: string[];
  budgetA: BudgetRange;
  budgetB: BudgetRange;
  weather: WeatherSnapshot;
}

/** 온보딩 → 이벤트 → 코스 선택 → 결과 → 예약 → 완료 까지 공유하는 상태 */
export interface Plan {
  sessionId: string;
  input: PlanInput;
  courses: Record<CourseKey, GeneratedCourse>;
  selectedCourse: CourseKey;
  events: string[];
  selectedEvent?: RecommendedEvent | null;
  coursesReady?: boolean;   // 이벤트 선택 후 실제 코스를 받았는지 (false면 샘플 코스)
  createdAt: string;
}

interface PlanCtx {
  plan: Plan | null;
  startPlan: (sessionId: string, input: PlanInput, courses: Record<CourseKey, GeneratedCourse>) => void;
  setEvents: (events: string[]) => void;
  setCourses: (courses: Record<CourseKey, GeneratedCourse>, selectedEvent: RecommendedEvent | null) => void;
  selectCourse: (key: CourseKey) => void;
  removePlace: (key: CourseKey, placeName: string) => void;
  replacePlace: (key: CourseKey, oldName: string, place: CoursePlace, walkFromPrev?: number | null) => void;
  clearPlan: () => void;
}

const STORAGE_KEY = "dateflow_plan";

/** 장소가 바뀌면 두 사람 평균 만족도와 격차를 다시 계산 (backend scoring.course_metrics 와 같은 식) */
function withMetrics(c: GeneratedCourse): GeneratedCourse {
  if (!c.places.length) return c;
  const avg = (xs: number[]) => Math.round((xs.reduce((s, x) => s + x, 0) / xs.length) * 10) / 10;
  const a = avg(c.places.map(p => p.satisfactionA));
  const b = avg(c.places.map(p => p.satisfactionB));
  return { ...c, avgSatisfactionA: a, avgSatisfactionB: b, fairnessGap: Math.round(Math.abs(a - b) * 10) / 10 };
}

const Ctx = createContext<PlanCtx | null>(null);

function loadPlan(): Plan | null {
  try {
    const s = sessionStorage.getItem(STORAGE_KEY);
    return s ? JSON.parse(s) : null;
  } catch {
    return null;
  }
}

export function PlanProvider({ children }: { children: ReactNode }) {
  const [plan, setPlan] = useState<Plan | null>(loadPlan);

  // 새로고침해도 진행 중인 코스가 유지되도록 sessionStorage 동기화
  useEffect(() => {
    try {
      if (plan) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(plan));
      else sessionStorage.removeItem(STORAGE_KEY);
    } catch { /* storage 사용 불가 → 메모리 상태만 유지 */ }
  }, [plan]);

  const update = useCallback((fn: (p: Plan) => Plan) => setPlan(p => (p ? fn(p) : p)), []);

  const value: PlanCtx = {
    plan,
    startPlan: (sessionId, input, courses) =>
      setPlan({ sessionId, input, courses, selectedCourse: "A", events: [], createdAt: new Date().toISOString() }),
    setEvents:    (events) => update(p => ({ ...p, events })),
    setCourses:   (courses, selectedEvent) => update(p => ({
      ...p, courses, selectedEvent, coursesReady: true, selectedCourse: "A",
      events: selectedEvent ? [selectedEvent.name] : [],
    })),
    selectCourse: (selectedCourse) => update(p => ({ ...p, selectedCourse })),
    removePlace:  (key, placeName) => update(p => ({
      ...p,
      courses: {
        ...p.courses,
        [key]: { ...p.courses[key], places: p.courses[key].places.filter(pl => pl.name !== placeName) },
      },
    })),
    replacePlace: (key, oldName, place, walkFromPrev) => update(p => {
      const old = p.courses[key].places;
      const idx = old.findIndex(pl => pl.name === oldName);
      if (idx < 0) return p;
      const places = old.map((pl, i) =>
        i === idx ? place
        : i === idx - 1 && walkFromPrev != null ? { ...pl, travelTimeToNext: walkFromPrev, carTimeToNext: undefined }
        : pl);
      return { ...p, courses: { ...p.courses, [key]: withMetrics({ ...p.courses[key], places }) } };
    }),
    clearPlan: () => setPlan(null),
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePlan(): PlanCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("usePlan must be used inside <PlanProvider>");
  return ctx;
}

/** <RequirePlan> 안쪽 페이지 전용 — plan 이 반드시 있음 */
export function useActivePlan(): PlanCtx & { plan: Plan } {
  const ctx = usePlan();
  if (!ctx.plan) throw new Error("useActivePlan must be used inside <RequirePlan>");
  return ctx as PlanCtx & { plan: Plan };
}
