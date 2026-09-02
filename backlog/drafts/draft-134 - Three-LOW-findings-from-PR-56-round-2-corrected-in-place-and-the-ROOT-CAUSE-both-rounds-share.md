---
id: DRAFT-134
title: >-
  Three LOW findings from PR #56 round 2, corrected in place; and the ROOT CAUSE
  both rounds share
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-153
  - >-
    `tasks/reviews/pr56-r2.json` R11-R13; `tasks/reviews/pr56-r2-red.txt`;
    `tasks/reviews/pr56-r2-resolution.json`
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Three LOW findings from PR #56 round 2, corrected in place; and the ROOT CAUSE both rounds share** (added 2026-08-26, Origin: PR #56 R11/R12/R13) — (a) **R11** the round-1 §b3a insertion orphaned §b3's closing paragraph into a section whose subject is a different filing, leaving "those five filings" with no antecedent and breaking the `§b3` citation this ledger uses; the paragraph is moved back inside §b3. (b) **R12** a stale `fast` suite size survived in the hooksPath Debt row — the same defect R6 had just removed, in the same file R6 edited; now score-only. (c) **R13** §g cited PR #56 R1 for the falsification of the burn-rule ground, which was R3. **THE ROOT CAUSE, recorded because it recurred across two consecutive review rounds and is the reason this PR needed three:** a correction was applied at the line each finding cited while a restatement of the same claim survived elsewhere — R4's third stale copy in round 1, then R8's settled burn answer sitting 50 lines below the text withdrawing its ground, and R10's arithmetic left unchanged when the enumeration it summed was rewritten. Round 3 was dispatched as a claim-wide sweep instead of a line patch, and `tasks/reviews/pr56-r2-red.txt` carries both the pre-fix evidence and a post-fix sweep proving each old claim now has zero live hits

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
