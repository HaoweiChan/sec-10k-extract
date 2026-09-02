---
id: DRAFT-95
title: '`_declared_for` stays media-blind for every caller but one'
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-112
  - >-
    `src/repo_hygiene/eval_adapter.py` — `_flat_rules`' own docstring names this
    hole
  - >-
    `_without_media` is the one-caller workaround;
    `evals/adversarial/ui-split-breakpoint.json` exercises it
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`_declared_for` stays media-blind for every caller but one** (added 2026-08-24, Origin: D5) — D5 needed `.split`'s UNCONDITIONAL `grid-template-columns` and read the narrowest breakpoint's instead, because `_flat_rules` yields a rule inside `@media(...){...}` exactly like a top-level one and `_declared_for` takes the last match. D5 added `_without_media` and used it in `check_split_breakpoint` ONLY; `check_pane_heights`, `check_title_legibility` and `css_contrast`'s helpers still read the media-blind value

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
