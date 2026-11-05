import Link from "next/link";
import { ApiError } from "@/components/ApiError";
import { PageTitle } from "@/components/PageTitle";
import { SourceChip } from "@/components/SourceChip";
import { api } from "@/lib/api";
import { DOC_TYPE, fmtDate, fullName, REC_CATEGORY } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { DocumentAnalysis } from "@/lib/types";
import { ImportVaccinations } from "./ImportVaccinations";

export default async function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const me = await getMe();
  const name = me.ok ? fullName(me.data.subject) : "";
  let r = await api<DocumentAnalysis>(`/api/documents/${encodeURIComponent(id)}/analysis`);
  if (!r.ok && r.status === 404) r = await api<DocumentAnalysis>(`/api/documents/${encodeURIComponent(id)}/analyze`, { method: "POST" });
  if (!r.ok) return <ApiError status={r.status} detail={r.detail} subjectName={name} />;
  const a = r.data;
  const benefitIds = [...new Set(a.recommendations.flatMap((x) => x.related_benefit_ids ?? []))];
  const isImaging = a.doc_type === "imaging_report";

  return (
    <>
      <p className="mb-2">
        <Link href="/dokumente" className="link">
          ← Alle Dokumente
        </Link>
      </p>
      <PageTitle eyebrow={`${DOC_TYPE[a.doc_type]} · ${a.pages} Seiten`} title={a.filename} />

      <div role="note" className="card mb-6 border-l-4 border-l-info bg-info-soft">
        <h2 className="text-lg font-bold">Was steht drin – und was nicht</h2>
        <p className="mt-1">{a.notice_de}</p>
        <p className="mt-1 text-muted">
          Wir übernehmen nur ausdrücklich dokumentierte Empfehlungen. Wir deuten keine Befunde und geben keine
          medizinische Einschätzung.
        </p>
      </div>

      {isImaging && a.recommendations.length === 0 && (
        <div className="card mb-6 border-2 border-warn bg-warn-soft">
          <p className="font-bold">⚠ Befunde besprechen Sie bitte mit Ihrer Ärztin bzw. Ihrem Arzt.</p>
          <p>Der Lotse interpretiert keine Bildgebungsbefunde.</p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <section aria-labelledby="rec-h">
          <h2 id="rec-h" className="mb-3 text-xl font-bold">
            Empfehlungen im Dokument ({a.recommendations.length})
          </h2>
          {a.recommendations.length === 0 && (
            <p className="card text-muted">
              {a.doc_type === "vaccination_record"
                ? "Ein e-Impfpass enthält keine Empfehlungen – die dokumentierten Impfungen können Sie in „Vorsorge“ übernehmen."
                : "In diesem Dokument stehen keine ausdrücklichen Empfehlungen, die wir übernehmen können."}
            </p>
          )}
          <ul className="space-y-4">
            {a.recommendations.map((rec) => (
              <li key={rec.id} className="card">
                <p className="eyebrow">{REC_CATEGORY[rec.category] ?? rec.category}</p>
                <p className="mt-1 text-lg font-bold">{rec.text_de}</p>
                <blockquote className="mt-3 border-l-4 border-accent/50 pl-3 text-muted italic">„{displayQuote(rec.quote)}“</blockquote>
                <p className="mt-2">
                  <SourceChip source={{ kind: "document", label: `${a.filename}, S. ${rec.page}`, quote: rec.quote, ref: a.document_id }} />
                </p>
              </li>
            ))}
          </ul>
          {a.doc_type === "vaccination_record" && <ImportVaccinations documentId={a.document_id} subjectName={name} />}
          {benefitIds.length > 0 && (
            <div className="card mt-6 flex flex-wrap items-center gap-4 border-accent/30 bg-accent-soft">
              <p className="flex-1 text-lg font-bold">Passende Leistungen jetzt prüfen</p>
              <Link href={`/leistungen?doc=${encodeURIComponent(a.document_id)}`} className="btn-primary">
                Leistungen prüfen →
              </Link>
            </div>
          )}
        </section>
        <aside className="space-y-6">
          <section className="card">
            <h2 className="text-lg font-bold">Erkannte Angaben</h2>
            <dl className="mt-2 space-y-1">
              {(
                [
                  ["Name", [a.person.first_name, a.person.last_name].filter(Boolean).join(" ")],
                  ["Geburtsdatum", a.person.birth_date ? fmtDate(a.person.birth_date) : null],
                  ["Adresse", a.person.address],
                  ["Versicherung", a.person.insurer],
                  ["Wohnsituation", a.person.living_situation],
                ] as const
              )
                .filter(([, v]) => v)
                .map(([k, v]) => (
                  <div key={k}>
                    <dt className="text-sm text-muted">{k}</dt>
                    <dd className="font-bold">{v}</dd>
                  </div>
                ))}
            </dl>
          </section>
          {a.open_tasks?.length ? (
            <section className="card">
              <h2 className="text-lg font-bold">Offene Aufgaben laut Dokument</h2>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {a.open_tasks.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
              <Link href="/fall" className="link mt-3 inline-block">
                In „Mein Fall“ ansehen →
              </Link>
            </section>
          ) : null}
          {a.extraction_mode && <p className="text-sm text-muted">Auslesemodus: {a.extraction_mode}</p>}
        </aside>
      </div>
    </>
  );
}

/** Display only: drop a leading list bullet carried over from the PDF. The stored quote stays verbatim. */
function displayQuote(q: string) {
  return q.replace(/^\s*[•·\-–*]\s*/, "");
}
