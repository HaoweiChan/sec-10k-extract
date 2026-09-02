---
id: DRAFT-28
title: >-
  R6: the capabilities content check is defeated by distinct-but-meaningless
  filler
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-30
  - '`tasks/reviews/pr21-r2.json` finding R6'
  - evidence and acceptance verbatim
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**R6: the capabilities content check is defeated by distinct-but-meaningless filler** (added 2026-08-21, Origin: PR #21 R6) — `check_capabilities_parse` (src/repo_hygiene/eval_adapter.py) only checks within-row/within-item distinctness and a per-cell minimum length, never cross-row duplication or a real content signal, so a README mutation using 9 rows whose three cells read `Alpha row`, `Sample A1`, `Passes fine` (and so on down the rows) and 3 items reading `**Some Term N.** This is a plausible looking filler sentence padded out` returns `passed: True`. **Not blocking**: the acceptance bar (R1) was that a README edit which EMPTIES the panel turns red, and that still holds — defeating the check requires hand-authored, distinct, sufficiently long filler, not a realistic accidental regression

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
