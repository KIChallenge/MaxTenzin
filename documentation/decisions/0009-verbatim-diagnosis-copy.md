# 0009 Verbatim copy of documented diagnoses into forms is allowed (D9)
**Context:** PAL 080 asks for "Krankheiten bzw. Beeinträchtigungen". Refusing to touch diagnoses forced relatives to retype them; letting the model summarise them would be interpretation (use case §4 allows administrative help, not medical assessment). An early version looped on refusals.

**Decision:** Documents extract `main_diagnosis` / `secondary_diagnoses` deterministically (regex, verbatim, quote + page). PAL 080 `Leiden` is prefilled unconfirmed from `document.main_diagnosis`. A copy request (copy intent + diagnosis/letter, no interpretation words) is exempt from the input guard, and Lotsi writes the verbatim text deterministically. Explaining or assessing a diagnosis stays blocked.

**Consequence:** The form is almost complete without any medical interpretation; the boundary between copying and interpreting is explicit, deterministic and covered by the `diagnose_uebernehmen` eval.
