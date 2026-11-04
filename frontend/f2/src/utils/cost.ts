import type { CoursePlace } from "../types/course";
import type { GooglePlaceDetails } from "../api/course";

/** 장소 1곳의 2인 예상 비용.
 *  Google Maps 1인 가격대가 있으면 ×2 범위, 없으면 기존 예산 배분 추정치 (source 로 구분해 화면에 밝힘) */
export interface PlaceCost { min: number; max: number; mid: number; source: "google" | "estimate" }

export const placeKey = (p: Pick<CoursePlace, "name" | "lat" | "lon">) => `${p.name}|${p.lat}|${p.lon}`;

export function placeCost(place: CoursePlace, g?: GooglePlaceDetails | null): PlaceCost {
  if (g?.found && g.price_min != null) {
    const min = g.price_min * 2;
    const max = (g.price_max ?? g.price_min) * 2;
    return { min, max, mid: Math.round((min + max) / 2 / 1000) * 1000, source: "google" };
  }
  return { min: place.estimatedCost, max: place.estimatedCost, mid: place.estimatedCost, source: "estimate" };
}

export const fmtRange = (c: PlaceCost) =>
  c.min === c.max ? `${c.min.toLocaleString()}원` : `${c.min.toLocaleString()}~${c.max.toLocaleString()}원`;
