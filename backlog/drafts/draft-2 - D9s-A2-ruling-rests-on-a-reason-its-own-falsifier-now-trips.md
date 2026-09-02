---
id: DRAFT-2
title: D9's A2 ruling rests on a reason its own falsifier now trips
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-1
  - >-
    `specs/decisions/ADR-034-pointer-and-fanout-rulings.md` §e2 (dated
    cross-reference note) and §f row 3 (marked TRIPPED); the measurement re-runs
    from `src/sec10k/validate.py`'s `item_span_near_empty` over
    `evals/fixtures/`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**D9's A2 ruling rests on a reason its own falsifier now trips** (added 2026-08-26, Origin: PR #57 merge cross-check) — [ADR-034](../specs/decisions/ADR-034-pointer-and-fanout-rulings.md) §e2 gives two reasons for DECLINING A2, and reason 2 ("Nothing reaches it. The D8 trigger is measured silent on all five filings") generalised a measurement of item 1 alone to "the D8 trigger". D8 shipped `item_span_near_empty` over items **1, 7 and 8** at `SPAN_FLOOR` 1,500, and re-running §d1's table against it — exactly what §f row 3 directs — gives **4 fires of 5** (`cvx-2015` 7/8, `jpm-2024` 7/8, `ge-1994` 8, `spatz-2014` 8; only `bac-2006` silent) against a stated threshold of **one**. No §d1 figure is wrong: item 1 IS full-length on all five and that reproduces. Reason 1, the unadjudicated `cvx-2015` item-6 disagreement, is untouched.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
