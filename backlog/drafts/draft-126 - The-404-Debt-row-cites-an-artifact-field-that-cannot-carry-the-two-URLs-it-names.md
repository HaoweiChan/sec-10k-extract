---
id: DRAFT-126
title: >-
  The 404 Debt row cites an artifact field that cannot carry the two URLs it
  names
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-143
  - >-
    `tasks/reviews/pr55-r1.json` R5; the row above ('The compare pane's iframe
    logs subresource 404s')
  - evidence column
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The 404 Debt row cites an artifact field that cannot carry the two URLs it names** (added 2026-08-26, `Origin: PR #55 R5`, LOW) — verbatim from the reviewer: *The new Debt row cites a field of the walk artifact that cannot support the claim it makes — the row names two specific 404 URLs, the cited field holds one deduped URL-less string.* Evidence verbatim: *`tasks/TODO.md:210` claims `GET /api/source/aapl-20250927_g1.jpg 404` and `_g2.jpg 404`, evidence column `tasks/reviews/d10-agent-walk.json, steps.deep_link.console_errors_ungraded`. That field (`d10-agent-walk.json:14-16`) is `["Failed to load resource: the server responded with a status of 404 (Not Found)"]` — one entry, no URL, no method, no path. The underlying fact is independently true (`evals/fixtures/aapl-2025/` contains only `filing.htm`, whose `<img src="aapl-20250927_g1.jpg">` / `_g2.jpg` have nothing to serve), but the named artifact is not where it is recorded.* Acceptance verbatim: *Either the walk records `m.location` / the request URL alongside each console error so the artifact carries the two paths, or the Debt row cites where the two URLs were actually observed (server log) instead of the artifact*

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
