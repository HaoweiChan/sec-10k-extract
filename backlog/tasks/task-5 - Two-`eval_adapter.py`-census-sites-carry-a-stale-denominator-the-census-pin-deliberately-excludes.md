---
id: TASK-5
title: >-
  Two `eval_adapter.py` census sites carry a stale denominator the census pin
  deliberately excludes
status: To Do
assignee: []
created_date: '2026-09-02 17:45'
labels: []
dependencies: []
references:
  - TODO.md TD-164
  - >-
    `tasks/reviews/pr61-r4.json` R24; `src/repo_hygiene/eval_adapter.py` (the
    `18 of 43 dev documents` sites and the exclusion note)
priority: low
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R21's census pin excludes `eval_adapter.py` on the ground that its numerator cannot be checked — but the pin is **denominators only** by explicit design, so no pinned site's numerator is checked either. Meanwhile the excluded lines publish "18 of 43 dev documents" while the live sweep measures the dev corpus at 44. 43 is the pre-burn corpus: the same one-off rot R21 was filed against.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
