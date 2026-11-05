import { startForm } from "@/app/actions";
import { ApiError } from "@/components/ApiError";
import { Badge } from "@/components/Badge";
import { PageTitle } from "@/components/PageTitle";
import { SourceChip, SourceList } from "@/components/SourceChip";
import { api, isPlain } from "@/lib/api";
import { ELIGIBILITY, fmtAmount, fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { DocumentSummary, EligibilityResult, FormDefinition, SourceRef } from "@/lib/types";

type Amount = { label_de?: string; value?: number; unit?: string; source?: SourceRef };

export default async function BenefitsPage({ searchParams }: { searchParams: Promise<{ error?: string; status?: string }> }) {
  const sp = await searchParams;
  const [me, plain] = await Promise.all([getMe(), isPlain()]);
  if (!me.ok) return <ApiError status={me.status} detail={me.detail} />;
  const subject = me.data.subject;
  const name = fullName(subject);

  const docs = await api<DocumentSummary[]>("/api/documents");
  const documentIds = docs.ok ? docs.data.map((d) => d.document_id) : [];
  const [elig, forms] = await Promise.all([
    api<EligibilityResult[]>("/api/benefits/eligibility", {
      method: "POST",
      body: { subject_id: subject.id, facts: {}, document_ids: documentIds },
    }),
    api<FormDefinition[]>("/api/forms"),
  ]);
  const formTitle = new Map((forms.ok ? forms.data : []).map((f) => [f.form_id, f.title_de]));
  const canPrepare = me.data.scopes.includes("prepare_applications");

  return (
    <>
      <PageTitle eyebrow="Leistungen" title={`Was für ${name} in Frage kommt`}>
        Geprüft nach festen Regeln aus Gesetz und Werte-Tabellen{documentIds.length ? `, auf Basis von ${documentIds.length} Dokument(en)` : ""}.
        Die Entscheidung trifft immer der zuständige Träger.
      </PageTitle>
      {sp.error && <div className="mb-6"><ApiError status={Number(sp.status ?? 0)} detail={sp.error} subjectName={name} /></div>}
      {!elig.ok ? (
        <ApiError status={elig.status} detail={elig.detail} subjectName={name} />
      ) : elig.data.length === 0 ? (
        <p className="card text-muted">Derzeit keine passenden Leistungen gefunden. Laden Sie z. B. einen Entlassungsbrief hoch.</p>
      ) : (
        <ul id="antraege" className="space-y-6">
          {elig.data.map((r) => {
            const st = ELIGIBILITY[r.status];
            const b = r.benefit;
            const amounts = (r.amounts ?? []) as Amount[];
            return (
              <li key={b.id} id={b.id} className={`card border-l-8 ${toneBorder(st.tone)}`}>
                <div className="flex flex-wrap items-start gap-3">
                  <div className="flex-1">
                    <p className="eyebrow">{b.provider}</p>
                    <h2 className="text-2xl font-bold">{b.name_de}</h2>
                    <p className="mt-1 text-lg">{plain && b.plain_de ? b.plain_de : b.summary_de}</p>
                  </div>
                  <Badge tone={st.tone}>{st.label}</Badge>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-muted">Rechtsgrundlage:</span>
                  <SourceList sources={b.legal_basis} />
                </div>

                <div className="mt-4 grid gap-6 md:grid-cols-2">
                  <section>
                    <h3 className="font-bold">Voraussetzungen</h3>
                    <ul className="mt-2 space-y-3">
                      {r.criteria.map((c) => (
                        <li key={c.id} className="flex gap-3">
                          <span
                            aria-hidden
                            className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full font-bold ${
                              c.met === true ? "bg-ok text-white" : c.met === false ? "bg-danger text-white" : "bg-info-soft text-info border border-info/40"
                            }`}
                          >
                            {c.met === true ? "✓" : c.met === false ? "✕" : "?"}
                          </span>
                          <div>
                            <p className="font-bold">
                              {c.label_de}
                              <span className="sr-only">{c.met === true ? " – erfüllt" : c.met === false ? " – nicht erfüllt" : " – noch offen"}</span>
                            </p>
                            <p className="text-muted">{c.explanation_de}</p>
                            {c.source && <SourceChip source={c.source} />}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </section>
                  <section className="space-y-4">
                    {amounts.length > 0 && (
                      <div>
                        <h3 className="font-bold">Beträge</h3>
                        <ul className="mt-2 space-y-2">
                          {amounts.map((a, i) => (
                            <li key={i} className="flex flex-wrap items-center gap-2">
                              <span>{a.label_de}:</span>
                              <strong className="text-lg">{a.value != null ? fmtAmount(a.value, a.unit ?? "") : "–"}</strong>
                              {a.source && <SourceChip source={a.source} />}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {r.missing_fields?.length ? (
                      <div className="rounded-lg bg-info-soft p-3">
                        <h3 className="font-bold text-info">Noch offen</h3>
                        <ul className="list-disc pl-5">
                          {r.missing_fields.map((m) => (
                            <li key={m}>{MISSING[m] ?? m}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    {r.next_steps_de?.length ? (
                      <div>
                        <h3 className="font-bold">Nächste Schritte</h3>
                        <ol className="mt-1 list-decimal space-y-1 pl-5">
                          {r.next_steps_de.map((s) => (
                            <li key={s}>{s}</li>
                          ))}
                        </ol>
                      </div>
                    ) : null}
                    {b.required_documents_de?.length ? (
                      <div>
                        <h3 className="font-bold">Unterlagen</h3>
                        <ul className="list-disc pl-5">
                          {b.required_documents_de.map((d) => (
                            <li key={d}>{d}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </section>
                </div>

                <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-line pt-4">
                  {b.form_ids?.map((fid) => (
                    <form key={fid} action={startForm}>
                      <input type="hidden" name="form_id" value={fid} />
                      <input type="hidden" name="benefit_id" value={b.id} />
                      <button className="btn-primary" disabled={!canPrepare} title={canPrepare ? undefined : "Berechtigung „Anträge vorbereiten“ fehlt"}>
                        📝 Antrag vorbereiten{b.form_ids.length > 1 ? `: ${formTitle.get(fid) ?? fid}` : ""}
                      </button>
                    </form>
                  ))}
                  {!canPrepare && <span className="text-muted">Dafür hat {name} keine Berechtigung erteilt.</span>}
                  <SourceList sources={b.sources} />
                  {r.rule_ids?.length ? <span className="ml-auto text-sm text-muted">Regel: {r.rule_ids.join(", ")}</span> : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}

const MISSING: Record<string, string> = {
  care_hours_estimate: "Geschätzter Pflegebedarf in Stunden pro Monat (stellt die PVA beim Hausbesuch fest)",
};

function toneBorder(t: string) {
  return { ok: "border-l-ok", warn: "border-l-warn", info: "border-l-info", neutral: "border-l-neutral", danger: "border-l-danger" }[t] ?? "";
}
