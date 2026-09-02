---
id: DRAFT-53
title: txt-era `<TABLE>`/`<S>`/`<C>` SGML tables are not structured
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-70
  - ADR-029 §e; `src/sec10k/normalize.normalize` docstring
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**txt-era `<TABLE>`/`<S>`/`<C>` SGML tables are not structured** (added 2026-08-23, Origin: S7) — `normalize(..., tables=True)` answers `[]` for the txt era (ge-1994 77 `<TABLE>`, ibm-1997 73; textron-2001 0); their columns are fixed-width runs of spaces, untagged, and the `<S>`/`<C>` markers are already `edgar_chrome` lines under ADR-026

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
