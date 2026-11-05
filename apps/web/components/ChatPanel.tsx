"use client";
import { FileText, History, LoaderCircle, Mic, MicOff, Paperclip, SquarePen, TriangleAlert, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { bff } from "@/lib/client";
import { fmtDateTime, toolLabel } from "@/lib/labels";
import type { ChatAction, ChatResponse, ToolTrace } from "@/lib/types";
import type { components } from "@/lib/api-types";
import { ACCEPT, uploadAndAnalyze } from "@/lib/upload";
import { LotsiAvatar } from "./Lotsi";
import { SimpleMarkdown } from "./SimpleMarkdown";
import { SlotChoices } from "./SlotChoices";

type Conversation = components["schemas"]["Conversation"];
type Attachment = {
  key: string;
  filename: string;
  status: "pending" | "uploading" | "ready" | "error";
  file?: File;
  documentId?: string;
  error?: string;
};
type Msg =
  | { role: "user"; text: string; files?: string[] }
  | { role: "assistant"; text: string; trace: ToolTrace[]; boundary: boolean; suggestions: string[]; actions?: ChatAction[] }
  | { role: "error"; text: string };

const STARTERS = ["Was steht im Entlassungsbrief?", "Welche Leistungen kommen in Frage?", "Hilf mir beim Pflegegeld-Antrag"];

// Minimal typing for the browser speech API (not in lib.dom for all targets).
type Recognition = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onend: (() => void) | null;
  onerror: ((e: { error: string }) => void) | null;
};
function createRecognition(): Recognition | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
  const Ctor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
  return Ctor ? new Ctor() : null;
}

