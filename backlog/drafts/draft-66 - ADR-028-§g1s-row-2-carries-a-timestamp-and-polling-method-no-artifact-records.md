---
id: DRAFT-66
title: ADR-028 §g1's row 2 carries a timestamp and polling method no artifact records
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-83
  - '`specs/decisions/ADR-028-build-identity.md:189`'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**ADR-028 §g1's row 2 carries a timestamp and polling method no artifact records** (added 2026-08-23, Origin: PR #37 R15) — verbatim from the reviewer: *§g1's row 2 carries a timestamp and a polling method that no committed artifact records — the same class of detail R9 removed from the paragraph directly below it.* A grep across `.md`/`.json`/`.py` returns exactly one hit for `~09:47Z` / 'bounded poll' / 'every 20 s': that line; `5ad1a0f` records the reading but gives no time and no method

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
