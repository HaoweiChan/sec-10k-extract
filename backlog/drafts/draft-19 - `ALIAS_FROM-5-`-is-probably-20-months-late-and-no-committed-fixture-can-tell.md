---
id: DRAFT-19
title: >-
  `ALIAS_FROM["5"]` is probably 20 months late, and no committed fixture can
  tell
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-19
  - >-
    ADR-023 §f; **corrected PR #17 R1** — the item-5 check in
    `evals/adversarial/era-label-bac-2006.json` bounds `ALIAS_FROM["5"]` from
    ABOVE only (period end 2006-12-31) and is blind to the 2004-03-15 move this
    row contemplates
  - >-
    which left the gate green; the two-sided assert in
    `src/sec10k/segment.py::_demo` is what now catches it
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`ALIAS_FROM["5"]` is probably 20 months late, and no committed fixture can tell** (added 2026-08-20, T14/A6) — the table dates Item 5's "…and Issuer Purchases of Equity Securities" caption to 2005-12-01 (the Securities Offering Reform date that brought 1A/1B). The A6 diff reads it as Release 33-8335's (*Purchases of Certain Equity Securities by the Issuer and Others*, 2003-11-10), whose Item 703 disclosures bind periods ending on or after 2004-03-15. Every filing with a period end in that 20-month band renders a caption its era had already replaced

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
