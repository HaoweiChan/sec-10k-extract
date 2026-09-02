---
id: DRAFT-24
title: >-
  `button:disabled` sits at 2.20:1 and is deliberately excluded from the
  enforced contrast set
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-25
  - >-
    `evals/adversarial/ui-contrast-and-specificity.json` (`triage` note);
    `tasks/reviews/pr18-r1.json`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`button:disabled` sits at 2.20:1 and is deliberately excluded from the enforced contrast set** (added 2026-08-21, Origin: PR #18 R8 second pass) — while an extraction is in flight all three Extract buttons are disabled and their labels drop to 2.20:1, far under AA. The pair is *knowingly* left out of `evals/adversarial/ui-contrast-and-specificity.json`'s enforced list, and the case's `triage` note says so in writing rather than leaving a silent hole

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
