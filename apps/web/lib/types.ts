import type { components } from "./api-types";

type S = components["schemas"];
export type Person = S["Person"];
export type Session = S["Session"];
export type Scope = S["Scope"];
export type Delegation = S["Delegation"];
export type SourceRef = S["SourceRef"];
export type DocumentSummary = S["DocumentSummary"];
export type DocumentAnalysis = S["DocumentAnalysis"];
export type Recommendation = S["Recommendation"];
export type Benefit = S["Benefit"];
export type EligibilityResult = S["EligibilityResult"];
export type EligibilityStatus = S["EligibilityStatus"];
export type FormDefinition = S["FormDefinition"];
export type FormField = S["FormField"];
export type FormSession = S["FormSession"];
export type FieldValue = S["FieldValue"];
export type Case = S["Case"];
export type CaseStep = S["CaseStep"];
export type StepStatus = S["StepStatus"];
export type Notification = S["Notification"];
export type PreventionOverview = S["PreventionOverview"];
export type PreventionItem = S["PreventionItem"];
export type PreventionStatus = S["PreventionStatus"];
export type AuditEvent = S["AuditEvent"];
export type ChatResponse = S["ChatResponse"];
export type ToolTrace = S["ToolTrace"];
export type Office = S["Office"];
export type Medication = S["Medication"];
export type LegalHit = S["LegalHit"];
export type LegalParagraph = S["LegalParagraph"];

/** Result of an API call: never throws for HTTP errors, so pages can render 403s nicely. */
export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; detail: string };
