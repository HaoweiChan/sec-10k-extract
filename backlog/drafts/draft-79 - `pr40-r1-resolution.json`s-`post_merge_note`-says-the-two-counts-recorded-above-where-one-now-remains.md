---
id: DRAFT-79
title: >-
  `pr40-r1-resolution.json`'s `post_merge_note` says "the two counts recorded
  above" where one now remains
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-96
  - '`tasks/reviews/pr40-r1-resolution.json`'
  - >-
    keys `post_merge_note` and `table_integrity`; `tasks/reviews/pr40-r3.json`
    R5
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`pr40-r1-resolution.json`'s `post_merge_note` says "the two counts recorded above" where one now remains** (added 2026-08-23, Origin: PR #40 R5) — verbatim from the reviewer: *the repair created a dangling self-reference: `post_merge_note` still opens 'The two counts recorded above', but the repair removed one of those two counts from the keys above it, leaving only one.* The two were `findings[1].verification`'s struck-row grep and `table_integrity`'s 'Debt row count unchanged at 91'; PR #40 R3 withdrew the second, and the note's trailing parenthetical acknowledges the withdrawal without fixing the count of counts

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
