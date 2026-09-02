---
id: DRAFT-102
title: '`boilerplate_applied` inherits the `DISPLAY_MAX` ceiling from `display_text`'
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-119
  - '`tasks/reviews/pr46-r2.json` finding R9'
  - >-
    with a runnable constructed repro; the standing PR #27 R8 debt row names the
    same `DISPLAY_MAX` ceiling for the payload-doubling question
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`boilerplate_applied` inherits the `DISPLAY_MAX` ceiling from `display_text`** (added 2026-08-24, Origin: PR #46 R9) — `view.py` sets `display_text` from a FULL-string comparison (`if body != raw`) and then truncates to `DISPLAY_MAX` 40,000, while the pane renders `it.display_text ?? it.text`, also capped at 40,000. An item whose only chrome lies beyond character 40,000 therefore yields a `display_text` byte-identical to the shown `text`, `boilerplate_applied` True, and the D5 note firing over a pane in which nothing visibly changed — the exact residue R1 was repaired to remove, arriving by a second route. **Not observed**: all 42 committed fixtures were run and every one with `display_text` had `identical_shown = 0`, so this is constructible, not live, and `ui-exclusion-note-trigger` would not catch it

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
