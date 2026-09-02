---
id: DRAFT-11
title: 'Two LOW findings from PR #42 round 2'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-11
  - '`tasks/reviews/pr42-r2.json`'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Two LOW findings from PR #42 round 2** (added 2026-08-23, Origin: PR #42 R5/R6) — (a) **R5** the published check count is off by one: `ba-2003-asterisk-ibr` has 25 checks (5 at 1343bf8, 19 at 3c7db31, 25 at f841f5d) while ADR-031 §h, the D4 ledger row and `pr42-r1-resolution.json` say 26 / twenty-one added; (b) **R6** ADR-031 §d's 'every other check type REFUSES it loudly' is not true for `table` checks — `run_case` routes `type: table` to `table_fidelity` before `eval_check`, so an `evidence` key on a table check is silently ignored (no committed case does so; no gate impact today)

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
