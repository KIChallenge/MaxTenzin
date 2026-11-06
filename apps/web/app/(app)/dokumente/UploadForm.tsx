"use client";
// Drop zone: drag a PDF or photo onto it, or click / press Enter to choose one. Upload starts right away.
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Camera, FileUp, LoaderCircle, Sparkles } from "lucide-react";
import { ACCEPT, uploadAndAnalyze } from "@/lib/upload";

/** compact: the home-page quick drop (smaller, no camera row). */
export function UploadForm({ subjectName, compact = false }: { subjectName: string; compact?: boolean }) {
  const [stage, setStage] = useState<"idle" | "upload" | "analyze">("idle");
  const [over, setOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const camera = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const busy = stage !== "idle";

  async function handle(list: FileList | File[] | null | undefined) {
    const files = Array.from(list ?? []);
    if (!files.length || busy) return;
    setError(null);
    setName(files.length > 1 ? `${files.length} Fotos` : files[0].name);
    const r = await uploadAndAnalyze(files.length > 1 ? files : files[0], setStage);
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
          handle(e.dataTransfer.files);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 ${compact ? "h-full py-5" : "py-10"} text-center transition-colors ${
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
            {stage === "upload" ? "Wird hochgeladen und gelesen …" : "Wird ausgewertet …"} <span className="font-normal text-muted">{name}</span>
          </p>
        ) : (
          <>
            {compact && (
              <p className="inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2.5 py-0.5 text-xs font-semibold tracking-wide text-accent-strong uppercase">
                <Sparkles className="h-3.5 w-3.5" aria-hidden /> Schnellstart · automatische Erkennung
              </p>
            )}
            <p className="font-semibold">
              {over ? "Loslassen zum Hochladen" : compact ? "Dokument ablegen – Lotsi erkennt, was es ist" : "Dokument hierher ziehen"}
            </p>
            {compact && (
              <p className="text-sm text-muted">Entlassungsbrief, Befund oder e-Impfpass: wird gelesen, eingeordnet und direkt zur Prüfung geöffnet.</p>
            )}
            <p className="text-sm text-muted">
              oder <span className="font-semibold text-accent underline underline-offset-2">Datei auswählen</span> · ein PDF oder Fotos
              (JPG, PNG) – mehrere Fotos werden ein Dokument
            </p>
            {!compact && <p className="text-sm text-muted">z. B. Entlassungsbrief, Befund oder e-Impfpass von {subjectName}</p>}
          </>
        )}
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          multiple
          className="sr-only"
          tabIndex={-1}
          onChange={(e) => {
            handle(e.target.files);
            e.target.value = "";
          }}
        />
      </div>
      <div className={compact ? "hidden" : "mt-2 flex items-center gap-2"}>
        <button type="button" className="btn-secondary py-1 text-sm" disabled={busy} onClick={() => camera.current?.click()}>
          <Camera className="h-4 w-4" aria-hidden /> Foto aufnehmen
        </button>
        <span className="text-sm text-muted">Am Handy öffnet sich die Kamera. Gut ausleuchten, ganze Seite aufs Bild.</span>
        <input
          ref={camera}
          type="file"
          accept="image/*"
          capture="environment"
          multiple
          className="sr-only"
          tabIndex={-1}
          onChange={(e) => {
            handle(e.target.files);
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
