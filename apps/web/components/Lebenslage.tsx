"use client";
// Lebenslage: the person's care situation as overlapping episodes. The person/representative sets them;
// documents only create suggestions that take effect after an explicit "Ja, übernehmen".
import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  BedDouble,
  CalendarClock,
  Check,
  ClipboardList,
  HeartPulse,
  Home,
  Hospital,
  Info,
  Plus,
  Thermometer,
  TreePine,
  X,
  type LucideIcon,
} from "lucide-react";
import { bff } from "@/lib/client";
import { fmtDate } from "@/lib/labels";
import { EPISODE_TYPE, episodeWhen, THERAPY_SUBTYPES, type Effect, type Episode, type EpisodeType, type SituationOverview } from "@/lib/situation";
import { SourceChip } from "./SourceChip";

const ICON: Record<EpisodeType, LucideIcon> = {
  hospital: Hospital,
  rehab_inpatient: HeartPulse,
  rehab_outpatient: HeartPulse,
  therapy: Activity,
  home_care: Home,
  nursing_home: BedDouble,
  sick_leave: Thermometer,
  cure: TreePine,
};
const EFFECT_ICON: Record<Effect["kind"], LucideIcon> = {
  reminder: CalendarClock,
  case_step: ClipboardList,
  fact: Info,
  prefill: ClipboardList,
  hint: Info,
};

type Props =
  | { ok: true; data: SituationOverview; subjectName: string; firstName: string }
  | { ok: false; status: number; detail: string; subjectName: string; firstName: string };

