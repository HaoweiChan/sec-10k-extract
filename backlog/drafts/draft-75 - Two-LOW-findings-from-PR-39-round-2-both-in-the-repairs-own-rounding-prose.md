---
id: DRAFT-75
title: 'Two LOW findings from PR #39 round 2, both in the repair''s own rounding prose'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-92
  - '`tasks/reviews/pr39-r2.json`'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Two LOW findings from PR #39 round 2, both in the repair's own rounding prose** (added 2026-08-23, Origin: PR #39 R4/R5) — (a) **R4** the round-1 repair relabels v4's warm-up value 1.031 as 'a rounding slip' and publishes 1.032, but 1.031 is the correct 3-place rounding of the measured ko-1997 ratio (0.0131 / 0.0127 = 1.03149…); 1.032 arises only by double-rounding the stored 4-place field 1.0315 (float 1.03150000000000008) — the run-order correction stands, the relabel does not (report §3.2, ADR-021 §d1, the PR #39 R2/R3 debt row, the resolution artifact); (b) **R5** report §3.2's '~20–28 MiB accrues' over the seven clean-tree runs reads 20.5–28.9 MiB when all seven are differenced (corpus peak minus largest-only: 28.9, 28.5, 24.9, 20.5, 23.9, 23.0, 28.2); the hand-check listed four of seven — within the tilde and 2-sig-fig rounding

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
