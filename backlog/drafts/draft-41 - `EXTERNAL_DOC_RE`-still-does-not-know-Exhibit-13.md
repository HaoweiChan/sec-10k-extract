---
id: DRAFT-41
title: '`EXTERNAL_DOC_RE` still does not know ''Exhibit 13'''
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-45
  - >-
    `src/sec10k/segment.py` `EXTERNAL_DOC_RE`;
    `evals/adversarial/ibr-security-holders.json` provenance (the 'OUT OF THIS
    FIX' sentence)
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`EXTERNAL_DOC_RE` still does not know 'Exhibit 13'** (added 2026-08-22, Origin: gates-2026-08-22 T4-1, the finding's third probe) — verbatim from the reviewer's evidence: *'Exhibit 13 to this Form 10-K' MISSES.* A pointer whose only external-document term is the exhibit number ('incorporated by reference to Exhibit 13 hereto') would still classify `extracted` at 0.95

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
