---
id: DRAFT-38
title: The truncation notice compares two different quantities under exclusion
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-42
  - >-
    `src/sec10k/web/static/index.html`'s `.pane-meta` `<dl>`;
    `src/sec10k/web/view.py::build_view` (`chars` = `len(raw)`
  - '`truncated` = `len(body) > display_max`)'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The truncation notice compares two different quantities under exclusion** (added 2026-08-22, Origin: S8) — the `shown` row reads "first N of M characters" where, with the box ticked, N counts the STRIPPED text and M is the full span length (`chars`, deliberately unmoved so INV-S2 offsets stay readable). N/M is therefore not a truncation ratio on an excluded run, and on an item whose chrome exceeds `DISPLAY_MAX - span` the numbers can look contradictory.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
