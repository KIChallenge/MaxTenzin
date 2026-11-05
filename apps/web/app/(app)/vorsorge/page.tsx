import { ApiError } from "@/components/ApiError";
import { Badge } from "@/components/Badge";
import { PageTitle } from "@/components/PageTitle";
import { SourceList } from "@/components/SourceChip";
import { api } from "@/lib/api";
import { fmtDate, fullName, PREVENTION_STATUS } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { PreventionOverview } from "@/lib/types";

export default async function PreventionPage() {
  const [me, r] = await Promise.all([getMe(), api<PreventionOverview>("/api/prevention/overview")]);
  const name = me.ok ? fullName(me.data.subject) : "";
  return (
    <>
      <PageTitle eyebrow="Vorsorge" title={`Vorsorge & Impfungen – ${name}`}>
        Hinweise laut Österreichischem Impfplan und den Angeboten der Krankenversicherung.
      </PageTitle>
      {!r.ok ? (
        <ApiError status={r.status} detail={r.detail} subjectName={name} />
      ) : (
        <>
          <div role="note" className="card mb-6 border-l-4 border-l-info bg-info-soft">
            <p>{r.data.disclaimer_de}</p>
            <p className="mt-1 text-sm text-muted">Stand: {fmtDate(r.data.as_of)}</p>
          </div>
          <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
            <ul className="space-y-4">
              {r.data.items.map((it) => {
                const st = PREVENTION_STATUS[it.status];
                // "laut Impfplan" only fits vaccinations; screenings are offers of the insurer.
                const label = it.kind !== "vaccination" && it.status === "due" ? "empfohlen – kostenloses Angebot" : st.label;
                const meta = [
                  it.last_date && `Zuletzt dokumentiert: ${fmtDate(it.last_date)}`,
                  it.due_date && `empfohlen bis ${fmtDate(it.due_date)}`,
                  it.cost_de && `Kosten: ${it.cost_de}`,
                ].filter(Boolean);
                return (
                  <li key={it.id} className="card">
                    <div className="flex flex-wrap items-start gap-3">
                      <h2 className="flex-1 text-xl font-bold">{it.title_de}</h2>
                      <Badge tone={st.tone}>{label}</Badge>
                    </div>
                    <p className="mt-1">{it.explanation_de}</p>
                    {meta.length > 0 && <p className="mt-1 text-sm text-muted">{meta.join(" · ")}</p>}
                    <div className="mt-2">
                      <SourceList sources={it.sources} />
                    </div>
                  </li>
                );
              })}
            </ul>
            <section className="card h-fit">
              <h2 className="text-lg font-bold">Im e-Impfpass dokumentiert</h2>
              {r.data.vaccinations.length === 0 ? (
                <p className="text-muted">Keine Einträge.</p>
              ) : (
                <ul className="mt-2 divide-y divide-line">
                  {r.data.vaccinations.map((v, i) => (
                    <li key={i} className="py-2">
                      <p className="font-bold">{v.disease}</p>
                      <p className="text-sm text-muted">
                        {fmtDate(v.date)} · {v.vaccine}
                        {v.dose_label && ` · ${v.dose_label}`}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </>
  );
}
