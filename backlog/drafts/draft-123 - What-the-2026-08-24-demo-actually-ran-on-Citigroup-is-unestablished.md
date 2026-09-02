---
id: DRAFT-123
title: What the 2026-08-24 demo actually ran on Citigroup is unestablished
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-140
  - '`evals/heldout/README.md` H4 entry; postmortem §8'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What the 2026-08-24 demo actually ran on Citigroup is unestablished** (added 2026-08-26, Origin: D6) — the postmortem records the demo showing per-item `conf 0.95` on a recent Citigroup 10-K, and §8 explains it as headings matched to the wrong instances. The D6 baseline on `c-2025` (the most recent Citigroup 10-K on EDGAR, the only one in CIK 831001's recent-submissions window) produces the opposite: zero extracted items, **21 `missing` at 0.40 and two `omitted` at 0.75 (items 9C and 16)**, `doc_status` `ambiguous`. (This row read "22 `missing`" until PR #52 R2 round 2 — the same stale number the D6 row above was corrected for, in the same file, in the row D7 and D8 are told to read. The argument is strengthened, not weakened: zero extracted is still zero extracted, and the item-level confidence the demo showed as 0.95 is 0.40 on 21 items and 0.75 on two.) So either the demo ran a different document, or the 0.95 the audience saw came from somewhere other than a Citigroup 10-K item. The accession the demo used was never written down

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
