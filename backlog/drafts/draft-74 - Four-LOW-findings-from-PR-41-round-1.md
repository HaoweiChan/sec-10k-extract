---
id: DRAFT-74
title: 'Four LOW findings from PR #41 round 1'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-91
  - '`tasks/reviews/pr41-r1.json`'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Four LOW findings from PR #41 round 1** (added 2026-08-23, Origin: PR #41 R1/R2/R3/R4) — (a) **R1** present-tense corpus counts went stale with the new fixture directory and carry no dated marker: `docs/analysis-report.md` §4.2 '41 dev-corpus fixtures … 42 directories' and ADR-021 §b8 'Forty-two fixture directories' — at HEAD `iter_fixtures` yields 42 and there are 43 directories (the bench artifact of record stays n=41, ADR-030 §g says so); (b) **R2** `prompts/017` attributes the 7.4 largest/second-largest span ratio to a legitimate filing; re-measured wfc-2008 6.95, cvx-2015 5.76, mrk-1995 5.58 — 7.41 is jpm-2024, a `last_item_dominates` defect, as ADR-030 §b2 correctly lists; (c) **R3** ADR-030 §c reason 2 says 'no committed real filing, dev or held-out, fires' as evidence for the escalation ruling, while §g disclaims any held-out derivation — under `evals/heldout/README.md`'s burn rule (influence, not re-running) and the axp-2008 precedent the two statements are in tension; the dev false-positive set alone carries the argument; (d) **R4** ADR-020 §e condition 2 is met per ADR-030 §g but ADR-020 carries no dated in-place note; the T5-5 row's Where cell still points at 'the standing A non-last span … row above' (now struck and PROMOTED) and its Why cell still says none of the three classes is a one-line fix while class 1 is closed

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
