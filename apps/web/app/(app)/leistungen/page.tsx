import { Check, ChevronRight, FilePen, Paperclip, X } from "lucide-react";
import Link from "next/link";
import { OpenFromHash } from "@/components/OpenFromHash";
import { startForm } from "@/app/actions";
import { FactQuestion } from "@/components/FactQuestion";
import { findEvidence } from "@/lib/facts";
import type { components } from "@/lib/api-types";
import { ApiError } from "@/components/ApiError";
import { Badge } from "@/components/Badge";
import { PageTitle } from "@/components/PageTitle";
import { SourceChip, SourceList } from "@/components/SourceChip";
import { api, getFacts, isPlain } from "@/lib/api";
import { FactAnswers } from "@/components/FactAnswers";
import { ELIGIBILITY, fmtAmount, fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { CriterionResult, DocumentSummary, EligibilityResult, EligibilityStatus, FormDefinition, SourceRef } from "@/lib/types";

type Amount = { label_de?: string; value?: number; unit?: string; source?: SourceRef };

const ORDER: Record<EligibilityStatus, number> = { likely: 0, possible: 1, needs_info: 2, not_applicable: 3 };

export default async function BenefitsPage({ searchParams }: { searchParams: Promise<{ error?: string; status?: string; doc?: string }> }) {
  const sp = await searchParams;
  const [me, plain, known] = await Promise.all([getMe(), isPlain(), getFacts()]);
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
  const docMap = Object.fromEntries(used.map((d) => [d.filename, d.document_id]));
  const prefillDoc =
    (sp.doc && documentIds.includes(sp.doc) ? sp.doc : undefined) ??
    used.find((d) => d.doc_type === "discharge_letter")?.document_id ??
    used[0]?.document_id ??
    "";

  // Text of the document used for the questions – to show matching passages verbatim next to them.
  const transcript = prefillDoc ? await api<components["schemas"]["DocumentTranscript"]>(`/api/documents/${prefillDoc}/transcript`) : null;
  const transcriptPages = transcript?.ok ? transcript.data.pages.map((p) => ({ page: p.page, text: p.text })) : [];
  const prefillName = used.find((d) => d.document_id === prefillDoc)?.filename;
  const [elig, forms, ...analyses] = await Promise.all([
    api<EligibilityResult[]>("/api/benefits/eligibility", {
      method: "POST",
      body: { subject_id: subject.id, facts: {}, document_ids: documentIds }, // stored facts are merged by the service
    }),
    api<FormDefinition[]>("/api/forms"),
    ...documentIds.map((id) => api<components["schemas"]["DocumentAnalysis"]>(`/api/documents/${id}/analysis`)),
  ]);
  // Benefits the document's explicit recommendations point to (e.g. "Kontaktaufnahme … Beratungsstellen" → Pflegeberatung)
  const recommendedIds = new Set(
    analyses.flatMap((a) => (a.ok ? (a.data as components["schemas"]["DocumentAnalysis"]).recommendations.flatMap((r) => r.related_benefit_ids ?? []) : [])),
  );
  const formTitle = new Map((forms.ok ? forms.data : []).map((f) => [f.form_id, f.title_de]));
  const canPrepare = me.data.scopes.includes("prepare_applications");
  const results = elig.ok ? [...elig.data].sort((a, b) => ORDER[a.status] - ORDER[b.status]) : [];
  const relevant = results.filter((r) => r.status !== "not_applicable");
  const notApplicable = results.filter((r) => r.status === "not_applicable");
  // With a document: what the letter itself points to comes first; the rest of the catalog is folded away.
  const fromDoc = relevant.filter((r) => recommendedIds.has(r.benefit.id) || r.criteria.some((c) => c.source?.kind === "document"));
  const others = fromDoc.length ? relevant.filter((r) => !fromDoc.includes(r)) : relevant;

  return (
    <>
      <OpenFromHash />
      <PageTitle eyebrow="Leistungen" title={`Was für ${name} in Frage kommt`}>
        Geprüft nach festen Regeln aus Gesetz und Werte-Tabellen
        {used.length ? ` – auf Basis von: ${used.map((d) => d.filename).join(", ")}` : ""}. Die Entscheidung trifft immer
        der zuständige Träger.
      </PageTitle>
      <FactAnswers facts={known.facts} sources={known.sources} name={subject.first_name} />
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
          {fromDoc.length > 0 && (
            <h2 className="mb-2 font-semibold">
              Laut {used.some((d) => d.doc_type === "discharge_letter") ? "Entlassungsbrief" : "Dokument"} empfohlen ({fromDoc.length})
            </h2>
          )}
          {(() => {
            const cards = (list: EligibilityResult[]) => (
              <ul className="space-y-2">
                {list.map((r) => (
                  <li key={r.benefit.id} id={r.benefit.id} className="scroll-mt-32">
                    <BenefitCard
                      r={r}
                      plain={plain}
                      name={name}
                      canPrepare={canPrepare}
                      prefillDoc={prefillDoc}
                      formTitle={formTitle}
                      docMap={docMap}
                      transcriptPages={transcriptPages}
                      prefillName={prefillName}
                    />
                  </li>
                ))}
              </ul>
            );
            return (
              <div id="antraege">
                {fromDoc.length > 0 ? cards(fromDoc) : cards(others)}
                {fromDoc.length > 0 && others.length > 0 && (
                  <details className="group mt-8">
                    <summary className="mb-2 flex cursor-pointer list-none items-center gap-2 font-semibold text-muted hover:text-ink [&::-webkit-details-marker]:hidden">
                      <ChevronRight className="h-4 w-4 transition-transform group-open:rotate-90" aria-hidden />
                      Weitere Leistungen, die passen könnten ({others.length})
                    </summary>
                    {cards(others)}
                  </details>
                )}
              </div>
            );
          })()}
          {notApplicable.length > 0 && (
            <details className="group mt-8">
              <summary className="mb-2 flex cursor-pointer list-none items-center gap-2 font-semibold text-muted hover:text-ink [&::-webkit-details-marker]:hidden">
                <ChevronRight className="h-4 w-4 transition-transform group-open:rotate-90" aria-hidden />
                Trifft derzeit nicht zu ({notApplicable.length})
              </summary>
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
            </details>
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
  docMap,
  transcriptPages,
  prefillName,
}: {
  r: EligibilityResult;
  plain: boolean;
  name: string;
  canPrepare: boolean;
  prefillDoc: string;
  formTitle: Map<string, string>;
  docMap: Record<string, string>;
  transcriptPages: { page: number; text: string }[];
  prefillName?: string;
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
  // Action first: next steps without the disclaimer line (moves to the footer); the form button sits on the step that mentions it.
  const allSteps = r.next_steps_de ?? [];
  const disclaimer = allSteps.find((x) => /^Unverbindliche Information/i.test(x));
  const steps = allSteps.filter((x) => x !== disclaimer);
  const formIds = b.form_ids ?? [];
  const formStep = formIds.length ? Math.max(0, steps.findIndex((x) => /Antrag|Formular/i.test(x))) : -1;
  const docHint = docCriteria[0];
  const values = amounts.filter((a) => a.value != null && a.unit === "EUR").map((a) => a.value!);
  const range = values.length > 1 ? `${fmtAmount(Math.min(...values), "EUR")} bis ${fmtAmount(Math.max(...values), "EUR")}` : null;
  const rangeNote = /Stufe/.test(amounts.map((a) => a.label_de ?? "").join(" ")) ? "je nach Stufe" : "je nach Fall";

  return (
    <details className={`group card border-l-4 p-0 ${toneBorder(st.tone)}`}>
      <summary className="flex cursor-pointer list-none flex-wrap items-start gap-x-3 gap-y-1 px-4 py-3 [&::-webkit-details-marker]:hidden">
        <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-accent transition-transform group-open:rotate-90" aria-hidden />
        <span className="min-w-0 flex-1">
          <span className="block">
            <span className="text-lg font-semibold">{b.name_de}</span>
            <span className="ml-2 text-sm text-muted">{b.provider}</span>
          </span>
          <span className="mt-0.5 block text-sm text-muted group-[:not([open])]:line-clamp-1">{plain && b.plain_de ? b.plain_de : b.summary_de}</span>
          <span className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm">
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

      <div className="max-w-3xl space-y-5 border-t border-line px-4 py-4 pl-12">
        {/* 1 · Was jetzt zu tun ist */}
        <section aria-label="Was jetzt zu tun ist" className="rounded-xl border border-accent/25 bg-accent-soft/50 p-4">
          <h3 className="font-semibold">Was jetzt zu tun ist</h3>
          <p className="mt-0.5 text-sm text-muted">{leadSentence(r, formIds.length > 0)}</p>
          {steps.length > 0 && (
            <ol className="mt-3 space-y-2">
              {steps.map((s, i) => (
                <li key={s} className="flex flex-wrap items-start gap-x-3 gap-y-1.5">
                  <span aria-hidden className="grid h-6 w-6 shrink-0 place-items-center rounded-full border-2 border-accent bg-surface text-xs font-semibold text-accent-strong">
                    {i + 1}
                  </span>
                  <span className="min-w-0 flex-1 pt-0.5">{s}</span>
                  {i === formStep &&
                    formIds.map((fid) => (
                      <form key={fid} action={startForm}>
                        <input type="hidden" name="form_id" value={fid} />
                        <input type="hidden" name="benefit_id" value={b.id} />
                        <input type="hidden" name="document_id" value={prefillDoc} />
                        <button className="btn-primary py-1 text-sm" disabled={!canPrepare} title={canPrepare ? (formTitle.get(fid) ?? undefined) : "Berechtigung „Anträge vorbereiten“ fehlt"}>
                          <FilePen className="h-4 w-4" aria-hidden /> {formIds.length > 1 ? (formTitle.get(fid) ?? "Antrag vorbereiten") : "Antrag vorbereiten"}
                        </button>
                      </form>
                    ))}
                </li>
              ))}
            </ol>
          )}
          {b.required_documents_de?.length ? (
            <p className="mt-3 text-sm">
              <span className="font-semibold">Mitschicken: </span>
              {b.required_documents_de.join(" · ")}
            </p>
          ) : null}
          <p className="mt-2 flex flex-wrap gap-x-4 text-sm">
            <Link href={`/stellen?topic=${encodeURIComponent(b.id)}`} className="link">
              Zuständige Stelle
            </Link>
            {!canPrepare && formIds.length > 0 && <span className="text-muted">Für Anträge hat {name} keine Berechtigung erteilt.</span>}
          </p>
        </section>

        {/* 3 · Was Sie vorab klären können */}
        {missing.length > 0 && (
          <section aria-label="Was Sie vorab klären können">
            <h3 className="font-semibold">Noch offene Angaben</h3>
            <p className="mb-1.5 text-sm text-muted">Beantworten Sie, was Sie wissen – die Prüfung wird sofort aktualisiert.</p>
            <ul className="divide-y divide-line rounded-lg border border-info/30 bg-info-soft/40">
              {missing.map((m) => (
                <FactQuestion
                  key={m}
                  factKey={m}
                  benefitName={b.name_de}
                  evidence={findEvidence(m, transcriptPages)}
                  documentId={prefillDoc || undefined}
                  filename={prefillName}
                />
              ))}
            </ul>
          </section>
        )}

        {/* 2 · Warum das passt */}
        <section aria-label="Warum das passt">
          <h3 className="mb-1.5 font-semibold">Warum das passt</h3>
          <ul className="space-y-1.5">
            {docHint && (
              <li className="flex gap-2.5">
                <Paperclip className="mt-1 h-4 w-4 shrink-0 text-accent" aria-hidden />
                <span className="min-w-0">
                  {docHint.explanation_de} {docHint.source && <SourceChip source={docHint.source} documents={docMap} />}
                </span>
              </li>
            )}
            {ruleCriteria.map((c) => (
              <li key={c.id} className="flex gap-2.5">
                <Marker met={c.met} small />
                <span className="min-w-0">
                  <span className="font-semibold">{c.label_de}</span>
                  <span className="sr-only">{c.met === true ? " – erfüllt" : c.met === false ? " – nicht erfüllt" : " – noch offen"}</span>
                  {c.explanation_de && <span className="text-muted"> – {c.explanation_de}</span>} {c.source && <SourceChip source={c.source} documents={docMap} />}
                </span>
              </li>
            ))}
          </ul>
        </section>


        {/* 4 · Wie viel? */}
        {amounts.length > 0 && (
          <section aria-label="Wie viel">
            <h3 className="mb-1 font-semibold">Wie viel?</h3>
            {amounts.length === 1 ? (
              <p>
                {amounts[0].label_de}: <strong>{amounts[0].value != null ? fmtAmount(amounts[0].value, amounts[0].unit ?? "") : "–"}</strong>{" "}
                {amounts[0].source && <SourceChip source={amounts[0].source} />}
              </p>
            ) : (
              <details className="group/amt">
                <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                  {range ? (
                    <>
                      <strong>{range}</strong> <span className="text-muted">{rangeNote}</span>
                    </>
                  ) : (
                    <span>{amounts.length} Beträge</span>
                  )}{" "}
                  <span className="text-sm font-semibold text-accent group-open/amt:hidden">Alle Beträge ›</span>
                </summary>
                <table className="mt-2 text-sm">
                  <tbody>
                    {amounts.map((a, i) => (
                      <tr key={i}>
                        <td className="py-0.5 pr-4 text-muted">{a.label_de}</td>
                        <td className="py-0.5 text-right font-semibold tabular-nums">{a.value != null ? fmtAmount(a.value, a.unit ?? "") : "–"}</td>
                        {!sharedSource && <td className="pl-3">{a.source && <SourceChip source={a.source} />}</td>}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {sharedSource && (
                  <p className="mt-1 text-sm">
                    <span className="text-muted">Alle Beträge laut </span>
                    <SourceChip source={sharedSource} />
                  </p>
                )}
              </details>
            )}
          </section>
        )}

        {/* 5 · Quellen & Hinweis */}
        <footer className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-line pt-3 text-sm text-muted">
          <span>Rechtsgrundlage:</span>
          <SourceList sources={b.legal_basis} documents={docMap} />
          {b.sources?.length ? <SourceList sources={b.sources} documents={docMap} /> : null}
          {r.rule_ids?.length ? <span>· Regel {r.rule_ids.join(", ")}</span> : null}
          <span className="w-full">{disclaimer ?? `Unverbindliche Information – die Entscheidung trifft ${b.provider}.`}</span>
        </footer>
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

function Marker({ met, small = false }: { met: boolean | null | undefined; small?: boolean }) {
  return (
    <span
      aria-hidden
      className={`mt-0.5 grid shrink-0 place-items-center rounded-full font-semibold ${small ? "h-5 w-5 text-xs" : "h-7 w-7"} ${
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

/** One plain sentence above the steps: what the status means and who decides. */
function leadSentence(r: EligibilityResult, hasForm: boolean) {
  const who = r.benefit.provider;
  const base =
    r.status === "likely"
      ? "Die Voraussetzungen sind voraussichtlich erfüllt."
      : r.status === "possible"
        ? `Das kann passen – ob es gewährt wird, entscheidet ${who}.`
        : r.status === "needs_info"
          ? `Ob es passt, hängt von offenen Angaben ab – die Entscheidung trifft ${who}.`
          : "Trifft derzeit nicht zu.";
  return hasForm && r.status !== "not_applicable" ? `${base} Den Antrag können Sie schon jetzt vorbereiten.` : base;
}
