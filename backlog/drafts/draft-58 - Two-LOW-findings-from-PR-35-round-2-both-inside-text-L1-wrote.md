---
id: DRAFT-58
title: 'Two LOW findings from PR #35 round 2, both inside text L1 wrote'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-75
  - '`tasks/reviews/pr35-r2.json` R7/R8'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Two LOW findings from PR #35 round 2, both inside text L1 wrote** (added 2026-08-23, Origin: PR #35 R7/R8) — verbatim from the reviewer: (a) **R7** *Row 63's closure note cites the reworded ADR-020 table row as 'ADR-020:141', but the same commit's header edit (2 → 3 lines at :15-17) moved that row to :142; :141 is the heading-unnumbered row.* (b) **R8** *README.md:198-200's new coverage sentence says all decimals in the window 'are checked', but check_docs also skips decimals adjacent to $/%/× and every (file, fixture, value) in DOC_ALLOW, and bounds the window at the next backticked fixture name — the sentence is narrower than 'anywhere in this repo' but still slightly wider than the instrument.*

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
