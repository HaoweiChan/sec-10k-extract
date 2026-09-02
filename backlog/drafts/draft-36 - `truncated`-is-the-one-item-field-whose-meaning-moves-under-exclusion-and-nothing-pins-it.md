---
id: DRAFT-36
title: >-
  `truncated` is the one item field whose meaning moves under exclusion, and
  nothing pins it
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-40
  - >-
    `src/sec10k/web/view.py` (`truncated` = `len(body) > display_max` beside
    `chars` = `len(raw)`); `src/repo_hygiene/eval_adapter.py`'s `pinned` tuple
  - which lists every field that IS pinned
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`truncated` is the one item field whose meaning moves under exclusion, and nothing pins it** (added 2026-08-22, Origin: PR #27 R3) — verbatim from the reviewer: it is *"pinned by nothing — the new check omits it from `pinned` and never asserts it, so an implementation that computes it from the un-stripped span still passes"*. Measured: the mutation `truncated = len(raw) > display_max` leaves `check_boilerplate_exclusion` at 0 failures / `items_stripped` 16, and the fixtures do reach the region (ge-1994's largest item is 46,929 chars, msft-2013's 111,892, both over `DISPLAY_MAX` 40,000). The visible symptom would be the "shown first N of M" notice appearing on an item whose stripped body is entirely on screen.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
