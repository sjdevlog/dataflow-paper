import type { GooglePlaceDetails } from "../api/course";

const ink = "#3d3d3d", quiet = "#999", soft = "#f5f3fb";

/** 구글 정책: 출처 "Google Maps" 표기(번역·줄바꿈 금지), 리뷰·사진 작성자 표시, 원문 링크 */
export function GoogleAttribution({ uri }: { uri?: string }) {
    const label = (
        <span translate="no" style={{ fontFamily: "Roboto, Arial, sans-serif", fontWeight: 400, fontSize: 11, color: "#5E5E5E", whiteSpace: "nowrap" }}>
            Google Maps
        </span>
    );
    return (
        <div style={{ textAlign: "right", marginTop: 4 }}>
            {uri ? <a href={uri} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>{label}</a> : label}
        </div>
    );
}

const fmtTime = (iso?: string | null) => {
    if (!iso) return "";
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("ko-KR", { hour: "numeric", minute: "2-digit" });
};

const stars = (n: number | null | undefined) => (n == null ? "" : "★".repeat(Math.round(n)) + "☆".repeat(5 - Math.round(n)));

/** 상단 요약: 별점·리뷰 수·업종·1인 가격대·영업 상태 */
export function GoogleSummary({ g }: { g: GooglePlaceDetails }) {
    const price = g.price_min != null ? `1인 ₩${g.price_min.toLocaleString()}${g.price_max ? `~${g.price_max.toLocaleString()}` : ""}` : "";
    const open = g.open_now == null ? "" : g.open_now
        ? `영업 중${g.next_close_time ? ` · ${fmtTime(g.next_close_time)}에 영업 종료` : ""}`
        : `영업 전·종료${g.next_open_time ? ` · ${fmtTime(g.next_open_time)}에 영업 시작` : ""}`;
    return (
        <div style={{ background: soft, borderRadius: 12, padding: "10px 12px" }}>
            {g.rating != null && (
                <div style={{ fontSize: 13, color: ink }}>
                    <b>{g.rating.toFixed(1)}</b> <span style={{ color: "#F4B400" }}>{stars(g.rating)}</span>
                    {g.rating_count != null && <span style={{ color: quiet }}> ({g.rating_count.toLocaleString()})</span>}
                </div>
            )}
            {(g.type_name || price) && (
                <div style={{ fontSize: 12, color: "#666", marginTop: 3 }}>{[g.type_name, price].filter(Boolean).join(" · ")}</div>
            )}
            {open && <div style={{ fontSize: 12, marginTop: 3, color: g.open_now ? "#388E3C" : "#c0607a" }}>{open}</div>}
            <GoogleAttribution uri={g.google_maps_uri} />
        </div>
    );
}

/** 사진 (최대 3장) — 작성자 표시 */
export function GooglePhotos({ g }: { g: GooglePlaceDetails }) {
    if (!g.photos?.length) return null;
    return (
        <div>
            <div style={{ display: "flex", gap: 6, overflowX: "auto" }}>
                {g.photos.map((p, i) => (
                    <a key={i} href={g.google_maps_uri} target="_blank" rel="noreferrer" style={{ flex: "0 0 auto", textDecoration: "none" }}>
                        <img src={p.url} alt={`${g.name ?? ""} 사진 ${i + 1}`} style={{ width: 120, height: 120, objectFit: "cover", borderRadius: 10, display: "block" }} />
                        {p.author && <div style={{ fontSize: 10, color: quiet, marginTop: 2, maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>사진: {p.author}</div>}
                    </a>
                ))}
            </div>
            <GoogleAttribution uri={g.google_maps_uri} />
        </div>
    );
}

/** 리뷰 (최대 5개, 구글 관련성 순) — 작성자 사진·이름·링크 */
export function GoogleReviews({ g }: { g: GooglePlaceDetails }) {
    if (!g.reviews?.length) return null;
    return (
        <div>
            <p style={{ fontSize: 13, fontWeight: 600, color: ink, marginBottom: 8 }}>리뷰</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {g.reviews.map((r, i) => (
                    <div key={i} style={{ background: soft, borderRadius: 12, padding: 12 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                            {r.author_photo && <img src={r.author_photo} alt="" width={22} height={22} style={{ borderRadius: "50%" }} />}
                            <a href={r.author_uri || r.google_maps_uri} target="_blank" rel="noreferrer" style={{ fontSize: 12, fontWeight: 600, color: ink, textDecoration: "none" }}>{r.author}</a>
                            <span style={{ fontSize: 11, color: "#F4B400" }}>{stars(r.rating)}</span>
                            <span style={{ fontSize: 11, color: quiet, marginLeft: "auto" }}>{r.relative_time}</span>
                        </div>
                        <p style={{ fontSize: 12.5, color: "#555", margin: 0, lineHeight: 1.6, display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{r.text}</p>
                        <a href={r.google_maps_uri} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: "#7b6bad" }}>원문 보기</a>
                    </div>
                ))}
            </div>
            <p style={{ fontSize: 10.5, color: "#bbb", margin: "6px 0 0" }}>구글이 관련성 순으로 고른 리뷰 최대 5개예요.</p>
            <GoogleAttribution uri={g.google_maps_uri} />
        </div>
    );
}
