---
id: DRAFT-99
title: >-
  D5's render evidence was collected at one viewport height, and the note costs
  111px of it
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-116
  - '`tasks/reviews/pr46-r1.json` finding R5'
  - evidence and acceptance verbatim
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**D5's render evidence was collected at one viewport height, and the note costs 111px of it** (added 2026-08-24, Origin: PR #46 R5) — every measurement in `tasks/reviews/d5-browser-walk.json` was taken at height **860**, while D5's own acceptance names **1024x768**. At 1024x768 with the note on, `#pane`/`#source` top = 693 against `innerHeight` 768, so **75px of a 568px pane** is above the fold before scrolling (186px with the note off; at height 860 the same ratio is 167/636). Separately, commit `1008232`'s headline quotes 1024 pane tops as 582 without saying that is the exclusion-OFF number — the exclusion-ON number at the same width is 693, and the walk records both

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
