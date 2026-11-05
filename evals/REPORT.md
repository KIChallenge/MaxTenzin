# Agent eval report

Generated 2026-11-05T17:23:52 · mode **live** · model `gpt-5-4-mini` · **1/1 passed** · 1 turns · latency per LLM turn (n=1) p50 15.7s, p90 15.7s, max 15.7s · boundary turns answer in < 0.2s without LLM

Run: `make eval` (live if `AZURE_API_KEY` is set, else scripted fake mode). Assertions are behavioural: tool sequence, boundary, scope handling, sources named, every € amount traceable to a deterministic service.

| Suite | Case | Result | Mode per turn | Tools called | Latency/turn (s) | Notes |
|---|---|---|---|---|---|---|
| language | english_hero | ✅ | live | analyze_document → check_benefits | 15.7 |  |
