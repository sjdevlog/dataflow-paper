import type { CoursePlace } from "../types/course";
import type { PlaceCost } from "../utils/cost";
import { fmtRange } from "../utils/cost";
import { isLikelyClosed } from "../utils/isLikelyClosed";
// 크롤링 날짜 기반 폐점 가능성 자동 판단

interface Props {
    place: CoursePlace;
    onClick: (place: CoursePlace) => void;
    cost?: PlaceCost;
}

export default function CoursePlaceItem({ place, onClick, cost }: Props) {
    return (
        <div
            onClick={() => onClick(place)}
            style={{ cursor: 'pointer', padding: '12px 0' }}
        >
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <span style={{ color: "#888", fontSize: '13px', minWidth: '40px' }}>
                    {place.time}
                </span>
                <strong style={{ fontSize: '15px' }}>{place.name}</strong>

                {/* 폐점 가능성 경고 — 빨간 텍스트 대신 뱃지로 변경 */}
                {(place.possiblyClosedWarning || isLikelyClosed(place.crawledAt, place.category)) && (
                    <span style={{
                        fontSize: '11px',
                        background: '#faeef2',
                        color: '#c0607a',
                        padding: '2px 8px',
                        borderRadius: '999px',
                        fontWeight: 600,
                        border: '1px solid #f0c0cc',
                    }}>
                        ⚠ 폐점 가능성
                    </span>
                )}
            </div>

            <p style={{ margin: '4px 0 0 52px', fontSize: '13px', color: '#555' }}>
                {place.desc}
            </p>

            <div style={{ margin: '8px 0 0 52px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '12px', color: '#888', minWidth: '30px' }}>A님</span>
                    <div style={{ flex: 1, height: '6px', background: '#eee', borderRadius: '3px' }}>
                        <div style={{ width: `${place.satisfactionA}%`, height: '100%', background: '#C9B8E8', borderRadius: '3px' }} />
                    </div>
                    <span style={{ fontSize: '12px', color: '#888' }}>{place.satisfactionA}%</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '12px', color: '#888', minWidth: '30px' }}>B님</span>
                    <div style={{ flex: 1, height: '6px', background: '#eee', borderRadius: '3px' }}>
                        <div style={{ width: `${place.satisfactionB}%`, height: '100%', background: '#B8C9F2', borderRadius: '3px' }} />
                    </div>
                    <span style={{ fontSize: '12px', color: '#888' }}>{place.satisfactionB}%</span>
                </div>
            </div>

            <div style={{ margin: '6px 0 0 52px', fontSize: '12px', color: '#888' }}>
                예상 비용 (2인) {cost ? fmtRange(cost) : `${place.estimatedCost.toLocaleString()}원`}
                <span style={{ marginLeft: '8px', color: '#aaa' }}>
                    {cost?.source === "google" ? "· Google Maps 가격대 기준" : "· 예산 배분 추정"}
                </span>
            </div>
        </div>
    );
}