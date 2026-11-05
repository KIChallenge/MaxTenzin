# Architecture

## Principle
Defined processes first, AI as top layer. Every decision with consequences (eligibility, amounts, prevention status, form content)
is made by a deterministic, tested, source-citing service. The LLM understands, routes, extracts and explains.

## Request path
1. Person logs in (mock ID Austria) → token `demo-<persona>`. Selecting "handelt für" sets `X-Subject-Id`.
2. `app/core/auth.py` resolves actor, subject and effective scopes (self = all, otherwise from delegation).
3. Each route declares its scope via `require(Scope.x)`. Missing scope → 403, recorded in audit with `allowed=false`.
4. Services read committed knowledge (`app/core/knowledge.py`) and cite sources via `ctx.cite()`.
5. `AuditMiddleware` writes one row per call: actor, subject, via (ui/agent), agent tool, scope, status, sources, rule ids.
6. The agent is a client like the UI: it calls the HTTP API with the user's token plus `X-Via: agent`, `X-Agent-Tool`.

## Trust boundaries
- LLM output never reaches the user unchecked for facts: document quotes are verified against page text; benefits/amounts only
  from service responses; medical boundary guard before and after generation.
- Raw data (`docs/`) never at runtime; only committed, hashed extracts.

## Why a modular monolith
Same service boundaries and contracts as microservices (router + contract + store collection per service), but one process.
Splitting is a deployment decision on the roadmap, not a rewrite.
