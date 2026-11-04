import type { CoursePlace } from "../types/course";
import type { GooglePlaceDetails } from "../api/course";

/** 장소 1곳의 2인 예상 비용 — Google Maps 1인 가격대 × 2명. 가격대가 등록 안 된 곳은 "정보 없음" */
export type PlaceCost =
  | { known: true; min: number; max: number; mid: number }
  | { known: false };

export const placeKey = (p: Pick<CoursePlace, "name" | "lat" | "lon">) => `${p.name}|${p.lat}|${p.lon}`;

export function placeCost(g?: GooglePlaceDetails | null): PlaceCost {
  if (g?.found && g.price_min != null) {
    // 구글맵의 "₩1~10,000"은 '1만원 이하'라는 뜻이라 하한 1원은 0으로 본다
    const min = g.price_min < 1000 ? 0 : g.price_min * 2;
    const max = (g.price_max ?? g.price_min) * 2;
    return { known: true, min, max, mid: Math.round((min + max) / 2 / 1000) * 1000 };
  }
  return { known: false };
}

export const fmtRange = (c: PlaceCost) =>
  !c.known ? "정보 없음"
  : c.min === c.max ? `${c.min.toLocaleString()}원`
  : c.min === 0 ? `${c.max.toLocaleString()}원 이하`
  : `${c.min.toLocaleString()}~${c.max.toLocaleString()}원`;
