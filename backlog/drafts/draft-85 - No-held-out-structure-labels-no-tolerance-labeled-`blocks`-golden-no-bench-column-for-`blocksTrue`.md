---
id: DRAFT-85
title: >-
  No held-out structure labels, no tolerance-labeled `blocks` golden, no bench
  column for `blocks=True`
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-102
  - ADR-032 §c2
  - §f
  - §e
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**No held-out structure labels, no tolerance-labeled `blocks` golden, no bench column for `blocks=True`** (added 2026-08-23, Origin: S9) — every `blocks` check asserts an exact sequence, so on a green suite `structure_*_fidelity` is 1.0 by construction and its gate fires together with the suite's (ADR-032 §c2, the same standing ADR-029 §c2 stated for table fidelity); `evals/bench.py` times the default and `tables=True` paths only, so the 1.37× / +119% jpm-2024 figures in ADR-032 §f are one-off medians of 5, not an artifact of record

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
