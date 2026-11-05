# 0007 Statute-only amounts are cited from the paragraph (D7)
**Context:** Some parameters exist only in a statute or guideline, not in veraendW: Fahrtkosten in Satzung ÖGK 2025 § 46, the 2 % Rezeptgebühren-Obergrenze in RRZ § 13 Abs. 1a.

**Decision:** Such values are cited from that paragraph via the `legal` service (label + in-force date). veraendW stays primary wherever a table exists.

**Consequence:** Every amount still has a citable source; the eligibility engine adds rule-based amounts with their law `SourceRef`. Amounts without any source in the corpus (e.g. Ersatzpflege) are not shown.
