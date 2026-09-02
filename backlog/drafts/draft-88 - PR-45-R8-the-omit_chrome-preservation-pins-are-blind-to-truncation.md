---
id: DRAFT-88
title: 'PR #45 R8: the omit_chrome preservation pins are blind to truncation'
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-105
  - '`tasks/reviews/pr45-r3.json`'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**PR #45 R8: the omit_chrome preservation pins are blind to truncation** (added 2026-08-24, Origin: PR #45 R8) — a renderer returning only the first half of each stripped window passes `blocks-omit-chrome` whole, because both preserved snippets sit very early in their windows (offset 47375 in a ~1.36M-char document window; 201373 is 75 chars into item 15's ~1.01M-char span); measured with a half-truncating `to_markdown` variant on a temp copy of 50dfd2b — case passed. The empty-render and chrome halves are pinned; only truncation escapes

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
