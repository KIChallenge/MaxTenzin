import { ChevronRight } from "lucide-react";
import { ApiError } from "@/components/ApiError";
import { Autocomplete } from "@/components/Autocomplete";
import { PageTitle } from "@/components/PageTitle";
import { SourceChip } from "@/components/SourceChip";
import { api } from "@/lib/api";
import type { Medication } from "@/lib/types";

const BOX: Record<string, { label: string; meaning: string; cls: string }> = {
  G: { label: "frei verschreibbar", meaning: "Grüner Bereich des EKO", cls: "border-ok/30 bg-ok-soft text-ok" },
  Y: { label: "Bewilligung nötig", meaning: "Gelber Bereich: Bewilligung durch den chef-/kontrollärztlichen Dienst", cls: "border-warn/30 bg-warn-soft text-warn" },
  R: { label: "nur im Einzelfall", meaning: "Roter Bereich: nur in begründeten Einzelfällen, Bewilligung nötig", cls: "border-danger/30 bg-danger-soft text-danger" },
};
const RESTRICTION: Record<string, string> = {
  IND: "Anwendungsgebiete eingeschränkt",
  RE1: "Bewilligung vor Abgabe",
  RE2: "Bewilligung oder Dokumentation",
  L: "Mengenbegrenzung",
};
const COLS = "grid-cols-[1fr_auto] sm:grid-cols-[5rem_10rem_minmax(0,1fr)_6rem_1rem]";
// Shown once at the top instead of in every row (display only – the API text itself is unchanged).
const SHARED_HINT = /\s*Fragen zu Wirkung, Einnahme oder Dosierung[^.]*\./;

const eur = (v: number | null | undefined) => (v == null ? "–" : v.toLocaleString("de-AT", { style: "currency", currency: "EUR" }));

export default async function MedicationsPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  const r = q ? await api<Medication[]>(`/api/medications/search?q=${encodeURIComponent(q)}&limit=40`) : null;

  // Same product (name) → one group, packs as rows.
  const groups = new Map<string, Medication[]>();
  for (const m of r?.ok ? r.data : []) groups.set(m.name, [...(groups.get(m.name) ?? []), m]);
  const source = r?.ok ? r.data[0]?.source : undefined;

  return (
    <>
      <PageTitle title="Medikamente: Kosten & Bewilligung">
        Angaben laut Erstattungskodex (EKO). Keine Empfehlung zu Medikamenten oder Dosierung – Fragen zu Wirkung, Einnahme oder
        Dosierung klären Sie bitte mit Ihrer Ärztin, Ihrem Arzt oder in der Apotheke.
      </PageTitle>
      <form className="mb-5 flex max-w-3xl items-end gap-3" role="search">
        <Autocomplete source="medications" name="q" label="Produktname oder Wirkstoff" defaultValue={q} placeholder="z. B. Letrozol" />
        <button className="btn-primary">Suchen</button>
      </form>

      {r && !r.ok && <ApiError status={r.status} detail={r.detail} />}
      {r?.ok && r.data.length === 0 && <p className="card text-muted">Keine Treffer für „{q}“.</p>}
      {r?.ok && r.data.length > 0 && (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <span className="text-muted">
              {r.data.length} Packungen in {groups.size} {groups.size === 1 ? "Produkt" : "Produkten"}
            </span>
            {source && <SourceChip source={source} />}
          </div>

          <div role="table" aria-label="Packungen" className="overflow-hidden rounded-xl border border-line bg-surface text-sm">
            <div role="row" className={`sticky top-0 hidden ${COLS} gap-3 border-b border-line bg-paper px-4 py-1.5 text-xs font-semibold text-muted sm:grid`}>
              <span role="columnheader">Packung</span>
              <span role="columnheader">Verschreibung</span>
              <span role="columnheader">Hinweis</span>
              <span role="columnheader" className="text-right">Kassenpreis</span>
              <span />
            </div>
            {[...groups.entries()].map(([name, packs]) => (
              <div key={name} role="rowgroup">
                <h2 role="row" className="border-t border-line bg-paper/50 px-4 pt-2 pb-1 font-semibold first:border-t-0">
                  {name}
                </h2>
                {packs.map((m) => (
                  <details key={m.pharma_nr} className="group">
                    <summary
                      role="row"
                      className={`grid cursor-pointer list-none ${COLS} items-center gap-x-3 px-4 py-1.5 hover:bg-neutral-soft/60 [&::-webkit-details-marker]:hidden`}
                    >
                      <span role="cell" className="tabular-nums">
                        {m.pack.replace(/^(\d+)\s*St$/, "$1 Stk.")}
                      </span>
                      <span role="cell">
                        {BOX[m.box] ? (
                          <span title={BOX[m.box].meaning} className={`rounded-full border px-2 text-xs font-semibold whitespace-nowrap ${BOX[m.box].cls}`}>{BOX[m.box].label}</span>
                        ) : (
                          m.box
                        )}
                      </span>
                      <span role="cell" className="col-span-2 truncate text-muted sm:col-span-1">
                        {m.restriction ? (
                          <>
                            <span className="font-semibold text-ink">{m.restriction}</span> · {RESTRICTION[m.restriction] ?? "laut EKO"}
                          </>
                        ) : (
                          "–"
                        )}
                      </span>
                      <span role="cell" className="text-right font-semibold tabular-nums">
                        {eur(m.price_eur)}
                      </span>
                      <ChevronRight className="hidden h-4 w-4 text-muted transition-transform group-open:rotate-90 sm:block" aria-hidden />
                    </summary>
                    <dl className="grid gap-x-6 gap-y-1 bg-paper/60 px-4 py-2.5 sm:grid-cols-[9rem_minmax(0,1fr)]">
                      <dt className="text-muted">Verschreibung</dt>
                      <dd>{m.approval_needed_de.replace(SHARED_HINT, "")}</dd>
                      <dt className="text-muted">Ihre Kosten</dt>
                      <dd>{m.patient_cost_note_de}</dd>
                      {m.indication_text && (
                        <>
                          <dt className="text-muted">Anwendungsgebiet</dt>
                          <dd>{m.indication_text}</dd>
                        </>
                      )}
                      {m.rule_text && (
                        <>
                          <dt className="text-muted">Regel (EKO)</dt>
                          <dd>{m.rule_text}</dd>
                        </>
                      )}
                      <dt className="text-muted">Pharmanummer</dt>
                      <dd className="flex flex-wrap items-center gap-2 tabular-nums">
                        {m.pharma_nr} <SourceChip source={m.source} />
                      </dd>
                    </dl>
                  </details>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
