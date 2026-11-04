import type { CourseKey, CoursePlace } from "../types/course";

/** 공유 링크에 담는 최소 정보 (받는 사람 브라우저엔 PlanContext 가 없으므로 URL 에 직접 담음) */
export interface SharedCourse {
  region: string;
  date: string;
  course: CourseKey;
  title?: string;   // 코스 이름 (취향 태그로 지은 이름)
  places: Pick<CoursePlace, "time" | "name" | "category" | "openingHours">[];
}

const toBase64Url = (s: string) =>
  btoa(String.fromCharCode(...new TextEncoder().encode(s))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

const fromBase64Url = (s: string) => {
  const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/"));
  return new TextDecoder().decode(Uint8Array.from(bin, c => c.charCodeAt(0)));
};

export function encodeShare(data: SharedCourse): string {
  const slim: SharedCourse = {
    ...data,
    places: data.places.map(({ time, name, category, openingHours }) => ({ time, name, category, openingHours })),
  };
  return toBase64Url(JSON.stringify(slim));
}

export function decodeShare(token: string | null): SharedCourse | null {
  if (!token) return null;
  try {
    return JSON.parse(fromBase64Url(token));
  } catch {
    return null;
  }
}

export function shareUrl(data: SharedCourse): string {
  return `${window.location.origin}/complete?share=${encodeShare(data)}`;
}
