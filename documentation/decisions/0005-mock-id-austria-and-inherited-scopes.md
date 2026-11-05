# 0005 Mock ID Austria with delegations; the AI inherits the user's scopes (D5)
**Context:** Use case 1 needs representation (a daughter acting for her mother) with fine-grained permissions, and the AI must not become a privileged super-user. Real ID Austria / e-Vollmacht is not available in 24 h.

**Decision:** Stateless demo token `demo-<persona>` identifies the actor; `X-Subject-Id` selects the person acted for. Effective scopes = all for oneself, else the delegation's scopes (6 scopes). Every route declares `require(Scope…)`. The agent calls the API with the user's own token plus `X-Via: agent`.

**Consequence:** A revoked scope blocks the cockpit and Lotsi identically (403, audited, explained). Replacing the mock with real ID Austria changes only token validation and the delegation source (roadmap).
