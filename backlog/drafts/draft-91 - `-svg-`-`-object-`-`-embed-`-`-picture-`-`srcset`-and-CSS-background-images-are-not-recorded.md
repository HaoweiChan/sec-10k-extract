---
id: DRAFT-91
title: >-
  `<svg>`, `<object>`, `<embed>`, `<picture>`/`srcset` and CSS background images
  are not recorded
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-108
  - '`specs/decisions/ADR-033-image-reference-annotation.md` §e row 4 and §j1'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`<svg>`, `<object>`, `<embed>`, `<picture>`/`srcset` and CSS background images are not recorded** (added 2026-08-23, Origin: S10) — ADR-033 §e rules the annotation to `<img>` only. Zero of any other form carries a document graphic in the 42 committed filing fixtures, so nothing can be pinned red today; but an inline `<svg>` chart in a filing outside the corpus would be missed in total silence, which is INV-0's failure class. Named rather than guessed at: adding a tag to the recorder is three lines, and the reason not to is that no committed case could prove it right.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
