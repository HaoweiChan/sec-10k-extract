---
id: DRAFT-114
title: 'The `it.confidence` scan considers only the nearest preceding `${`'
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-131
  - >-
    `tasks/reviews/pr53-r3.json` finding R11; `src/repo_hygiene/eval_adapter.py`
    `check_confidence_honesty`
  - the `opened = live.rfind` line and its `ceiling` bullet 1
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The `it.confidence` scan considers only the nearest preceding `${`** (added 2026-08-26, Origin: PR #53 R11) — `eval_adapter.py`'s widened scan does `opened = live.rfind("${", 0, m.start())` and then drops the mention if that interpolation closed early, so a mention inside an enclosing interpolation that contains an earlier NESTED `${...}` is skipped entirely. A badge spelled a badge whose confidence interpolation opens with a nested `${…}` (a ternary that tests the warnings list and falls through to `it.confidence` on the else branch) renders a bare number on the else branch and stays green. The brace walk is also not string- or regex-aware, a ceiling `_js_block`'s docstring states for its own equivalent and this one does not

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
