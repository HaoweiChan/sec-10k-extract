---
id: DRAFT-76
title: Three relative cross-references in this table now point at deleted rows
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-93
  - this table
  - the three rows quoted above; ADR-019 §d; `tasks/DONE.md` D2 line
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Three relative cross-references in this table now point at deleted rows** (added 2026-08-23, Origin: D2) — the D2 sweep removed three settled rows and, under its no-other-row-touched binding, left the phrases that pointed at them: the non-last-span successor row's "the correctly-specified successor to the retired row above" and the msft-2013 row's "the `EXEC_OFFICERS_RE` fix (see T11 row above)" both named the retired span-coverage row, and the re-filed T13 (d)/(e) row's "re-filed from the PROMOTED row above" named the promoted T13-mechanisms row. Each target's narrative survives where the sweep's rationale said it would (ADR-019 §d for the retirement, ADR-021 §b12's D2 amendment and PR #39 for the promotion), so no reasoning is lost — the three phrases are simply no longer resolvable inside this file

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
