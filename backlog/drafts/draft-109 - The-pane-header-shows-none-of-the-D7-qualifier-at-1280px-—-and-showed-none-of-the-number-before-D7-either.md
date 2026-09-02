---
id: DRAFT-109
title: >-
  The pane header shows none of the D7 qualifier at 1280px — and showed none of
  the number before D7 either
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-126
  - '`tasks/reviews/d7-browser-walk.json` `round_1_remeasure` (both fixtures'
  - rendered form
  - band widths
  - >-
    and the pre/post D7 comparison); `tasks/reviews/pr53-r1.json` finding R5;
    `src/sec10k/web/static/index.html` `hdrRight`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The pane header shows none of the D7 qualifier at 1280px — and showed none of the number before D7 either** (added 2026-08-26, Origin: D7; re-measured at PR #53 R5) — `#pane`'s `.src-hdr` band is a `.lbl`, which ellipsises. Measured live at 1280x900 on the repaired page: cvx-2015 item 1 renders **`Part I · extracted · conf 0.95 …`** (band 316px, string 655px, 31 of 78 chars), and jpm-2024 item 15 — the one walked item carrying an item-targeted warning — renders **`Part IV · extracted · con…`** (band 251px, string 778px, 25 of 92 chars), cut before the confidence NUMBER finishes. Round 0 claimed the qualifier merely 'degrades to `· DOC…`'; that was measured on the cvx case only and is wrong for jpm. **Not a D7 regression, and this was measured rather than argued**: fitting each fixture's PRE-D7 header string into the same band with the same font gives `Part I · extracted · conf 0.95 …` and `Part IV · extracted · con…` — byte-identical to the post-D7 rendering, because what shows in that band is decided by the band's width, not the string's length. D7 lengthened a string that was already past the cut

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
