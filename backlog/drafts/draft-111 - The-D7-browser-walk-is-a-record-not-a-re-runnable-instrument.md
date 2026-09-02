---
id: DRAFT-111
title: 'The D7 browser walk is a record, not a re-runnable instrument'
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-128
  - '`tasks/reviews/d7-browser-walk.json` `method.why_not_a_script`'
  - which states this in the artifact itself
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The D7 browser walk is a record, not a re-runnable instrument** (added 2026-08-26, Origin: D7) — D5's evidence is `tasks/reviews/d5_browser_walk.py`, a script with a non-zero exit code, so its claims can be re-measured against any later tree; D7's is `tasks/reviews/d7-browser-walk.json`, measurements taken by hand through the in-app browser tools. The numbers are the same shape (rect, `checkVisibility`, viewport intersection, text) but nothing re-checks them after a later commit

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
