---
id: DRAFT-120
title: '`evals/report/history.jsonl` records runs at SHAs that are on no branch'
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-137
  - >-
    The rows themselves; `evals/run.py` `git_sha()` writes the SHA at run time
    and has no notion of reachability
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`evals/report/history.jsonl` records runs at SHAs that are on no branch** (added 2026-08-26, Origin: D6 / PR #52 R13) — five rows carry `sha: 3f5078a`, a commit amended away during the PR #52 round-1 repair, so the runs are real and reproducible but the SHA resolves to nothing. Seven earlier unreachable SHAs are already committed in that file, so this is not new with D6; what is new is that it now has a name

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
