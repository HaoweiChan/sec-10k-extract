---
id: DRAFT-84
title: >-
  Definition lists, blockquotes, HTML `<pre>` and `<caption>` are paragraphs; a
  paragraph split by a page break is two blocks; nested tables get no block
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-101
  - ADR-032 §b1
  - §b2
  - §e; `msft-2013-blocks` window 2
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Definition lists, blockquotes, HTML `<pre>` and `<caption>` are paragraphs; a paragraph split by a page break is two blocks; nested tables get no block** (added 2026-08-23, Origin: S9) — `<dl>/<dt>/<dd>` (intc-2002, tgt-2002) and any `<blockquote>` are paragraphs; HTML `<pre>` (0 in the corpus) would be a paragraph since `_Plain` collapses its whitespace; a `<caption>` (0 in the corpus) would sit inside the table span but outside every cell; msft-2013's `…Our segments` / `provide management with…` paragraph is two blocks around the page break; an inner table's record gets no block of its own

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
