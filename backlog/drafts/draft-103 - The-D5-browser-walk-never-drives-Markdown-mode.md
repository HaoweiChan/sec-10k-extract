---
id: DRAFT-103
title: The D5 browser walk never drives Markdown mode
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-120
  - >-
    `tasks/reviews/d5_browser_walk.py` (`extract()` never touches `#render-md`);
    `evals/adversarial/ui-exclusion-note.json` pins the sentence STATICALLY
  - which is the same ceiling every D5 pin carries
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The D5 browser walk never drives Markdown mode** (added 2026-08-24, Origin: D5 merge) — every measurement in `tasks/reviews/d5-browser-walk.json` is taken with S9's `render as Markdown` box UNTICKED, including the aapl-2025 no-chrome control. The compare-pane note's wording was narrowed at this merge precisely because the extracted pane gains a second reason to differ in that mode, and the narrowed sentence has no render evidence in the mode it was written for

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
