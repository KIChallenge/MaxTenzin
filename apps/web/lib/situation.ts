import type { components } from "./api-types";

type S = components["schemas"];
export type SituationOverview = S["SituationOverview"];
export type Episode = S["Episode"];
export type EpisodeType = S["EpisodeType"];
export type Effect = S["Effect"];

export const EPISODE_TYPE: Record<EpisodeType, string> = {
  hospital: "Krankenhaus",
  rehab_inpatient: "Reha (stationär)",
  rehab_outpatient: "Reha (ambulant)",
  therapy: "Laufende Therapie",
  home_care: "Zu Hause mit Unterstützung",
  nursing_home: "Pflegeheim",
  sick_leave: "Krankenstand",
  cure: "Kur",
};
export const THERAPY_SUBTYPES = ["Strahlentherapie", "Chemotherapie", "Immuntherapie", "Physiotherapie", "Dialyse"];

const d = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString("de-AT", { day: "numeric", month: "numeric", year: "numeric" }) : "";

/** "seit 29.10.2026" · "16.11.–7.12.2026" · "ab 16.11.2026, ca. 3 Wochen" – dates as the person entered them. */
const estimate = (s: string) => (/^(ca\.|bis|etwa|voraussichtlich)/i.test(s) ? s : `voraussichtlich bis ${s}`);

export function episodeWhen(e: Episode) {
  if (!e.start && !e.end && !e.end_estimate_de)
    return e.status === "suggested" ? "Zeitraum noch offen" : e.status === "planned" ? "geplant, Termin noch offen" : "aktuell";
  const end = e.end ? d(e.end) : e.end_estimate_de ? estimate(e.end_estimate_de) : "";
  if (e.status === "ended" || (e.end && new Date(e.end) < new Date() && e.status !== "planned")) {
    return e.start ? `${d(e.start)} – ${end || "beendet"}` : `bis ${end || "?"}`;
  }
  if (e.status === "planned") return [e.start ? `ab ${d(e.start)}` : "geplant", end && (e.end ? `bis ${end}` : end)].filter(Boolean).join(", ");
  return [e.start ? `seit ${d(e.start)}` : e.end || e.end_estimate_de ? "" : "aktuell", end && (e.end ? `bis ${end}` : end)].filter(Boolean).join(", ");
}