export function ChatPanel({ subjectId, subjectName, plain, voice = false }: { subjectId: string; subjectName: string; plain: boolean; voice?: boolean }) {
  const storeKey = `lotse-chat-${subjectId}`;
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<"chat" | "history">("chat");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [conv, setConv] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<Attachment[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [history, setHistory] = useState<Conversation[] | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const recognition = useRef<Recognition | null>(null);
  const [listening, setListening] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  // Question handed over from a page ("Lotsi fragen"): sent once the fresh conversation state is in place.
  const [pendingSend, setPendingSend] = useState<string | null>(null);

  /** Speech → text field (de-AT). The person still presses "Senden" – nothing is sent unseen. */
  function toggleVoice() {
    if (listening) {
      recognition.current?.stop();
      return;
    }
    const r = createRecognition();
    if (!r) return setVoiceError("Spracheingabe wird von diesem Browser nicht unterstützt.");
    r.lang = "de-AT";
    r.interimResults = true;
    r.continuous = false;
    const base = input ? `${input.trim()} ` : "";
    r.onresult = (e) => {
      const text = Array.from(e.results)
        .map((res) => res[0]?.transcript ?? "")
        .join("");
      setInput(base + text);
    };
    r.onerror = (e) => setVoiceError(e.error === "not-allowed" ? "Bitte erlauben Sie den Zugriff auf das Mikrofon." : "Spracheingabe hat nicht geklappt.");
    r.onend = () => setListening(false);
    recognition.current = r;
    setVoiceError(null);
    setListening(true);
    r.start();
  }
  const router = useRouter();
  const pathname = usePathname();

  // Restore the current conversation per represented person (survives reloads within the tab).
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(storeKey);
      const saved = raw ? JSON.parse(raw) : null;
      setMsgs(saved?.msgs ?? []);
      setConv(saved?.conv ?? null);
      setOpen(sessionStorage.getItem("lotse-chat-open") === "1");
    } catch {}
    setFiles([]);
    setView("chat");
  }, [storeKey]);
  useEffect(() => {
    try {
      sessionStorage.setItem(storeKey, JSON.stringify({ msgs, conv }));
    } catch {}
    endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs, conv, storeKey]);
  useEffect(() => {
    const onOpen = (e: Event) => {
      const d = (e as CustomEvent<{ question?: string; send?: boolean; fresh?: boolean } | string | undefined>).detail;
      const detail = typeof d === "string" ? { question: d } : (d ?? {});
      setOpen(true);
      setView("chat");
      if (detail.fresh) {
        setConv(null);
        setMsgs([]);
        setFiles([]);
      }
      if (detail.question && detail.send) setPendingSend(detail.question);
      else if (detail.question) setInput(detail.question);
    };
    window.addEventListener("lotse:open-chat", onOpen);
    return () => window.removeEventListener("lotse:open-chat", onOpen);
  }, []);
  useEffect(() => {
    try {
      sessionStorage.setItem("lotse-chat-open", open ? "1" : "0");
    } catch {}
    // On wide screens the page makes room for the panel instead of being covered by it.
    document.body.classList.toggle("chat-open", open);
    return () => document.body.classList.remove("chat-open");
  }, [open]);

  /** Attach: only queue the files. They are uploaded and read when the message is sent (Enter / Senden), so the
   *  person can still write a question – and several photos of one letter become ONE document. */
  const attach = useCallback((list: FileList | File[] | null | undefined) => {
    const added = Array.from(list ?? []).map((file, i) => ({
      key: `${file.name}-${file.size}-${Date.now()}-${i}`,
      filename: file.name || "Foto",
      status: "pending" as const,
      file,
    }));
    if (added.length) setFiles((f) => [...f.filter((a) => a.status !== "error"), ...added]);
  }, []);

  /** Upload the queued files: all photos together as one document, each PDF on its own. */
  async function uploadPending(pending: Attachment[]): Promise<{ ids: string[]; names: string[]; error?: string }> {
    const photos = pending.filter((a) => a.file && a.file.type !== "application/pdf");
    const pdfs = pending.filter((a) => a.file && a.file.type === "application/pdf");
    const groups: Attachment[][] = [...(photos.length ? [photos] : []), ...pdfs.map((p) => [p])];
    const keys = new Set(pending.map((a) => a.key));
    setFiles((f) => f.map((a) => (keys.has(a.key) ? { ...a, status: "uploading" } : a)));
    const ids: string[] = [];
    const names: string[] = [];
    for (const g of groups) {
      const r = await uploadAndAnalyze(g.length > 1 ? g.map((a) => a.file!) : g[0].file!);
      const gk = new Set(g.map((a) => a.key));
      if (!r.ok) {
        const error = r.status === 403 ? `Dafür hat ${subjectName} keine Berechtigung erteilt. ${r.detail}` : r.detail;
        setFiles((f) => f.map((a) => (gk.has(a.key) ? { ...a, status: "error", error } : a)));
        return { ids, names, error };
      }
      ids.push(r.doc.document_id);
      names.push(r.doc.filename);
      setFiles((f) => f.map((a) => (gk.has(a.key) ? { ...a, status: "ready", documentId: r.doc.document_id } : a)));
    }
    router.refresh();
    return { ids, names };
  }

  function newConversation() {
    setConv(null);
    setMsgs([]);
    setFiles([]);
    setInput("");
    setView("chat");
  }

  async function showHistory() {
    setView("history");
    setHistory(null);
    const r = await bff<Conversation[]>("/api/agent/conversations");
    const list = r.ok ? r.data : [];
    setHistory([...list].sort((a, b) => (b.updated_at ?? b.created_at).localeCompare(a.updated_at ?? a.created_at)));
  }

  async function openConversation(id: string) {
    const r = await bff<Conversation>(`/api/agent/conversations/${id}`);
    if (!r.ok) return;
    const restored: Msg[] = r.data.turns.flatMap((t) => [
      { role: "user" as const, text: t.user },
      {
        role: "assistant" as const,
        text: t.reply,
        trace: (t.tool_trace ?? []) as ToolTrace[],
        boundary: !!t.boundary_triggered,
        suggestions: t.suggestions_de ?? [],
      },
    ]);
    setConv(id);
    setMsgs(restored);
    setFiles([]);
    setView("chat");
  }

  async function send(text: string) {
    const pending = files.filter((f) => f.status === "pending");
    if (busy || files.some((f) => f.status === "uploading") || (!text.trim() && !pending.length)) return;
    setBusy(true);
    const up = pending.length ? await uploadPending(pending) : { ids: [] as string[], names: [] as string[] };
    if (up.error) {
      setBusy(false);   // keep the text and the files; the error is shown above the input
      return;
    }
    const n = pending.length;
    const message =
      text.trim() || `Bitte sieh dir ${up.ids.length > 1 ? "diese Dokumente" : n > 1 ? `dieses Dokument (${n} Fotos)` : "dieses Dokument"} an.`;
    setInput("");
    setFiles([]);
    setMsgs((m) => [...m, { role: "user", text: message, files: pending.map((f) => f.filename) }]);
    const ctx = pageContext(pathname);
    const documentIds = [...up.ids, ...(ctx.document_ids ?? [])];
    const r = await bff<ChatResponse>("/api/agent/chat", {
      body: {
        message,
        conversation_id: conv,
        language: "de",
        plain_language: plain,
        ...ctx,
        ...(documentIds.length ? { document_ids: documentIds } : {}),
      },
    });
    setBusy(false);
    if (!r.ok) {
      setMsgs((m) => [
        ...m,
        {
          role: "error",
          text:
            r.status === 403
              ? `Dafür hat ${subjectName} keine Berechtigung erteilt. ${r.detail}`
              : "Lotsi ist gerade nicht erreichbar. Sie können alle Schritte auch direkt im Cockpit erledigen.",
        },
      ]);
      return;
    }
    setConv(r.data.conversation_id);
    setMsgs((m) => [
      ...m,
      {
        role: "assistant",
        text: r.data.reply,
        trace: r.data.tool_trace ?? [],
        boundary: !!r.data.boundary_triggered,
        suggestions: r.data.suggestions_de ?? [],
        actions: r.data.actions ?? [],
      },
    ]);
    // The agent may have changed data (case steps, form values) — refresh server views.
    if (r.data.tool_trace?.length) router.refresh();
  }

  useEffect(() => {
    if (!pendingSend || busy || conv !== null || msgs.length) return;
    const q = pendingSend;
    setPendingSend(null);
    send(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingSend, conv, msgs.length, busy]);

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="btn-primary fixed right-5 bottom-5 z-40 rounded-full py-2 pr-5 pl-2 text-lg shadow-lg"
      >
        <LotsiAvatar size={36} />
        Frag Lotsi
      </button>
    );
  }

  const uploading = files.some((f) => f.status === "uploading");
  const canSend = !busy && !uploading && (!!input.trim() || files.some((f) => f.status === "pending"));

  return (
    <aside
      aria-label="Chat mit Lotsi"
      onDragOver={(e) => {
        if (view !== "chat") return;
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOver(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        attach(e.dataTransfer.files);
      }}
      className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-line bg-surface shadow-2xl"
    >
      <div className="flex items-center gap-3 border-b border-line px-4 py-3">
        <LotsiAvatar size={40} />
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold">Lotsi</h2>
          <p className="truncate text-sm text-muted">für {subjectName} · nutzt nur Ihre Berechtigungen</p>
        </div>
        <button type="button" onClick={newConversation} className="btn-ghost p-2" title="Neues Gespräch" aria-label="Neues Gespräch">
          <SquarePen className="h-5 w-5" aria-hidden />
        </button>
        <button
          type="button"
          onClick={() => (view === "history" ? setView("chat") : showHistory())}
          className={`btn-ghost p-2 ${view === "history" ? "bg-accent-soft" : ""}`}
          title="Frühere Gespräche"
          aria-label="Frühere Gespräche"
          aria-pressed={view === "history"}
        >
          <History className="h-5 w-5" aria-hidden />
        </button>
        <button type="button" onClick={() => setOpen(false)} className="btn-ghost p-2" aria-label="Chat schließen">
          <X className="h-5 w-5" aria-hidden />
        </button>
      </div>

      {view === "history" ? (
        <div className="flex-1 overflow-y-auto px-2 py-3">
          <div className="flex items-center justify-between px-2 pb-2">
            <h3 className="font-semibold">Frühere Gespräche</h3>
            <button type="button" className="link text-sm" onClick={newConversation}>
              Neues Gespräch
            </button>
          </div>
          {history === null && <p className="px-2 text-muted">Wird geladen …</p>}
          {history?.length === 0 && <p className="px-2 text-muted">Noch keine Gespräche für {subjectName}.</p>}
          <ul className="space-y-0.5">
            {history?.map((c) => {
              const first = c.turns[0]?.user ?? "Gespräch";
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => openConversation(c.id)}
                    className={`w-full rounded-lg px-3 py-2 text-left hover:bg-neutral-soft ${c.id === conv ? "bg-accent-soft" : ""}`}
                  >
                    <span className="block truncate font-semibold">{first}</span>
                    <span className="block text-sm text-muted">
                      {fmtDateTime(c.updated_at ?? c.created_at)} · {c.turns.length} {c.turns.length === 1 ? "Frage" : "Fragen"}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ) : (
        <div className="relative flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
          {dragOver && (
            <div className="pointer-events-none absolute inset-2 z-10 grid place-items-center rounded-xl border-2 border-dashed border-accent bg-accent-soft/90 text-center">
              <p className="font-semibold text-accent-strong">Dokument oder Foto hier ablegen</p>
            </div>
          )}
          {msgs.length === 0 && (
            <div className="space-y-3">
              <p className="text-muted">
                Ich bin Lotsi und zeige Ihnen den Weg durch die Sozialversicherung: Leistungen finden, Anträge vorbereiten.
                Ich stelle keine Diagnosen, und abschicken tun immer Sie selbst.
              </p>
              <p className="text-sm text-muted">Sie können mir auch ein Dokument oder Foto geben – über die Büroklammer, per Ziehen oder Einfügen.</p>
              <div className="flex flex-wrap gap-2">
                {STARTERS.map((s) => (
                  <button key={s} type="button" className="btn-secondary py-1 text-sm" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {msgs.map((m, i) => (
            <ChatMessage key={i} msg={m} onSuggest={send} pathname={pathname} latest={i === msgs.length - 1} busy={busy} />
          ))}
          {busy && <p className="text-muted">Lotsi arbeitet …</p>}
          <div ref={endRef} />
        </div>
      )}

      {view === "chat" && (
        <form
          className="border-t border-line p-3"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          {voiceError && <p className="mb-2 text-sm text-danger">{voiceError}</p>}
          {files.length > 0 && (
            <ul className="mb-2 flex flex-wrap gap-2">
              {files.map((f) => (
                <li
                  key={f.key}
                  className={`inline-flex max-w-full items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm ${
                    f.status === "error" ? "border-danger/40 bg-danger-soft text-danger" : "border-line bg-paper"
                  }`}
                  title={f.error}
                >
                  {f.status === "uploading" ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
                  ) : (
                    <FileText className="h-4 w-4" aria-hidden />
                  )}
                  <span className="truncate">{f.filename}</span>
                  {f.status === "uploading" && <span className="text-muted">wird gelesen …</span>}
                  <button
                    type="button"
                    aria-label={`${f.filename} entfernen`}
                    onClick={() => setFiles((all) => all.filter((a) => a.key !== f.key))}
                    className="rounded-full p-0.5 hover:bg-neutral-soft"
                  >
                    <X className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </li>
              ))}
            </ul>
          )}
          {/* each distinct error once, in full (four photos with the same 403 used to show four truncated chips) */}
          {[...new Set(files.filter((f) => f.status === "error" && f.error).map((f) => f.error as string))].map((msg) => (
            <p key={msg} role="alert" className="mb-2 text-sm text-danger">
              {msg}
            </p>
          ))}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              className="btn-ghost p-2"
              title="Dokument oder Foto anhängen"
              aria-label="Dokument oder Foto anhängen"
            >
              <Paperclip className="h-5 w-5" aria-hidden />
            </button>
            <input
              ref={fileInput}
              type="file"
              accept={ACCEPT}
              multiple
              className="sr-only"
              tabIndex={-1}
              onChange={(e) => {
                attach(e.target.files);
                e.target.value = "";
              }}
            />
            {voice && (
              <button
                type="button"
                onClick={toggleVoice}
                aria-pressed={listening}
                className={`btn-ghost p-2 ${listening ? "animate-pulse bg-danger-soft text-danger" : ""}`}
                title={listening ? "Aufnahme beenden" : "Sprechen statt tippen"}
                aria-label={listening ? "Aufnahme beenden" : "Spracheingabe starten"}
              >
                {listening ? <MicOff className="h-5 w-5" aria-hidden /> : <Mic className="h-5 w-5" aria-hidden />}
              </button>
            )}
            <label htmlFor="chat-input" className="sr-only">
              Nachricht an Lotsi
            </label>
            <textarea
              id="chat-input"
              className="input resize-none"
              rows={Math.min(5, Math.max(1, input.split("\n").length))}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                // Enter sends, Shift+Enter = new line (no send while an IME composition is open)
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  e.currentTarget.form?.requestSubmit();
                }
              }}
              onPaste={(e) => {
                const images = Array.from(e.clipboardData.files).filter((f) => f.type.startsWith("image/") || f.type === "application/pdf");
                if (images.length) {
                  e.preventDefault();
                  attach(images);
                }
              }}
              placeholder={listening ? "Ich höre zu …" : files.length ? "Frage zum Dokument (optional) – Enter sendet" : "Ihre Frage …"}
              autoComplete="off"
            />
            <button className="btn-primary" disabled={!canSend}>
              Senden
            </button>
          </div>
        </form>
      )}
    </aside>
  );
}

function ChatMessage({
  msg,
  onSuggest,
  pathname,
  latest = false,
  busy = false,
}: {
  msg: Msg;
  onSuggest: (s: string) => void;
  pathname: string;
  latest?: boolean;
  busy?: boolean;
}) {
  if (msg.role === "user") {
    return (
      <div className="ml-8 space-y-1.5 rounded-xl bg-accent px-3 py-2 text-white">
        {msg.files?.length ? (
          <ul className="flex flex-wrap gap-1.5">
            {msg.files.map((f) => (
              <li key={f} className="inline-flex items-center gap-1 rounded-full bg-white/20 px-2 py-0.5 text-sm">
                <FileText className="h-3.5 w-3.5" aria-hidden />
                {f}
              </li>
            ))}
          </ul>
        ) : null}
        <p>{msg.text}</p>
      </div>
    );
  }
  if (msg.role === "error") {
    return (
      <div role="alert" className="mr-8 rounded-xl border border-danger/30 bg-danger-soft px-3 py-2 text-ink">
        {msg.text}
      </div>
    );
  }
  return (
    <div className="mr-8 space-y-2">
      {msg.trace.length > 0 && (
        <details className="rounded-lg border border-line bg-paper px-3 py-2 text-sm">
          <summary className="cursor-pointer font-semibold text-muted">
            Lotsi hat abgefragt: {msg.trace.map((t) => t.summary_de || t.tool).join(" → ")}
          </summary>
          <ul className="mt-2 space-y-1">
            {msg.trace.map((t, i) => (
              <li key={i} className={t.status >= 400 ? "text-danger" : ""}>
                <span className="font-semibold" title={t.tool}>{toolLabel(t.tool)}</span> · HTTP {t.status}
                {t.status === 403 && " (keine Berechtigung)"} — {t.summary_de}
                {t.sources?.length > 0 && <span className="block text-muted">Quellen: {t.sources.join(", ")}</span>}
              </li>
            ))}
          </ul>
        </details>
      )}
      <div
        className={`rounded-xl px-3 py-2 ${
          msg.boundary ? "border-2 border-warn bg-warn-soft" : "border border-line bg-paper"
        }`}
      >
        {msg.boundary && <p className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-warn"><TriangleAlert className="h-4 w-4" aria-hidden /> Medizinische Grenze – bitte mit Ärztin/Arzt klären</p>}
        <SimpleMarkdown text={msg.text} />
      </div>
      {latest && <SlotChoices actions={(msg.actions ?? []).filter((a) => a.kind === "choose_slot")} onChoose={onSuggest} disabled={busy} />}
      {msg.actions && msg.actions.some((a) => a.kind !== "choose_slot") && (
        <div className="flex flex-wrap gap-2">
          {msg.actions
            .filter((a) => a.kind !== "choose_slot" && !(a.kind === "open_form" && a.url === pathname))
            .map((a) => (
              <ActionButton key={a.kind + a.url} action={a} />
            ))}
        </div>
      )}
      {msg.suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {msg.suggestions.map((s) => (
            <button key={s} type="button" className="btn-secondary py-1 text-sm" onClick={() => onSuggest(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** Buttons the agent attaches (draft download, open wizard, open case). Navigation is decided by kind, not trusted URLs. */
function ActionButton({ action }: { action: ChatAction }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  async function run() {
    if (action.kind === "open_form" && action.url.startsWith("/forms/")) return router.push(action.url);
    if (action.kind === "open_case") return router.push("/fall");
    if (action.kind === "open_appointments") return router.push("/termine");
    if (action.kind === "download_ics" && action.url.startsWith("/api/appointments/")) {
      window.location.href = `/bff${action.url}`;
      return;
    }
    if (action.kind === "download_pdf" && action.url.startsWith("/api/forms/sessions/")) {
      setBusy(true);
      const res = await fetch(`/bff${action.url}`, { method: action.method || "POST" }).catch(() => null);
      setBusy(false);
      if (!res?.ok) return;
      const blob = await res.blob();
      const name = /filename="?([^"]+)"?/.exec(res.headers.get("content-disposition") ?? "")?.[1] ?? "Antrag_ENTWURF.pdf";
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = name;
      link.click();
      URL.revokeObjectURL(url);
    }
  }
  return (
    <button type="button" className="btn-primary py-1 text-sm" onClick={run} disabled={busy}>
      {busy ? "Wird erstellt …" : action.label_de}
    </button>
  );
}

/** What the user is looking at, so the Lotse works on the same form/document instead of starting a new one.
 *  Both fields are part of ChatRequest; the agent continues exactly this form session. */
function pageContext(pathname: string): { document_ids?: string[]; form_session_id?: string } {
  const form = /^\/forms\/([^/]+)/.exec(pathname);
  if (form) return { form_session_id: form[1] };
  const doc = /^\/dokumente\/([^/]+)/.exec(pathname);
  if (doc) return { document_ids: [doc[1]] };
  return {};
}
