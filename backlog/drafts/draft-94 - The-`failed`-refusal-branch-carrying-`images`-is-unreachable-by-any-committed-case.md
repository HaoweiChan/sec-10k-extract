---
id: DRAFT-94
title: >-
  The `failed` refusal branch carrying `images` is unreachable by any committed
  case
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-111
  - >-
    `src/sec10k/extract.py:126-127`; `specs/001-sec10k-contract.md`;
    `evals/adversarial/images-refusal-path.json`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The `failed` refusal branch carrying `images` is unreachable by any committed case** (added 2026-08-24, Origin: PR #44 R6) — verbatim from the reviewer: *`src/sec10k/extract.py:126-127` (normalization_collapse return) passes `images=imgs`, and `specs/001-sec10k-contract.md:208` says "Carried on refusal envelopes too when asked for" [cited as :157 at review time, re-anchored to :187 on 2026-08-26 when D8/ADR-035 inserted 25 lines above it, and to :208 on 2026-08-28 when ADR-042 inserted the collective-pointer and cross-reference clauses above it; the line NUMBER moves, the quoted sentence never has]; `images-refusal-path` exercises only `unsupported` (aapl-2026-10q). The only `failed` filing fixtures are truncated-download and the repo_hygiene files, all with 0 images, so the `failed` line is a code path no committed case can reach — the same untestable-path concern ADR-033 §b1 invokes against attribute-only sizing.* Acceptance if taken: a case or self-check asserts the list survives the `failed` return, or the contract sentence names `unsupported` only.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
