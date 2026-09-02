---
id: DRAFT-67
title: >-
  PR #36 R3: the S2 gate record presented e6810a4 as the observed start of the
  sha chain
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-84
  - >-
    `tasks/reviews/pr36-r1.json` R3; `tasks/reviews/s2-postmerge-gate.json`
    (`verdict`
  - '`not_claimed`)'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**PR #36 R3: the S2 gate record presented e6810a4 as the observed start of the sha chain** (added 2026-08-23, Origin: PR #36 R3; **corrected in place in round 1**) — verbatim from the reviewer: *The verdict presents e6810a4 as the observed start of the sha chain and flags only 6c71ca6 as unobserved, but no /api/meta response ever showed e6810a4 either — only one move (1efc457 -> 1ed784c) was seen at both ends; the e6810a4 -> 1efc457 'move one' is inferred and not_claimed omits it.* Evidence, verbatim: *`tasks/reviews/s2-postmerge-gate.json` verdict: 'sha moved e6810a4 -> (6c71ca6, not observed) -> 1efc457e598d -> 1ed784ccf68e'; not_claimed lists only 6c71ca6 and the 1efc457 non-reproduction. No curl/meta observation of e6810a4 deployed exists on record; the only pre-S2 deployed observation is git_sha 'unknown'. DONE.md line: 'i.e. e6810a4 -> 1efc457 -> 1ed784c across the push-to-main redeploys'.* Corrected in place: verdict, `not_claimed` (now the full set: e6810a4 and 6c71ca6 never observed, one move seen end-to-end, no failed-to-move build, 1efc457 not reproduced by the implementer, no claim about when inside the 87–239 s window the image came up, and the record's own first version's errors), the S2 row's Status cell (and the DONE.md line it becomes when the row archives) all read '(e6810a4, 6c71ca6 not observed) -> 1efc457 observed -> 1ed784c observed' — two distinct real shas, one move seen at both ends, which still meets the gate's two-curl wording

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
