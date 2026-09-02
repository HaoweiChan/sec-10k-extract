---
id: DRAFT-42
title: >-
  T3 cold-review `vacuous_coverage`: three normalization paths no check can
  reach
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-49
  - '`src/sec10k/normalize.py` `normalize` (txt branch)'
  - '`_Plain.handle_data`; `src/sec10k/eval_adapter.py` check vocabulary'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**T3 cold-review `vacuous_coverage`: three normalization paths no check can reach** (added 2026-08-22, Origin: gates-2026-08-22 T3 vacuous_coverage) — verbatim from the reviewer: (1) *txt-era CRLF/strip branch unasserted by any case*; (2) *`<pre>` unhandled and untested; an ASCII 10-K wrapped in `<pre>` normalizes to one line and yields all-missing*; (3) *meta.format_era / document_selected unreadable by any check type*. Implementer note on (2), checked not assumed: `pre` IS in `BLOCK_TAGS`, so the element's edges break lines, but `_Plain.handle_data` collapses every newline inside the chunk to a space — a `<pre>`-wrapped fixed-width filing keeps its first and last line break and loses all the others, which is the one-line collapse the reviewer describes; no committed fixture has that shape

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
