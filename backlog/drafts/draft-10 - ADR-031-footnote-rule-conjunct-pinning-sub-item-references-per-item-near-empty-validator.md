---
id: DRAFT-10
title: >-
  ADR-031 footnote rule: conjunct pinning, sub-item references, per-item
  near-empty validator
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-10
  - '`tasks/reviews/pr42-r1.json` R2/R3/R4; ADR-031 §b4'
  - §i
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**ADR-031 footnote rule: conjunct pinning, sub-item references, per-item near-empty validator** (added 2026-08-23, `Origin: PR #42 R2/R3/R4`) — R2 (LOW): two of the rule's three conjuncts (same asterisk run on the heading; footnote names THIS code) are pinned only by `segment._demo`, not by any fast/invariant case; evidence verbatim: "In-memory mutation appending `*` to every heading_text before `footnote_pointer` -> zero status changes on 47 docs, ba-2003-asterisk-ibr green. Only `_demo` (run by ci.yml, not by the eval gate) asserts the `**` vs `*` and not-named cases (src/sec10k/segment.py:862-867). ADR-031 §b4 'each is pinned (§h)' is true only via the self-check." — corrected in place: ADR-031 §b4 now says the marker-run and named-code conjuncts are pinned by the CI self-check only. R3 (LOW): `ITEM_LIST_RE` reads a dotted or parenthesised sub-item reference as a top-level code; evidence verbatim: "ITEM_LIST_RE on 'Item 5.03 of Form 8-K' -> {'5'}; axp-2008@326904 and xom-2021@385888 are two of the census's 11 non-external lines that carry this shape." — corrected in place: ADR-031 §i names sub-item references as not guarded (regex unchanged, so the census 14 / 3 figures stand; the lookahead is deferred because a list ending a sentence must still name its last code). R4 (LOW): the triage note's per-item near-empty-success validator is tracked nowhere once the Debt row is struck; evidence verbatim: "src/sec10k/eval_adapter.py:270-276 sums all extracted spans; tasks/TODO.md struck row; ADR-031 §i lists only the furniture-only body as undecided." — corrected in place: ADR-031 §i bullet names it as unbuilt

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
