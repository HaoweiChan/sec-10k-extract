---
id: DRAFT-117
title: D7's declaration-count guard leaves a dead branch with the wrong message
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-134
  - >-
    `tasks/reviews/pr53-r3.json` finding R14; `src/repo_hygiene/eval_adapter.py`
    `check_confidence_honesty`
  - the `seen != 1` guard and the `got_body is None` branch below it
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**D7's declaration-count guard leaves a dead branch with the wrong message** (added 2026-08-26, Origin: PR #53 R14) — `check_confidence_honesty` continues whenever `seen != 1`, and `_js_block` returns None exactly when that same literal occurs zero times, so the `if got_body is None:` branch ("no such function in the live markup — the qualifier has no producer") is unreachable. A renamed or differently-spaced helper now reports "declared 0 times … a second declaration shadows the pinned one at runtime", which describes the opposite of what happened

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
