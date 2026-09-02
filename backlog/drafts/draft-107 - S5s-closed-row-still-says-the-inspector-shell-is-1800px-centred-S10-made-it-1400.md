---
id: DRAFT-107
title: >-
  S5's closed row still says the inspector shell is "1800px centred"; S10 made
  it 1400
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-124
  - >-
    `tasks/DONE.md:31`; `src/sec10k/web/static/index.html` header/main/footer
    rules; `evals/adversarial/ui-layout-centering.json` (value-blind
  - still green)
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**S5's closed row still says the inspector shell is "1800px centred"; S10 made it 1400** (added 2026-08-24, Origin: D5 merge 2) — `tasks/DONE.md:31` records S5's validation as an 1800px centred shell, and PR #44/#48 changed `header`/`main`/`footer` to `max-width:min(1400px,94vw)` (with `h1` 22px -> 40px and more header/main padding). No eval case went stale — `check_layout_centering` pins that a `max-width` and a centring margin are DECLARED, never which value — and D5's four measured widths are unaffected, since 94vw is below 1400 at 1280 and under, so the cap never binds there (confirmed with the instrument: identical grid tracks at all four widths)

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
