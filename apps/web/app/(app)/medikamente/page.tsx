import { ApiError } from "@/components/ApiError";
import { PageTitle } from "@/components/PageTitle";
import { SourceChip } from "@/components/SourceChip";
import { api } from "@/lib/api";
import type { Medication } from "@/lib/types";

const BOX: Record<string, string> = { G: "Grüner Bereich", Y: "Gelber Bereich", R: "Roter Bereich" };

export default async function MedicationsPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  const r = q ? await api<Medication[]>(`/api/medications/search?q=${encodeURIComponent(q)}&limit=20`) : null;
  return (
    <>
      <PageTitle eyebrow="Medikamente" title="Kosten & Bewilligung">
        Angaben laut Erstattungskodex (EKO). Keine Empfehlung zu Medikamenten oder Dosierung – fragen Sie dazu Ihre Ärztin bzw. Ihren Arzt.
      </PageTitle>
      <form className="card mb-6 flex flex-wrap items-end gap-4" role="search">
        <label className="flex flex-1 flex-col gap-1">
          <span className="font-bold">Produktname</span>
          <input name="q" defaultValue={q} className="input" placeholder="z. B. Letrozol" />
        </label>
        <button className="btn-primary">Suchen</button>
      </form>
      {r && !r.ok && <ApiError status={r.status} detail={r.detail} />}
      {r?.ok && r.data.length === 0 && <p className="card text-muted">Nichts gefunden.</p>}
      {r?.ok && r.data.length > 0 && (
        <ul className="space-y-3">
          {r.data.map((m) => (
            <li key={m.pharma_nr} className="card">
              <div className="flex flex-wrap items-start gap-3">
                <h2 className="flex-1 text-lg font-bold">{m.name}</h2>
                <span className="rounded-full border border-line px-2 text-sm font-bold">{BOX[m.box] ?? m.box}</span>
              </div>
              <p className="text-muted">Packung: {m.pack}</p>
              <p className="mt-1">{m.approval_needed_de}</p>
              <p>{m.patient_cost_note_de}</p>
              {m.restriction && <p className="text-muted">Einschränkung: {m.restriction}</p>}
              <p className="mt-2"><SourceChip source={m.source} /></p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
