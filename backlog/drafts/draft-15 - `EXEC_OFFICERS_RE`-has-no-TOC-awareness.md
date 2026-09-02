---
id: DRAFT-15
title: '`EXEC_OFFICERS_RE` has no TOC awareness'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-15
  - ADR-019 §f (TOC-awareness subsection)
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`EXEC_OFFICERS_RE` has no TOC awareness** (added 2026-08-19, post-commit review) — every other candidate path in `segment.py` routes through `_toc_runs` before trusting a heading match; this regex is a raw `text.search()` with none. It already matches TOC entries today: `jnj-2016` ("…Registrant\n\n10\n\nPART II"), `msft-2013` ("…Registrant\n12\n\nItem 1A."), `nike-2006` ("…Registrant\n8\n\nItem 1A."). Harmless today because every TOC hit falls outside the search window; a filing whose TOC sits *after* the first accepted item heading (none in this corpus do) would have it land inside the window and truncate that item to near-nothing, silently. Same class as the `(?!\.)` guard, which catches GE's wrapped-prose period but not a comma-terminated wrapped line

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
