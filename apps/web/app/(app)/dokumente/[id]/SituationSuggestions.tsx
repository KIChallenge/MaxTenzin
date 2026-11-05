"use client";
// Suggestions for the Lebenslage derived from this document. Nothing takes effect until the person says "Ja, übernehmen".
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Check, Sparkles } from "lucide-react";
import { SourceChip } from "@/components/SourceChip";
import { bff } from "@/lib/client";
import { EPISODE_TYPE, episodeWhen, type Episode } from "@/lib/situation";

export function SituationSuggestions({ documentId, initial, firstName }: { documentId: string; initial: Episode[]; firstName: string }) {
  const [items, setItems] = useState<Episode[]>(initial);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [, start] = useTransition();
  const router = useRouter();

  async function suggest() {
    setBusy(true);
    setMsg(null);
    const r = await bff<Episode[]>(`/api/situation/suggestions/from-document/${documentId}`, { method: "POST" });
    setBusy(false);
    if (!r.ok) return setMsg(r.status === 403 ? "Für die Lebenslage fehlt die Berechtigung." : r.status === 501 ? "Diese Funktion wird gerade fertiggestellt." : r.detail);
    setItems(r.data);
    if (!r.data.length) setMsg("In diesem Dokument stehen keine Angaben zu Aufenthalten oder Therapien.");
  }
  async function decide(e: Episode, yes: boolean) {
    const r = await bff(`/api/situation/suggestions/${e.id}/${yes ? "confirm" : "reject"}`, { method: "POST" });
    if (!r.ok) return setMsg(r.detail);
    setItems((all) => all.filter((x) => x.id !== e.id));
    setMsg(yes ? "Übernommen – siehe Lebenslage auf der Übersicht." : "Nicht übernommen.");
    start(() => router.refresh());
  }

  return (
    <section aria-labelledby="sit-h" className="card mt-6">
      <h2 id="sit-h" className="flex items-center gap-2 font-semibold">
        <Sparkles className="h-4 w-4 text-accent" aria-hidden /> Lebenslage von {firstName}
      </h2>
      {items.length === 0 ? (
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <p className="flex-1 text-sm text-muted">Aufenthalte und Therapien aus diesem Dokument als Vorschlag übernehmen – Sie entscheiden bei jedem Eintrag.</p>
          <button type="button" className="btn-secondary py-1 text-sm" onClick={suggest} disabled={busy}>
            {busy ? "Wird gelesen …" : "Vorschläge erstellen"}
          </button>
        </div>
      ) : (
        <ul className="mt-2 space-y-2">
          {items.map((e) => (
            <li key={e.id} className="rounded-lg border border-info/30 bg-info-soft px-3 py-2">
              <p>
                <span className="font-semibold">{e.title_de || EPISODE_TYPE[e.type]}</span>
                <span className="text-muted"> · {episodeWhen(e)}</span>
                {e.institution && <span className="text-muted"> · {e.institution}</span>} <SourceChip source={e.source} />
              </p>
              <div className="mt-1.5 flex gap-2">
                <button type="button" className="btn-primary py-1 text-sm" onClick={() => decide(e, true)}>
                  <Check className="h-4 w-4" aria-hidden /> Ja, übernehmen
                </button>
                <button type="button" className="btn-ghost py-1 text-sm" onClick={() => decide(e, false)}>
                  Nein
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {msg && <p className="mt-2 text-sm text-muted">{msg}</p>}
    </section>
  );
}
