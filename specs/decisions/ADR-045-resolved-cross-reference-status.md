# ADR-045 — resolved cross-reference content qualifies low coverage

Date: 2026-08-29. Status: accepted. ADR-044 is occupied by unmerged PR #75,
so this decision uses the next available number. Qualifies
[ADR-042](ADR-042-cross-reference-index.md) and the envelope status rule in
`specs/001-sec10k-contract.md`.

**Ruling**: with both `cross_reference_index` and `low_item_coverage`, coverage alone yields `success_with_warning`; other ambiguity codes still escalate, spans stay unmoved, and paid escalation stays suppressed.
**Because**: resolved regions are reliable alternative content, but Intel's overlapping and nested page ranges cannot become `start`/`end` without violating INV-S1; the owner resolved this product-semantic ambiguity.
**Enforced by**: `evals/adversarial/intc-2025-cross-reference-index.json` requires `success_with_warning`, both warnings, and the resolved regions.

---
