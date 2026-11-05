# 0008 Clinical instructions to physicians are never relisted (D8)
**Context:** Discharge letters contain instructions addressed to physicians (lab controls, blood pressure, medication, side effects, fluid balance). Even quoted verbatim, relisting them to a relative reads like medical advice.

**Decision:** After extraction a deterministic CLINICAL filter in `documents/extract.py` removes such items and adds a neutral notice; imaging reports and vaccination records never yield recommendations at all.

**Consequence:** Only administrative and organisational recommendations reach the person (e.g. Kontrolltermin, Pflegegeld, Reha). The filter is keyword-based and tested; it errs on the side of dropping.
