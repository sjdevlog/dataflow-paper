import { C } from "../../constants/theme";
import type { CourseSource } from "../../types/course";

/** 백엔드 실패로 샘플 코스를 보여줄 때 표시 */
export default function SampleDataNotice({ source }: { source: CourseSource }) {
  if (source !== "mock") return null;
  return (
    <div style={{ background: C.warnBg, border: `1px solid ${C.warnBorder}`, borderRadius: 10, padding: "9px 14px", fontSize: 12, color: C.warn, marginBottom: 16 }}>
      ⚠ 서버에서 코스를 받지 못해 샘플 데이터를 보여드리고 있어요.
    </div>
  );
}
