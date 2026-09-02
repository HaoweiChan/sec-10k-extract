---
id: DRAFT-63
title: ADR-029 §i1's four table-shape figures are prose with no runnable pin
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-80
  - >-
    `specs/decisions/ADR-029-structured-tables-annotation.md` §i1 (the four
    table rows and the per-figure method bullets under them);
    `src/sec10k/normalize.py:271`
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**ADR-029 §i1's four table-shape figures are prose with no runnable pin** (added 2026-08-23, Origin: PR #37 R10) — the four rows added by the S2-close amendment (constant `colspan`-weighted row width 3,733 of 3,902; canonical width ≤ 1 = 693; single-row 1,018; modal canonical width 2 on 1,595) are published figures no case asserts. They are also the only figures in the ADR that the shipped API cannot return: `normalize.py:271` drops the 50 all-empty tables before they reach the envelope, so re-deriving them needs the recorder with that filter lifted. PR #37 round 2 found the published *method* for two of them did not reproduce them (following it gave 3,902 and 2,011); the method was corrected, but nothing stops the same drift recurring, and this repo has been bitten by stale figures in documents of record before (PR #31 R14, the T3 `normalized_chars` row). **Not a present defect**: all four were re-derived at `fab439f` and again at this commit, by two independent routes that agree

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
