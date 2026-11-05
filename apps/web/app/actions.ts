"use server";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { api } from "@/lib/api";
import { COOKIE_PLAIN, COOKIE_SUBJECT, COOKIE_TOKEN } from "@/lib/session";
import type { Case, DocumentAnalysis, DocumentSummary, FormSession, Session } from "@/lib/types";

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
  const documentId = String(formData.get("document_id") ?? "");
  const base = `/api/forms/definitions/${encodeURIComponent(formId)}/sessions`;
  // Prefill from the analysed document when we have one; fall back to profile-only prefill.
  let r = await api<FormSession>(documentId ? `${base}?document_id=${encodeURIComponent(documentId)}` : base, { method: "POST" });
  if (!r.ok && documentId && r.status === 404) r = await api<FormSession>(base, { method: "POST" });
  if (!r.ok) redirect(`/leistungen?error=${encodeURIComponent(r.detail)}&status=${r.status}`);
  // Link the new session to the matching "Mein Fall" step (best effort; case may not exist yet).
  const benefitId = String(formData.get("benefit_id") ?? "");
  if (benefitId) {
    const cases = await api<Case[]>("/api/cases");
    if (cases.ok) {
      for (const c of cases.data) {
        const step = c.steps.find((s) => s.benefit_id === benefitId && !s.form_session_id);
        if (step) {
          await api<Case>(`/api/cases/${c.id}/steps/${step.id}`, { method: "PATCH", body: { form_session_id: r.data.id } });
          break;
        }
      }
    }
  }
  redirect(`/forms/${r.data.id}`);
}

/** "Mein Fall" from the latest analysed document: its open tasks + the benefits it mentions. */
export async function createCase() {
  const docs = await api<DocumentSummary[]>("/api/documents");
  if (!docs.ok) redirect(`/fall?error=${encodeURIComponent(docs.detail)}&status=${docs.status}`);
  const latest = [...docs.data].sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at))[0];
  if (!latest) redirect(`/fall?error=${encodeURIComponent("Bitte zuerst ein Dokument hochladen.")}`);
  const an = await api<DocumentAnalysis>(`/api/documents/${latest.document_id}/analysis`);
  const benefitIds = an.ok ? [...new Set(an.data.recommendations.flatMap((x) => x.related_benefit_ids ?? []))] : [];
  const me = await api<Session>("/api/identity/me");
  const r = await api<Case>("/api/cases", {
    method: "POST",
    body: {
      subject_id: me.ok ? me.data.subject.id : "",
      title_de: "Versorgung nach dem Spitalsaufenthalt",
      document_id: latest.document_id,
      benefit_ids: benefitIds,
    },
  });
  if (!r.ok) redirect(`/fall?error=${encodeURIComponent(r.detail)}&status=${r.status}`);
  revalidatePath("/fall");
  redirect("/fall");
}
