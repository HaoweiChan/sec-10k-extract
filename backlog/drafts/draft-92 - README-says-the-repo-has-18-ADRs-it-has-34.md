---
id: DRAFT-92
title: README says the repo has 18 ADRs; it has 34
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-109
  - '`README.md:92` against `specs/decisions/INDEX.md`'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**README says the repo has 18 ADRs; it has 34** (added 2026-08-23, Origin: S10) — `README.md:148` reads "Full rationale in `specs/decisions/` (18 ADRs)"; `ls specs/decisions/ADR-*.md` counts 33 at `origin/main` f00b635 and 34 with ADR-033 (32 and 33 respectively when this row was written at 3e16f70; S9's ADR-032 landed in between). Pre-existing and unrelated to S10 — found while adding the ADR-033 line to the capability paragraph twelve lines above it. Not fixed here because a hand-written count that goes stale on every ADR is a check, not an edit: `check_index` already walks `specs/decisions/ADR-*.md` and could assert this number the way `ledger_table_shape` asserts the ledger's, and doing that is a repo-hygiene change outside this PR's spec.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
