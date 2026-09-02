---
id: DRAFT-71
title: 'Two LOW findings from PR #39 round 1, both prose beside a correct number'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-88
  - '`tasks/reviews/pr39-r1.json` R2/R3'
  - >-
    `pr39-r1-resolution.json`; `docs/analysis-report.md` §3.2; ADR-021 §d1;
    `evals/bench.py` `DOC_ALLOW`
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Two LOW findings from PR #39 round 1, both prose beside a correct number** (added 2026-08-23, Origin: PR #39 R2/R3) — (a) **R2** report §3.2 listed the three 2026-08-23 warm-up maxima sorted (1.048 / 1.051 / 1.056) but the fixtures in run order, so the implied pairing was wrong; corrected in place to run order 1.056 / 1.048 / 1.051 on `sandston-2021`, `jpm-2024`, `ko-1997`, matching ADR-021 §d1 — and the same sentence's 2026-08-20 parenthetical (and ADR-021 §d1's original, pre-D2 text) carried the v4 trio as 1.021 / 1.031 / 1.042, also sorted, with the first value a rounding slip: the artifacts read 1.0315 / 1.0208 / 1.0424 in run order, so 1.032 / 1.021 / 1.042 (`round(1.0315, 3)` is 1.032); both corrected in place with a dated marker. (b) **R3** the `DOC_ALLOW` comment on `("analysis-report.md", "ksb-2007", "0.0025")` said `first_s == min_s (0.0026 on 185707)`; `20260823-185707` reads first 0.0027, min 0.0026, median 0.0026 — the comment now says so. Found while sweeping for R1's class: `1.295` was quoted as `1.30×` in README, report (v5 block, §3.2 twice), ADR-021 §b13/§g, ADR-029 §f and the D2 ledger row — `round(1.295, 2)` is 1.29 under the check's own rounding rule, so `1.30` reproduces from nothing; all quote 1.3× (two significant figures, `round(1.295, 1)`) or the field's 1.295 now, and the trio range 1.27–1.30 reads 1.274–1.295 verbatim

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
