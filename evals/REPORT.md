# Agent eval report

Generated 2026-11-05T14:36:16 · mode **live** · model `gpt-5-4-mini` · **1/1 passed** · 5 turns · latency per LLM turn (n=5) p50 5.2s, p90 6.3s, max 6.3s · boundary turns answer in < 0.2s without LLM

Run: `make eval` (live if `AZURE_API_KEY` is set, else scripted fake mode). Assertions are behavioural: tool sequence, boundary, scope handling, sources named, every € amount traceable to a deterministic service.

| Suite | Case | Result | Mode per turn | Tools called | Latency/turn (s) | Notes |
|---|---|---|---|---|---|---|
| scenario | hero_pflege | ✅ | live, live, live, live, live | analyze_document → check_benefits → check_benefits → get_benefit → start_form → get_next_questions → set_form_fields → render_form | 5.2, 3.9, 6.3, 5.7, 2.6 |  |
