---
id: DRAFT-96
title: >-
  The S8 pane header and evidence panel still say "boilerplate hidden" when
  nothing was hidden
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-113
  - '`src/sec10k/web/static/index.html` (`hdrRight`'
  - >-
    the `.pane-meta` boilerplate `<dd>`); `view.build_view` now emits
    `boilerplate_applied`
  - which is the field they would read
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The S8 pane header and evidence panel still say "boilerplate hidden" when nothing was hidden** (added 2026-08-24, Origin: D5, PR #46 R1's untaken sibling) — the same asked-for-versus-applied confusion R1 found in the D5 note, one layer over: `index.html`'s `hdrRight` prefixes `"boilerplate hidden · "` and the `.pane-meta` `<dd>` says "detected chrome is hidden from the text above", both keyed on `VIEW.boilerplate_excluded`. Measured live at 1280 on aapl-2025 with the box ticked (0 spans, 0 items stripped): header reads `boilerplate hidden · Part I · extracted · conf 0.95 · via heading_strict` over text byte-identical to the un-flagged run

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
