---
id: DRAFT-116
title: The D7 mutation probe's own header counts its round-1 shape
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-133
  - >-
    `tasks/reviews/pr53-r3.json` finding R13;
    `tasks/reviews/pr53_mutation_probe.py` docstring lines 1
  - 19 and 27
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The D7 mutation probe's own header counts its round-1 shape** (added 2026-08-26, Origin: PR #53 R13) — `tasks/reviews/pr53_mutation_probe.py` line 1 says "the six findings as one-defect mutations" and line 27 says "Six more would make it worse", while `MUTATIONS` now holds ten entries spanning PR #53 rounds 1 and 2. Line 19 of the same docstring WAS corrected in that round (sixteen -> fourteen), so the file was open and two neighbouring counts were left behind

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
