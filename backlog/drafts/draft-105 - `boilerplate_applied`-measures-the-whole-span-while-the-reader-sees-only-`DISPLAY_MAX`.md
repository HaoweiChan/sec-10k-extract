---
id: DRAFT-105
title: >-
  `boilerplate_applied` measures the whole span while the reader sees only
  `DISPLAY_MAX`
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-122
  - '`tasks/reviews/pr46-r3.json` finding R11'
  - >-
    evidence and acceptance verbatim; the standing PR #46 R9 row names the same
    `DISPLAY_MAX` ceiling
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`boilerplate_applied` measures the whole span while the reader sees only `DISPLAY_MAX`** (added 2026-08-24, Origin: PR #46 R11) — the merge accumulator ORs `strip_chrome(text, spans, s, e) != raw` over the FULL span, while the pane body and the `display_text` gate both work on `[:display_max]` 40,000. An item whose chrome falls entirely beyond character 40,000 therefore sets `boilerplate_applied` True while the extracted pane on screen is byte-identical to the raw slice — the PR #46 R1 shape (a note asserting an invisible disagreement) reached through truncation instead of through Markdown. Constructed envelope: `normalized_text` = 'x'*100 + 'HEAD' + 'y'*100, one item, boilerplate at 100–105, `display_max=50` gives `boilerplate_applied True` with `display_text` absent. **Not reachable on the committed corpus** — all 42 fixtures agree. Note the direction: post-S9 the OLD expression would have been False here, so this corner is a behaviour change the merge introduced

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
