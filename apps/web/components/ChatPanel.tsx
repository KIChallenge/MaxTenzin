"use client";
import { TriangleAlert, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { bff } from "@/lib/client";
import type { ChatAction, ChatResponse, ToolTrace } from "@/lib/types";
import { LotsiAvatar } from "./Lotsi";
import { SimpleMarkdown } from "./SimpleMarkdown";

type Msg =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; trace: ToolTrace[]; boundary: boolean; suggestions: string[]; actions?: ChatAction[] }
  | { role: "error"; text: string };

const STARTERS = ["Was steht im Entlassungsbrief?", "Welche Leistungen kommen in Frage?", "Hilf mir beim Pflegegeld-Antrag"];

export function ChatPanel({ subjectId, subjectName, plain }: { subjectId: string; subjectName: string; plain: boolean }) {
  const storeKey = `lotse-chat-${subjectId}`;
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [conv, setConv] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const pathname = usePathname();

  // Restore conversation per represented person (survives reloads within the tab).
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(storeKey);
      const saved = raw ? JSON.parse(raw) : null;
      setMsgs(saved?.msgs ?? []);
      setConv(saved?.conv ?? null);
      setOpen(sessionStorage.getItem("lotse-chat-open") === "1");
    } catch {}
  }, [storeKey]);
  useEffect(() => {
    try {
      sessionStorage.setItem(storeKey, JSON.stringify({ msgs, conv }));
    } catch {}
    endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs, conv, storeKey]);
  useEffect(() => {
    const onOpen = (e: Event) => {
      setOpen(true);
      const q = (e as CustomEvent<string | undefined>).detail;
      if (q) setInput(q);
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

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text: message }]);
    setBusy(true);
    const r = await bff<ChatResponse>("/api/agent/chat", {
      body: { message, conversation_id: conv, language: "de", plain_language: plain, ...pageContext(pathname) },
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

  return (
    <aside
      aria-label="Chat mit Lotsi"
      className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-line bg-surface shadow-2xl"
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div className="flex items-center gap-3">
          <LotsiAvatar size={44} />
          <div>
          <h2 className="font-semibold">Lotsi</h2>
          <p className="text-sm text-muted">für {subjectName} · nutzt nur Ihre Berechtigungen</p>
          </div>
        </div>
        <button type="button" onClick={() => setOpen(false)} className="btn-ghost" aria-label="Chat schließen">
          <X className="h-5 w-5" aria-hidden />
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
        {msgs.length === 0 && (
          <div className="space-y-3">
            <p className="text-muted">
              Ich bin Lotsi und zeige Ihnen den Weg durch die Sozialversicherung: Leistungen finden, Anträge vorbereiten.
              Ich stelle keine Diagnosen, und abschicken tun immer Sie selbst.
            </p>
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
          <ChatMessage key={i} msg={m} onSuggest={send} pathname={pathname} />
        ))}
        {busy && <p className="text-muted">Lotsi arbeitet …</p>}
        <div ref={endRef} />
      </div>

      <form
        className="flex gap-2 border-t border-line p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <label htmlFor="chat-input" className="sr-only">
          Nachricht an Lotsi
        </label>
        <input
          id="chat-input"
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ihre Frage …"
          autoComplete="off"
        />
        <button className="btn-primary" disabled={busy || !input.trim()}>
          Senden
        </button>
      </form>
    </aside>
  );
}

function ChatMessage({ msg, onSuggest, pathname }: { msg: Msg; onSuggest: (s: string) => void; pathname: string }) {
  if (msg.role === "user") {
    return <div className="ml-8 rounded-xl bg-accent px-3 py-2 text-white">{msg.text}</div>;
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
                <code className="font-semibold">{t.tool}</code> · HTTP {t.status}
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
      {msg.actions && msg.actions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {msg.actions
            .filter((a) => !(a.kind === "open_form" && a.url === pathname))
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
