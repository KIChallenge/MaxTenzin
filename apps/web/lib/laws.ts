// Laws and guidelines in the legal corpus (knowledge/extracted/legal). Static until the legal service offers
// GET /api/legal/laws (contract request in PROGRESS.md). key = law_key used by the API.
export type Law = { key: string; abbr: string; title: string };

export const LAWS: Law[] = [
  { key: "ASVG", abbr: "ASVG", title: "Allgemeines Sozialversicherungsgesetz" },
  { key: "BPGG", abbr: "BPGG", title: "Bundespflegegeldgesetz" },
  { key: "FLAG", abbr: "FLAG", title: "Familienlastenausgleichsgesetz 1967" },
  { key: "KBGG", abbr: "KBGG", title: "Kinderbetreuungsgeldgesetz" },
  { key: "KrankenO_OEGK_2025", abbr: "KrankenO ÖGK 2025", title: "Krankenordnung der Österreichischen Gesundheitskasse 2025" },
  { key: "Satzung_OEGK_2025", abbr: "Satzung ÖGK 2025", title: "Satzung der Österreichischen Gesundheitskasse 2025" },
  { key: "MuKiPassV_2002", abbr: "MuKiPassV 2002", title: "Mutter-Kind-Pass-Verordnung 2002" },
  { key: "VO-EKO", abbr: "VO-EKO", title: "Verfahrensordnung zur Herausgabe des Erstattungskodex (§ 351g ASVG)" },
  { key: "RPGG_2012", abbr: "RPGG 2012", title: "Richtlinien für die einheitliche Anwendung des Bundespflegegeldgesetzes 2012" },
  { key: "RRK_2021", abbr: "RRK 2021", title: "Richtlinien für Rehabilitation, Festigung der Gesundheit und Gesundheitsvorsorge" },
  { key: "RRZ_2008", abbr: "RRZ 2008", title: "Richtlinien für die Befreiung von der Rezeptgebühr 2008" },
  { key: "RUF_2020", abbr: "RUF 2020", title: "Richtlinien für Zuschüsse aus dem Unterstützungsfonds der ÖGK" },
  { key: "RVU", abbr: "RVU", title: "Richtlinien für die Durchführung und Auswertung der Vorsorgeuntersuchungen" },
  { key: "RFG_2020", abbr: "RFG 2020", title: "Richtlinien zur Festigung der Gesundheit (§ 155 ASVG) und Krankheitsverhütung (§ 156 ASVG)" },
  { key: "RGFP", abbr: "RGFP", title: "Richtlinien für Gesundheitsförderung und Prävention" },
  { key: "RJU_2016", abbr: "RJU 2016", title: "Richtlinien für die Jugendlichenuntersuchungen 2016" },
  { key: "RBA", abbr: "RBA", title: "Richtlinien für die Nachsicht vom Behandlungsbeitrag-Ambulanz" },
  { key: "RBS_2005", abbr: "RBS 2005", title: "Richtlinien für die Befreiung vom Service-Entgelt 2005" },
  { key: "RBZRehab_2005", abbr: "RBZRehab 2005", title: "Richtlinien für die Befreiung von Zuzahlungen bei Rehabilitation 2005" },
];

export function lawByKey(key?: string | null) {
  return LAWS.find((l) => l.key === key);
}

const norm = (s: string) => s.toLowerCase().replace(/[\s_\-.]/g, "").replace(/ö/g, "oe").replace(/ä/g, "ae").replace(/ü/g, "ue");
/** Matches abbreviation, API key or full title ("pfleg" → BPGG, RPGG 2012; "OEGK" → KrankenO/Satzung ÖGK). */
export function matchLaws(q: string) {
  const n = norm(q);
  if (!n) return LAWS;
  return LAWS.filter((l) => norm(l.abbr).includes(n) || norm(l.key).includes(n) || norm(l.title).includes(n));
}
