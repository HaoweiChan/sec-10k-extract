---
id: DRAFT-97
title: >-
  `ui-exclusion-note` cannot tell "correctly hidden until exclusion is on" from
  "never shown at all"
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-114
  - '`tasks/reviews/pr46-r1.json` finding R3'
  - >-
    evidence and acceptance verbatim; `src/repo_hygiene/eval_adapter.py`
    (`check_exclusion_note`); the case's own `ceiling` field
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`ui-exclusion-note` cannot tell "correctly hidden until exclusion is on" from "never shown at all"** (added 2026-08-24, Origin: PR #46 R3) — the check reads only that `#bp-note` exists, carries the `hidden` attribute, has the pinned `$("#bp-note").hidden = …` assignment and the must_say/must_not_say wording. Appending `#bp-note{display:none}` to the stylesheet block in `index.html` leaves `python3 -m evals.run --suite invariant` at **55/55 with `ui-exclusion-note` PASS**; only the browser walk catches it (4 failures, "the exclusion note stays off screen with exclusion ON"). This is the same pin-mechanism hole PR #27 R12 recorded for the `exclude-bp` checkbox, now reproduced on the note — and the case's own `ceiling` field states it, so it is disclosed, not hidden

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
