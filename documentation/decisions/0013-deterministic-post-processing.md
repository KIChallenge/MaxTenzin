# 0013 Deterministic post-processing of agent replies
**Context:** Live evals showed failure modes a prompt cannot reliably prevent: claiming a field was entered when it was not, stating consent was given, guessing why a value was rejected, leaking session UUIDs or tool names.

**Decision:** After the model and the output guard, `orchestrator.py` rewrites the reply deterministically from tool results: an "Eingetragen im Antrag: <Label> = <Wert>" block from successful `set_form_fields`; open consent checkboxes listed as "bitte selbst ankreuzen" and model consent claims removed; 422 messages relayed verbatim; 403 explained; sources appended if none named; internal ids and tool names stripped; UI actions (download PDF, open form/case/appointments, .ics) derived from tool outcomes only.

**Consequence:** What the reply says about state changes always matches what actually happened. The model still writes the explanatory text; facts about actions come from code.
