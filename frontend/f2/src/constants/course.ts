import type { CourseKey, PlaceCategory } from "../types/course";

export const CAT_EMOJI: Record<PlaceCategory, string> = {
  cafe: "☕",
  culture: "🎨",
  restaurant: "🍽️",
  activity: "🏃",
  shopping: "🛍️",
};

// 코스 생성 로딩 화면 단계
export const LOADING_STEPS = [
  "지역 좌표를 확인하는 중...",
  "현재 날씨를 확인하는 중...",
  "취향을 분석하는 중...",
  "데이트 코스를 구성하는 중...",
];

export const COURSE_LABEL: Record<CourseKey, string> = {
  A: "차분한 감성 코스",
  B: "액티브 핫플 코스",
};
