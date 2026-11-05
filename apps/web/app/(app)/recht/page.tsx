import { ApiError } from "@/components/ApiError";
import { Autocomplete } from "@/components/Autocomplete";
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
          <Autocomplete source="legal" name="q" label="Stichwort" defaultValue={sp.q} placeholder="z. B. Pflegegeld" />
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
                {shortTitle(h.paragraph)}
              </a>
              <p className="text-sm text-muted">
                {[h.paragraph.law_title, ...trail(h.paragraph.heading)].join(" › ")} · Fassung in Kraft seit {fmtDate(h.paragraph.in_force)}
              </p>
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
      <h2 className="text-2xl font-bold">{shortTitle(p)}</h2>
      {trail(p.heading).length > 0 && <p className="text-sm text-muted">{trail(p.heading).join(" › ")}</p>}
      <p className="mt-1 rounded-lg bg-info-soft px-3 py-1 font-bold text-info">
        Fassung in Kraft seit {fmtDate(p.in_force)} · unverbindliche Information, keine Rechtsberatung
      </p>
      <div className="mt-4 max-w-3xl whitespace-pre-wrap">{p.text}</div>
    </article>
  );
}

/** "§ 1 BPGG – Zweck des Pflegegeldes" instead of the full TEIL/ABSCHNITT chain. */
function shortTitle(p: LegalParagraph) {
  const parts = p.heading.split(" – ").map((x) => x.trim()).filter(Boolean);
  return `§ ${p.nr} ${p.law} – ${parts[parts.length - 1] ?? p.heading}`;
}
/** The structural part of the heading (Teil, Abschnitt), shown small as a breadcrumb. */
function trail(heading: string) {
  const parts = heading.split(" – ").map((x) => x.trim()).filter(Boolean);
  return parts.slice(0, -1).map((x) => x.replace(/\s*\(Bundespflegegeldgesetz[^)]*\)/, ""));
}
