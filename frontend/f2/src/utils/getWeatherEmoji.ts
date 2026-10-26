import type { WeatherType } from "../types/course";

// 날씨 타입을 이모티콘으로 변환 — 텍스트 대신 직관적으로 표시
export function getWeatherEmoji(weatherType: WeatherType): string {
    switch (weatherType) {
        case 'sunny': return '☀️';
        case 'cloudy': return '☁️';
        case 'rainy': return '🌧️';
        case 'snow': return '❄️';
        default: return '';
    }
}