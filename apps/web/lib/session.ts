export const API_URL = process.env.API_URL ?? "http://localhost:8000";
export const COOKIE_TOKEN = "lotse_token";
export const COOKIE_SUBJECT = "lotse_subject";
export const COOKIE_PLAIN = "lotse_plain";
export const COOKIE_TEXT = "lotse_text";
/** Answers to eligibility questions, per represented person (until the API stores them). */
export const factsCookie = (subjectId: string) => `lotse_facts_${subjectId.replace(/[^a-z0-9_-]/gi, "")}`;
