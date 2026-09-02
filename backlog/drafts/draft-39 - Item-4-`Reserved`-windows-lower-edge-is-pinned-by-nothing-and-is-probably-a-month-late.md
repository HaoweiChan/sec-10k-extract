---
id: DRAFT-39
title: >-
  Item 4 `Reserved` window's lower edge is pinned by nothing, and is probably a
  month late
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-43
  - '`src/sec10k/segment.py` `item_label` (the `date(2010'
  - '1'
  - >-
    1)` literal and the comment above it); `tasks/reviews/gates-2026-08-22.json`
    T4-2
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Item 4 `Reserved` window's lower edge is pinned by nothing, and is probably a month late** (added 2026-08-22, Origin: gates-2026-08-22 T4-2, MEDIUM, reviewer-stated) — verbatim from the reviewer: *The Item 4 era window starts at 2010-01-01 on the premise that 'Dec-2009 enders mostly filed before 2010-02-28'. That premise is backwards — calendar-FY2009 10-Ks are due 2010-03-01/03-16/03-31, so the largest cohort of that season filed AFTER the effective date and wrote 'Item 4. [Removed and Reserved]'. They are labelled 'Submission of Matters to a Vote of Security Holders'.* Evidence, verbatim: *segment.py:177, justification at :174-176. No committed fixture has a period end anywhere in 2009, so the window's lower edge is pinned by nothing.* Implementer note: ADR-010 ruling 2's own rule — the earliest period end whose report can land after the effective date — applied to 2010-02-28 puts the edge in late 2009, not at 2010-01-01, so the constant disagrees with the repo's stated convention as well as with the reviewer; the comment's 'mostly filed before it' is the one claim neither side has measured

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
