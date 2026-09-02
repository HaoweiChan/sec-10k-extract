---
id: DRAFT-90
title: >-
  Image containment is only as good as the item spans, and 2 of the 3 image
  goldens cannot tell
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-107
  - >-
    `evals/golden/xom-2021-images.json` and `evals/golden/jpm-2024-images.json`
    provenance; ADR-033 §e row 6
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Image containment is only as good as the item spans, and 2 of the 3 image goldens cannot tell** (added 2026-08-23, Origin: S10) — ADR-033 §b3 derives the item an image falls in from offsets rather than storing it, so on a filing whose segmentation is wrong the containment is wrong the same way. xom-2021 and jpm-2024 both fire `last_item_dominates`, so all 9 and all 14 of their images land in ONE over-long span (Item 16 covering [111730, 386385) of 388,848 chars; Item 15 covering [201298, 1211720) of 1,213,284), and their hand-labeled `item` values would be satisfied by an implementation that returned a constant. Only `bac-2006-images` discriminates — a `success` document with no warnings whose five images split across Item 7 and Item 8. If the dominance debt is ever closed, the xom and jpm labels move and those two cases go red for the right reason.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
