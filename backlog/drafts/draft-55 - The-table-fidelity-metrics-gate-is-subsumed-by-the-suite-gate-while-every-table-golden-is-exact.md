---
id: DRAFT-55
title: >-
  The table-fidelity metric's gate is subsumed by the suite gate while every
  table golden is exact
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-72
  - ADR-029 §c2/§h; `evals/run.py`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The table-fidelity metric's gate is subsumed by the suite gate while every table golden is exact** (added 2026-08-23, Origin: S7) — ADR-029 §c2 says so in the open: on a green suite the metric is 1.0 by construction, so its `REGRESSION` fires together with a case going red, never instead. Its value today is magnitude and the time series

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
