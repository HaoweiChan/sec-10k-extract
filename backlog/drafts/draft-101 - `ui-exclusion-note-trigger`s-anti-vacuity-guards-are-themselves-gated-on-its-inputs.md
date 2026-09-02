---
id: DRAFT-101
title: >-
  `ui-exclusion-note-trigger`'s anti-vacuity guards are themselves gated on its
  inputs
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-118
  - '`tasks/reviews/pr46-r2.json` finding R8'
  - evidence and acceptance verbatim
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`ui-exclusion-note-trigger`'s anti-vacuity guards are themselves gated on its inputs** (added 2026-08-24, Origin: PR #46 R8) — all three guards sit inside `if inp.get("fixtures"):` in `check_exclusion_note_trigger`, so setting the case's `input.fixtures` to `{}` leaves `[PASS] ui-exclusion-note-trigger` and invariant **56/56** with only the `wire` pin still running — while the case's own provenance says it refuses to pass vacuously. Only-True and only-False fixture sets DO go red, so the guards work whenever any fixture is present

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
