---
id: DRAFT-124
title: The compare pane's iframe logs subresource 404s on every extraction
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-141
  - '`tasks/reviews/d10-agent-walk.json`'
  - '`steps.deep_link.console_errors_ungraded` (recorded'
  - deliberately not graded
  - with the reason in `d10_agent_walk.py`)
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The compare pane's iframe logs subresource 404s on every extraction** (added 2026-08-26, `Origin: D10`) — found by the D10 browser walk, which listens for console errors: loading `aapl-2025` in the compare pane emits `GET /api/source/aapl-20250927_g1.jpg 404` and `_g2.jpg 404`, because the raw filing's `<img>` tags reference binaries the fixture directory does not commit and `/api/source/` has nothing to serve for them. Nothing a reader sees is wrong — the images are decorative signature/logo graphics and the compare pane's text, which is the only thing sync-scroll and the anchor contract use, is complete — but any instrument that grades console errors on this page (this walk was the first) sees a red herring before it sees a real one, and a future agent probing the deployment will too

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
