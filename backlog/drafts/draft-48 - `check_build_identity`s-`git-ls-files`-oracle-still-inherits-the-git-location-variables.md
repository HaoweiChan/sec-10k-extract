---
id: DRAFT-48
title: >-
  `check_build_identity`'s `git ls-files` oracle still inherits the git location
  variables
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-61
  - '`src/repo_hygiene/eval_adapter.py:1072-1074` — no `env=` filter'
  - >-
    twelve lines below the identical subprocess at `:1057-1060` that R10 gave
    one
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`check_build_identity`'s `git ls-files` oracle still inherits the git location variables** (added 2026-08-22, Origin: PR #31 R16) — verbatim from the reviewer: *the R10 fix was applied to one of the two ROOT git oracles in the same function: the `git ls-files` tracked-BUILD_SHA check still inherits the git location variables, so an ambient GIT_DIR can make it answer about a foreign repository.* Measured: with a scratch repo that tracks a file named `BUILD_SHA`, `GIT_DIR`/`GIT_WORK_TREE` pointed at it gives 1 failure ('BUILD_SHA is TRACKED') on a tree where `git ls-files -- BUILD_SHA` is empty; the inverse direction masks a genuinely tracked `BUILD_SHA`

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
