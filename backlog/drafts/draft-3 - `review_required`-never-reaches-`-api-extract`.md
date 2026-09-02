---
id: DRAFT-3
title: '`review_required` never reaches `/api/extract`'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-2
  - >-
    `tasks/reviews/pr57-r1.json` finding R2 (its two `view.py` line refs
    re-verified and shifted +1 when `origin/main` 6b37ffa merged in — D12 added
    an `import hashlib` above them; the quoted code is unchanged);
    `src/sec10k/web/view.py:84-94`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`review_required` never reaches `/api/extract`** (added 2026-08-26, Origin: PR #57 R2) — verbatim from the reviewer: *`src/sec10k/web/view.py:84-94` builds each item by explicit whitelist (`item, part, title, status, confidence, method, heading_text, start, end, chars, text, truncated, evidence`); `review_required` is absent, so `build_view` silently omits the field `specs/001-sec10k-contract.md:81` now marks required on every status. `meta` is passed through whole (view.py:100) so `meta.coverage` does survive — the omission is item-level only. The demo failure D8 exists to fix was read off this exact surface (postmortem §8 gap 2). The item's `evidence.warnings` does survive and D7 renders it, so the UI is not silent, which is why this is LOW rather than a contract break.* Repro: `python3 -c "import sys; sys.path.insert(0,'.'); from src.sec10k.extract import extract_items; from src.sec10k.web.view import build_view; print('review_required' in build_view(extract_items('evals/fixtures/cvx-2015/filing.htm'))['items'][0])"` → `False`

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
