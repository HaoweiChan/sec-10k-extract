---
id: DRAFT-129
title: The R4 debt row says "Evidence verbatim" over evidence that was reworded
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-147
  - >-
    `tasks/reviews/pr55-r2.json` R12; `tasks/TODO.md:211` (the R4 row);
    `tasks/reviews/pr55-r1-resolution.json` R4 note
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The R4 debt row says "Evidence verbatim" over evidence that was reworded** (added 2026-08-26, `Origin: PR #55 R12`, LOW) — verbatim from the reviewer: *The R4 debt row labels its evidence "Evidence verbatim" and the resolution artifact claims all three fields were "carried verbatim", but R4's evidence was reworded to get past `ledger_table_shape`.* Evidence verbatim: *`tasks/TODO.md:211` renders `el => el.getAttribute('aria-label') OR el.textContent` (`tasks/reviews/pr55-r1.json` R4 evidence, the two characters between the operands being the JS logical-or) as "(an `evaluate` returning `el.getAttribute('aria-label')` falling back to `el.textContent`)", and drops the leading claim clause; a normalized substring comparison of the four debt rows against `pr55-r1.json` shows R4 claim and R4 evidence as the only two that differ. `tasks/reviews/pr55-r1-resolution.json:53` nonetheless states "claim, evidence and acceptance carried verbatim in the row". The substance of the finding is preserved — this is a labelling inaccuracy, not a dropped finding.* Acceptance verbatim: *The R4 row says the evidence is paraphrased (pipes are not representable in a ledger cell) rather than "verbatim", and the resolution note for R4 says the same*

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
