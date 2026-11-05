import type { components } from "./api-types";

type S = components["schemas"];
export type CareTeam = S["CareTeam"];
export type CareTeamMember = S["CareTeamMember"];
export type Provider = S["Provider"];
export type Slot = S["Slot"];
export type Appointment = S["Appointment"];
export type Preferences = S["Preferences"];

/** What people book for (provider topics) – most common first. */
export const TOPICS: [string, string][] = [
  ["hausarzt_kontrolle", "Kontrolle bei der Hausärztin / beim Hausarzt"],
  ["vorsorgeuntersuchung", "Vorsorgeuntersuchung"],
  ["influenza", "Grippeimpfung"],
  ["covid19", "COVID-19-Impfung"],
  ["impfung", "Andere Impfung"],
  ["rezept", "Rezept / Überweisung"],
  ["nachsorge", "Nachsorge"],
  ["onkologie_nachsorge", "Onkologische Nachsorge"],
  ["reha", "Rehabilitation (Beratung)"],
  ["pflegeberatung", "Pflegeberatung"],
  ["pflegegeld", "Pflegegeld (Beratung)"],
  ["mobile_pflege", "Mobile Pflege (FSW)"],
  ["mammografie", "Mammografie"],
  ["darmkrebs_vorsorge", "Darmkrebs-Vorsorge"],
  ["physikalische_medizin", "Physikalische Medizin"],
  ["ernaehrungsberatung", "Ernährungsberatung"],
  ["oegk_kundenservice", "ÖGK-Kundenservice"],
];
export const topicLabel = (t?: string | null) => TOPICS.find(([k]) => k === t)?.[1] ?? "Termin";
