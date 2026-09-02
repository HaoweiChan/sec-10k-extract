---
id: DRAFT-118
title: Bench population of record is stale after D6
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-135
  - 'Enumerated here by file:line'
  - >-
    and `ADR-021:211`'s "no real filing joined the corpus since" is **retracted
    in place** rather than left standing
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Bench population of record is stale after D6** (added 2026-08-26, Origin: D6 / PR #52 R1) — `evals/bench.py:232 heldout_sizes()` reads `evals/heldout/fixtures/` by `stat`, so adding `intc-2025` (3.167 MiB) and `c-2025` (15.403 MiB) silently moved the `real_edgar_committed` population from 33 / 2.104 MiB to 35 / ~2.514 MiB (+19.5%), and with it the projection of record (153 s → ~183 s; 1,072 s ≈ 18 min → ~1,281 s ≈ 21 min). Six statements now describe a corpus that no longer exists: `docs/analysis-report.md:553` ("the five held-out filings in `evals/heldout/fixtures/` are"), `:893` ("the five held-out filings … the second-largest filing in the repo (`spg-2019`, 9.36 MiB)" — `spg-2019` is now third), `:902` ("**`real_edgar_committed`** ← of record") — the table row reading 33 / 2.104 MiB / 153 s / 1,072 s, `:922` ("the 28 real dev fixtures plus the 5 held-out filings"), and `ADR-021:224` ("read for all 33 real filings, the 5 held-out among them by `stat`"), `ADR-021:762` ("Projection of record (`real_edgar_committed`, n=33, 2.104 MiB"). Repro: `python3 -c "print((33*2.104 + 3320720/1048576 + 16150764/1048576)/35)"` → 2.5143; and `evals/heldout/fixtures` now holds 7 directories

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
