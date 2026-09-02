---
id: DRAFT-40
title: >-
  `TOC_CLUSTER_MIN=5` is a hard floor: a contents page leaking ≤4 titled rows is
  never examined
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-44
  - '`src/sec10k/segment.py` `TOC_CLUSTER_MIN`'
  - '`_toc_runs`'
  - '`filter_candidates`; `tasks/reviews/gates-2026-08-22.json` T4-3'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`TOC_CLUSTER_MIN=5` is a hard floor: a contents page leaking ≤4 titled rows is never examined** (added 2026-08-22, Origin: gates-2026-08-22 T4-3, MEDIUM, reviewer-stated) — verbatim from the reviewer: *TOC_CLUSTER_MIN=5 is a hard floor, so a table of contents leaking FOUR or fewer titled rows is never examined and never dropped; the fourth row's span then annexes the cover page, the remaining TOC and all of real Items 1/1A/1B/2.* Evidence, verbatim: *segment.py:348 and :365-366. boundary_hygiene, verbatim, no_overlap_ordered all pass (the span does open with its heading); last_item_dominates cannot fire because the item is not last; toc_manifest_mismatch checks presence, never position. Raising TOC_CLUSTER_MIN to 6/7/8 leaves the whole suite green.* **Implementer check 2026-08-22, not assumed**: the natural reproduction — premier-pacific-2016 with only the first 4 of its 43 TOC row boundaries merged, using toc-titled's own regex capped at 4 — does NOT reproduce: the remaining rows are title-promoted by `find_candidates`'s next-line rule (they are on the unmutated fixture too), the front run stays dense at 21 codes, all four merged rows are still rejected as `table-of-contents cluster`, and items 1/1A/1B/2 resolve to their real bodies (7,496 / 129 / 142 / 367 chars). Reproducing it needs a contents page whose other rows yield no candidate at all — a shape no committed filing has and a hand-built fixture would have to invent

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
