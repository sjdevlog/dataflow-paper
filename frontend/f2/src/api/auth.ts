import { postJson, ApiError } from "./http";

export interface AuthUser {
  user_id: string;
  username: string;
  nickname: string;
  gender: string;
  token: string;
}

export type Gender = "M" | "F" | "N";

type TokenResponse = Omit<AuthUser, "token"> & { access_token: string };

export async function login(username: string, password: string): Promise<AuthUser> {
  const data = await postJson<TokenResponse>("/auth/login", { username, password });
  return { ...data, token: data.access_token };
}

export async function register(username: string, password: string, nickname: string, gender: Gender): Promise<AuthUser> {
  const data = await postJson<TokenResponse>("/auth/register", { username, password, nickname, gender });
  return { ...data, token: data.access_token };
}

/** FastAPI 에러(detail 문자열 또는 pydantic 검증 배열)를 사용자 메시지로 */
export function authErrorMessage(e: unknown): string {
  if (!(e instanceof ApiError)) return "서버에 연결할 수 없습니다.";
  const d = e.detail;
  if (Array.isArray(d)) return d.map((x: { msg: string }) => x.msg.replace("Value error, ", "")).join(" / ");
  return typeof d === "string" ? d : "오류가 발생했습니다.";
}
