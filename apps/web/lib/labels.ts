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
