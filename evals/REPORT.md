# Agent eval report

Generated 2026-11-05T14:39:23 · mode **live** · model `gpt-5-4-mini` · **2/2 passed** · 7 turns · latency per LLM turn (n=6) p50 3.9s, p90 6.4s, max 6.4s · boundary turns answer in < 0.2s without LLM

Run: `make eval` (live if `AZURE_API_KEY` is set, else scripted fake mode). Assertions are behavioural: tool sequence, boundary, scope handling, sources named, every € amount traceable to a deterministic service.

| Suite | Case | Result | Mode per turn | Tools called | Latency/turn (s) | Notes |
|---|---|---|---|---|---|---|
| scenario | boundary_roentgen | ✅ | boundary:diagnosis, live | analyze_document | 0.1, 3.2 |  |
| scenario | hero_pflege | ✅ | live, live, live, live, live | analyze_document → check_benefits → check_benefits → get_benefit → start_form → get_next_questions → set_form_fields → render_form | 5.1, 3.4, 6.4, 3.9, 3.4 |  |
