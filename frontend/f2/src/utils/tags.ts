// 온보딩 취향 태그 (backend/B1/app/services/scoring.py 의 CATEGORY_TAG_MATCH 와 같은 어휘)
export const PREF_TAGS: Record<string, string[]> = {
  분위기: ["조용한 분위기", "활기찬 분위기", "로맨틱", "캐주얼", "고급스러운"],
  활동:   ["전시·문화", "맛집 탐방", "활동적인 코스", "핫플 방문", "산책·자연"],
  카페:   ["여유로운 카페", "감성 카페", "디저트 맛집", "브런치"],
};

const FOOD_TAGS = ["맛집 탐방", "여유로운 카페", "감성 카페", "디저트 맛집", "브런치", "전시·문화", "활동적인 코스", "산책·자연", "핫플 방문"];

export function tagToMood(tags: string[]): string {
  if (tags.includes("로맨틱"))        return "로맨틱";
  if (tags.includes("고급스러운"))    return "고급스러운";
  if (tags.includes("조용한 분위기")) return "조용한";
  if (tags.includes("활기찬 분위기")) return "활기찬";
  return "감성적";
}

export const tagToFoodType = (tags: string[]) => tags.filter(t => FOOD_TAGS.includes(t));

export const commonTags = (a: string[], b: string[]) => a.filter(t => b.includes(t));
