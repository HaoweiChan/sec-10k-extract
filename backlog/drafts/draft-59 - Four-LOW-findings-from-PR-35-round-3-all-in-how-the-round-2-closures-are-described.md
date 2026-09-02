---
id: DRAFT-59
title: >-
  Four LOW findings from PR #35 round 3, all in how the round-2 closures are
  described
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-76
  - '`tasks/reviews/pr35-r3.json`'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Four LOW findings from PR #35 round 3, all in how the round-2 closures are described** (added 2026-08-23, Origin: PR #35 R9/R10/R11/R12) — (a) **R9** `pr35-r2-resolution.json` R6.fix says the round-2 reviewer's repro 'prints nothing' after the fix; it still prints ADR-020:557 in its reworded, correct form ('leaves item 10 with 956 …' matches neither exclusion pattern of the repro) — the claim is wider than its grep, the class round 2 was repairing; (b) **R10** the 'four times' residual sweep missed `docs/analysis-report.md:676-677` 'ADR-020's arithmetic, which was corrected four / times under review' — the phrase wraps across a line break, so the recorded sweep command cannot match it; ADR-020 header and §h3 say three corrections / four figures; (c) **R11** this round's own two-line insertion in analysis-report §1 moved the 'twelve measurement choices' line from :421 to :423, leaving three `docs/analysis-report.md:421` citations stale (L1 Status cell, row 66 note and Where cell) while the R7/R8 debt row says no line number in a touched closure note can move; (d) **R12** row 63 (6)'s wide-sweep hit list and the resolution JSON file three ADR-020 hits under §h / §h2 that are in §c (ADR-020:223/:232/:234, the 'Row 7's scope' paragraph); verdicts right, section labels wrong

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
