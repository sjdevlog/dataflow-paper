import { useState } from "react";
import { C, FONT } from "../../constants/theme";
import { KO_DAYS, formatDateKo, isWeekendDate, todayStr } from "../../utils/date";

export default function CalendarPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const today = todayStr();
  const [view, setView] = useState(() => {
    const d = new Date((value || today) + "T00:00:00");
    return { year: d.getFullYear(), month: d.getMonth() };
  });

  const { year: vy, month: vm } = view;
  const prevMonth = () => setView(v => v.month === 0  ? { year:v.year-1, month:11 } : { ...v, month:v.month-1 });
  const nextMonth = () => setView(v => v.month === 11 ? { year:v.year+1, month:0  } : { ...v, month:v.month+1 });

  const firstDow    = new Date(vy, vm, 1).getDay();
  const daysInMonth = new Date(vy, vm + 1, 0).getDate();
  const cells: (number | null)[] = [
    ...Array(firstDow).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const weekend = isWeekendDate(value);

  return (
    <div style={{ marginBottom:16 }}>
      <div style={{ background:C.card, border:`1.5px solid ${C.cardBorder}`, borderRadius:20, padding:"16px 14px 20px", boxShadow:"0 2px 12px #B8A9D910" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
          <button onClick={prevMonth} style={{ width:32, height:32, borderRadius:"50%", border:"none", background:C.inputBg, color:C.textDim, fontSize:16, cursor:"pointer", lineHeight:"1" }}>‹</button>
          <span style={{ fontSize:15, fontWeight:700, color:C.text, fontFamily:FONT }}>{vy}년 {vm + 1}월</span>
          <button onClick={nextMonth} style={{ width:32, height:32, borderRadius:"50%", border:"none", background:C.inputBg, color:C.textDim, fontSize:16, cursor:"pointer", lineHeight:"1" }}>›</button>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(7,1fr)", marginBottom:6 }}>
          {KO_DAYS.map((d, i) => (
            <div key={d} style={{ textAlign:"center", fontSize:11, fontWeight:700, padding:"4px 0",
              color: i===0 ? "#E07070" : i===6 ? "#6090D0" : C.textMuted }}>{d}</div>
          ))}
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(7,1fr)", gap:"2px" }}>
          {cells.map((day, idx) => {
            if (!day) return <div key={`e${idx}`} />;
            const ds     = `${vy}-${String(vm+1).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
            const dow    = new Date(vy, vm, day).getDay();
            const isPast = ds < today;
            const isSel  = ds === value;
            const isToday= ds === today;
            return (
              <button key={ds} onClick={() => !isPast && onChange(ds)} style={{
                padding:"8px 2px", borderRadius:10,
                border: isToday && !isSel ? `1.5px solid ${C.main}` : "none",
                background: isSel ? C.main : "transparent",
                color: isPast ? C.textMuted : isSel ? "#fff" : dow===0 ? "#E07070" : dow===6 ? "#6090D0" : C.text,
                fontSize:13, fontWeight: isSel||isToday ? 700 : 400,
                cursor: isPast ? "default" : "pointer", opacity: isPast ? 0.3 : 1,
                fontFamily:FONT, transition:"background 0.15s, color 0.15s",
              }}>{day}</button>
            );
          })}
        </div>
      </div>
      {value && (
        <div style={{ marginTop:10, display:"flex", alignItems:"center", gap:8 }}>
          <span style={{ fontSize:13, color:C.text, fontWeight:600, fontFamily:FONT }}>📅 {formatDateKo(value)}</span>
          <span style={{ fontSize:11, padding:"2px 9px", borderRadius:"999px", fontWeight:600,
            background: weekend ? C.pointDim : C.mainDim,
            color:      weekend ? C.point    : C.main }}>
            {weekend ? "주말" : "평일"}
          </span>
        </div>
      )}
    </div>
  );
}
