---
id: DRAFT-4
title: '`extract.py:236` still says "the four validators named in AMBIGUOUS_CODES"'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-3
  - '`tasks/reviews/pr57-r1.json` finding R3; `src/sec10k/extract.py:236`'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`extract.py:236` still says "the four validators named in AMBIGUOUS_CODES"** (added 2026-08-26, Origin: PR #57 R3) — verbatim from the reviewer: *`src/sec10k/extract.py:236` still reads "Only the four validators named in AMBIGUOUS_CODES may reach `ambiguous`", four lines above the loop this diff added at :251, while `src/sec10k/validate.py:112` now defines `AMBIGUOUS_CODES` with five members (`len(AMBIGUOUS_CODES)` → 5, the count ADR-035 §j cites as the check). validate.py's own module docstring was updated to "the five named in AMBIGUOUS_CODES"; this one was not.*

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
