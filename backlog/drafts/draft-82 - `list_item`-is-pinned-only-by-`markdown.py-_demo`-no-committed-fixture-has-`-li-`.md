---
id: DRAFT-82
title: >-
  `list_item` is pinned only by `markdown.py::_demo`; no committed fixture has
  `<li>`
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-99
  - ADR-032 §b2
  - §e; `blocks-bullet-paragraphs`
  - '`msft-2013-blocks` window 3'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`list_item` is pinned only by `markdown.py::_demo`; no committed fixture has `<li>`** (added 2026-08-23, Origin: S9) — the corpus census (2026-08-23) finds 0 `<li>` in 34 HTML/iXBRL fixtures (intc-2002 and tgt-2002 use `<ul>` as an indent wrapper); bullet lists are glyph paragraphs (cat-2023, jpm-2024) or four-cell tables (msft-2013), which render as paragraphs and one-row tables respectively; nested lists render flat and every ordered item is written `1.`

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
