import { cache } from "react";
import { api } from "./api";
import type { Person, Session } from "./types";

/** Current session (actor, subject, effective scopes) — deduped per request. */
export const getMe = cache(async () => api<Session>("/api/identity/me"));
export const getRepresented = cache(async () => api<Person[]>("/api/identity/represented"));
