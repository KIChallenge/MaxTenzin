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

export async function uploadAndAnalyze(file: File, onStage?: (s: "upload" | "analyze") => void): Promise<UploadResult> {
  const problem = checkFile(file);
  if (problem) return { ok: false, status: 0, detail: problem };
  onStage?.("upload");
  const fd = new FormData();
  // Pasted screenshots have no useful name
  fd.append("file", file, file.name && file.name !== "image.png" ? file.name : `Foto-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-")}.png`);
  const up = await bff<DocumentSummary>("/api/documents", { form: fd });
  if (!up.ok) return up;
  onStage?.("analyze");
  const an = await bff<DocumentAnalysis>(`/api/documents/${up.data.document_id}/analyze`, { method: "POST" });
  return { ok: true, doc: up.data, analysis: an.ok ? an.data : null };
}
