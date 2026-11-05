// Facts the eligibility engine asks for (missing_fields) – German question + input type.
// Source: services/api/app/services/benefits/README.md. The person answers; the service decides.
export type FactInput =
  | { kind: "bool" }
  | { kind: "number"; unit?: string; min?: number; max?: number }
  | { kind: "choice"; options: [string, string][] }
  | { kind: "text"; placeholder?: string };

/** lookFor: words to find the matching passages in the person's documents – shown verbatim as context, never evaluated. */
type Def = { q: string; input: FactInput; hint?: string; lookFor?: RegExp };

const B: FactInput = { kind: "bool" };
export const FACTS: Record<string, Def> = {
  care_need_months: { q: "Wie lange wird voraussichtlich Pflege gebraucht?", input: { kind: "number", unit: "Monate", min: 0, max: 120 }, lookFor: /längerfristig|dauerhaft|unterstützungsbedarf|pflegebedarf/i },
  care_hours_estimate: { q: "Wie viele Stunden Hilfe pro Monat ungefähr?", input: { kind: "number", unit: "Std./Monat", min: 0, max: 744 }, lookFor: /unterstützung bei|aktivitäten des täglichen|körperpflege|haushalt|mobilität/i, hint: "Körperpflege, Essen, Haushalt, Wege – die PVA stellt den genauen Bedarf beim Hausbesuch fest." },
  receives_pflegegeld: { q: "Wird bereits Pflegegeld bezogen?", input: B },
  pflegegeld_applied: { q: "Wurde Pflegegeld schon beantragt?", input: B },
  care_need_at_home: { q: "Wird Unterstützung bei Pflege oder Betreuung zu Hause gebraucht?", input: B },
  home_nursing_ordered: {
    q: "Hat die Ärztin bzw. der Arzt Hauskrankenpflege angeordnet?",
    input: B,
    hint: "Steht meist auf einer eigenen Verordnung – im Zweifel in der Ordination nachfragen.",
    lookFor: /hauskrankenpflege|wundversorgung|pflege zu hause/i,
  },
  reha_application_with_medical_statement: { q: "Liegt eine ärztliche Begründung für die Reha vor?", input: B },
  gross_income_monthly: { q: "Monatliches Bruttoeinkommen", input: { kind: "number", unit: "€", min: 0 } },
  walking_unable_confirmed: {
    q: "Hat die Ärztin bzw. der Arzt eine Transportanweisung ausgestellt?",
    input: B,
    hint: "Die ÖGK zahlt den Transport nur mit ärztlicher Transportanweisung (Gehunfähigkeit, auch mit Begleitung oder Gehhilfe). Ob das zutrifft, entscheidet die Ärztin bzw. der Arzt – nicht der Befund allein.",
    lookFor: /\b(geh(strecke|unfähig|hilfe|en\b)|rollator|rollstuhl|transport|mobilität|sturz)/i,
  },
  treatment_type: {
    lookFor: /strahlentherapie|bestrahlung|chemotherapie|immuntherapie|dialyse/i,
    q: "Welche Behandlung steht an?",
    input: { kind: "choice", options: [["strahlentherapie", "Strahlentherapie"], ["chemotherapie", "Chemotherapie"], ["immuntherapie", "Immuntherapie"], ["dialyse", "Dialyse"], ["andere", "Andere"]] },
  },
  distance_km: { q: "Wie weit ist die Behandlungsstelle entfernt?", input: { kind: "number", unit: "km", min: 0 } },
  treatment_outside_home_town: { q: "Liegt die Behandlungsstelle außerhalb des Wohnorts?", input: B },
  companion_needed: { q: "Ist eine Begleitperson nötig?", input: B },
  rgb_exempt: { q: "Besteht bereits eine Rezeptgebührenbefreiung?", input: B },
  net_income_monthly: { q: "Monatliches Nettoeinkommen", input: { kind: "number", unit: "€", min: 0 } },
  household: { q: "Allein lebend oder als Paar?", input: { kind: "choice", options: [["alleinstehend", "allein"], ["paar", "als Paar"]] } },
  lives_alone: { q: "Lebt die Person allein?", input: B },
  children_count: { q: "Anzahl der Kinder im Haushalt", input: { kind: "number", min: 0, max: 20 } },
  chronic_illness_expenses: { q: "Gibt es nachgewiesene krankheitsbedingte Mehrausgaben?", input: B },
  receives_ausgleichszulage: { q: "Wird eine Ausgleichszulage bezogen?", input: B },
  costs_eur: { q: "Welche krankheitsbedingten Kosten fallen an?", input: { kind: "number", unit: "€", min: 0 } },
  familienbeihilfe_received: { q: "Wird Familienbeihilfe bezogen?", input: B },
  shared_household_with_child: { q: "Lebt das Kind im gemeinsamen Haushalt?", input: B },
  aid_needed: { q: "Wird ein Hilfsmittel gebraucht (z. B. Rollator, Pflegebett)?", input: B, lookFor: /rollator|gehhilfe|pflegebett|rollstuhl|hilfsmittel|heilbehelf/i },
  aid_type: { q: "Welches Hilfsmittel?", input: { kind: "text", placeholder: "z. B. Rollator" } },
  aid_prescribed: { q: "Hat die Ärztin bzw. der Arzt das Hilfsmittel verordnet?", input: B },
  pflegegeld_level: { q: "Welche Pflegegeldstufe besteht derzeit?", input: { kind: "number", min: 0, max: 7 }, hint: "0 = kein Pflegegeld" },
  dementia_documented: { q: "Ist eine Demenz ärztlich dokumentiert?", input: B },
  main_carer_since_months: { q: "Seit wie vielen Monaten pflegen Sie hauptsächlich?", input: { kind: "number", unit: "Monate", min: 0 } },
  carer_prevented: { q: "Sind Sie als pflegende Person verhindert (Krankheit, Urlaub)?", input: B },
  care_24h_needed: { q: "Wird Betreuung rund um die Uhr gebraucht?", input: B },
  care_24h_carer_qualified: { q: "Hat die Betreuungskraft die nötige Qualifikation?", input: B },
  pflegekarenz_agreed: { q: "Ist eine Pflegekarenz bzw. -teilzeit mit dem Arbeitgeber vereinbart?", input: B },
  caregiver_insured_3m: { q: "Waren Sie in den letzten 3 Monaten versichert beschäftigt?", input: B },
  caregiver_main_carer: { q: "Pflegen Sie hauptsächlich (Hauptpflegeperson)?", input: B },
  financial_hardship: { q: "Reicht das Einkommen nicht für den Lebensunterhalt?", input: B },
};

