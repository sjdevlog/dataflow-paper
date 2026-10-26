import { postJson } from "./http";
import { tagToFoodType, tagToMood } from "../utils/tags";

/** POST /user/prefs — A님 취향을 세션 사용자로 저장 (실패해도 코스 생성은 진행) */
export async function savePrefs(sessionId: string, tagsA: string[], tagsB: string[], budget: number): Promise<boolean> {
  try {
    await postJson("/user/prefs", {
      user_id:    `${sessionId}_A`,
      partner_id: `${sessionId}_B`,
      mood:       tagToMood(tagsA),
      food_type:  tagToFoodType([...tagsA, ...tagsB]),
      budget,
      age_group:  "20대",
    }, 5000);
    return true;
  } catch {
    return false;
  }
}
