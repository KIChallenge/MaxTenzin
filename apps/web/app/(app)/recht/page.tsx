import { ApiError } from "@/components/ApiError";
import { PageTitle } from "@/components/PageTitle";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/labels";
import type { LegalHit, LegalParagraph } from "@/lib/types";

export default async function LegalPage({ searchParams }: { searchParams: Promise<{ q?: string; law?: string; nr?: string }> }) {
  const sp = await searchParams;
  const para = sp.law && sp.nr ? await api<LegalParagraph>(`/api/legal/paragraphs/${encodeURIComponent(sp.law)}/${encodeURIComponent(sp.nr)}`) : null;
  const hits = sp.q ? await api<LegalHit[]>(`/api/legal/search?q=${encodeURIComponent(sp.q)}&limit=10`) : null;
  return (
    <>
      <PageTitle eyebrow="Rechtsgrundlagen" title="Gesetzestexte nachlesen">
        Unverbindliche Information, keine Rechtsberatung. Es gilt immer die angegebene Fassung.
      </PageTitle>
      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <form className="card flex flex-wrap items-end gap-3" role="search">
          <label className="flex flex-1 flex-col gap-1">
            <span className="font-bold">Stichwort</span>
            <input name="q" defaultValue={sp.q} className="input" placeholder="z. B. Pflegegeld" />
          </label>
          <button className="btn-primary">Suchen</button>
        </form>
        <form className="card flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1">
            <span className="font-bold">Gesetz</span>
            <input name="law" defaultValue={sp.law ?? "BPGG"} className="input w-28" />
          </label>
          <label className="flex flex-col gap-1">
            <span className="font-bold">§</span>
            <input name="nr" defaultValue={sp.nr ?? "4"} className="input w-20" />
          </label>
          <button className="btn-secondary">Paragraf öffnen</button>
        </form>
      </div>
      {para && !para.ok && <ApiError status={para.status} detail={para.detail} />}
      {para?.ok && <Paragraph p={para.data} />}
      {hits && !hits.ok && <ApiError status={hits.status} detail={hits.detail} />}
      {hits?.ok && (
        <ul className="space-y-3">
          {hits.data.length === 0 && <p className="card text-muted">Keine Treffer.</p>}
          {hits.data.map((h) => (
            <li key={h.paragraph.doc_id} className="card">
              <a className="link text-lg" href={`/recht?law=${encodeURIComponent(h.paragraph.law_key)}&nr=${encodeURIComponent(h.paragraph.nr)}`}>
                {h.paragraph.citation_de || `§ ${h.paragraph.nr} ${h.paragraph.law}`} – {h.paragraph.heading}
              </a>
              <p className="text-sm text-muted">{h.paragraph.law_title} · Fassung in Kraft seit {fmtDate(h.paragraph.in_force)}</p>
              <p className="mt-1">{h.snippet}</p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function Paragraph({ p }: { p: LegalParagraph }) {
  return (
    <article className="card mb-6">
      <p className="eyebrow">{p.law_title}</p>
      <h2 className="text-2xl font-bold">
        {p.citation_de || `§ ${p.nr} ${p.law}`} – {p.heading}
      </h2>
      <p className="mt-1 rounded-lg bg-info-soft px-3 py-1 font-bold text-info">
        Fassung in Kraft seit {fmtDate(p.in_force)} · unverbindliche Information, keine Rechtsberatung
      </p>
      <div className="mt-4 max-w-3xl whitespace-pre-wrap">{p.text}</div>
    </article>
  );
}
