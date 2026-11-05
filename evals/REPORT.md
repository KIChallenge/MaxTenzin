# Agent eval report

Generated 2026-11-05T16:58:31 · mode **live** · model `gpt-5-4-mini` · **3/3 passed** · 4 turns · latency per LLM turn (n=4) p50 3.9s, p90 4.3s, max 4.3s · boundary turns answer in < 0.2s without LLM

Run: `make eval` (live if `AZURE_API_KEY` is set, else scripted fake mode). Assertions are behavioural: tool sequence, boundary, scope handling, sources named, every € amount traceable to a deterministic service.

| Suite | Case | Result | Mode per turn | Tools called | Latency/turn (s) | Notes |
|---|---|---|---|---|---|---|
| scenario | familie_darmkrebs | ✅ | live | get_prevention | 3.9 |  |
| scenario | gesundheit_stefan | ✅ | live | match_bundle | 3.5 |  |
| scenario | prevention_stefan | ✅ | live, live | import_vaccination_record → find_office | 3.6, 4.3 |  |
