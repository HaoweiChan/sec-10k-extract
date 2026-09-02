---
id: DRAFT-119
title: '`intc-2025` is satisfiable by repairing 4 of its 23 items'
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-136
  - '`evals/heldout/intc-2025-heldout.json` declination (f)'
  - which states the hole and the reason it is not closed
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`intc-2025` is satisfiable by repairing 4 of its 23 items** (added 2026-08-26, Origin: D6 / PR #52 R7) — floors and anchors sit only on items 1, 1A, 7 and 8, so a slow path that repairs exactly those and leaves the other 19 as 20-to-226-char cross-reference-index stubs at `extracted`/0.95 clears the exam. Item **9A** is the concrete gap: its index row is a lone contiguous "Page 109" outside every other item's range, so it is as floorable from the index alone as 1A's 37-51 is

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