export function Lebenslage(props: Props) {
  const [adding, setAdding] = useState(false);
  const [showPast, setShowPast] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const router = useRouter();

  async function act(path: string, method: "POST" | "PATCH" | "DELETE", body?: unknown) {
    setError(null);
    const r = await bff(path, { method, body });
    if (!r.ok) {
      setError(r.status === 501 ? "Diese Funktion wird gerade fertiggestellt." : r.detail);
      return false;
    }
    start(() => router.refresh());
    return true;
  }

  const header = (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <h2 className="text-lg font-semibold">Lebenslage von {props.firstName}</h2>
      {props.ok && props.data.summary_de && <p className="text-muted">{props.data.summary_de}</p>}
    </div>
  );

  if (!props.ok) {
    return (
      <section aria-label="Lebenslage" className="card">
        {header}
        <p className="mt-1 text-sm text-muted">
          {props.status === 403
            ? `Für die Lebenslage hat ${props.subjectName} keine Berechtigung erteilt (Einstellungen → Vollmachten).`
            : props.status === 501
              ? "Die Lebenslage wird gerade fertiggestellt."
              : "Die Lebenslage ist gerade nicht verfügbar."}
        </p>
      </section>
    );
  }

  const o = props.data;
  const empty = !o.current?.length && !o.upcoming?.length && !o.past?.length && !(o.suggestions ?? []).length;
  const effects = o.effects ?? [];
  // Always visible: deadlines and hints that change what the person must do. The rest is folded away.
  const important = effects.filter((e) => e.kind === "reminder" || e.kind === "hint");
  const steps = effects.filter((e) => e.kind === "case_step");
  const prefill = effects.filter((e) => e.kind === "prefill");
  const facts = effects.filter((e) => e.kind === "fact");
  const folded = [...steps, ...prefill, ...facts];
  // A suggestion that already exists as an entry (same type and dates, e.g. from a second copy of the letter) is noise.
  const known = [...(o.current ?? []), ...(o.upcoming ?? []), ...(o.past ?? [])];
  const suggestions = (o.suggestions ?? []).filter(
    (s) => !known.some((k) => k.type === s.type && (k.start ?? null) === (s.start ?? null) && (k.end ?? null) === (s.end ?? null)),
  );

  return (
    <section id="lebenslage" aria-label="Lebenslage" className="card scroll-mt-28 space-y-3" aria-busy={pending}>
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">{header}</div>
        <button type="button" className="btn-secondary py-1 text-sm" onClick={() => setAdding(true)}>
          <Plus className="h-4 w-4" aria-hidden /> Situation hinzufügen
        </button>
      </div>

      {suggestions.map((s) => (
        <div key={s.id} role="group" aria-label="Vorschlag zur Lebenslage" className="rounded-lg border border-info/30 bg-info-soft px-3 py-2.5">
          <p className="text-sm">
            <span className="font-semibold">Vorschlag aus </span>
            <SourceChip source={s.source} />
          </p>
          <p className="mt-1">
            <span className="font-semibold">{s.title_de || EPISODE_TYPE[s.type]}</span>
            <span className="text-muted"> · {episodeWhen(s)}</span>
            {s.institution && <span className="text-muted"> · {s.institution}</span>}
          </p>
          <p className="mt-0.5 text-sm text-muted">Wird erst übernommen, wenn Sie zustimmen.</p>
          <div className="mt-2 flex gap-2">
            <button type="button" className="btn-primary py-1 text-sm" onClick={() => act(`/api/situation/suggestions/${s.id}/confirm`, "POST")}>
              <Check className="h-4 w-4" aria-hidden /> Ja, übernehmen
            </button>
            <button type="button" className="btn-ghost py-1 text-sm" onClick={() => act(`/api/situation/suggestions/${s.id}/reject`, "POST")}>
              Nein
            </button>
          </div>
        </div>
      ))}

      {empty && (
        <p className="text-sm text-muted">
          Noch nichts erfasst. Fügen Sie hinzu, wo {props.firstName} gerade ist – oder sagen Sie es Lotsi, z. B. „ab Montag auf Reha“. Daraus
          ergeben sich Fristen, passende Leistungen und Angaben für Anträge.
        </p>
      )}

      <EpisodeGroup title="Aktuell" episodes={o.current} act={act} />
      <EpisodeGroup title="Geplant" episodes={o.upcoming} act={act} />
      {o.past?.length ? (
        <div>
          <button type="button" className="text-sm font-semibold text-muted hover:text-ink" onClick={() => setShowPast((v) => !v)} aria-expanded={showPast}>
            {showPast ? "Vorbei ausblenden" : `Vorbei (${o.past.length})`}
          </button>
          {showPast && <EpisodeGroup episodes={o.past} act={act} />}
        </div>
      ) : null}

      {effects.length > 0 && (
        <div className="border-t border-line pt-3">
          <h3 className="mb-1.5 font-semibold">Was das jetzt bedeutet</h3>
          <ul className="space-y-2 text-sm">
            {important.map((e, i) => (
              <EffectRow key={i} e={e} />
            ))}
          </ul>
          {folded.length > 0 && (
            <details className="mt-2 text-sm">
              <summary className="cursor-pointer text-muted hover:text-ink">
                Außerdem:{" "}
                {[
                  steps.length && `${steps.length} ${steps.length === 1 ? "neuer Schritt" : "neue Schritte"} in Mein Fall`,
                  prefill.length && `${prefill.length} ${prefill.length === 1 ? "Angabe" : "Angaben"} für Anträge`,
                  facts.length && `${facts.length} ${facts.length === 1 ? "Angabe" : "Angaben"} für die Leistungsprüfung`,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </summary>
              <ul className="mt-2 space-y-1.5">
                {folded.map((e, i) => (
                  <EffectRow key={i} e={e} compact />
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {error && !adding && (
        <p role="alert" className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}
      {adding && (
        <AddEpisode
          firstName={props.firstName}
          error={error}
          onClose={() => {
            setAdding(false);
            setError(null);
          }}
          onSave={(body) => act("/api/situation/episodes", "POST", body)}
        />
      )}
    </section>
  );
}

function EffectRow({ e, compact = false }: { e: Effect; compact?: boolean }) {
  const Icon = EFFECT_ICON[e.kind] ?? Info;
  return (
    <li className="flex gap-2">
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${e.kind === "reminder" ? "text-warn" : "text-muted"}`} aria-hidden />
      <span className="min-w-0">
        <span className="font-semibold">{e.title_de}</span>
        {e.due_date && <span className="ml-1.5 rounded-full bg-warn-soft px-1.5 font-semibold text-warn">bis {fmtDate(e.due_date)}</span>}
        {e.detail_de && !compact && <span className="block text-muted">{e.detail_de}</span>}
        {e.source && (
          <span className="ml-1.5">
            <SourceChip source={e.source} />
          </span>
        )}
      </span>
    </li>
  );
}

function EpisodeGroup({
  title,
  episodes,
  act,
}: {
  title?: string;
  episodes?: Episode[];
  act: (path: string, method: "POST" | "PATCH" | "DELETE", body?: unknown) => Promise<boolean>;
}) {
  if (!episodes?.length) return null;
  return (
    <div>
      {title && <h3 className="mb-1 text-sm font-semibold text-muted">{title}</h3>}
      <ul className="divide-y divide-line rounded-lg border border-line">
        {episodes.map((e) => {
          const Icon = ICON[e.type] ?? Info;
          const ended = e.status === "ended";
          return (
            <li key={e.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2">
              <Icon className={`h-5 w-5 shrink-0 ${ended ? "text-muted" : "text-accent"}`} aria-hidden />
              <span className="min-w-0 flex-1">
                <span className="font-semibold">{e.title_de || EPISODE_TYPE[e.type]}</span>
                {e.subtype && !(e.title_de ?? "").toLowerCase().includes(e.subtype.toLowerCase()) && <span className="text-muted"> · {e.subtype}</span>}
                <span className="block text-sm text-muted">
                  {episodeWhen(e)}
                  {e.institution && ` · ${e.institution}`}
                </span>
              </span>
              <SourceChip source={e.source} />
              {!ended && (
                <span className="flex gap-1 text-sm">
                  {e.status === "active" && (
                    <button
                      type="button"
                      className="btn-ghost px-2 py-0.5 text-sm"
                      onClick={() => act(`/api/situation/episodes/${e.id}`, "PATCH", { status: "ended", end: new Date().toISOString().slice(0, 10) })}
                    >
                      Beenden
                    </button>
                  )}
                  <button
                    type="button"
                    aria-label={`${e.title_de || EPISODE_TYPE[e.type]} entfernen`}
                    title="Versehentlich eingetragen? Entfernen"
                    className="btn-ghost px-1.5 py-0.5"
                    onClick={() => act(`/api/situation/episodes/${e.id}`, "DELETE")}
                  >
                    <X className="h-4 w-4" aria-hidden />
                  </button>
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function AddEpisode({
  firstName,
  error,
  onClose,
  onSave,
}: {
  firstName: string;
  error: string | null;
  onClose: () => void;
  onSave: (body: unknown) => Promise<boolean>;
}) {
  const [type, setType] = useState<EpisodeType>("rehab_inpatient");
  const [busy, setBusy] = useState(false);
  const form = useRef<HTMLFormElement>(null);
  useEffect(() => {
    form.current?.querySelector("select")?.focus();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);
  return (
    <div role="dialog" aria-modal="true" aria-labelledby="add-ep-h" className="fixed inset-0 z-50 grid place-items-center bg-ink/30 p-4 backdrop-blur-sm" onClick={onClose}>
      <form
        ref={form}
        onClick={(e) => e.stopPropagation()}
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const val = (k: string) => (String(f.get(k) ?? "").trim() || null);
          setBusy(true);
          const ok = await onSave({
            type,
            subtype: type === "therapy" ? val("subtype") : null,
            start: val("start"),
            end: val("end"),
            end_estimate_de: val("end") ? null : val("end_estimate_de"),
            institution: val("institution"),
            note_de: val("note_de"),
          });
          setBusy(false);
          if (ok) onClose();
        }}
        className="w-full max-w-lg space-y-3 rounded-xl border border-line bg-surface p-5 shadow-2xl"
      >
        <h2 id="add-ep-h" className="text-lg font-semibold">
          Wo ist {firstName} gerade – oder demnächst?
        </h2>
        <label className="flex flex-col gap-1">
          <span className="font-semibold">Art</span>
          <select className="input" value={type} onChange={(e) => setType(e.target.value as EpisodeType)}>
            {(Object.keys(EPISODE_TYPE) as EpisodeType[]).map((t) => (
              <option key={t} value={t}>
                {EPISODE_TYPE[t]}
              </option>
            ))}
          </select>
        </label>
        {type === "therapy" && (
          <label className="flex flex-col gap-1">
            <span className="font-semibold">Welche Therapie?</span>
            <select name="subtype" className="input">
              {THERAPY_SUBTYPES.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
        )}
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1">
            <span className="font-semibold">Beginn</span>
            <input name="start" type="date" className="input" />
          </label>
          <label className="flex flex-col gap-1">
            <span className="font-semibold">Ende</span>
            <input name="end" type="date" className="input" />
          </label>
        </div>
        <label className="flex flex-col gap-1">
          <span className="font-semibold">
            Ende ungefähr <span className="font-normal text-muted">(wenn kein Datum bekannt)</span>
          </span>
          <input name="end_estimate_de" className="input" placeholder="z. B. Mitte November, ca. 3 Wochen" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-semibold">
            Einrichtung <span className="font-normal text-muted">(optional)</span>
          </span>
          <input name="institution" className="input" placeholder="z. B. Reha-Zentrum, Krankenhaus" />
        </label>
        {error && (
          <p role="alert" className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn-ghost" onClick={onClose}>
            Abbrechen
          </button>
          <button className="btn-primary" disabled={busy}>
            {busy ? "Wird gespeichert …" : "Hinzufügen"}
          </button>
        </div>
      </form>
    </div>
  );
}
