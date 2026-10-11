const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8005/api/v1";

/** WP1's pagination envelope, returned by every list route. */
export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init);
  if (!response.ok) {
    // Every WP5 failure follows WP1's ApiError contract: one reader handles them all.
    const body = await response.json().catch(() => null);
    throw new Error(body?.message ?? `Erreur HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export const apiGet = <T,>(path: string) => request<T>(path);

export const apiPost = <T,>(path: string, body?: unknown) =>
  request<T>(path, {
    method: "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });