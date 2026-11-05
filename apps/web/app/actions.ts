"use server";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { api } from "@/lib/api";
import { COOKIE_PLAIN, COOKIE_SUBJECT, COOKIE_TOKEN } from "@/lib/session";
import type { FormSession, Session } from "@/lib/types";

const cookieOpts = { httpOnly: true, sameSite: "lax" as const, path: "/" };

export async function login(formData: FormData) {
  const persona = String(formData.get("persona_id") ?? "");
  const r = await api<Session>("/api/identity/login", { method: "POST", body: { persona_id: persona } });
  if (!r.ok) redirect(`/login?error=${encodeURIComponent(r.detail)}`);
  const jar = await cookies();
  jar.set(COOKIE_TOKEN, r.data.token, cookieOpts);
  jar.set(COOKIE_SUBJECT, r.data.subject.id, cookieOpts);
  jar.set(COOKIE_PLAIN, r.data.actor.plain_language ? "1" : "0", cookieOpts);
  redirect("/");
}

export async function logout() {
  const jar = await cookies();
  jar.delete(COOKIE_TOKEN);
  jar.delete(COOKIE_SUBJECT);
  redirect("/login");
}

export async function setSubject(subjectId: string) {
  (await cookies()).set(COOKIE_SUBJECT, subjectId, cookieOpts);
  revalidatePath("/", "layout");
}

export async function setPlain(on: boolean) {
  (await cookies()).set(COOKIE_PLAIN, on ? "1" : "0", cookieOpts);
  revalidatePath("/", "layout");
}

/** "Antrag vorbereiten": start a prefilled form session and open the wizard. */
export async function startForm(formData: FormData) {
  const formId = String(formData.get("form_id") ?? "");
  const r = await api<FormSession>(`/api/forms/definitions/${encodeURIComponent(formId)}/sessions`, { method: "POST" });
  if (!r.ok) redirect(`/leistungen?error=${encodeURIComponent(r.detail)}&status=${r.status}`);
  redirect(`/forms/${r.data.id}`);
}
