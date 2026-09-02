---
id: DRAFT-30
title: '`anchor.py` is a hand-maintained Python mirror of the browser anchor JS'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-32
  - >-
    verified in `tasks/reviews/pr21-r3.json`; the contract case is
    `evals/adversarial/ui-anchor-contract.json`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`anchor.py` is a hand-maintained Python mirror of the browser anchor JS** (added 2026-08-22, Origin: PR #21 orchestrator) — `src/sec10k/web/anchor.py` (347 lines) reimplements the anchoring algorithm that actually ships in `src/sec10k/web/static/index.html`, and `ui-anchor-contract` gates the **Python copy**, not the JS the user runs. Round 3 confirmed the two match line-for-line today and that the one asymmetry found (the JS decodes HTML entities via a scratch `<textarea>`, Python does not) cannot manifest, because `heading_text` comes from `normalized_text`, which `src/sec10k/normalize.py` already passes through `html.unescape`. **The risk is drift, not a present defect**: a future edit to either copy alone leaves the suite green while the product changes, which is the same second-copy hazard INV-S2 exists to prevent and which requirement 7 of this very task was solved by avoiding

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
