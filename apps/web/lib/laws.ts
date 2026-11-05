// Laws and guidelines of the legal corpus, as served by GET /api/legal/laws.
export type Law = { key: string; abbr: string; title: string; paragraphs?: number };

const norm = (s: string) => s.toLowerCase().replace(/[\s_\-.]/g, "").replace(/ö/g, "oe").replace(/ä/g, "ae").replace(/ü/g, "ue");
/** Matches abbreviation, API key or full title ("pfleg" → BPGG, RPGG 2012; "OEGK" → KrankenO/Satzung ÖGK). */
export function matchLaws(laws: Law[], q: string) {
  const n = norm(q);
  if (!n) return laws;
  return laws.filter((l) => norm(l.abbr).includes(n) || norm(l.key).includes(n) || norm(l.title).includes(n));
}

export type LawParagraph = { nr: string; type: string; label: string; heading: string; in_force: string };

/** Entries that GET /api/legal/paragraphs/{law}/{nr} can open: every §, other types only if no § has the same nr;
 *  the law's own table of contents (INH) is left out. */
export function linkableParagraphs(list: LawParagraph[]) {
  const paraNrs = new Set(list.filter((p) => p.type === "PARA").map((p) => p.nr));
  return list.filter((p) => p.type !== "INH" && (p.type === "PARA" || !paraNrs.has(p.nr)));
}
