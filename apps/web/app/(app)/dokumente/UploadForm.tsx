"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { bff } from "@/lib/client";
import type { DocumentAnalysis, DocumentSummary } from "@/lib/types";

export function UploadForm({ subjectName }: { subjectName: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<"idle" | "upload" | "analyze">("idle");
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError(null);
    setState("upload");
    const fd = new FormData();
    fd.append("file", file);
    const up = await bff<DocumentSummary>("/api/documents", { form: fd });
    if (!up.ok) {
      setState("idle");
      setError(up.status === 403 ? `Dafür hat ${subjectName} keine Berechtigung erteilt. ${up.detail}` : up.detail);
      return;
    }
    setState("analyze");
    const an = await bff<DocumentAnalysis>(`/api/documents/${up.data.document_id}/analyze`, { method: "POST" });
    if (!an.ok) {
      setState("idle");
      setError(an.detail);
      return;
    }
    router.push(`/dokumente/${up.data.document_id}`);
  }

  return (
    <form onSubmit={submit} className="card space-y-4 border-2 border-dashed border-accent/40">
      <div>
        <label htmlFor="doc" className="font-semibold">
          Dokument hochladen (PDF)
        </label>
        <p className="text-muted">z. B. Entlassungsbrief, Befund oder e-Impfpass-Ausdruck von {subjectName}.</p>
      </div>
      <input
        id="doc"
        type="file"
        accept="application/pdf"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="block w-full text-ink file:mr-4 file:rounded-lg file:border-0 file:bg-accent-soft file:px-4 file:py-2 file:font-semibold file:text-accent-strong"
      />
      <button className="btn-primary" disabled={!file || state !== "idle"}>
        {state === "upload" ? "Wird hochgeladen …" : state === "analyze" ? "Wird gelesen …" : "Hochladen und lesen"}
      </button>
      {error && (
        <p role="alert" className="rounded-lg bg-danger-soft p-3 text-danger">
          {error}
        </p>
      )}
    </form>
  );
}
