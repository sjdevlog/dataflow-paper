export const API_BASE     = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const KAKAO_JS_KEY = (import.meta.env.VITE_KAKAO_MAPS_API_KEY as string | undefined) || "";

// 좌표를 못 구했을 때 쓰는 기본 위치 (서울시청)
export const DEFAULT_LAT = 37.5665;
export const DEFAULT_LON = 126.978;
