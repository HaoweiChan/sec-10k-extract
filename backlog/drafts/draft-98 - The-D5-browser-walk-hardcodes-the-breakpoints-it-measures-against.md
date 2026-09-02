---
id: DRAFT-98
title: The D5 browser walk hardcodes the breakpoints it measures against
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-115
  - '`tasks/reviews/pr46-r1.json` finding R4'
  - evidence and acceptance verbatim
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The D5 browser walk hardcodes the breakpoints it measures against** (added 2026-08-24, Origin: PR #46 R4) — `tasks/reviews/d5_browser_walk.py:30-31` sets `SIDE_BY_SIDE = 1024` and `STACK_AT = 1000` as literals, while `check_split_breakpoint` derives the expected `matchMedia` width from the served CSS. The CSS/JS pair is tied to itself but nothing ties the walk to either: moving BOTH the CSS `@media(max-width:1000px)` and `matchMedia("(max-width:1000px)")` to 900 keeps `ui-split-breakpoint` green (900 < `min_side_by_side` 1024) while the walk then reports a stacking failure at 900 that is not a defect

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
