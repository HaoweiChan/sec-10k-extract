---
id: DRAFT-43
title: >-
  Edge shapes of the `<title>` skip: an unclosed `<title>` now swallows the
  whole document into `failed`; `<noscript>` text in `<head>` still leaks
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-52
  - '`src/sec10k/normalize.py` `SKIP_TAGS`'
  - '`_Plain.handle_starttag`/`handle_endtag` (`skip_depth`)'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Edge shapes of the `<title>` skip: an unclosed `<title>` now swallows the whole document into `failed`; `<noscript>` text in `<head>` still leaks** (added 2026-08-22, Origin: PR #30 R6, LOW) — verbatim from the reviewer: *Edge shapes of the title skip: an unclosed <title> now swallows the whole document (html.parser treats title as RCDATA on 3.11 and 3.14, skip_depth never returns to 0) -> 0 chars -> failed/normalization_collapse, where main emitted tag soup; <noscript> text inside <head> still leaks; self-closing <title/>, uppercase <TITLE>, entities and nested tags in the title all behave. No committed or held-out fixture has a <title> outside <head>, an unclosed one, <noscript> or <textarea> (34 fixtures have exactly one open/one close, all before <body>).* Evidence, verbatim: *select_and_normalize('<html><head><title>x<meta charset=x></head><body><p>FORM 10-K</p>...') -> '' on both python3.11 and 3.14.6; '<noscript>JS OFF TEXT</noscript>' in head -> 'JS OFF TEXT\n\nFORM 10-K'.*

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
