---
id: DRAFT-110
title: '`evals/snapshot.py` extracts UI mutation fixtures as if they were filings'
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-127
  - >-
    `evals/snapshot.py` `corpus()` (the `os.listdir` walk and its `.md`-only
    skip); `tasks/reviews/d7-browser-walk.json` is the walk
  - the digest diff is in the D7 PR evidence pack
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`evals/snapshot.py` extracts UI mutation fixtures as if they were filings** (added 2026-08-26, Origin: D7) — the tool walks every subdirectory of `evals/fixtures` and runs `extract_items` on every non-`.md` file, so `evals/fixtures/repo_hygiene/`'s hand-broken HTML/py mutation fixtures are in the corpus: **14 of the 56** dev entries before D7, 15 of 57 after. Adding one UI regression fixture therefore moves the published corpus digest (`8c002dc…` -> `292fdc2…`) while every real filing's envelope is byte-identical, which is exactly the reading a display-only row's "default-flag digests must not move" acceptance is supposed to make easy. D7 had to diff the two snapshots entry-by-entry to show the 56 common entries were unchanged (`identical=True`, same `8c002dc…` both sides)

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
