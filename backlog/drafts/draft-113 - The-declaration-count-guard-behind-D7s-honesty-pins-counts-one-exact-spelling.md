---
id: DRAFT-113
title: The declaration-count guard behind D7's honesty pins counts one exact spelling
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-130
  - '`tasks/reviews/pr53-r3.json` finding R10'
  - >-
    evidence and acceptance verbatim; `src/repo_hygiene/eval_adapter.py`
    `check_confidence_honesty` and its `ceiling` bullet 2
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The declaration-count guard behind D7's honesty pins counts one exact spelling** (added 2026-08-26, Origin: PR #53 R10) — `check_confidence_honesty` guards each whole-body pin with `seen = live.count(f"function {fn_name}(")`, a raw substring, while every other comparison in that function goes through `_squash`. A second declaration spelled `function docQual () {` (one space before the paren) leaves the count at 1, the body pin byte-equal, and the case green with two declarations in the file and the stub winning at runtime. A post-declaration rebind — `docQual = () => "";` or `coverageStrip = () => "";` above `render()` — is green for the same reason. Verified independently by the orchestrator, not taken on report

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
