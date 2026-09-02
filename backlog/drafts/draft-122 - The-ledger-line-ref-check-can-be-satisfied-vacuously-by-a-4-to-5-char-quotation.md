---
id: DRAFT-122
title: >-
  The ledger line-ref check can be satisfied vacuously by a 4-to-5-char
  quotation
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-139
  - '`tasks/reviews/pr52-r3.json` finding R16'
  - evidence and acceptance verbatim
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The ledger line-ref check can be satisfied vacuously by a 4-to-5-char quotation** (added 2026-08-26, Origin: D6 / PR #52 R16) — `n_refs` is incremented before the fragment loop, and the loop skips any normalized piece under 6 chars while the regex accepts a fragment as short as 4. So a ref quoting `"zzzz"` against a line that does not exist counts toward the `min_refs` floor and verifies nothing: the orchestrator confirmed `README.md:9999` with a 4-char quotation returns green and still counts 9 refs. No instance of this shape exists in the tree today

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
