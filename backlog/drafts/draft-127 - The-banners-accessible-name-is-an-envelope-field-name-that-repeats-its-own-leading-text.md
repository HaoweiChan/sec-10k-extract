---
id: DRAFT-127
title: >-
  The banner's accessible name is an envelope field name that repeats its own
  leading text
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-144
  - >-
    `tasks/reviews/pr55-r1.json` R6; `src/sec10k/web/static/index.html:327`;
    `tasks/reviews/d10-agent-walk.json:107`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The banner's accessible name is an envelope field name that repeats its own leading text** (added 2026-08-26, `Origin: PR #55 R6`, LOW) — verbatim from the reviewer: *`aria-label="doc_status"` names the live region with an internal envelope field name that duplicates the region's own visible text, which is naming for the agent rather than for a screen-reader user — cutting against the row's stated evidence claim.* Evidence verbatim: *`src/sec10k/web/static/index.html:327` `aria-label="doc_status"`; the banner's own rendered content is `doc_status: <status>` (`index.html:831`). The PR's own artifact shows the duplication: `tasks/reviews/d10-agent-walk.json:107` `- status "doc_status": "doc_status: success - 18 extracted . 5 incorporated_by_reference fixture: aapl-2025"`. A screen reader announcing name-then-content speaks the token twice. `check_banner_status_role` accepts any non-empty name, so nothing binds this either way.* Acceptance verbatim: *The banner carries a human-readable name (e.g. 'extraction status') that is not a verbatim repeat of its own leading text, or the row's 'screen-reader correctness' evidence claim is qualified to say the name was chosen to match the envelope field*

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
