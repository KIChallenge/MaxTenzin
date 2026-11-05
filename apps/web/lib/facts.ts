// German wording for the fact keys the eligibility engine reports in `missing_fields`
// (see services/api/app/services/benefits/README.md). Unknown keys fall back to a generic line.
export const FACT_LABELS: Record<string, string> = {
  care_need_months: "Wie lange wird voraussichtlich Pflege gebraucht (in Monaten)?",
  care_hours_estimate: "Geschätzter Pflegebedarf in Stunden pro Monat (die PVA stellt ihn beim Hausbesuch fest)",
  receives_pflegegeld: "Wird bereits Pflegegeld bezogen?",
  pflegegeld_applied: "Wurde Pflegegeld schon beantragt?",
  care_need_at_home: "Wird Unterstützung bei Pflege oder Betreuung zu Hause gebraucht?",
  home_nursing_ordered: "Hat die Ärztin bzw. der Arzt Hauskrankenpflege angeordnet?",
  reha_application_with_medical_statement: "Liegt eine ärztliche Begründung für die Reha vor?",
  gross_income_monthly: "Monatliches Bruttoeinkommen (für die Höhe der Zuzahlung)",
  walking_unable_confirmed: "Ist die Gehunfähigkeit ärztlich bestätigt (Transportanweisung)?",
  treatment_type: "Welche Behandlung steht an (z. B. Strahlentherapie)?",
  distance_km: "Wie weit ist die Behandlungsstelle entfernt (km)?",
  treatment_outside_home_town: "Liegt die Behandlungsstelle außerhalb des Wohnorts?",
  companion_needed: "Ist eine Begleitperson nötig?",
  rgb_exempt: "Besteht bereits eine Rezeptgebührenbefreiung?",
  net_income_monthly: "Monatliches Nettoeinkommen",
  household: "Allein lebend oder als Paar?",
  lives_alone: "Allein lebend?",
  children_count: "Anzahl der Kinder im Haushalt",
  chronic_illness_expenses: "Gibt es nachgewiesene krankheitsbedingte Mehrausgaben?",
  receives_ausgleichszulage: "Wird eine Ausgleichszulage bezogen?",
  costs_eur: "Welche krankheitsbedingten Kosten fallen an (in €)?",
  familienbeihilfe_received: "Wird Familienbeihilfe bezogen?",
  shared_household_with_child: "Lebt das Kind im gemeinsamen Haushalt?",
};

export function factLabel(key: string) {
  return FACT_LABELS[key] ?? (/\s/.test(key) ? key : "Weitere Angabe nötig");
}
