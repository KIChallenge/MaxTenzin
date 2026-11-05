# 0006 LLM: Azure AI Foundry, gpt-5-4-mini, fake mode (D6)
**Context:** The challenge provides an Azure AI Foundry endpoint. Tests and offline demos must run without network or key.

**Decision:** One thin client (`app/core/llm.py`, OpenAI v1 API, model `gpt-5-4-mini`), `LLM_MODE=fake|live|auto`. Fake mode returns canned responses; extraction falls back to hand-verified goldens and the agent to a scripted planner with the same tools and guards.

**Consequence:** All 244 API tests run in fake mode. The model is used in four places only (extraction, photo transcription, agent loop, boundary double-check). Live behaviour is measured by `make eval` (34/34).
