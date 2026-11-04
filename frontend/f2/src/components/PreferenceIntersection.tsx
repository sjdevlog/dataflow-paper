interface PreferenceIntersectionProps {
    personA: string[];
    personB: string[];
    common: string[];
    nameA?: string;
    nameB?: string;
}

interface TagProps {
    label: string;
    variant: 'a' | 'b' | 'common';
}

const VARIANT_MAP: Record<'a' | 'b' | 'common', { tag: React.CSSProperties; dot: string }> = {
    a:      { tag: { background: '#E8E4F4', color: '#7B6BAD' }, dot: '#b8a9d9' },
    b:      { tag: { background: '#FAEEF2', color: '#c0607a' }, dot: '#e8a0b4' },
    common: { tag: { background: '#E4EEF8', color: '#5a84b0' }, dot: '#a8c4e0' },
};

function Tag({ label, variant }: TagProps) {
    return (
        <span style={{
            ...VARIANT_MAP[variant].tag,
            display: 'inline-block',
            padding: '4px 12px',
            borderRadius: '999px',
            fontSize: '13px',
            fontWeight: 500,
        }}>
            {label}
        </span>
    );
}

function LegendDot({ variant, label }: { variant: 'a' | 'b' | 'common'; label: string }) {
    return (
        <div style={{ display: "flex", alignItems: "center", gap: '4px', fontSize: '12px', color: '#999' }}>
            <span style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                background: VARIANT_MAP[variant].dot,
                display: 'inline-block',
            }} />
            {label}
        </div>
    );
}

export default function PreferenceIntersection({ personA, personB, common, nameA = "A", nameB = "B" }: PreferenceIntersectionProps) {
    return (
        <div style={{
            background: '#FFFFFF',
            borderRadius: '16px',
            padding: '16px',
            border: '1px solid #E8E4F4',
            boxShadow: '0 1px 4px rgba(184,169,217,0.15)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
        }}>
            <div>
                <p style={{ fontSize: '11px', color: '#B8A9D9', marginBottom: '6px', fontWeight: 600 }}>
                    {nameA}님 선호
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {personA.map((keyword) => (
                        <Tag key={keyword} label={keyword} variant="a" />
                    ))}
                </div>
            </div>

            <div>
                <p style={{ fontSize: '11px', color: '#E8A0B4', marginBottom: '6px', fontWeight: 600 }}>
                    {nameB}님 선호
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {personB.map((keyword) => (
                        <Tag key={keyword} label={keyword} variant="b" />
                    ))}
                </div>
            </div>

            <hr style={{ border: 'none', borderTop: '1px solid #E8E4F4' }} />

            <div>
                <p style={{ fontSize: '11px', color: '#A8C4E0', marginBottom: '6px', fontWeight: 600 }}>
                    공통 교집합
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {common.map((keyword) => (
                        <Tag key={keyword} label={keyword} variant="common" />
                    ))}
                </div>
            </div>

            <div style={{ display: 'flex', gap: '16px', paddingTop: '4px' }}>
                <LegendDot variant="a" label={`${nameA}님`} />
                <LegendDot variant="b" label={`${nameB}님`} />
                <LegendDot variant="common" label="공통" />
            </div>
        </div>
    );
}