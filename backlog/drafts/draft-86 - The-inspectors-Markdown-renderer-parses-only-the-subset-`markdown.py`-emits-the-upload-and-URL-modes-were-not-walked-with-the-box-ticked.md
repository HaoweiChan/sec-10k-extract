---
id: DRAFT-86
title: >-
  The inspector's Markdown renderer parses only the subset `markdown.py` emits;
  the upload and URL modes were not walked with the box ticked
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-103
  - ADR-032 §b5
  - §g; `tasks/reviews/s9-markdown-walk.json`
  - '`tasks/reviews/s3-browser-walk-s9.json`'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The inspector's Markdown renderer parses only the subset `markdown.py` emits; the upload and URL modes were not walked with the box ticked** (added 2026-08-23, Origin: S9) — `index.html::mdToHtml` handles ATX headings, paragraphs, whole-paragraph `**strong**`, `- `/`1. ` items, GFM tables and fenced pre; anything else in a Markdown string (none is emitted) renders as a paragraph; `tasks/reviews/s9_markdown_walk.py` checks the fixture mode in Markdown mode and the unticked default, and `s3_browser_walk.py` was re-run on the S9 build with the box unticked (`tasks/reviews/s3-browser-walk-s9.json`, `mode_failures: []`, font verdict DEGRADES as before) — the upload and URL modes with the box TICKED were not driven in a browser

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
