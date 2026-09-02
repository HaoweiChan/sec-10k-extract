---
id: TASK-3
title: 'The eval harness''s one escalating call is safe by convention, not by structure'
status: To Do
assignee: []
created_date: '2026-09-02 17:45'
labels: []
dependencies: []
references:
  - TODO.md TD-161
  - '`src/sec10k/eval_adapter.py:524`; PR #61 R9 (note only'
  - no action requested)
priority: low
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The eval harness's one escalating call is safe by convention, not by structure** (added 2026-08-27, Origin: PR #61 R9) — `extract_items(path, escalate=True)` at `src/sec10k/eval_adapter.py:524` is the only place the eval harness asks for the paid path. It is safe today because the cases that reach it name documents whose trigger stays quiet, so `route()` returns before any client is built; that is a property of the case tags, not of the harness. A case tagged onto a collapsing fixture would make `python3 -m evals.run` reach for a credential, and with one on the host it would spend. Measured safe: the reviewer observed zero outbound connections under both the invariant and fast suites, and `escalation-seam-offline` proves no gate import loads a network module. Acceptance if taken: the harness refuses to escalate unless the case opts in explicitly (an `allow_escalation` key, absent by default), watched red against a case that asks for a collapsing fixture

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
