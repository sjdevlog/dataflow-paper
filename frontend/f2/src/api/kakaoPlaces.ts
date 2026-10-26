import { KAKAO_JS_KEY } from "../config";
import { loadKakaoSDK } from "../utils/kakaoSDK";

export type PlaceSearchResult = { name: string; address: string; lat: number; lon: number };

type KakaoKeywordDoc = { place_name: string; address_name: string; x: string; y: string };

/** 카카오 JS SDK 키워드 검색 (키 없으면 빈 배열) */
export async function searchKakaoPlaces(query: string, limit = 8): Promise<PlaceSearchResult[]> {
  if (!KAKAO_JS_KEY || !query.trim()) return [];
  await loadKakaoSDK();
  const { services } = window.kakao.maps;
  return new Promise((resolve) => {
    new services.Places().keywordSearch(query, (results: KakaoKeywordDoc[], status: string) => {
      if (status !== services.Status.OK) { resolve([]); return; }
      resolve(results.slice(0, limit).map(d => ({
        name:    d.place_name,
        address: d.address_name,
        lat:     parseFloat(d.y),
        lon:     parseFloat(d.x),
      })));
    });
  });
}
