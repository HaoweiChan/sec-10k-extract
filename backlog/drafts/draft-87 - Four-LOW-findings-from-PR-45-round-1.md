---
id: DRAFT-87
title: 'Four LOW findings from PR #45 round 1'
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-104
  - '`tasks/reviews/pr45-r1.json`'
  - '`pr45-r1-resolution.json`; ADR-032 §b2'
  - §e
  - §f2
  - §g
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Four LOW findings from PR #45 round 1** (added 2026-08-24, Origin: PR #45 R3/R4/R5/R6) — verbatim from the reviewer: (a) **R3** *ADR-032 §f2 '44 of 46 below 25' is 43 of 46* — re-derived (cvx-2015 74, intc-2002 68, tgt-2002 68 are the three at or above 25) and corrected in place in §f2; (b) **R4** *ADR-032 §b2's 'By construction … the blocks cover every non-space character' is true by corpus measurement, not by construction: text inside a `<table>` that yields no ADR-029 record lands outside every block and is lost from the Markdown view* — `<p>a</p><table>stray text</table><p>b</p>` gives blocks [a, b]; 0 occurrences on the 47 fixtures; the wording option was taken (§b2 now says measured, pinned by `blocks_sane`), not the paragraph-block emission — a two-line fix with no fixture to pin it is a path only a self-check would exercise, the ADR-029 §e standing; (c) **R5** *Bold tracking pops the innermost same-name BOLD context on any end tag of that name, so a non-bold inner element of the same tag name ends the outer bold early (`<span style=bold><span>A</span> B</span>` is not strong); 0 mismatches against a stack model on all 47 fixtures* — noted in §b2 and §e next to the unclosed-carrier leak; (d) **R6** *The vocabulary-red run the ADR cites (145fe4a, 98/108, 23:14) left no committed artifact: no report and its history.jsonl line was not among the three lines curated into 7ab62a0; the red state is reproducible but rests on the ADR's word* — not recoverable retroactively; the round-1 repair kept the new case's red run with the repair (`evals/report/20260824-002657-fast.json` + its history line)

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
