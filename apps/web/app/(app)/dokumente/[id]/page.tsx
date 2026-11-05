import { CalendarPlus, Check, ChevronRight, ScanText, TriangleAlert } from "lucide-react";
import { createCase } from "@/app/actions";
import Link from "next/link";
import { ApiError } from "@/components/ApiError";
import { PageTitle } from "@/components/PageTitle";
import { SourceChip } from "@/components/SourceChip";
import { api } from "@/lib/api";
import { DOC_TYPE, fmtDate, fullName, REC_CATEGORY } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { Case, DocumentAnalysis } from "@/lib/types";
import { ImportVaccinations } from "./ImportVaccinations";
import type { components } from "@/lib/api-types";
import { SituationSuggestions } from "./SituationSuggestions";
import type { SituationOverview } from "@/lib/situation";

export default async function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const me = await getMe();
  const name = me.ok ? fullName(me.data.subject) : "";
  let r = await api<DocumentAnalysis>(`/api/documents/${encodeURIComponent(id)}/analysis`);
  if (!r.ok && r.status === 404) r = await api<DocumentAnalysis>(`/api/documents/${encodeURIComponent(id)}/analyze`, { method: "POST" });
  if (!r.ok) return <ApiError status={r.status} detail={r.detail} subjectName={name} />;
  const a = r.data;
  const benefitIds = [...new Set(a.recommendations.flatMap((x) => x.related_benefit_ids ?? []))];
  const transcript = await api<components["schemas"]["DocumentTranscript"]>(`/api/documents/${encodeURIComponent(id)}/transcript`);
  const fromPhoto = transcript.ok && transcript.data.source === "image";
  // Pending Lebenslage suggestions that came from this document (only when the situation service answers).
  const situation = a.doc_type === "discharge_letter" ? await api<SituationOverview>("/api/situation") : null;
  const fromThisDoc = situation?.ok
    ? (situation.data.suggestions ?? []).filter((e) => (e.source.ref ?? "").includes(a.document_id) || e.source.label.startsWith(a.filename))
    : [];
  const isImaging = a.doc_type === "imaging_report";
  // Already taken over: confirmed episodes whose source is this document.
  const fromDoc = (e: { source: { ref?: string | null; label: string } }) => (e.source.ref ?? "").includes(a.document_id) || e.source.label.startsWith(a.filename);
  const confirmedFromDoc = situation?.ok ? [...(situation.data.current ?? []), ...(situation.data.upcoming ?? []), ...(situation.data.past ?? [])].filter(fromDoc).length : 0;

  // Mein Fall: is there a case built from this document already?
  const cases = a.open_tasks?.length ? await api<Case[]>("/api/cases") : null;
  const hasCase = cases?.ok && cases.data.length > 0;
  const firstName = me.ok ? me.data.subject.first_name : "";
  const byCategory = new Map<string, DocumentAnalysis["recommendations"]>();
  for (const rec of a.recommendations) byCategory.set(rec.category, [...(byCategory.get(rec.category) ?? []), rec]);

  return (
    <>
      <p className="mb-2 text-sm">
        <Link href="/dokumente" className="link">
          Alle Dokumente
        </Link>
      </p>
      <PageTitle title={a.filename}>
        {DOC_TYPE[a.doc_type]}, {a.pages} {a.pages === 1 ? "Seite" : "Seiten"}
        {fromPhoto && " · aus Foto gelesen"}
      </PageTitle>

      <div className="max-w-4xl space-y-6">
        {/* 1 · Was jetzt zu tun ist */}
        <section aria-labelledby="todo-h" className="rounded-xl border border-accent/25 bg-accent-soft/50 p-4">
          <h2 id="todo-h" className="font-semibold">
            Was jetzt zu tun ist
          </h2>
          {isImaging ? (
            <div className="mt-2 space-y-2">
              <p className="flex items-center gap-2 font-semibold">
                <TriangleAlert className="h-5 w-5 shrink-0 text-warn" aria-hidden /> Befunde besprechen Sie bitte mit Ihrer Ärztin bzw. Ihrem Arzt.
              </p>
              <p className="text-sm text-muted">Lotsi interpretiert keine Bildgebungsbefunde.</p>
              <Link href="/termine?wo=provider&suche=1" className="btn-secondary py-1 text-sm">
                <CalendarPlus className="h-4 w-4" aria-hidden /> Termin bei der Hausärztin suchen
              </Link>
            </div>
          ) : (
            <ol className="mt-2 space-y-2">
              {situation?.ok && (
                <Todo n={1} done={fromThisDoc.length === 0 && confirmedFromDoc > 0} title={`Lebenslage von ${firstName} übernehmen`}>
                  {fromThisDoc.length > 0
                    ? `${fromThisDoc.length} Vorschläge – unten bestätigen oder ablehnen`
                    : confirmedFromDoc > 0
                      ? `${confirmedFromDoc} übernommen`
                      : "Vorschläge unten erstellen"}
                </Todo>
              )}
              {benefitIds.length > 0 && (
                <Todo n={situation?.ok ? 2 : 1} title={`Passende Leistungen prüfen (${benefitIds.length})`}>
                  <Link href={`/leistungen?doc=${encodeURIComponent(a.document_id)}`} className="btn-primary py-1 text-sm">
                    Leistungen prüfen
                  </Link>
                </Todo>
              )}
              {a.open_tasks?.length ? (
                <Todo n={(situation?.ok ? 1 : 0) + (benefitIds.length ? 1 : 0) + 1} title={`Offene Aufgaben aus dem Brief (${a.open_tasks.length}) im Blick behalten`}>
                  {hasCase ? (
                    <Link href="/fall" className="btn-secondary py-1 text-sm">
                      Mein Fall öffnen
                    </Link>
                  ) : (
                    <form action={createCase}>
                      <button className="btn-secondary py-1 text-sm">Als „Mein Fall“ anlegen</button>
                    </form>
                  )}
                </Todo>
              ) : null}
              {a.doc_type === "vaccination_record" && (
                <li>
                  <ImportVaccinations documentId={a.document_id} subjectName={name} />
                </li>
              )}
            </ol>
          )}
        </section>

        {/* Consent cards (labels used in the demo script: "Ja, übernehmen") */}
        {situation?.ok && (fromThisDoc.length > 0 || confirmedFromDoc === 0) && <SituationSuggestions documentId={a.document_id} initial={fromThisDoc} firstName={firstName} />}

        {/* 2 · Was im Dokument empfohlen wird */}
        <section aria-labelledby="rec-h">
          <h2 id="rec-h" className="font-semibold">
            Im Dokument ausdrücklich empfohlen ({a.recommendations.length})
          </h2>
          <p className="mb-2 text-sm text-muted">{a.notice_de} Wir deuten keine Befunde und geben keine medizinische Einschätzung.</p>
          {a.recommendations.length === 0 ? (
            <p className="card text-sm text-muted">
              {a.doc_type === "vaccination_record"
                ? "Ein e-Impfpass enthält keine Empfehlungen – die dokumentierten Impfungen können Sie in „Vorsorge“ übernehmen."
                : "In diesem Dokument stehen keine ausdrücklichen Empfehlungen, die wir übernehmen können."}
            </p>
          ) : (
            <div className="overflow-hidden rounded-xl border border-line bg-surface">
              {[...byCategory.entries()].map(([cat, recs]) => (
                // Collapsible per category; categories that lead to a benefit (e.g. Pflege) start open.
                <details
                  key={cat}
                  open={recs.some((r) => (r.related_benefit_ids ?? []).length > 0)}
                  className="group border-t border-line first:border-t-0"
                >
                  <summary className="flex cursor-pointer list-none items-center gap-2 bg-paper/60 px-4 py-2 text-sm font-semibold text-muted hover:text-ink [&::-webkit-details-marker]:hidden">
                    <ChevronRight className="h-4 w-4 shrink-0 transition-transform group-open:rotate-90" aria-hidden />
                    {REC_CATEGORY[cat] ?? cat}
                    <span className="font-normal">({recs.length})</span>
                  </summary>
                  <ul className="divide-y divide-line">
                    {recs.map((rec) => (
                      <li key={rec.id} className="px-4 py-2.5">
                        {/* the verbatim quote IS the recommendation – no paraphrase around it */}
                        <p className="font-semibold">
                          „{displayQuote(rec.quote)}“{" "}
                          <SourceChip source={{ kind: "document", label: `S. ${rec.page}`, quote: rec.quote, ref: `document:${a.document_id}#page=${rec.page}` }} />
                        </p>
                      </li>
                    ))}
                  </ul>
                </details>
              ))}
            </div>
          )}
        </section>

        {/* 3 · Details */}
        <section aria-label="Details" className="grid gap-4 md:grid-cols-2">
          <div className="card">
            <h2 className="font-semibold">Erkannte Angaben</h2>
            <dl className="mt-1.5 grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1 text-sm">
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
                  <div key={k} className="contents">
                    <dt className="text-muted">{k}</dt>
                    <dd className="font-semibold">{v}</dd>
                  </div>
                ))}
            </dl>
            {a.extraction_mode && <p className="mt-2 text-xs text-muted">Auslesemodus: {a.extraction_mode}</p>}
          </div>
          {a.open_tasks?.length ? (
            <div className="card">
              <h2 className="font-semibold">Offene Aufgaben laut Dokument</h2>
              <ul className="mt-1.5 list-disc space-y-0.5 pl-5 text-sm">
                {a.open_tasks.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {transcript.ok && transcript.data.pages.length > 0 && (
            <details open={fromPhoto} className="card md:col-span-2">
              <summary className="flex cursor-pointer items-center gap-2 font-semibold">
                <ScanText className="h-4 w-4 text-accent" aria-hidden /> Was Lotsi gelesen hat
              </summary>
              {transcript.data.notice_de && <p className="mt-2 rounded-md bg-warn-soft px-2.5 py-1.5 text-sm">{transcript.data.notice_de}</p>}
              <ol className="mt-2 space-y-3">
                {transcript.data.pages.map((p) => (
                  <li key={p.page}>
                    <p className="text-xs font-semibold text-muted">
                      Seite {p.page}
                      {p.unreadable > 0 && ` · ${p.unreadable} Stelle(n) unleserlich`}
                      {p.low_resolution && " · geringe Auflösung"}
                    </p>
                    <p className="max-h-64 overflow-y-auto text-sm whitespace-pre-wrap">{p.text}</p>
                  </li>
                ))}
              </ol>
            </details>
          )}
        </section>
      </div>
    </>
  );
}

function Todo({ n, title, done = false, children }: { n: number; title: string; done?: boolean; children?: React.ReactNode }) {
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
      <span
        aria-hidden
        // open = outlined (action required), done = filled with a check mark
        className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-semibold ${done ? "bg-ok text-white" : "border-2 border-accent bg-surface text-accent-strong"}`}
      >
        {done ? <Check className="h-3.5 w-3.5" /> : n}
      </span>
      <span className={`min-w-0 flex-1 font-semibold ${done ? "text-muted" : ""}`}>{title}</span>
      {children && <span className="text-sm text-muted">{children}</span>}
    </li>
  );
}

/** Display only: drop a leading list bullet carried over from the PDF. The stored quote stays verbatim. */
function displayQuote(q: string) {
  return q.replace(/^\s*[•·\-–*]\s*/, "");
}
