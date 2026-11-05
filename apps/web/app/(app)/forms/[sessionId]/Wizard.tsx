"use client";
import { Download } from "lucide-react";
import { Check, ClipboardCheck, Lock } from "lucide-react";
// Schema-driven form wizard. Polls the session every 2 s so changes made by the chat agent
// (same session, PATCH via X-Via: agent) appear live; fields being edited are never overwritten.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ApiError } from "@/components/ApiError";
import { SourceChip } from "@/components/SourceChip";
import { bff } from "@/lib/client";
import type { FieldValue, FormDefinition, FormField, FormSession, NextQuestions } from "@/lib/types";

type Val = string | boolean | null;
const REVIEW = "__review__";

function isFilled(v: Val | undefined) {
  return !(v === null || v === undefined || v === "");
}

export function Wizard({ definition, initial, subjectName }: { definition: FormDefinition; initial: FormSession; subjectName: string }) {
  const [session, setSession] = useState(initial);
  const [step, setStep] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, Val>>({});
  const [flash, setFlash] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  // Access lost while the wizard is open (e.g. the represented person revoked the scope).
  const [lost, setLost] = useState<{ status: number; detail: string } | null>(null);
  // Server truth for "missing": respects conditional fields (e.g. other citizenship only if "andere").
  const [missingIds, setMissingIds] = useState<Set<string> | null>(null);
  const [serverProgress, setServerProgress] = useState<number | null>(null);
  // Fields that just became required because of another answer (e.g. consent after "Pflegeberatung = Ja").
  const [newlyRequired, setNewlyRequired] = useState<string[]>([]);
  const prevMissing = useRef<Set<string> | null>(null);
  const editing = useRef(new Set<string>());
  const lastValues = useRef(initial.values);

  const steps = useMemo(() => [...definition.sections, REVIEW], [definition.sections]);
  const fieldsBySection = useMemo(() => {
    const m = new Map<string, FormField[]>();
    for (const f of definition.fields) m.set(f.section, [...(m.get(f.section) ?? []), f]);
    return m;
  }, [definition.fields]);
  const refreshMissing = useCallback(async () => {
    const r = await bff<NextQuestions>(`/api/forms/sessions/${initial.id}/next-questions`);
    if (r.ok) {
      const next = new Set(r.data.questions.map((q) => q.id));
      const prev = prevMissing.current;
      if (prev) {
        const added = [...next].filter((id) => !prev.has(id));
        setNewlyRequired((cur) => [...cur.filter((id) => next.has(id)), ...added.filter((id) => !cur.includes(id))]);
      }
      prevMissing.current = next;
      setMissingIds(next);
      setServerProgress(r.data.progress);
    }
  }, [initial.id]);
  useEffect(() => {
    refreshMissing();
  }, [refreshMissing, session.updated_at]);

  // Conditional fields (FormField.when), evaluated like the forms service does – on the live values incl. unsaved
  // clicks, so a dependent field appears immediately.
  const currentValue = (id: string): Val => (id in drafts ? drafts[id] : (session.values[id]?.value ?? null));
  const visible = (f: FormField) => {
    const c = f.when;
    if (!c) return true;
    if (c.proxy !== undefined && c.proxy !== null) return (session.actor_id !== session.subject_id) === c.proxy;
    if (!c.field) return true;
    const v = currentValue(c.field);
    if (c.one_of && c.one_of.length) return c.one_of.includes(v as string);
    if (c.equals === undefined || c.equals === null) return isFilled(v) && v !== false;
    return v === c.equals;
  };
  const missing = definition.fields.filter((f) => missingIds?.has(f.id));
  const progress = serverProgress ?? 0;

  const applyRemote = useCallback((next: FormSession) => {
    const changed: string[] = [];
    for (const [k, v] of Object.entries(next.values)) {
      const prev = lastValues.current[k];
      if (!editing.current.has(k) && JSON.stringify(prev) !== JSON.stringify(v)) changed.push(k);
    }
    lastValues.current = next.values;
    setSession(next);
    if (changed.length) {
      const now = Date.now();
      setFlash((f) => ({ ...f, ...Object.fromEntries(changed.map((k) => [k, now])) }));
    }
  }, []);

  // Live sync with chat (poll every 2 s while the tab is visible).
  useEffect(() => {
    const t = setInterval(async () => {
      if (document.hidden) return;
      const r = await bff<FormSession>(`/api/forms/sessions/${session.id}`);
      if (!r.ok && (r.status === 403 || r.status === 404)) setLost({ status: r.status, detail: r.detail });
      else if (r.ok) {
        setLost(null);
        if (r.data.updated_at !== session.updated_at) applyRemote(r.data);
      }
    }, 2000);
    return () => clearInterval(t);
  }, [session.id, session.updated_at, applyRemote]);

  async function save(values: Record<string, Val>) {
    setSaving(true);
    setError(null);
    const r = await bff<FormSession>(`/api/forms/sessions/${session.id}`, { method: "PATCH", body: { values, confirm: true } });
    setSaving(false);
    if (!r.ok) {
      setError(r.status === 403 ? `Dafür hat ${subjectName} keine Berechtigung erteilt. ${r.detail}` : r.detail);
      return;
    }
    lastValues.current = r.data.values;
    setSession(r.data);
    setDrafts((d) => {
      const n = { ...d };
      for (const k of Object.keys(values)) delete n[k];
      return n;
    });
  }

  async function downloadPdf() {
    setPdfBusy(true);
    setError(null);
    try {
      const res = await fetch(`/bff/api/forms/sessions/${session.id}/render`, { method: "POST" });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? `Fehler ${res.status}`);
      const blob = await res.blob();
      const cd = res.headers.get("content-disposition") ?? "";
      const name = /filename="?([^"]+)"?/.exec(cd)?.[1] ?? "Antrag_ENTWURF.pdf";
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF konnte nicht erstellt werden.");
    } finally {
      setPdfBusy(false);
    }
  }

  const current = steps[step];
  const isReview = current === REVIEW;

  if (lost) return <ApiError status={lost.status} detail={lost.detail} subjectName={subjectName} />;

  const jumpTo = (fieldId: string) => {
    const f = definition.fields.find((x) => x.id === fieldId);
    if (!f) return;
    setStep(steps.indexOf(f.section));
    setTimeout(() => {
      const el = document.getElementById(`f-${fieldId}`);
      el?.scrollIntoView({ block: "center", behavior: "smooth" });
      el?.focus();
    }, 50);
  };
  // Only point to fields outside the current step – a field that appears right under the click needs no banner.
  const newlyRequiredFields = newlyRequired
    .map((id) => definition.fields.find((f) => f.id === id))
    .filter((f): f is FormField => !!f && f.section !== current);

  return (
    <div className="grid gap-8 lg:grid-cols-[16rem_1fr]">
      <aside>
        <p className="eyebrow">{definition.provider}</p>
        <h1 className="text-xl font-semibold">{definition.title_de}</h1>
        <p className="text-muted">für {subjectName}</p>
        <div className="mt-4" aria-label="Fortschritt">
          <div className="flex justify-between text-sm font-semibold">
            <span>Pflichtangaben</span>
            <span>{Math.round(progress * 100)} %</span>
          </div>
          <div className="mt-1 h-3 rounded-full bg-neutral-soft" role="progressbar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-3 rounded-full bg-accent transition-all" style={{ width: `${progress * 100}%` }} />
          </div>
        </div>
        <ol className="mt-6 space-y-1">
          {steps.map((s, i) => {
            const sMissing = s === REVIEW ? 0 : (fieldsBySection.get(s) ?? []).filter((f) => missing.includes(f)).length;
            return (
              <li key={s}>
                <button
                  type="button"
                  onClick={() => setStep(i)}
                  aria-current={i === step ? "step" : undefined}
                  className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left ${i === step ? "bg-accent text-white" : "hover:bg-accent-soft"}`}
                >
                  <span className="w-6 text-center font-semibold">{s === REVIEW ? <ClipboardCheck className="mx-auto h-4 w-4" aria-hidden /> : (sectionNumber(s) ?? "•")}</span>
                  <span className="flex-1">{s === REVIEW ? "Überprüfen & PDF" : sectionTitle(s)}</span>
                  {sMissing > 0 && (
                    <span className={`rounded-full px-2 text-sm font-semibold ${i === step ? "bg-white text-warn" : "bg-warn-soft text-warn"}`}>{sMissing}</span>
                  )}
                </button>
              </li>
            );
          })}
        </ol>
        <p className="mt-6 text-sm text-muted">
          Änderungen über den Chat erscheinen hier automatisch.{" "}
          <span aria-live="polite">{saving ? "Speichert …" : "Gespeichert."}</span>
        </p>
      </aside>

      <section>
        {newlyRequiredFields.length > 0 && (
          <div role="status" className="mb-4 rounded-lg border-l-4 border-warn bg-warn-soft p-3">
            <p className="font-semibold">Durch Ihre Angabe ist jetzt zusätzlich nötig:</p>
            <ul className="mt-1 space-y-1">
              {newlyRequiredFields.map((f) => (
                <li key={f.id} className="flex flex-wrap items-center gap-x-3">
                  <span>
                    {f.label_de} <span className="text-muted">({sectionTitle(f.section)})</span>
                  </span>
                  <button type="button" className="link" onClick={() => jumpTo(f.id)}>
                    Zum Feld
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {error && (
          <p role="alert" className="mb-4 rounded-lg bg-danger-soft p-3 text-danger">
            {error}
          </p>
        )}
        {!isReview ? (
          <>
            <h2 className="mb-3 text-xl font-semibold">{current}</h2>
            <div className="@container divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
              {(fieldsBySection.get(current) ?? []).filter(visible).map((f) => (
                <FieldRow
                  key={f.id}
                  field={f}
                  fv={session.values[f.id]}
                  draft={drafts[f.id]}
                  flashAt={flash[f.id]}
                  isMissing={!!missingIds?.has(f.id)}
                  onDraft={(v) => setDrafts((d) => ({ ...d, [f.id]: v }))}
                  onFocus={() => editing.current.add(f.id)}
                  onBlur={() => editing.current.delete(f.id)}
                  onSave={(v) => save({ [f.id]: v })}
                />
              ))}
            </div>
            <div className="mt-6 flex gap-3">
              {step > 0 && (
                <button type="button" className="btn-secondary" onClick={() => setStep(step - 1)}>
                  Zurück
                </button>
              )}
              <button type="button" className="btn-primary" onClick={() => setStep(step + 1)}>
                Weiter
              </button>
            </div>
          </>
        ) : (
          <Review
            definition={definition}
            session={session}
            missing={missing}
            visible={visible}
            onJump={(sec) => setStep(steps.indexOf(sec))}
            onPdf={downloadPdf}
            pdfBusy={pdfBusy}
          />
        )}
      </section>
    </div>
  );
}

function FieldRow(props: {
  field: FormField;
  fv?: FieldValue;
  draft: Val | undefined;
  flashAt?: number;
  isMissing: boolean;
  onDraft: (v: Val) => void;
  onFocus: () => void;
  onBlur: () => void;
  onSave: (v: Val) => void;
}) {
  const { field: f, fv, draft, flashAt } = props;
  const value = draft !== undefined ? draft : (fv?.value ?? null);
  const filled = isFilled(fv?.value);
  const missingReq = props.isMissing;
  // Choice/checkbox save on click – they never need a "Speichern" button (it would only flash while saving).
  const instant = f.type === "choice" || f.type === "checkbox";
  const dirty = !instant && draft !== undefined && draft !== (fv?.value ?? null);
  const id = `f-${f.id}`;

  const rowBase = "grid gap-x-6 gap-y-2 px-5 py-4 @2xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]";
  const hint = f.ask_hint_de && <p className="mt-0.5 text-sm text-muted">{f.ask_hint_de}</p>;

  if (f.readonly_reason_de) {
    return (
      <div className={`${rowBase} bg-neutral-soft/60`}>
        <p className="font-semibold">{f.label_de}</p>
        <p className="flex items-start gap-1.5 text-sm text-muted"><Lock className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> {f.readonly_reason_de}</p>
      </div>
    );
  }

  return (
    <div
      key={flashAt}
      className={`${rowBase} border-l-4 ${missingReq ? "border-l-warn bg-warn-soft/30" : "border-l-transparent"} ${flashAt ? "flash" : ""}`}
    >
      <div>
        <label htmlFor={id} className="font-semibold">
          {f.label_de}
          {f.required && (
            <span className="text-warn" aria-label="Pflichtangabe">
              {" "}
              *
            </span>
          )}
        </label>
        {hint}
      </div>
      <div className="min-w-0">
        <Input field={f} id={id} value={value} onChange={props.onDraft} onFocus={props.onFocus} onBlur={props.onBlur} onCommit={props.onSave} />
        {(missingReq || flashAt || filled || dirty) && (
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
          {missingReq && <span className="font-semibold text-warn">Fehlt noch</span>}
          {flashAt && <span className="font-semibold text-info">Gerade über den Chat aktualisiert</span>}
          {fv?.source && filled && <SourceChip source={fv.source} />}
          {filled && fv?.confirmed && !dirty && <span className="inline-flex items-center gap-1 font-semibold text-ok"><Check className="h-4 w-4" aria-hidden /> Bestätigt</span>}
          <span className="ml-auto flex gap-2">
            {dirty && (
              <button type="button" className="btn-primary px-3 py-1 text-sm" onClick={() => props.onSave(draft ?? null)}>
                Speichern
              </button>
            )}
            {!dirty && filled && !fv?.confirmed && (
              <button type="button" className="btn-secondary px-3 py-1 text-sm" onClick={() => props.onSave(fv?.value ?? null)}>
                Stimmt so
              </button>
            )}
          </span>
        </div>
        )}
      </div>
    </div>
  );
}

function Input({
  field: f,
  id,
  value,
  onChange,
  onFocus,
  onBlur,
  onCommit,
}: {
  field: FormField;
  id: string;
  value: Val;
  onChange: (v: Val) => void;
  onFocus: () => void;
  onBlur: () => void;
  onCommit: (v: Val) => void;
}) {
  if (f.type === "checkbox") {
    return (
      <label className="inline-flex items-center gap-2">
        <input
          id={id}
          type="checkbox"
          className="h-5 w-5 accent-accent"
          checked={value === true}
          onChange={(e) => {
            onChange(e.target.checked);
            onCommit(e.target.checked);
          }}
        />
        Ja
      </label>
    );
  }
  if (f.type === "choice") {
    return (
      <fieldset className="flex flex-wrap gap-2" id={id}>
        <legend className="sr-only">{f.label_de}</legend>
        {f.options.map((o) => (
          <label
            key={o}
            className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-line px-3 py-1.5 has-[:checked]:border-accent has-[:checked]:bg-accent-soft has-[:checked]:font-semibold"
          >
            <input type="radio" name={id} className="accent-accent" checked={value === o} onChange={() => {
                onChange(o);
                onCommit(o);
              }} />
            {o}
          </label>
        ))}
      </fieldset>
    );
  }
  const common = {
    id,
    className: "input",
    value: typeof value === "string" ? value : "",
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(e.target.value),
    onFocus,
    onBlur,
  };
  if (f.type === "textarea") return <textarea rows={3} {...common} />;
  return <input type="text" inputMode={f.type === "date" ? "numeric" : undefined} placeholder={f.type === "date" ? "TT.MM.JJJJ" : undefined} {...common} className={`input ${f.type === "date" ? "max-w-48" : ""}`} />;
}

function Review({
  definition,
  session,
  missing,
  visible,
  onJump,
  onPdf,
  pdfBusy,
}: {
  definition: FormDefinition;
  session: FormSession;
  missing: FormField[];
  visible: (f: FormField) => boolean;
  onJump: (section: string) => void;
  onPdf: () => void;
  pdfBusy: boolean;
}) {
  return (
    <>
      <h2 className="mb-4 text-xl font-semibold">Überprüfen</h2>
      {missing.length > 0 && (
        <div role="alert" className="card mb-4 border-2 border-warn bg-warn-soft">
          <p className="font-semibold">Es fehlen noch {missing.length} Pflichtangabe(n):</p>
          <ul className="mt-1 list-disc pl-5">
            {missing.map((f) => (
              <li key={f.id}>
                <button type="button" className="link" onClick={() => onJump(f.section)}>
                  {f.label_de}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {definition.sections.map((sec) => (
        <section key={sec} className="card mb-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">{sec}</h3>
            <button type="button" className="btn-ghost py-1" onClick={() => onJump(sec)}>
              Bearbeiten
            </button>
          </div>
          <dl className="mt-2 divide-y divide-line">
            {definition.fields
              .filter((f) => f.section === sec && visible(f))
              .map((f) => {
                const fv = session.values[f.id];
                const v = fv?.value;
                return (
                  <div key={f.id} className="grid gap-1 py-2 sm:grid-cols-[1fr_1.5fr]">
                    <dt className="text-muted">{f.label_de}</dt>
                    <dd>
                      {f.readonly_reason_de ? (
                        <span className="inline-flex items-start gap-1.5 text-muted"><Lock className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> {f.readonly_reason_de}</span>
                      ) : isFilled(v) ? (
                        <span className="font-semibold">{v === true ? "Ja" : v === false ? "Nein" : String(v)}</span>
                      ) : (
                        <span className="text-muted">– leer –</span>
                      )}{" "}
                      {fv?.source && isFilled(v) && <SourceChip source={fv.source} />}
                    </dd>
                  </div>
                );
              })}
          </dl>
        </section>
      ))}
      <div className="card border-accent/40 bg-accent-soft">
        <p className="font-semibold">Entwurf – wird nicht automatisch gesendet</p>
        <p className="mt-1">{definition.submit_info_de}</p>
        <p className="mt-1 text-muted">Bitte prüfen Sie das PDF, unterschreiben Sie es und senden Sie es selbst ab. Ärztliche Abschnitte bleiben leer.</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button type="button" className={missing.length > 0 ? "btn-secondary" : "btn-primary"} onClick={onPdf} disabled={pdfBusy}>
            <Download className="h-4 w-4" aria-hidden />
            {pdfBusy
              ? "PDF wird erstellt …"
              : missing.length > 0
                ? `Unvollständigen Entwurf herunterladen (${missing.length} Pflichtangaben fehlen)`
                : "Entwurf als PDF herunterladen"}
          </button>
          <Link href="/fall" className="btn-secondary">
            Weiter zu „Mein Fall“
          </Link>
        </div>
      </div>
    </>
  );
}

/** Official section numbers ("1 Persönliche Angaben") are shown as the step number, not doubled. */
function sectionNumber(section: string) {
  return /^(\d+)\s/.exec(section)?.[1];
}
function sectionTitle(section: string) {
  return section.replace(/^\d+\s+/, "");
}