export function factLabel(key: string) {
  return FACTS[key]?.q ?? (/\s/.test(key) ? key : "Weitere Angabe nötig");
}

export type FactValue = string | number | boolean;
export function fmtFact(key: string, v: FactValue) {
  const def = FACTS[key];
  if (typeof v === "boolean") return v ? "Ja" : "Nein";
  if (def?.input.kind === "choice") return def.input.options.find(([k]) => k === v)?.[1] ?? String(v);
  if (def?.input.kind === "number" && def.input.unit) return `${v} ${def.input.unit}`;
  return String(v);
}

export type Evidence = { page: number; text: string };

/** Sentences of the document that contain the search words of a question (verbatim, max. 4). */
export function findEvidence(key: string, pages: { page: number; text: string }[]): Evidence[] {
  const re = FACTS[key]?.lookFor;
  if (!re) return [];
  const out: Evidence[] = [];
  for (const p of pages) {
    const sentences = p.text.replace(/\s+/g, " ").split(/(?<=[.!?])\s+(?=[A-ZÄÖÜ•])/);
    for (const raw of sentences) {
      const text = raw.replace(/^[•\-–\s]+/, "").trim();
      if (text.length > 12 && text.length < 320 && re.test(text) && !out.some((e) => e.text === text)) out.push({ page: p.page, text });
      if (out.length >= 4) return out;
    }
  }
  return out;
}
