---
id: DRAFT-26
title: '`check_button_specificity` misses descendant-scoped hover rules'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-28
  - >-
    `evals/adversarial/ui-contrast-and-specificity.json` (`triage` note);
    `tasks/reviews/pr18-r2.json` R17
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`check_button_specificity` misses descendant-scoped hover rules** (added 2026-08-21, Origin: PR #18 R17) — the check exists to stop a bare `button:hover` rule outranking `.it`'s own selected-row state, but it only flags selectors that literally *begin* with `button`. Appending `#sidebar button:hover{background:var(--amber)}` — specificity (1,2,1), which outranks `.it[aria-current=true]` (0,2,0) far more decisively than the (0,2,1) rule the check was written for — returns green. **Confirmed green, not assumed**: the mutation was run by both the implementer and the orchestrator, and the case's own `triage` note records it so the next reader cannot mistake it for covered

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
