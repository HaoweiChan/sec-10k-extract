---
id: DRAFT-83
title: >-
  Styled paragraphs are never headings; Part headings are not promoted; txt-era
  items are one `pre` block
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-100
  - ADR-032 §b2
  - §b3
  - §e; `msft-2013-blocks` window 1
  - '`aapl-2025-blocks` window 1'
  - '`ge-1994-blocks`'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Styled paragraphs are never headings; Part headings are not promoted; txt-era items are one `pre` block** (added 2026-08-23, Origin: S9) — a bold/underlined/centered paragraph stays a paragraph (`strong` at most), `PART I` is a strong paragraph, sub-headings such as aapl-2025's `Macroeconomic and Industry Risks` render as `**bold**` not `##`, and a txt-era filing's item headings inside the single `pre` block are not promoted

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
