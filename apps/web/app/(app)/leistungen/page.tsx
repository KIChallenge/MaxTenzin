import { Check, ChevronRight, FilePen, Paperclip, X } from "lucide-react";
import { startForm } from "@/app/actions";
import { ApiError } from "@/components/ApiError";
import { Badge } from "@/components/Badge";
import { PageTitle } from "@/components/PageTitle";
import { SourceChip, SourceList } from "@/components/SourceChip";
import { api, isPlain } from "@/lib/api";
import { factLabel } from "@/lib/facts";
import { ELIGIBILITY, fmtAmount, fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { CriterionResult, DocumentSummary, EligibilityResult, EligibilityStatus, FormDefinition, SourceRef } from "@/lib/types";

type Amount = { label_de?: string; value?: number; unit?: string; source?: SourceRef };

const ORDER: Record<EligibilityStatus, number> = { likely: 0, possible: 1, needs_info: 2, not_applicable: 3 };

export default async function BenefitsPage({ searchParams }: { searchParams: Promise<{ error?: string; status?: string; doc?: string }> }) {
  const sp = await searchParams;
  const [me, plain] = await Promise.all([getMe(), isPlain()]);
  if (!me.ok) return <ApiError status={me.status} detail={me.detail} />;
  const subject = me.data.subject;
  const name = fullName(subject);

  // Newest copy per file name (the eligibility service skips documents without analysis on its own).
  const docs = await api<DocumentSummary[]>("/api/documents");
  const analysed = docs.ok ? [...docs.data].sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at)) : [];
  const seen = new Set<string>();
  const used = analysed.filter((d) => (seen.has(d.filename) ? false : (seen.add(d.filename), true)));
  if (sp.doc && !used.some((d) => d.document_id === sp.doc)) {
    const fromDoc = analysed.find((d) => d.document_id === sp.doc);
    if (fromDoc) used.splice(used.findIndex((d) => d.filename === fromDoc.filename), 1, fromDoc);
  }
  const documentIds = used.map((d) => d.document_id);
  const prefillDoc =
    (sp.doc && documentIds.includes(sp.doc) ? sp.doc : undefined) ??
    used.find((d) => d.doc_type === "discharge_letter")?.document_id ??
    used[0]?.document_id ??
    "";

  const [elig, forms] = await Promise.all([
    api<EligibilityResult[]>("/api/benefits/eligibility", {
      method: "POST",
      body: { subject_id: subject.id, facts: {}, document_ids: documentIds },
    }),
    api<FormDefinition[]>("/api/forms"),
  ]);
  const formTitle = new Map((forms.ok ? forms.data : []).map((f) => [f.form_id, f.title_de]));
  const canPrepare = me.data.scopes.includes("prepare_applications");
  const results = elig.ok ? [...elig.data].sort((a, b) => ORDER[a.status] - ORDER[b.status]) : [];
  const relevant = results.filter((r) => r.status !== "not_applicable");
  const notApplicable = results.filter((r) => r.status === "not_applicable");

  return (
    <>
      <PageTitle eyebrow="Leistungen" title={`Was für ${name} in Frage kommt`}>
        Geprüft nach festen Regeln aus Gesetz und Werte-Tabellen
        {used.length ? ` – auf Basis von: ${used.map((d) => d.filename).join(", ")}` : ""}. Die Entscheidung trifft immer
        der zuständige Träger.
      </PageTitle>
      {sp.error && (
        <div className="mb-6">
          <ApiError status={Number(sp.status ?? 0)} detail={sp.error} subjectName={name} />
        </div>
      )}
      {!elig.ok ? (
        <ApiError status={elig.status} detail={elig.detail} subjectName={name} />
      ) : results.length === 0 ? (
        <p className="card text-muted">Derzeit keine passenden Leistungen gefunden. Laden Sie z. B. einen Entlassungsbrief hoch.</p>
      ) : (
        <>
          <ul id="antraege" className="space-y-3">
            {relevant.map((r) => (
              <li key={r.benefit.id} id={r.benefit.id}>
                <BenefitCard
                  r={r}
                  plain={plain}
                  name={name}
                  canPrepare={canPrepare}
                  prefillDoc={prefillDoc}
                  formTitle={formTitle}
                />
              </li>
            ))}
          </ul>
          {notApplicable.length > 0 && (
            <section aria-labelledby="na-h" className="mt-8">
              <h2 id="na-h" className="mb-2 font-semibold text-muted">
                Trifft derzeit nicht zu
              </h2>
              <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
                {notApplicable.map((r) => (
                  <li key={r.benefit.id} className="flex flex-wrap items-center gap-3 px-5 py-3">
                    <span className="flex-1">
                      <span className="font-semibold">{r.benefit.name_de}</span>
                      <span className="ml-2 text-sm text-muted">{r.benefit.provider}</span>
                    </span>
                    <Badge tone="neutral">{ELIGIBILITY.not_applicable.label}</Badge>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </>
  );
}

function BenefitCard({
  r,
  plain,
  name,
  canPrepare,
  prefillDoc,
  formTitle,
}: {
  r: EligibilityResult;
  plain: boolean;
  name: string;
  canPrepare: boolean;
  prefillDoc: string;
  formTitle: Map<string, string>;
}) {
  const st = ELIGIBILITY[r.status];
  const b = r.benefit;
  const amounts = (r.amounts ?? []) as Amount[];
  const docCriteria = dedupe(r.criteria.filter((c) => c.source?.kind === "document"));
  const ruleCriteria = r.criteria.filter((c) => c.source?.kind !== "document");
  const firstAmount = amounts.find((a) => a.value != null);
  const missing = r.missing_fields ?? [];
  // One chip instead of N identical ones when every amount comes from the same value table.
  const sharedSource =
    amounts.length > 1 && amounts.every((a) => a.source && a.source.label === amounts[0].source?.label) ? amounts[0].source : undefined;

  return (
    <details className={`group card border-l-4 p-0 ${toneBorder(st.tone)}`}>
      <summary className="flex cursor-pointer list-none flex-wrap items-start gap-x-4 gap-y-2 p-5 [&::-webkit-details-marker]:hidden">
        <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-accent transition-transform group-open:rotate-90" aria-hidden />
        <span className="min-w-0 flex-1">
          <span className="eyebrow block">{b.provider}</span>
          <span className="block text-lg font-semibold">{b.name_de}</span>
          <span className="mt-1 block text-muted">{plain && b.plain_de ? b.plain_de : b.summary_de}</span>
          <span className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {docCriteria.length > 0 && <span className="inline-flex items-center gap-1 font-semibold text-accent-strong"><Paperclip className="h-4 w-4" aria-hidden /> im Dokument empfohlen</span>}
            {firstAmount && (
              <span>
                {amounts.length > 1 ? "ab " : ""}
                <strong>{fmtAmount(firstAmount.value!, firstAmount.unit ?? "")}</strong>
              </span>
            )}
            {missing.length > 0 && <span className="text-info">{missing.length} Angabe(n) offen</span>}
            {b.form_ids?.length > 0 && <span className="inline-flex items-center gap-1"><FilePen className="h-4 w-4" aria-hidden /> Antrag kann vorbereitet werden</span>}
          </span>
        </span>
        <Badge tone={st.tone}>{st.label}</Badge>
      </summary>

      <div className="border-t border-line p-5">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted">Rechtsgrundlage:</span>
          <SourceList sources={b.legal_basis} />
        </div>

        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <section>
            <h3 className="font-semibold">Voraussetzungen</h3>
            {docCriteria.length > 0 && (
              <div className="mt-2 rounded-lg bg-accent-soft/60 p-3">
                <p className="flex items-center gap-1.5 font-semibold"><Paperclip className="h-4 w-4" aria-hidden /> Im Dokument ausdrücklich empfohlen</p>
                <ul className="mt-1 space-y-2">
                  {docCriteria.map((c) => (
                    <li key={c.id}>
                      <span>{c.explanation_de}</span> {c.source && <SourceChip source={c.source} />}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <ul className="mt-3 space-y-3">
              {ruleCriteria.map((c) => (
                <li key={c.id} className="flex gap-3">
                  <Marker met={c.met} />
                  <div>
                    <p className="font-semibold">
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
                <h3 className="font-semibold">Beträge</h3>
                <ul className="mt-2 space-y-1">
                  {amounts.map((a, i) => (
                    <li key={i} className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <span>{a.label_de}:</span>
                      <strong className="text-lg">{a.value != null ? fmtAmount(a.value, a.unit ?? "") : "–"}</strong>
                      {!sharedSource && a.source && <SourceChip source={a.source} />}
                    </li>
                  ))}
                </ul>
                {sharedSource && (
                  <p className="mt-2 text-sm">
                    <span className="text-muted">Alle Beträge laut </span>
                    <SourceChip source={sharedSource} />
                  </p>
                )}
              </div>
            )}
            {missing.length > 0 && (
              <div className="rounded-lg bg-info-soft p-3">
                <h3 className="font-semibold text-info">Noch offen</h3>
                <ul className="list-disc pl-5">
                  {missing.map((m) => (
                    <li key={m}>{factLabel(m)}</li>
                  ))}
                </ul>
              </div>
            )}
            {r.next_steps_de?.length ? (
              <div>
                <h3 className="font-semibold">Nächste Schritte</h3>
                <ol className="mt-1 list-decimal space-y-1 pl-5">
                  {r.next_steps_de.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ol>
              </div>
            ) : null}
            {b.required_documents_de?.length ? (
              <div>
                <h3 className="font-semibold">Unterlagen</h3>
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
              <input type="hidden" name="document_id" value={prefillDoc} />
              <button className="btn-primary" disabled={!canPrepare} title={canPrepare ? undefined : "Berechtigung „Anträge vorbereiten“ fehlt"}>
                <FilePen className="h-4 w-4" aria-hidden /> Antrag vorbereiten{b.form_ids.length > 1 || formTitle.get(fid) ? `: ${formTitle.get(fid) ?? fid}` : ""}
              </button>
            </form>
          ))}
          {!canPrepare && b.form_ids?.length > 0 && <span className="text-muted">Dafür hat {name} keine Berechtigung erteilt.</span>}
          <SourceList sources={b.sources} />
          {r.rule_ids?.length ? <span className="ml-auto text-sm text-muted">Regel: {r.rule_ids.join(", ")}</span> : null}
        </div>
      </div>
    </details>
  );
}

/** Same document hint extracted several times (live extraction, repeated uploads) → show once per text + page. */
function dedupe(criteria: CriterionResult[]) {
  const seen = new Set<string>();
  return criteria.filter((c) => {
    const key = `${c.explanation_de.toLowerCase().replace(/\W+/g, " ").trim()}|${c.source?.label ?? ""}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function Marker({ met }: { met: boolean | null | undefined }) {
  return (
    <span
      aria-hidden
      className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full font-semibold ${
        met === true ? "bg-ok text-white" : met === false ? "bg-danger text-white" : "border border-info/40 bg-info-soft text-info"
      }`}
    >
      {met === true ? <Check className="h-4 w-4" /> : met === false ? <X className="h-4 w-4" /> : <span className="text-sm font-semibold">?</span>}
    </span>
  );
}

function toneBorder(t: string) {
  return { ok: "border-l-ok", warn: "border-l-warn", info: "border-l-info", neutral: "border-l-neutral", danger: "border-l-danger" }[t] ?? "";
}
