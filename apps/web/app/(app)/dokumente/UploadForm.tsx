"use client";
// Drop zone: drag a PDF or photo onto it, or click / press Enter to choose one. Upload starts right away.
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileUp, LoaderCircle } from "lucide-react";
import { ACCEPT, uploadAndAnalyze } from "@/lib/upload";

export function UploadForm({ subjectName }: { subjectName: string }) {
  const [stage, setStage] = useState<"idle" | "upload" | "analyze">("idle");
  const [over, setOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const busy = stage !== "idle";

  async function handle(file: File | undefined) {
    if (!file || busy) return;
    setError(null);
    setName(file.name);
    const r = await uploadAndAnalyze(file, setStage);
    if (!r.ok) {
      setStage("idle");
      setError(r.status === 403 ? `Dafür hat ${subjectName} keine Berechtigung erteilt. ${r.detail}` : r.detail);
      return;
    }
    router.push(`/dokumente/${r.doc.document_id}`);
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Dokument hochladen: Datei hierher ziehen oder auswählen"
        aria-busy={busy}
        onClick={() => !busy && input.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), !busy && input.current?.click())}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          handle(e.dataTransfer.files?.[0]);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
          over ? "border-accent bg-accent-soft" : "border-line bg-surface hover:border-accent/60 hover:bg-accent-soft/40"
        } ${busy ? "cursor-wait" : ""}`}
      >
        {busy ? (
          <LoaderCircle className="h-8 w-8 animate-spin text-accent" aria-hidden />
        ) : (
          <FileUp className={`h-8 w-8 ${over ? "text-accent" : "text-muted"}`} aria-hidden />
        )}
        {busy ? (
          <p className="font-semibold">
            {stage === "upload" ? "Wird hochgeladen …" : "Wird gelesen …"} <span className="font-normal text-muted">{name}</span>
          </p>
        ) : (
          <>
            <p className="font-semibold">{over ? "Loslassen zum Hochladen" : "Dokument hierher ziehen"}</p>
            <p className="text-sm text-muted">
              oder <span className="font-semibold text-accent underline underline-offset-2">Datei auswählen</span> · PDF oder Foto
              (JPG, PNG)
            </p>
            <p className="text-sm text-muted">z. B. Entlassungsbrief, Befund oder e-Impfpass von {subjectName}</p>
          </>
        )}
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          tabIndex={-1}
          onChange={(e) => {
            handle(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </div>
      {error && (
        <p role="alert" className="mt-3 rounded-lg bg-danger-soft p-3 text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
