---
id: DRAFT-138
title: >-
  `spatz-2014` items 8 and 15 point at each other and the financial statements
  are in neither span
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-157
  - >-
    ADR-038 §c5; `tasks/reviews/d13-span-dump.txt`;
    `evals/fixtures/spatz-2014/filing.htm`
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`spatz-2014` items 8 and 15 point at each other and the financial statements are in neither span** (added 2026-08-27, Origin: D13) — item 8's body says the statements "are included in this report on pages 15 through 22"; item 15's body says `Financial Statements: as referenced in Item 8 hereof`. The cycle closes with the statements in neither: `(?i)report of independent registered public accounting firm` matches **exactly once in the whole document, at offset 48,815**, inside the 17,307-char region after item 15's span ends at 47,890. Also noted on the same filing: `heading_text` is the bare `Item 8.` with the title `Financial Statements and Supplementing Data` falling into the BODY rather than the heading line

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
