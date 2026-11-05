import { ApiError } from "@/components/ApiError";
import { Autocomplete } from "@/components/Autocomplete";
import { LawPicker } from "@/components/LawPicker";
import { PageTitle } from "@/components/PageTitle";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/labels";
import { type Law, type LawParagraph, linkableParagraphs } from "@/lib/laws";
import type { LegalHit, LegalParagraph } from "@/lib/types";

export default async function LegalPage({ searchParams }: { searchParams: Promise<{ q?: string; law?: string; nr?: string; abs?: string }> }) {
  const sp = await searchParams;
  const laws = await api<Law[]>("/api/legal/laws");
  const para = sp.law && sp.nr ? await api<LegalParagraph>(`/api/legal/paragraphs/${encodeURIComponent(sp.law)}/${encodeURIComponent(sp.nr)}`) : null;
  const toc =
    sp.law && !sp.nr && !sp.q
      ? await api<LawParagraph[]>(`/api/legal/laws/${encodeURIComponent(sp.law)}/paragraphs`)
      : null;
  const tocList = toc?.ok ? linkableParagraphs(toc.data) : [];
  const lawInfo = laws.ok ? laws.data.find((l) => l.key === sp.law) : undefined;
  const hits = sp.q ? await api<LegalHit[]>(`/api/legal/search?q=${encodeURIComponent(sp.q)}${sp.law ? `&law=${encodeURIComponent(sp.law)}` : ""}&limit=10`) : null;
  return (
    <>
      <PageTitle eyebrow="Rechtsgrundlagen" title="Gesetzestexte nachlesen">
        Unverbindliche Information, keine Rechtsberatung. Es gilt immer die angegebene Fassung.
      </PageTitle>
      <form className="card mb-6 grid gap-3 md:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1.3fr)_auto] md:items-end" role="search">
        <LawPicker laws={laws.ok ? laws.data : []} defaultKey={sp.law} defaultNr={sp.nr} />
        <Autocomplete source="legal" name="q" label="Stichwort" defaultValue={sp.q} placeholder="z. B. Pflegegeld" />
        <button className="btn-primary">Suchen</button>
        <p className="text-sm text-muted md:col-span-4">
          Nur ein Gesetz gewählt: Inhaltsverzeichnis. Mit § : der Paragraf. Ein Stichwort sucht im Volltext – mit gewähltem Gesetz nur darin.
        </p>
      </form>
      {toc?.ok && (
        <section aria-labelledby="toc-h" className="mb-6">
          <h2 id="toc-h" className="mb-2 font-semibold">
            {lawInfo ? `${lawInfo.abbr} – ${lawInfo.title}` : sp.law} · {tocList.length} Bestimmungen
          </h2>
          <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface text-sm">
            {tocList.map((p) => (
              <li key={p.type + p.nr}>
                <a href={`/recht?law=${encodeURIComponent(sp.law!)}&nr=${encodeURIComponent(p.nr)}`} className="flex gap-3 px-4 py-1.5 hover:bg-accent-soft/50">
                  <span className="w-20 shrink-0 font-semibold tabular-nums">{p.label}</span>
                  <span className="min-w-0 flex-1">{p.heading || <span className="text-muted">ohne Überschrift</span>}</span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
      {toc && !toc.ok && (
        <p className="card mb-6 text-sm text-muted">Das Inhaltsverzeichnis ist gerade nicht verfügbar – bitte § oder Stichwort eingeben.</p>
      )}
      {para && !para.ok && <ApiError status={para.status} detail={para.detail} />}
      {para?.ok && <Paragraph p={para.data} abs={sp.abs} />}
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

function Paragraph({ p, abs }: { p: LegalParagraph; abs?: string }) {
  // Split into Absätze "(1) … (2) …" so a cited Absatz can be highlighted and linked (#abs-2).
  const parts = p.text.split(/(?=\(\d+[a-z]?\)\s)/);
  return (
    <article id="paragraf" className="card mb-6 scroll-mt-28">
      <p className="eyebrow">{p.law_title}</p>
      <h2 className="text-xl font-semibold">{shortTitle(p)}</h2>
      {trail(p.heading).length > 0 && <p className="text-sm text-muted">{trail(p.heading).join(" › ")}</p>}
      <p className="mt-1 rounded-lg bg-info-soft px-3 py-1 font-semibold text-info">
        Fassung in Kraft seit {fmtDate(p.in_force)} · unverbindliche Information, keine Rechtsberatung
      </p>
      <div className="mt-4 max-w-3xl space-y-2 whitespace-pre-wrap">
        {parts.map((t, i) => {
          const n = /^\((\d+[a-z]?)\)/.exec(t)?.[1];
          const hit = !!abs && n === abs;
          return (
            <p key={i} id={n ? `abs-${n}` : undefined} className={`scroll-mt-28 ${hit ? "rounded-md bg-warn-soft px-2 py-1 ring-1 ring-warn/40" : ""}`}>
              {t.trim()}
            </p>
          );
        })}
      </div>
    </article>
  );
}

/** "§ 1 BPGG – Zweck des Pflegegeldes" instead of the full TEIL/ABSCHNITT chain. */
function shortTitle(p: LegalParagraph) {
  const parts = p.heading.split(" – ").map((x) => x.trim()).filter(Boolean);
  const title = (parts[parts.length - 1] ?? p.heading).trim();
  return title ? `§ ${p.nr} ${p.law} – ${title}` : `§ ${p.nr} ${p.law}`;
}
/** The structural part of the heading (Teil, Abschnitt), shown small as a breadcrumb. */
function trail(heading: string) {
  const parts = heading.split(" – ").map((x) => x.trim()).filter(Boolean);
  return parts.slice(0, -1).map((x) => x.replace(/\s*\(Bundespflegegeldgesetz[^)]*\)/, ""));
}
