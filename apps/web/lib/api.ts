// Server-side API access. Reads the mock-ID-Austria token + chosen subject from cookies
// and calls the FastAPI services with the user's own rights (via: ui).
import { cookies } from "next/headers";
import { API_URL, COOKIE_PLAIN, COOKIE_SUBJECT, COOKIE_TOKEN, factsCookie } from "./session";
import type { ApiResult } from "./types";

export async function authHeaders(): Promise<Record<string, string>> {
  const jar = await cookies();
  const h: Record<string, string> = { "X-Via": "ui" };
  const token = jar.get(COOKIE_TOKEN)?.value;
  const subject = jar.get(COOKIE_SUBJECT)?.value;
  if (token) h.Authorization = `Bearer ${token}`;
  if (subject) h["X-Subject-Id"] = subject;
  return h;
}

export async function isPlain(): Promise<boolean> {
  return (await cookies()).get(COOKIE_PLAIN)?.value === "1";
}

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<ApiResult<T>> {
  const headers = await authHeaders();
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: init.method ?? "GET",
      headers,
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
      cache: "no-store",
    });
  } catch {
    return { ok: false, status: 0, detail: "Der Dienst ist gerade nicht erreichbar." };
  }
  if (!res.ok) return { ok: false, status: res.status, detail: await errorDetail(res) };
  return { ok: true, data: (await res.json()) as T };
}

export async function errorDetail(res: Response): Promise<string> {
  try {
    const j = await res.json();
    if (typeof j.detail === "string") return j.detail;
    return JSON.stringify(j.detail ?? j);
  } catch {
    return res.statusText || `Fehler ${res.status}`;
  }
}

/** Like api() but throws on error — for data a page cannot render without. */
export async function apiOrThrow<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  const r = await api<T>(path, init);
  if (!r.ok) throw new Error(`${r.status}: ${r.detail}`);
  return r.data;
}

/** Facts the person entered for the current subject (see saveFact). */
export async function getFacts(): Promise<Record<string, string | number | boolean>> {
  const jar = await cookies();
  const subject = jar.get(COOKIE_SUBJECT)?.value;
  if (!subject) return {};
  try {
    return JSON.parse(jar.get(factsCookie(subject))?.value ?? "{}");
  } catch {
    return {};
  }
}
