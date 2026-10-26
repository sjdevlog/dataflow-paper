import { API_BASE } from "../config";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(`API ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

/** fetch + 타임아웃 + JSON 파싱. 2xx 가 아니면 ApiError */
export async function requestJson<T>(path: string, init: RequestInit = {}, timeoutMs = 30000): Promise<T> {
  const ctrl  = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
    const res = await fetch(url, { ...init, signal: ctrl.signal });
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new ApiError(res.status, data?.detail ?? data);
    return data as T;
  } finally {
    clearTimeout(timer);
  }
}

export function postJson<T>(path: string, body: unknown, timeoutMs?: number): Promise<T> {
  return requestJson<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }, timeoutMs);
}
