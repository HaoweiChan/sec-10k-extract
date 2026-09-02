---
id: DRAFT-93
title: evals/snapshot.py --self-check cannot fail if corpus() regresses
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-110
  - 'evals/snapshot.py:73-87; .github/workflows/ci.yml; ADR-033 §d'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**evals/snapshot.py --self-check cannot fail if corpus() regresses** (added 2026-08-24, Origin: PR #44 R5) — verbatim from the reviewer: *evals/snapshot.py:73-87: _demo builds its own dig lambda duplicating the dict literal at :51-58 instead of calling corpus. Drop "keys": sorted(r) from corpus's dict and --self-check still prints ok, while the "an added envelope key is a difference" property the docstring sells is gone. .github/workflows/ci.yml adds only python3 evals/snapshot.py --self-check; nothing in any suite runs corpus.* — with the reviewer's own note that the instrument does work today: mutating a scratch origin/main tree to emit an [IMAGE] placeholder into the text makes the two snapshots differ, and the shipped digests reproduce. Acceptance if taken: _demo drives corpus() against a two-file temp tree, one of them producing an extra envelope key.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
