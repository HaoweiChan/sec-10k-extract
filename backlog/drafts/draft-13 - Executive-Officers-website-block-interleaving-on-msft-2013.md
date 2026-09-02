---
id: DRAFT-13
title: Executive-Officers/website-block interleaving on msft-2013
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-13
  - '`evals/adversarial/msft-2013-website-block.json` (`debt` suite); ADR-019 §f'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Executive-Officers/website-block interleaving on msft-2013** — the `EXEC_OFFICERS_RE` fix (see T11 row above) correctly excludes the officer bios from Item 1, but on this one fixture a genuine 1,643-char piece of Item 1 content ("Available Information") sits *after* the bios and is lost with them, because INV-S2 forbids a discontiguous span

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
