---
id: DRAFT-32
title: >-
  Three LOW findings from PR #25 round 2 — every one of them says the checks
  cover LESS than they do
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-34
  - '`tasks/reviews/pr25-r2.json` findings R8–R10'
  - >-
    evidence and acceptance verbatim; R9 and R10 were re-measured independently
    by the orchestrator (MIN_SPREAD 0.83 → `[FAIL] boilerplate-section-heads`
  - 74/75; above-only → 143 and below-only → 143)
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Three LOW findings from PR #25 round 2 — every one of them says the checks cover LESS than they do** (added 2026-08-22, Origin: PR #25 R8–R10) — (a) **R8** the `boilerplate_stripped` sub-assertion labelled "the reconstruction identity" (`src/sec10k/eval_adapter.py:281-282`) cannot fail: it tests only that a published span's slice of `normalized_text` is non-blank, which `find_chrome` guarantees by construction, and it never passes anything through `strip_chrome`. **R2 is still genuinely closed** — the reviewer monkeypatched seven wrong `strip_chrome` implementations (total no-op, +1 shift, remove-head-N, remove-tail-N, window-relative spans, start/end ignored, end-1 off-by-one) and all seven went red via the other four sub-assertions; (b) **R9** `tasks/reviews/pr25-r1-resolution.json` `unverified[2]` says `MIN_SPREAD` "is pinned only from below" — false: jpm-2024's running head has spread 0.8202, so `MIN_SPREAD = 0.83` drops the fixture from 572 spans to 0 and turns `boilerplate-section-heads` red. It is pinned on both sides (red at 0.40 and 0.83, green across 0.65–0.82). `MIN_REPEATS` genuinely is one-sided: 8→20 leaves fast 75/75 with only `_demo` red; (c) **R10** `boilerplate-section-heads`' provenance says jpm-2024 "puts its page number ABOVE the running head" and so exercises the `neighbour(i, -1)` branch. The fixture actually splits 143/143, so BOTH single-direction mutations give 143 and both turn the case red — the case pins both halves of the adjacency rule, not the one its provenance names

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
