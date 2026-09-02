---
id: TASK-2
title: >-
  `evals/snapshot.py` extracts the `repo_hygiene` CHECK fixtures as if they were
  filings
status: To Do
assignee: []
created_date: '2026-09-02 17:45'
labels: []
dependencies: []
references:
  - TODO.md TD-159
  - >-
    `evals/snapshot.py::corpus`; measured 2026-08-27 while proving the
    escalate-default-on change moved no default-flag digest
priority: low
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`evals/snapshot.py` extracts the `repo_hygiene` check fixtures as if they were filings** (added 2026-08-27, Origin: the escalate-default-on verification) — `corpus()` walks every subdirectory of `evals/fixtures` and skips only `.md`, so the eight `.py` and `.html` files in `evals/fixtures/repo_hygiene/` — which are deliberately-broken SOURCE fixtures for the wire checks, not 10-K filings — are run through `extract_items` and land in the snapshot. Measured: the escalate-default-on branch's snapshot differs from `origin/main` (d83b8a2) at exactly six entries, all of them `repo_hygiene/…`, while all 44 real filings are byte-identical. The instrument still answers correctly if you read the per-entry diff, but its headline — one sha256 per corpus, `cmp before.json after.json` — reports a difference for a change that touched no extraction code, which is the failure mode a "nothing moved" instrument must not have. Acceptance if taken: `corpus()` skips `repo_hygiene` (or, better, takes the fixture list from the same predicate `web/fixtures.py::list_fixtures` uses, so the snapshot and the inspector's dropdown cannot disagree about what a fixture is), with the 44-file count asserted so the skip cannot silently widen

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
