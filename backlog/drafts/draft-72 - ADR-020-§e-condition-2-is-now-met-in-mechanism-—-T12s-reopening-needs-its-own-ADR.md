---
id: DRAFT-72
title: >-
  ADR-020 §e condition 2 is now met in mechanism — T12's reopening needs its own
  ADR
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-89
  - ADR-030 §g; ADR-020 §e.2
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**ADR-020 §e condition 2 is now met in mechanism — T12's reopening needs its own ADR** (added 2026-08-23, Origin: D3) — ADR-020 §e says any met condition 'reopens T12 with its own ADR'; condition 2 is 'the escalation-policy successor named in ADR-019 §d ships and gives non-last span dominance a doc-level signal'. ADR-030 ships it. On the two rows condition 2 names the signal is silent today (cvx-2015's largest non-last span 0.1986, msft-2013's 0.3581, both under ITEM_MAX 0.55), so neither document acquires a firing trigger — but the condition is about the mechanism, and the honest reading is that it is met. Whether 'should the fallback fire on it' is live, with ADR-020's row-4/5 objections (relocation ambiguity, INV-S2 contiguity) still standing, is a T12 question

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
