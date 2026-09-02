---
id: DRAFT-57
title: 'Three LOW findings from PR #35 round 1, all inside text L1 wrote'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-74
  - '`tasks/reviews/pr35-r1.json` R3/R4/R5'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Three LOW findings from PR #35 round 1, all inside text L1 wrote** (added 2026-08-23, Origin: PR #35 R3/R4/R5) — verbatim from the reviewer: (a) **R3** *The L1 Status cell's row inventory mislabels line 112 as the `src/sec10k/boilerplate.py` comment row; that row is 113, which the same cell files under class C.* (b) **R4** *Row 109's closure note and Where cell cite 'ADR-027 §c:162' for the sandston/fy2021 pair, but this PR's own §b insertion moved that table line to :165 (:162 is now the table header).* (c) **R5** *The pr33-r1-resolution.json edit is not literally additions-only in `git diff` (the shared_state line is re-emitted with a trailing comma), though the JSON content diff is exactly one added key.*

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
