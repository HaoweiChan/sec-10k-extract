---
id: DRAFT-137
title: >-
  `cvx-2015-internal-pointer.json` asserts a capability outcome on the two items
  D13 rules `correct`
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-156
  - ADR-038 §e1; `evals/adversarial/cvx-2015-internal-pointer.json`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`cvx-2015-internal-pointer.json` asserts a capability outcome on the two items D13 rules `correct`** (added 2026-08-27, Origin: D13) — the case's whole debt is two `min_chars` checks (items 7 and 8, floor 5,000), i.e. that the real MD&A and financial-statement text ends up inside those spans. [ADR-038](../specs/decisions/ADR-038-internal-pointer-adjudication.md) rules items 7 and 8 **`correct`** — ADR-035's `item_span_near_empty` already carries them at 0.80 with `review_required: true` — and rules items 2, 6 and 7A `defect` on a property the case asserts nothing about. So the older case's red now means "we would like internal-pointer resolution", not "this is broken", while the adjudicated defect is carried by the new `evals/adversarial/cvx-2015-silent-pointer-items.json`. Both are `debt` and both are red; nothing is failing that should not be

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
