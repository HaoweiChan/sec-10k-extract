---
id: DRAFT-6
title: 'Three `app.py` line refs in this table are stale, and D12 moved them again'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-6
  - '`tasks/reviews/pr54-r1.json` finding R3; the row it is about'
  - >-
    higher in this table; the pending ADR-019 line-ref cleanup this is
    consistent with
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Three `app.py` line refs in this table are stale, and D12 moved them again** (added 2026-08-26, Origin: PR #54 R3) — verbatim from the reviewer: *The diff shifts app.py line numbers that a committed tasks/TODO.md debt row cites, leaving the citations further out of date than they already were. tasks/TODO.md:113 cites SOURCE_CACHE at src/sec10k/web/app.py:50, the ponytail: marker at app.py:47, and the honest-miss path at app.py:211-214. On origin/main those were 49 / 46 / ~207; after this diff they are 54 / 48 / 244-248. No check catches it — the gate is green with all three refs wrong.* Acceptance if taken: the row's line refs match the post-D12 file, or are replaced with symbol refs such as `app.py::api_source`. **Widened 2026-08-26 by the PR #57 merge audit** (no new row, deliberately — a new row would shift every `tasks/TODO.md:NNN` self-ref below it and add to the very rot it describes). Re-verifying every `file:line` citation in this table found five more that are wrong at `origin/main` 6b37ffa too, i.e. not this branch's doing: `tasks/TODO.md:90` cites `src/sec10k/eval_adapter.py:270-276` for "sums all extracted spans" (that region is the offsets/status check on both trees); `:96` cites `src/sec10k/extract.py:111` for `body = text[c["heading_end"]:c["end"]]` (a docstring line on both); `:116` cites `src/sec10k/eval_adapter.py:281-282` for the boilerplate non-blank slice; `:120` cites `src/sec10k/web/view.py:62-63` for the `display_text` duplication; `:199` cites `src/sec10k/extract.py:126-127` for the `normalization_collapse` return (a docstring line on both). The two rows this branch DID move were repaired in place rather than deferred: `:80`'s two `view.py` refs (+1 from D12's `import hashlib`) and `:217`'s three `extract.py`/`validate.py` refs (D8 inserted above all of them). `ledger-line-refs`' `min_refs` 9 covers only the refs that quote their target; none of these eight does, which is why the gate was green with all of them wrong.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
