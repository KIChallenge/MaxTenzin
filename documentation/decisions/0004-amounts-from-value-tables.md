# 0004 Amounts only from veraendW value tables (D4)
**Context:** Law texts in the corpus can be outdated: § 5 BPGG still shows the 2020 Pflegegeld amounts (Stufe 1: 157,30 €). A language model answering from memory would repeat such numbers.

**Decision:** Every amount comes from the `values` service (veraendW 2026, table + year as `SourceRef`) whenever a table exists. The agent's output guard rejects any € amount that does not occur in this turn's tool data.

**Consequence:** Pflegegeld Stufe 1 is shown as 206,20 € (veraendW Tab. 54, 2026) with source. Amounts without a value table are cited from the statute (ADR 0007).
