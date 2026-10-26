// 장소 카테고리
export type PlaceCategory = 
    | 'cafe'
    | 'restaurant'
    | 'activity'
    | 'shopping'
    | 'culture'; // 전시, 영화 등

// 공간 유형
export type SpaceType = 
    | 'indoor'
    | 'outdoor'
    | 'mixed'; // 루프탑 등

// 날씨 분류
export type WeatherType = 'sunny' | 'rainy' | 'cloudy' | 'snow';

export interface WeatherInfo {
    pop: number;                        // 강수확률 — f1의 pop
    weatherType: WeatherType;
    description: string;               // 날씨 설명 (ex: "맑음", "흐림")
    temp?: number;                      // 기온 — f1의 temp
    humidity?: number;                  // 습도 — f1의 humidity
    windSpeed?: number;                 // 풍속 — f1의 windSpeed
    skyDesc?: string;                   // 하늘 상태 — f1의 skyDesc
    cityName?: string;                  // 도시명 — f1의 cityName
    isOutdoorOk?: boolean;              // 실외 활동 가능 여부 — f1의 isOutdoorOk
    source?: 'kma' | 'openmeteo';      // 날씨 데이터 출처 — f1의 source
}

//추천 메뉴 데이터
export interface RecommendedMenu {
    name: string;
    price: number;
    isSignature: boolean;
    menuCategory: 'food' | 'drink' | 'dessert' | 'side';
}

// 장소 데이터
export interface CoursePlace {
    time: string;
    name: string;
    desc: string;
    category: PlaceCategory;
    spaceType: SpaceType;
    satisfactionA: number;
    satisfactionB: number;
    lat: number; // 위도
    lon: number; // 경도 — f1의 lon
    waitingTime?: string;
    relationKeywords: string[];
    crawledAt?: string; // 크롤링 날짜
    possiblyClosedWarning?: boolean;
    recommendedMenus: RecommendedMenu[];
    estimatedCost: number;
    budgetRatio: number;
    isOverBudget: boolean;
    phone?: string;
    parkingAvailable?: boolean;
    reservationAvailable: boolean;
    naverReservationUrl?: string;
    reservationUrl?: string;
    admissionFee?: number;
    originalName?: string;
    travelTimeToNext?: number;
    travelModeToNext?: 'walk' | 'car' | 'transit';
    carTimeToNext?: number;             // 자동차 이동 시간 (분) — 백엔드 car_minutes_to_next
    openingHours?: string;
    closedDays?: string;
    breakTime?: string;
}

// 코스 전체 데이터
export interface CourseResult {
    title: string;
    places: CoursePlace[];
    tagsA: string[];   // A님 취향 태그 (f1의 tagsA)
    tagsB: string[];   // B님 취향 태그 (f1의 tagsB)
    common: string[];  // 공통 취향
    weather: WeatherInfo;
    budget: number;
}

// A안 / B안
export type CourseKey = 'A' | 'B';

// 코스 출처 — ai: AI 에이전트, b2: 장소 DB 폴백, mock: 백엔드 실패 시 샘플 데이터
export type CourseSource = 'ai' | 'b2' | 'mock';

// 프론트에서 쓰는 생성된 코스 한 개
export interface GeneratedCourse {
    title: string;
    places: CoursePlace[];
    source: CourseSource;
    avgSatisfactionA?: number;
    avgSatisfactionB?: number;
    fairnessGap?: number;              // |평균 만족도 A − B|
}

// 백엔드 POST /course/generate 응답 (backend/B1/app/schemas/course.py)
export interface BackendPlace {
    name: string;
    category: string;
    region: string;
    time: string;
    price: number;
    is_open: boolean;
    latitude?: number | string | null;
    longitude?: number | string | null;
    walk_minutes_to_next?: number | null;
    car_minutes_to_next?: number | null;
    satisfaction_a?: number | null;
    satisfaction_b?: number | null;
}

export interface BackendCourse {
    title: string;
    total_price: number;
    places: BackendPlace[];
    source?: 'ai' | 'b2';
    avg_satisfaction_a?: number | null;
    avg_satisfaction_b?: number | null;
    fairness_gap?: number | null;
}

export interface BackendCourseResponse {
    course_id: string;
    user_id: string;
    region: string;
    budget_max: number;
    weather?: string | null;
    courses: BackendCourse[];
}

// 시간대별 혼잡도 데이터
export interface CrowdByHour {
    hour: number;
    level: 'low'| 'mid'| 'high';
}

// 후기 한 개의 데이터
export interface Review {
    source: string;
    content: string;
    daysAgo: number;
}