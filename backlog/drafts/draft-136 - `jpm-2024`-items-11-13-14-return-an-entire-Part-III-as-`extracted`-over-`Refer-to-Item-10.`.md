---
id: DRAFT-136
title: >-
  `jpm-2024` items 11/13/14 return an entire Part III as `extracted` over `Refer
  to Item 10.`
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-155
  - '`tasks/reviews/d13-auditor-verdicts.md` §2.8 (blind extraction-auditor pass'
  - D13); `evals/fixtures/jpm-2024/filing.htm`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`jpm-2024` items 11/13/14 return an entire Part III as `extracted` over `Refer to Item 10.`** (added 2026-08-27, Origin: D13 auditor pass) — verbatim from the auditor: *"jpm Items 11, 13 and 14 are `'Refer to Item 10.'` at `0.75 / review_required=False, status=extracted`. Item 10's own span is executive-officer biography text. JPMorgan's Part III is incorporated by reference through a two-hop pointer, and the classifier follows none of it — so an entire Part III comes back `extracted`."* This is a TWO-HOP internal pointer: the item points at item 10, and item 10 points at the proxy statement. ADR-038's R3 resolves one hop only and deliberately says so, so this shape is outside what D13 adjudicated; the first hop lands inside a span, which under R3 would read `correct`, while the answer a consumer wants is in a document nobody fetched

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
