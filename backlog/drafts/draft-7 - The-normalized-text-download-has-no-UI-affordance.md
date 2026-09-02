---
id: DRAFT-7
title: The normalized-text download has no UI affordance
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-7
  - '`evals/adversarial/ui-offset-reproduction-contract.json`'
  - >-
    which pins the endpoint and both copies of the recipe and pins nothing at
    all in `index.html`; `src/sec10k/web/app.py::api_normalized`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The normalized-text download has no UI affordance** (added 2026-08-26, Origin: D12) — `/api/normalized/{token}` is reachable only by a consumer who reads `source.token` out of the extraction response. The inspector's compare pane still offers the raw source only, so a human at the screen cannot fetch the text the offsets index without leaving the page.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
