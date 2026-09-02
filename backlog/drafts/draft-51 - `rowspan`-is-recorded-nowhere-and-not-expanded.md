---
id: DRAFT-51
title: '`rowspan` is recorded nowhere and not expanded'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-68
  - ADR-029 §e; `src/sec10k/tables.grid` docstring
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`rowspan` is recorded nowhere and not expanded** (added 2026-08-23, Origin: S7) — a `rowspan=n` cell appears once, in the row it is written in; the n-1 rows below are one cell short in the grid and the Markdown, so columns to its right shift left in those rows. 12 such cells in aapl-2025, 180 in jpm-2024, 8 in nvda-2024, 1 in cat-2023 (raw counts, 2026-08-23)

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
