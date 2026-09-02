---
id: DRAFT-108
title: >-
  The D5 walk publishes a delta of two ROUNDED numbers, so it moves when the
  geometry does not
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-125
  - >-
    `tasks/reviews/pr46-r3-resolution.json` `merge_with_main_2`;
    `tasks/reviews/d5_browser_walk.py` (`measure()` rounds before differencing)
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The D5 walk publishes a delta of two ROUNDED numbers, so it moves when the geometry does not** (added 2026-08-24, Origin: D5 merge 2) — `d5_browser_walk.py` reports `round(source.top) - round(pane.top)`. The S10 merge shifted the whole shell down 58px (h1 22px to 40px, header padding 16/16 to 22/26, main padding 16 to 24) and the published 768 delta moved **651 to 650** while the real gap did not move at all: measured unrounded it is **650.390625px at BOTH 900 and 768**, one constant, the same value the pre-S10 tree had, because nothing below `main`'s top edge changed. 900 rounds to 776/1427 giving 651; 768 rounds to 1494/2144 giving 650. No threshold is crossed — 768 is a stacking width where `panes_same_row` is false by design and `ROW_TOLERANCE` is 4px — and the note-on figure at 768 was already 650 in the pre-merge artifact

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
