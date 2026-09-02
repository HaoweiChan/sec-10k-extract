---
id: DRAFT-47
title: Two of the three location-var assertions in `build-identity` cannot fail
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-59
  - >-
    `src/repo_hygiene/eval_adapter.py` (the `GIT_LOCATION_VARS` loop in
    `check_build_identity`); `src/sec10k/web/build_id.py` `GIT_LOCATION_VARS`
    and its comment; `tasks/reviews/pr31-r2.json` R13
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Two of the three location-var assertions in `build-identity` cannot fail** (added 2026-08-22, Origin: PR #31 R13) — Two of the three per-variable location-var assertions cannot fail: with a non-repository cwd, GIT_WORK_TREE and GIT_COMMON_DIR alone never make `git rev-parse` answer, so only GIT_DIR binds the scrub the code and prose describe as covering all three. **Evidence (verbatim):** src/repo_hygiene/eval_adapter.py:973-981 loops over GIT_LOCATION_VARS; control measurement with the scrub removed and cwd a temp dir: GIT_DIR -> rc 0, '537dfdb'; GIT_WORK_TREE -> rc 128 'not a git repository'; GIT_COMMON_DIR -> rc 128. Mutation M8b (`_rev_parse` strips GIT_DIR only, keeps GIT_WORK_TREE and GIT_COMMON_DIR) -> check_build_identity returns 0 failures, versus 2 for the full-scrub-removal M8. **Repro:** Rebind build_id._rev_parse to a version whose env filter excludes only 'GIT_DIR', then ea.check_build_identity(case) -> [] (green). **Acceptance (verbatim):** Either the two extra assertions run in a state where those variables can actually redirect the answer (e.g. a real checkout as `root` with GIT_COMMON_DIR pointed at another repo), or the comment at build_id.py:31-36 and the case docstring stop claiming all three are held by a check. Re-measured in this round's process-isolated run: mutation M8b (strip `GIT_DIR` only, keep `GIT_WORK_TREE` and `GIT_COMMON_DIR`) is the ONE measurement out of fourteen that comes back green — 0 failures, against 2 for the full-scrub removal M8 and 3 for M8 under an ambient `GIT_DIR`. Recorded, not fixed: `src/sec10k/web/build_id.py`'s comment and `check_build_identity`'s docstring both still describe the scrub as covering all three variables, and only `GIT_DIR` is actually held by a check.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
