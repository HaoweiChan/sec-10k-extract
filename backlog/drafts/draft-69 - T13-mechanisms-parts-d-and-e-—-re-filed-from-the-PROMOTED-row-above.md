---
id: DRAFT-69
title: 'T13 mechanisms, parts (d) and (e) — re-filed from the PROMOTED row above'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-86
  - '`evals/bench.py` `PAYLOAD_KEYS` / `UNITS` / `SYNTHETIC`; ADR-021 §b10'
  - §b12 amendment
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**T13 mechanisms, parts (d) and (e) — re-filed from the PROMOTED row above** (added 2026-08-23, Origin: D2; PR #12 R28/R31) — (d) the payload inversion stops at the top-level *key set*: `units`' contents are unasserted, and a fabricated new top-level block passes green once its name is added to `PAYLOAD_KEYS`; (e) `SYNTHETIC` (13 names at D2, driving the §5 projection of record) has exactly one member asserted (`toc-titled`, in `_demo`); the row's own demonstration — the published projection moving from n=33 / 2.104 MiB to n=34 / 2.06 MiB with `--self-check` green — came from dropping `items-stripped`, and nothing in D2 changed that: `run_all`'s existence check catches a *renamed* member, not a *removed* one

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
