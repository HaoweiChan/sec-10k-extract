---
id: DRAFT-112
title: >-
  `expected_item_missing` is an item-targeted warning the panel qualifier never
  names
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-129
  - '`tasks/reviews/pr53-r1.json` finding R6'
  - >-
    evidence and acceptance verbatim (three line refs re-verified and moved by
    D8/PR #57
  - 'which inserted above all of them: extract.py 208->212 and 229-237->242-257'
  - >-
    validate.py 301-303->387-389; the quoted code is unchanged); the exclusion
    is stated in `check_confidence_honesty`'s docstring and in
    `ui-confidence-honesty`'s `note`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`expected_item_missing` is an item-targeted warning the panel qualifier never names** (added 2026-08-26, Origin: PR #53 R6) — `src/sec10k/extract.py:212` emits `{"code": "expected_item_missing", "item": i["item"], …}`, so by the letter of D7's Contents sentence ("any item-targeted warnings beside the per-item number") it belongs in the badge. `src/sec10k/validate.py:387-389` strips it from `ev["warnings"]` per ADR-018, and `index.html`'s `itemQual` reads `it.evidence.warnings`, so a `missing` item's own warning never appears beside its `conf 0.4` while the warnings card below the banner does list it with an `item` hint. Mitigating, and the reason this is not a defect: any warning at all forces `doc_status` off `success` (`extract.py:242-257`), so `docQual()` always fires and the number is never bare; the `missing` status badge already states the same fact the warning would repeat

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
