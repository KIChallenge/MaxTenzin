"use client";
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
      setMissingIds(new Set(r.data.questions.map((q) => q.id)));
      setServerProgress(r.data.progress);
    }
  }, [initial.id]);
  useEffect(() => {
    refreshMissing();
  }, [refreshMissing, session.updated_at]);

  // Until FormField exposes its condition (contract request): an empty required field the server does not
  // report as missing is currently irrelevant → hide it.
  const isHidden = (f: FormField) =>
    missingIds !== null && f.required && !f.readonly_reason_de && !isFilled(session.values[f.id]?.value) && !missingIds.has(f.id);
  const visible = (f: FormField) => !isHidden(f);
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

  return (
    <div className="grid gap-8 lg:grid-cols-[16rem_1fr]">
      <aside>
        <p className="eyebrow">{definition.provider}</p>
        <h1 className="text-2xl font-bold">{definition.title_de}</h1>
        <p className="text-muted">für {subjectName}</p>
        <div className="mt-4" aria-label="Fortschritt">
          <div className="flex justify-between text-sm font-bold">
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
                  <span className="w-6 text-center font-bold">{s === REVIEW ? "✓" : (sectionNumber(s) ?? "•")}</span>
                  <span className="flex-1">{s === REVIEW ? "Überprüfen & PDF" : sectionTitle(s)}</span>
                  {sMissing > 0 && (
                    <span className={`rounded-full px-2 text-sm font-bold ${i === step ? "bg-white text-warn" : "bg-warn-soft text-warn"}`}>{sMissing}</span>
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
        {error && (
          <p role="alert" className="mb-4 rounded-lg bg-danger-soft p-3 text-danger">
            {error}
          </p>
        )}
        {!isReview ? (
          <>
            <h2 className="mb-4 text-2xl font-bold">{current}</h2>
            <div className="space-y-4">
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
                  ← Zurück
                </button>
              )}
              <button type="button" className="btn-primary" onClick={() => setStep(step + 1)}>
                Weiter →
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
  const dirty = draft !== undefined && draft !== (fv?.value ?? null);
  const id = `f-${f.id}`;

  if (f.readonly_reason_de) {
    return (
      <div className="card bg-neutral-soft">
        <p className="font-bold">{f.label_de}</p>
        <p className="text-muted">🔒 {f.readonly_reason_de}</p>
      </div>
    );
  }

  return (
    <div key={flashAt} className={`card ${missingReq ? "border-2 border-warn" : ""} ${flashAt ? "flash" : ""}`}>
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor={id} className="text-lg font-bold">
          {f.label_de}
          {f.required && <span className="text-warn"> *</span>}
        </label>
        {missingReq && <span className="rounded-full bg-warn-soft px-2 text-sm font-bold text-warn">fehlt noch</span>}
        {flashAt && <span className="rounded-full bg-info-soft px-2 text-sm font-bold text-info">gerade aktualisiert</span>}
      </div>
      {f.ask_hint_de && <p className="text-muted">{f.ask_hint_de}</p>}
      <div className="mt-2">
        <Input field={f} id={id} value={value} onChange={props.onDraft} onFocus={props.onFocus} onBlur={props.onBlur} onCommit={props.onSave} />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
        {fv?.source && filled && (
          <>
            <span className="text-muted">vorausgefüllt aus</span>
            <SourceChip source={fv.source} />
          </>
        )}
        {filled && fv?.confirmed && !dirty && <span className="font-bold text-ok">✓ bestätigt</span>}
        <span className="ml-auto flex gap-2">
          {dirty && (
            <button type="button" className="btn-primary py-1" onClick={() => props.onSave(draft ?? null)}>
              Speichern
            </button>
          )}
          {!dirty && filled && !fv?.confirmed && (
            <button type="button" className="btn-secondary py-1" onClick={() => props.onSave(fv?.value ?? null)}>
              ✓ Stimmt so
            </button>
          )}
        </span>
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
      <fieldset className="flex flex-wrap gap-3" id={id}>
        <legend className="sr-only">{f.label_de}</legend>
        {f.options.map((o) => (
          <label key={o} className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-1">
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
  if (f.type === "textarea") return <textarea rows={4} {...common} />;
  return <input type="text" inputMode={f.type === "date" ? "numeric" : undefined} placeholder={f.type === "date" ? "TT.MM.JJJJ" : undefined} {...common} />;
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
      <h2 className="mb-4 text-2xl font-bold">Überprüfen</h2>
      {missing.length > 0 && (
        <div role="alert" className="card mb-4 border-2 border-warn bg-warn-soft">
          <p className="font-bold">Es fehlen noch {missing.length} Pflichtangabe(n):</p>
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
            <h3 className="text-lg font-bold">{sec}</h3>
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
                        <span className="text-muted">🔒 {f.readonly_reason_de}</span>
                      ) : isFilled(v) ? (
                        <span className="font-bold">{v === true ? "Ja" : v === false ? "Nein" : String(v)}</span>
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
        <p className="text-lg font-bold">Entwurf – wird nicht automatisch gesendet</p>
        <p className="mt-1">{definition.submit_info_de}</p>
        <p className="mt-1 text-muted">Bitte prüfen Sie das PDF, unterschreiben Sie es und senden Sie es selbst ab. Ärztliche Abschnitte bleiben leer.</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button type="button" className={missing.length > 0 ? "btn-secondary" : "btn-primary"} onClick={onPdf} disabled={pdfBusy}>
            {pdfBusy
              ? "PDF wird erstellt …"
              : missing.length > 0
                ? `⬇ Unvollständigen Entwurf herunterladen (${missing.length} Pflichtangaben fehlen)`
                : "⬇ Entwurf als PDF"}
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
