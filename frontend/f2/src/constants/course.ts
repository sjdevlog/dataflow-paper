import type { CourseKey, GeneratedCourse, PlaceCategory } from "../types/course";

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

/** 코스 이름 — 백엔드가 두 사람 취향 태그로 지은 이름. 없으면 '추천 코스 1·2' */
export const courseLabel = (c: Pick<GeneratedCourse, "title"> | undefined, key: CourseKey) =>
  c?.title?.replace(/\s*\([^)]*\)\s*$/, "").trim() || `추천 코스 ${key === "A" ? 1 : 2}`;
