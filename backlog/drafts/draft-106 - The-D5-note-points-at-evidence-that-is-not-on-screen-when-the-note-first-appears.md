---
id: DRAFT-106
title: >-
  The D5 note points at evidence that is not on screen when the note first
  appears
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-123
  - '`tasks/reviews/pr46-r3.json` finding R13'
  - evidence and acceptance verbatim
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The D5 note points at evidence that is not on screen when the note first appears** (added 2026-08-24, Origin: PR #46 R13) — the merge added a sentence saying the Markdown form difference 'is stated in the pane's own evidence'. But `render()` un-hides `#bp-note` and, ten lines later, resets `#pane` to the 'Select an item to read its extracted text.' placeholder; the `details.pane-meta` carrying the `markdown` entry is written only by `show(i)` and renders collapsed even then. Measured live at 1280x860 on ge-1994 with exclude and markdown both ticked: immediately after extraction `noteVisible True, paneMeta False`; after clicking the first item `noteVisible True, paneMeta True, metaOpen False`. So at the one moment the reader meets the sentence, the thing it points at does not exist

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
