---
id: DRAFT-52
title: Nested tables are exercised only by a synthetic self-check
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-69
  - 'ADR-029 §e; `src/sec10k/tables.py::_demo`'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Nested tables are exercised only by a synthetic self-check** (added 2026-08-23, Origin: S7) — the recorder handles a `<table>` inside a `<td>` (inner record, spans nest, sorted by start) and `tables.py::_demo` pins it, but zero of the 16 HTML fixtures surveyed contain one, so no eval case can go red on a real nested table

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
