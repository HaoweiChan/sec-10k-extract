---
id: DRAFT-29
title: >-
  R7: `_margin_centers` does not recognize the
  `margin-inline-start`/`margin-inline-end` longhand form
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-31
  - '`tasks/reviews/pr21-r2.json` finding R7'
  - evidence and acceptance verbatim
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**R7: `_margin_centers` does not recognize the `margin-inline-start`/`margin-inline-end` longhand form** (added 2026-08-21, Origin: PR #21 R7) — `check_layout_centering`'s helper (src/repo_hygiene/eval_adapter.py) regex-matches literal `margin-inline\s*:` and `margin\s*:` only, so `margin-inline-start:auto;margin-inline-end:auto` — a legitimate way to write the same centring rule — returns False and would be wrongly flagged as not centring

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
