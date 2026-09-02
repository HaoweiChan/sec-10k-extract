---
id: DRAFT-100
title: The D5 browser walk cannot see a pane that is rendered but not on screen
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-117
  - '`tasks/reviews/pr46-r2.json` finding R6'
  - >-
    evidence and acceptance verbatim; `tasks/reviews/d5_browser_walk.py`
    (`vis()`
  - and the only per-width visibility assertion)
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The D5 browser walk cannot see a pane that is rendered but not on screen** (added 2026-08-24, Origin: PR #46 R6) — `d5_browser_walk.py`'s `vis()` uses `Element.checkVisibility(...)`, which answers *rendered*, not *on screen*; nothing compares a pane rect against the viewport. Reproduced live at `d2faf12`: with `@media(min-width:1001px) and (max-width:1100px){#source{position:relative;left:-9999px}}` the walk records at 1024 `source: top 582, left -9375, width 349, height 636, visible true, has_offset_parent true` while `#pane` sits at left 261 — the compare pane's right edge is at x=-9026, nothing of it on screen — and still reports `panes_visible true`, `panes_same_row true`, `failures []`, exit 0. `clip-path:inset(100%)` on `#source` is likewise fully green. This is PR #46 R2's shape one mechanism over: R2 closed the *rendered* hole, this is the *on-screen* hole behind it

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
