---
id: DRAFT-133
title: 'Four LOW findings from PR #56 round 1, all CORRECTED IN PLACE in the same pass'
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-152
  - >-
    `tasks/reviews/pr56-r1.json` R4-R7; red evidence for R4 and the R5/R6/R7
    repros in `tasks/reviews/pr56-r1-red.txt`;
    `tasks/reviews/pr56-r1-resolution.json`
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Four LOW findings from PR #56 round 1, all CORRECTED IN PLACE in the same pass** (added 2026-08-26, Origin: PR #56 R4/R5/R6/R7; routed to debt by the reviewer, corrected in place per the L1 and D5 precedent in `tasks/DONE.md`) — (a) **R4** the multi-code prevalence denominator was off by one: the scan hits 18 fixtures, not 17, so it is seventeen others, not sixteen; corrected in ADR-034 §c1, the combined-heading Debt row and the `axp-2008` triage note. (b) **R5** "Each is adjudicated below" and "Every other hit is" were sweep sentences over enumerations that omitted 2 of 15 Class-A hit fixtures and 7 of 18 Class-B hit fixtures; §b3 now says it adjudicates the real-EDGAR hits and names the two synthetics as out of scope, and §c1 enumerates the buckets with the arithmetic shown, and round 2's R10 corrected it further: the sum is over hit FIXTURES, not the 39 individual hits the scan emits, and `gs-2002` and `xom-2021` each fall in two buckets, and round 3's R15 then dropped the entry count altogether — it had been published wrong twice (18, then 20), so §c1 now states only the 39-hits-over-18-fixtures facts and the single body-heading adjudication that actually carries the ruling. The reviewer's sharpest catch rides here: `interior-span-dominates` carries a multi-code string WITH missing items. **Round 2's R9 then showed the repair itself was still wrong** — the co-occurrence of a multi-code string with missing items is NOT unique to `axp-2008` even among real filings: `c-2025` (cover string, items 10-14 missing) and `xom-2021` (prose string at offset 39731, item 6 missing) both show it, with no causal link in either case. §c1 now defends only the claim that carries the ruling — `axp-2008` is the one filing in 49 whose multi-code string is a **body heading over item content** — and tabulates both falsifying filings. (c) **R6** the published gate figures 67/67 and 130/130 were already stale at the PR's own merge SHA (68/68, 131/131 after D12); suite sizes are now dropped in favour of score 1.000 plus baseline untouched, which is what the D6 row does and calls the R8 defect. (d) **R7** the sonnet-5 price row was published under a claim that a 1M-context $2.00/MTok tier "now exists", implying it post-dated ADR-020, while §d also dates the basis to ADR-020's own 2026-06-24 table; it was on that table all along and ADR-020 §d simply did not enumerate the mid tier. Re-worded to a correction of ADR-020's reading, not of the price basis; no arithmetic cell moved

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
