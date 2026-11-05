"use client";
// Browser-side API access through the same-origin BFF proxy (/bff/*), which attaches
// the token + subject from httpOnly cookies. Never throws for HTTP errors.
import type { ApiResult } from "./types";

export async function bff<T>(path: string, init: { method?: string; body?: unknown; form?: FormData } = {}): Promise<ApiResult<T>> {
  let res: Response;
  try {
    res = await fetch(`/bff${path}`, {
      method: init.method ?? (init.body !== undefined || init.form ? "POST" : "GET"),
      headers: init.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: init.form ?? (init.body !== undefined ? JSON.stringify(init.body) : undefined),
      cache: "no-store",
    });
  } catch {
    return { ok: false, status: 0, detail: "Der Dienst ist gerade nicht erreichbar." };
  }
  if (!res.ok) {
    let detail = res.statusText || `Fehler ${res.status}`;
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch {}
    return { ok: false, status: res.status, detail };
  }
  return { ok: true, data: (await res.json()) as T };
}
