---
id: DRAFT-46
title: >-
  `BUILD_SHA` holding non-UTF-8 bytes raises out of `/api/meta` as a 500 instead
  of resolving to `unknown`
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-58
  - >-
    `src/sec10k/web/build_id.py` `build_sha()` (`except OSError`); `NOT_A_SHA`
    in `src/repo_hygiene/eval_adapter.py`; `tasks/reviews/pr31-r1.json` R8
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`BUILD_SHA` holding non-UTF-8 bytes raises out of `/api/meta` as a 500 instead of resolving to `unknown`** (added 2026-08-22, Origin: PR #31 R8) — `build_sha` catches only OSError, so a BUILD_SHA holding non-UTF-8 bytes raises out of `/api/meta` (HTTP 500) instead of resolving to `unknown`. **Evidence (verbatim):** src/sec10k/web/build_id.py:33-36 — `read_text()` inside `try/except OSError`; UnicodeDecodeError is a ValueError. Measured: writing b'\xff\xfe abc' to BUILD_SHA and calling `git_sha(root, {'PATH': ...})` raises UnicodeDecodeError, which propagates through app.py:127. NOT_A_SHA (eval_adapter.py:841) claims to cover 'everything a BUILD can hand the runtime that is NOT a build identity' but has no non-UTF-8 member, so no case goes red. Low because a build writing binary into that path is not a realistic input. **Repro:** `cd <worktree> && python3 -c "import os,tempfile,pathlib;from src.sec10k.web import build_id;td=tempfile.mkdtemp();pathlib.Path(td,'BUILD_SHA').write_bytes(b'\xff\xfe abc');print(build_id.git_sha(td,{'PATH':os.environ['PATH']}))" -> UnicodeDecodeError` **Acceptance (verbatim):** `except (OSError, ValueError)` (or `read_bytes` + decode with errors handled), with a non-UTF-8 member added to NOT_A_SHA and watched red first. Note the overclaim is part of the debt: `NOT_A_SHA`'s comment says it covers everything a build can hand the runtime that is not a build identity, and it does not — it now says so, and names this row.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
