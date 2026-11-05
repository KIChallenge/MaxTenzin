"use client";
// Upload + analyse a document for the current subject (same path for the Dokumente drop zone and the Lotsi chat).
import { bff } from "./client";
import type { DocumentAnalysis, DocumentSummary } from "./types";

export const ACCEPT = "application/pdf,image/jpeg,image/png";
const ALLOWED = ["application/pdf", "image/jpeg", "image/png"];
const MAX_MB = 20;

export type UploadResult =
  | { ok: true; doc: DocumentSummary; analysis: DocumentAnalysis | null }
  | { ok: false; status: number; detail: string };

export function checkFile(file: File): string | null {
  if (!ALLOWED.includes(file.type)) return "Bitte eine PDF-Datei oder ein Foto (JPG, PNG) verwenden.";
  if (file.size > MAX_MB * 1024 * 1024) return `Die Datei ist größer als ${MAX_MB} MB.`;
  return null;
}

/** One PDF or one photo → `file`; several photos → `files` (one page each, in the given order). */
export async function uploadAndAnalyze(input: File | File[], onStage?: (s: "upload" | "analyze") => void): Promise<UploadResult> {
  const files = Array.isArray(input) ? input : [input];
  for (const f of files) {
    const problem = checkFile(f);
    if (problem) return { ok: false, status: 0, detail: problem };
  }
  if (files.length > 1 && files.some((f) => f.type === "application/pdf"))
    return { ok: false, status: 0, detail: "Mehrere Seiten bitte als Fotos – oder ein einzelnes PDF." };
  onStage?.("upload");
  const fd = new FormData();
  const named = (f: File, i: number) =>
    f.name && f.name !== "image.png" ? f.name : `Foto-${i + 1}-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-")}.${f.type === "image/png" ? "png" : "jpg"}`;
  if (files.length === 1) fd.append("file", files[0], named(files[0], 0));
  else files.forEach((f, i) => fd.append("files", f, named(f, i)));
  const up = await bff<DocumentSummary>("/api/documents", { form: fd });
  if (!up.ok) return up;
  onStage?.("analyze");
  const an = await bff<DocumentAnalysis>(`/api/documents/${up.data.document_id}/analyze`, { method: "POST" });
  // Discharge letters: prepare Lebenslage suggestions (never applied without the person's "Ja, übernehmen").
  if (an.ok && an.data.doc_type === "discharge_letter") {
    await bff(`/api/situation/suggestions/from-document/${up.data.document_id}`, { method: "POST" });
  }
  return { ok: true, doc: up.data, analysis: an.ok ? an.data : null };
}
