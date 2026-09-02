---
id: DRAFT-22
title: The new `ALIAS_FROM` header comment overstates itself twice
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-22
  - 'PR #17 round 1 R3 (LOW'
  - >-
    routed to debt); the comment block above `ALIAS_FROM` in
    `src/sec10k/segment.py`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The new `ALIAS_FROM` header comment overstates itself twice** (added 2026-08-20, Origin: PR #17 R3) — verbatim from the reviewer: *the new `ALIAS_FROM` header comment says every date in the table is written by a rule keying on fiscal-period end "except '5'", which the same diff contradicts for "15" (2004-05-23 is Release 33-8400's effective date run through the ADR-010 ruling-2 period-end compromise) and ADR-023 §g contradicts for "6" (2021-02-10 is 33-10890's early-compliance date; §g says the period-end-keyed date is 2021-08-09). The adjacent claim "each one below now names the release it comes from" is also false for entries 4, 5, 6 and 14, which name no release.* Evidence: `src/sec10k/segment.py:133`, `.claude/skills/sec10k-domain/SKILL.md`

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
