---
id: DRAFT-33
title: >-
  `display_text` roughly doubles the ON-path inspector payload, and nothing
  disclosed the cost
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-37
  - '`tasks/reviews/pr27-r2.json` finding R8'
  - >-
    evidence and acceptance verbatim; re-measured independently by the
    orchestrator
  - whose corpus-wide figures are the ones above
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`display_text` roughly doubles the ON-path inspector payload, and nothing disclosed the cost** (added 2026-08-22, Origin: PR #27 R8) — the R1 repair split the stripped string out of `text` into a new `display_text` so the anchor oracle keeps the verbatim slice (`src/sec10k/web/view.py:62-63`). Both are truncated at `DISPLAY_MAX` 40,000, so every item containing any chrome now serialises its body twice on an opt-in run. **Orchestrator-measured at `5a2df35`, 37 fixtures**: corpus total 3,854,698 → 5,990,113 bytes (**×1.55**); 21 of 37 fixtures grow by more than 20 KB; worst cases cat-2023 222,559 → 428,434 (+205,875), heading-unnumbered +180,261, nvda-2024 +180,055, msft-2013 +178,273. Separately `display_text` is emitted whenever `body != raw` even if the difference falls beyond `DISPLAY_MAX`, in which case it is byte-identical to `text`; the exclusion check's dead-payload guard only fires when NOTHING was stripped, so that redundancy is unpinned — 0 such items on today's fixtures, so no live symptom

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
