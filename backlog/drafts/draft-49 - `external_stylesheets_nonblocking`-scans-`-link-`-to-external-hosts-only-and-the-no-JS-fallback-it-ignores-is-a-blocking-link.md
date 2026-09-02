---
id: DRAFT-49
title: >-
  `external_stylesheets_nonblocking` scans `<link>` to external hosts only, and
  the no-JS fallback it ignores is a blocking link
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-62
  - >-
    `src/repo_hygiene/eval_adapter.py` `check_external_stylesheets_nonblocking`
    docstring; `tasks/reviews/s3-browser-walk-after-font-fix.json`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`external_stylesheets_nonblocking` scans `<link>` to external hosts only, and the no-JS fallback it ignores is a blocking link** (added 2026-08-22, Origin: S3-FONT disposition on `task/S3`) — (a) `@import url(https://…)` inside `<style>` and a `<script src>` on an external host are the same blackhole failure and are not scanned; `index.html` has neither today, so there is no instance to watch red first; (b) the `<noscript>` copy of the Google Fonts link is render-blocking for a JS-off visitor on a blackholing network, stripped by the check on purpose; (c) `tasks/reviews/s3_browser_walk.py`'s blackhole route holds the request open with `wait_for_timeout(600000)`, so `p2.close()` prints a `TargetClosedError` traceback from the route callback on the re-run — cosmetic, exit code 0 and the record are unaffected; whether the 2026-08-22 defect run printed the same is not recorded

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
