---
id: DRAFT-31
title: Inspector source cache is process-local
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-33
  - >-
    `src/sec10k/web/app.py:47` — the `ponytail:` marker names both the ceiling
    and the trigger
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Inspector source cache is process-local** (added 2026-08-22, Origin: `ponytail:` marker — one of four in the repo, not the only one: the others are `src/sec10k/boilerplate.py:56`, `src/repo_hygiene/eval_adapter.py:699` and a docstring-form one at `src/repo_hygiene/css_contrast.py:9`; corrected 2026-08-22 in S2) — `SOURCE_CACHE` (`src/sec10k/web/app.py:50`) is an in-process `OrderedDict` capped at 3 documents, so a restart or a second uvicorn worker empties it and the S4 compare pane's token stops resolving. **Fails honestly, not silently**: the miss path returns 404 `source_not_cached` with "re-run the extraction" (`app.py:211-214`), never a stale or fabricated body

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
