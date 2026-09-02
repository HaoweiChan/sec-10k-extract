---
id: DRAFT-121
title: The ledger line-ref check misses the possessive form
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-138
  - '`tasks/reviews/pr52-r3.json` finding R15'
  - evidence and acceptance verbatim
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The ledger line-ref check misses the possessive form** (added 2026-08-26, Origin: D6 / PR #52 R15) — `LEDGER_LINE_REF_RE` in `src/repo_hygiene/eval_adapter.py` allows only an optional `reads`/`says` between the closing backtick and the opening quote, so a ref written possessively is neither verified nor counted. The R1 Debt row in this file uses exactly that form. Mutating that ref's line number to a nonexistent line leaves the check green and the suite at 61/61, while the same mutation on an ordinary ref goes red — verified both ways by the orchestrator. The ref resolves correctly today, so nothing is stale; this is an erosion path

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
