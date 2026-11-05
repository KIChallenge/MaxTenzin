import type { EligibilityStatus, PreventionStatus, Scope, StepStatus } from "./types";

export const SCOPE_LABELS: Record<Scope, string> = {
  read_documents: "Dokumente lesen",
  prepare_applications: "Anträge vorbereiten",
  manage_appointments: "Termine verwalten",
  view_health_prevention: "Vorsorge & Impfungen",
  manage_case: "Fall verwalten",
  manage_situation: "Lebenslage",
};
export const ALL_SCOPES = Object.keys(SCOPE_LABELS) as Scope[];

export const ELIGIBILITY: Record<EligibilityStatus, { label: string; tone: Tone }> = {
  likely: { label: "Voraussichtlich Anspruch", tone: "ok" },
  possible: { label: "Möglicherweise Anspruch", tone: "warn" },
  needs_info: { label: "Angaben fehlen noch", tone: "info" },
  not_applicable: { label: "Trifft nicht zu", tone: "neutral" },
};

export const STEP_STATUS: Record<StepStatus, { label: string; tone: Tone }> = {
  open: { label: "Offen", tone: "neutral" },
  in_progress: { label: "In Arbeit", tone: "info" },
  done: { label: "Erledigt", tone: "ok" },
  blocked: { label: "Blockiert", tone: "danger" },
};

export const PREVENTION_STATUS: Record<PreventionStatus, { label: string; tone: Tone }> = {
  due: { label: "laut Impfplan empfohlen", tone: "warn" },
  upcoming: { label: "demnächst", tone: "info" },
  up_to_date: { label: "dokumentiert", tone: "ok" },
  not_documented: { label: "nicht im e-Impfpass dokumentiert", tone: "neutral" },
};

export const REC_CATEGORY: Record<string, string> = {
  rehabilitation: "Rehabilitation",
  care: "Pflege & Betreuung",
  follow_up: "Nachsorge",
  transport: "Transport",
  costs: "Kosten",
  aids: "Hilfsmittel",
  nutrition: "Ernährung",
  other: "Sonstiges",
};

export const DOC_TYPE: Record<string, string> = {
  discharge_letter: "Entlassungsbrief",
  imaging_report: "Bildgebungsbefund",
  vaccination_record: "e-Impfpass",
  other: "Dokument",
};

export type Tone = "ok" | "warn" | "info" | "neutral" | "danger";

export function fullName(p?: { first_name: string; last_name: string } | null) {
  return p ? `${p.first_name} ${p.last_name}` : "";
}

export function fmtDate(iso?: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("de-AT", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function fmtDateTime(iso?: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("de-AT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function fmtAmount(value: number, unit: string) {
  if (unit === "EUR") return value.toLocaleString("de-AT", { style: "currency", currency: "EUR" });
  return `${value.toLocaleString("de-AT")} ${unit}`;
}

/** API links (service names, English) → cockpit routes (German). Unknown links pass through unchanged. */
const ROUTES: Record<string, string> = {
  "/case": "/fall",
  "/lebenslage": "/#lebenslage",
  "/situation": "/#lebenslage",
  "/cases": "/fall",
  "/prevention": "/vorsorge",
  "/benefits": "/leistungen",
  "/documents": "/dokumente",
  "/forms": "/leistungen",
  "/audit": "/transparenz",
  "/directory": "/stellen",
  "/medications": "/medikamente",
  "/legal": "/recht",
};
export function cockpitRoute(link: string) {
  const [path, rest = ""] = link.split(/(?=[?#])/);
  if (/^\/forms\/[^/]+$/.test(path)) return link;
  return (ROUTES[path] ?? path) + rest;
}

/** Lotsi's tools (app/agent/tools.py) in plain German – the technical name stays visible as tooltip. */
export const TOOL_LABELS: Record<string, string> = {
  list_documents: "Dokumente auflisten",
  analyze_document: "Dokument lesen",
  check_benefits: "Leistungen prüfen",
  get_benefit: "Leistung nachschlagen",
  start_form: "Antrag beginnen",
  change_permissions: "Vollmacht ändern",
  get_next_questions: "Offene Angaben abfragen",
  set_form_fields: "Antrag ausfüllen",
  preview_form: "Antrag prüfen",
  render_form: "PDF-Entwurf erstellen",
  list_cases: "Fall ansehen",
  create_case: "Fall anlegen",
  update_case_step: "Fall-Schritt ändern",
  get_prevention: "Vorsorge abfragen",
  import_vaccination_record: "e-Impfpass übernehmen",
  find_office: "Zuständige Stelle suchen",
  get_situation: "Lebenslage abfragen",
  add_episode: "Lebenslage eintragen",
  update_episode: "Lebenslage ändern",
  suggest_situation_from_document: "Lebenslage aus Dokument vorschlagen",
  confirm_situation_suggestion: "Lebenslage-Vorschlag übernehmen",
  match_bundle: "Passende Hilfen bündeln",
  get_care_team: "Behandlungsteam abfragen",
  set_care_team: "Behandlungsteam ändern",
  search_slots: "Termine suchen",
  book_appointment: "Termin buchen",
  list_appointments: "Termine ansehen",
  cancel_appointment: "Termin absagen",
  search_medication: "Medikament nachschlagen",
  search_law: "Gesetz nachschlagen",
  get_value: "Betrag nachschlagen",
  "context:save_facts": "Angaben merken",
};
export const toolLabel = (t?: string | null) => (t ? (TOOL_LABELS[t] ?? t) : "");
