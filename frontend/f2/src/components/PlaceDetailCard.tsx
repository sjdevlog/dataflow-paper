import { useEffect, useState } from "react";
import type { CoursePlace } from "../types/course";
import { fetchPlaceDetails } from "../api/course";
import type { GooglePlaceDetails } from "../api/course";
import CrowdBars from "./CrowdBars";
import { placeCost, fmtRange } from "../utils/cost";
import { GooglePhotos, GoogleReviews, GoogleSummary } from "./GooglePlaceInfo";
import PlaceActionButtonGroup from "./PlaceActionButtonGroup";
import { isLikelyClosed } from "../utils/isLikelyClosed";

interface Props {
    place: CoursePlace;
    onClose: () => void;
    onSkip: (place: CoursePlace) => void;       // 이 장소 건너뛰기
    onRecommendOther: (place: CoursePlace) => void; // 다른 장소 추천
    onWishlist: (place: CoursePlace) => void;    // 찜하기
    google?: GooglePlaceDetails | null;          // 결과 화면에서 이미 받아온 구글 상세 (없으면 카드가 직접 조회)
    visitDate?: string;                          // YYYY-MM-DD — 혼잡도에서 방문 요일·시각 표시용
}

export default function PlaceDetailCard({ place, onClose, onSkip, onRecommendOther, onWishlist, google, visitDate }: Props) {
    // 구글 상세 — 정책상 저장하지 않고 카드를 열 때마다 조회 (결과는 어느 장소 것인지 key로 구분)
    const key = `${place.name}|${place.lat}|${place.lon}`;
    const [res, setRes] = useState<{ key: string; g: GooglePlaceDetails | null } | null>(null);
    useEffect(() => {
        if (google !== undefined) return;     // 결과 화면이 이미 받아 둔 경우 다시 호출하지 않음
        let cancelled = false;
        fetchPlaceDetails({ name: place.name, lat: place.lat, lon: place.lon })
            .then(d => { if (!cancelled) setRes({ key, g: d.found ? d : null }); })
            .catch(() => { if (!cancelled) setRes({ key, g: null }); });
        return () => { cancelled = true; };
    }, [key, place.name, place.lat, place.lon, google]);
    const gLoading = google === undefined && res?.key !== key;
    const g = google !== undefined ? google : gLoading ? null : res?.g ?? null;

    // 2인 예상 비용: 구글 1인 가격대 × 2명, 등록 안 된 곳은 '정보 없음'
    const cost = placeCost(g);

    return (
        <div style={{
            background: '#ffffff',
            borderRadius: '16px',
            padding: '20px',
            border: '1px solid #e8e4f4',
            boxShadow: '0 2px 8px rgba(184, 169, 217, 0.2)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
        }}>
            {/* 상단 — 장소명 + 닫기 버튼 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#2d2d2d', margin: 0, textAlign: 'left' }}>
                        {place.name}
                    </h2>
                    <p style={{
                        fontSize: '13px',
                        color: '#999',
                        margin: '4px 0 0 0',
                        height: '36px',
                        overflow: 'hidden',
                        lineHeight: '18px',
                        textAlign: 'left',
                    }}>
                        {place.desc}
                    </p>
                </div>
                <button
                    onClick={onClose}
                    style={{
                        background: 'none',
                        border: 'none',
                        fontSize: '18px',
                        cursor: 'pointer',
                        color: '#b8a9d9',
                        padding: '0 0 0 12px',
                    }}
                >
                    ✕
                </button>
            </div>

            {gLoading && <p style={{ fontSize: 12, color: '#bbb', margin: 0 }}>Google Maps 정보를 불러오는 중...</p>}
            {g && <GoogleSummary g={g} />}
            {g && <GooglePhotos g={g} />}

            {/* 장소 액션 버튼 — 건너뛰기, 다른 장소 추천, 찜하기, 공유하기 */}
            <PlaceActionButtonGroup
                place={place}
                onSkip={onSkip}
                onRecommendOther={onRecommendOther}
                onWishlist={onWishlist}
                onClose={onClose}
            />

            {/* 웨이팅 + 공간 유형 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ background: '#f5f3fb', borderRadius: '12px', padding: '12px' }}>
                    <p style={{ fontSize: '11px', color: '#b8a9d9', margin: '0 0 4px 0', fontWeight: 600 }}>현재 웨이팅</p>
                    <p style={{ fontSize: '16px', fontWeight: 'bold', color: '#5a4480', margin: 0 }}>
                        {place.waitingTime ?? '정보 없음'}
                    </p>
                </div>
                <div style={{ background: '#f5f3fb', borderRadius: '12px', padding: '12px' }}>
                    <p style={{ fontSize: '11px', color: '#b8a9d9', margin: '0 0 4px 0', fontWeight: 600 }}>공간 유형</p>
                    <p style={{ fontSize: '16px', fontWeight: 'bold', color: '#5a4480', margin: 0 }}>
                        {place.spaceType === 'indoor' ? '실내' : place.spaceType === 'outdoor' ? '실외' : '복합'}
                    </p>
                </div>
            </div>

            {/* 입장료 */}
            {place.admissionFee !== undefined && place.admissionFee > 0 && (
                <div style={{
                    background: '#f5f3fb',
                    borderRadius: '12px',
                    padding: '12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#5a4480' }}>입장료</span>
                    <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#5a4480' }}>
                        {place.admissionFee.toLocaleString()}원
                    </span>
                </div>
            )}

            {/* 예약 링크 버튼 — 네이버 우선, 없으면 캐치테이블 */}
            {place.reservationAvailable && (place.naverReservationUrl ?? place.reservationUrl) && (
                <a
                    href={place.naverReservationUrl ?? place.reservationUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                        background: '#5a4480',
                        color: '#fff',
                        padding: '12px',
                        borderRadius: '12px',
                        fontWeight: 700,
                        fontSize: '14px',
                        textDecoration: 'none',
                    }}
                >
                    📅 {place.naverReservationUrl ? '네이버 예약하기' : '캐치테이블 예약하기'}
                </a>
            )}

            {/* 영업 정보 — 영업시간, 브레이크 타임, 휴무일 */}
            <div style={{
                background: '#f5f3fb',
                borderRadius: '12px',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
            }}>
                <p style={{ fontSize: '11px', color: '#b8a9d9', margin: '0 0 4px 0', fontWeight: 600 }}>
                    영업 정보
                </p>
                {place.openingHours && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '12px', color: '#888' }}>영업시간</span>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: '#5a4480' }}>{place.openingHours}</span>
                    </div>
                )}
                {place.breakTime && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '12px', color: '#888' }}>브레이크 타임</span>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: '#e8a0b4' }}>{place.breakTime}</span>
                    </div>
                )}
                {place.closedDays && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '12px', color: '#888' }}>정기 휴무</span>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: '#888' }}>{place.closedDays}</span>
                    </div>
                )}
            </div>

            {/* 메뉴·비용 — 메뉴 정보가 있을 때만 목록을 보여주고, 없으면 예산 배분 기준 추정치임을 밝힌다 */}
            <div>
                {place.recommendedMenus.length > 0 && (
                    <>
                        <p style={{ fontSize: '13px', fontWeight: 600, color: '#3d3d3d', marginBottom: '8px' }}>
                            {place.category === 'activity' ? '액티비티 목록' : '메뉴 가격'}
                        </p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '10px' }}>
                            {place.recommendedMenus.map((menu) => (
                                <div key={menu.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontSize: '13px', color: '#3d3d3d' }}>{menu.name}</span>
                                    <span style={{ fontSize: '13px', color: '#5a5a5a', fontWeight: 500 }}>{menu.price.toLocaleString()}원</span>
                                </div>
                            ))}
                        </div>
                    </>
                )}
                <div style={{ paddingTop: '10px', borderTop: '1px solid #e8e4f4', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontSize: '13px', color: '#999' }}>
                        예상 비용 (2인)
                        {cost.known && <span style={{ fontSize: '11px', color: '#bbb' }}> · Google Maps 1인 가격대 기준</span>}
                    </span>
                    <span style={{ fontSize: '14px', fontWeight: 'bold', color: cost.known ? '#5a4480' : '#bbb' }}>
                        {gLoading ? "불러오는 중" : fmtRange(cost)}
                    </span>
                </div>
            </div>

            <CrowdBars place={place} visitDate={visitDate} />

            {g && <GoogleReviews g={g} />}

            {/* 폐점 경고 */}
            {(place.possiblyClosedWarning || isLikelyClosed(place.crawledAt, place.category)) && (
                <div style={{
                    background: '#faeef2',
                    borderRadius: '10px',
                    padding: '12px 14px',
                    border: '1px solid #f0c0cc',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                }}>
                    <span style={{ fontSize: '13px', color: '#c0607a', fontWeight: 700 }}>⚠ 폐점 가능성이 있어요</span>
                    <span style={{ fontSize: '12px', color: '#d08090' }}>
                        마지막 수집 정보: {place.crawledAt ?? '날짜 불명'} · 방문 전 확인을 권장해요
                    </span>
                </div>
            )}

        </div>
    );
}