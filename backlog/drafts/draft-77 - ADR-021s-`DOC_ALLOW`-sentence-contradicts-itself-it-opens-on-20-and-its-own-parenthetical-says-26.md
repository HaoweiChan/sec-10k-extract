---
id: DRAFT-77
title: >-
  ADR-021's `DOC_ALLOW` sentence contradicts itself: it opens on 20 and its own
  parenthetical says 26
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-94
  - '`specs/decisions/ADR-021-benchmark-instrument.md:387` against :389-391'
  - >-
    and §b12's amendment at :418-420; `evals/bench.py:543`;
    `tasks/reviews/pr40-r1.json` R1; the `evals/bench._demo` DOC_ALLOW row in
    this table
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**ADR-021's `DOC_ALLOW` sentence contradicts itself: it opens on 20 and its own parenthetical says 26** (added 2026-08-23, Origin: D2; **corrected 2026-08-23, PR #40 R1**) — the `evals/bench._demo` DOC_ALLOW row in this table predicted the published count would drift, and it has: `python3 -c "import sys;sys.path.insert(0,'.');from evals.bench import DOC_ALLOW;print(len(DOC_ALLOW))"` answers **26** at this commit. The ADR did move the count — `specs/decisions/ADR-021-benchmark-instrument.md:389` reads "**26 after D2**, same day: +13 dated entries … −7 …", and it reconciles against the 20 it started from and against §b12's own amendment at :418-420 (gained 13, lost 7). What was not moved is the **lead** integer of that same sentence at :377, which still opens "The 20 remaining legitimate non-measurements are listed in `DOC_ALLOW`" — so a reader who stops before the parenthesis reads 20 and a reader who finishes it reads 26. Nothing mechanical guards either number: `--check-docs` reads decimals within 60 chars after a backticked fixture name, so a bare integer in ADR prose is outside its window by construction. This row's first wording claimed the count "was not moved with them", which mis-read the file it cites — a row written to document a stale-number defect carrying the exact class it names

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
