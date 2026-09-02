---
id: DRAFT-18
title: >-
  `evals/bench._demo` has no assertion that the published `DOC_ALLOW` count
  equals `len(DOC_ALLOW)`
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-18
  - 'PR #12 comments (reviewer round 4 R29'
  - >-
    R30); `specs/decisions/ADR-021-benchmark-instrument.md:328`;
    `docs/analysis-report.md:421`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`evals/bench._demo` has no assertion that the published `DOC_ALLOW` count equals `len(DOC_ALLOW)`** (added 2026-08-20 as 'Two counts about executable things, written from memory', PR #12 round 4, R29/R30; **both counts CLOSED by L1 (2026-08-23, PR #35 R2)** — ADR-021 §b12:328 now reads 20: `python3 -c "import sys;sys.path.insert(0,'.');from evals.bench import DOC_ALLOW;print(len(DOC_ALLOW))"` → 20 at this commit, `grep -n '14 remaining legitimate' specs/decisions/ADR-021-benchmark-instrument.md` → nothing; `docs/analysis-report.md:421` now reads 'twelve measurement choices' — checked against ADR-021 itself, not assumed: §b enumerates choices **1.**–**12.** (:51 to :301) and its own lead sentence at :42 says **Twelve**, so 'ten' was the stale one; `grep -n 'ten measurement choices' docs/analysis-report.md` → nothing. The T13 ledger row's '14' and 'eleven' are archived in `tasks/DONE.md` (full text in git history at the pre-split commit) and are not edited) — **open**: the durable fix, an assertion in `evals/bench._demo` that the published count equals `len(DOC_ALLOW)`, so it cannot drift again

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
