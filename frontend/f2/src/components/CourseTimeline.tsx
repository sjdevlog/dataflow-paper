import type { CoursePlace } from "../types/course";
import CoursePlaceItem from "./CoursePlaceItem";
import type { PlaceCost } from "../utils/cost";

interface Props {
    places: CoursePlace[];
    onSelectPlace: (place: CoursePlace) => void;
    costs?: (PlaceCost | undefined)[];
    nameA?: string;
    nameB?: string;
}

export default function CourseTimeline({ places, onSelectPlace, costs, nameA, nameB }: Props) {
    return (
        <div style={{ padding: '0 16px' }}>
            <h2 style={{ color: "#888", fontSize: '16px', fontWeight: 'bold', marginBottom: '4px' }}>
                코스 타임라인
            </h2>

            {places.map((place, index) => (
                <div key={index}>
                    {/* 장소 아이템 */}
                    <CoursePlaceItem place={place} onClick={onSelectPlace} cost={costs?.[index]} nameA={nameA} nameB={nameB} />

                    {/* 마지막 장소가 아닐 때만 이동 시간 점선 표시 */}
                    {index < places.length - 1 && (
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            margin: '4px 0 4px 52px',
                        }}>
                            {/* 점선 — 장소 사이 시각적 구분용 */}
                            <div style={{
                                width: '1px',
                                height: '32px',
                                borderLeft: '2px dashed #d8d0f0',
                                marginLeft: '4px',
                            }} />
                            {/* 이동 수단 아이콘 + 소요 시간 */}
                            <span style={{
                                fontSize: '12px',
                                color: '#b8a9d9',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                            }}>
                                {place.travelModeToNext === 'walk' && '🚶'}
                                {place.travelModeToNext === 'car' && '🚗'}
                                {place.travelModeToNext === 'transit' && '🚇'}
                                {place.travelTimeToNext ? `${place.travelTimeToNext}분` : '이동'}
                                {place.carTimeToNext != null && ` · 🚗 ${place.carTimeToNext}분`}
                            </span>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}