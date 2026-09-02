---
id: DRAFT-81
title: An unclosed bold carrier leaks `strong` to following blocks
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-98
  - ADR-032 §b2
  - §e (measured); no case pins the leak count
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**An unclosed bold carrier leaks `strong` to following blocks** (added 2026-08-23, Origin: S9) — a bold context closes at the matching end tag, so an unclosed `<b>`/`<font style=bold>` marks every later block strong until the next same-name end tag: `malformed-html` (15 `</font>` removed from premier-pacific-2016) has 177 strong blocks where its source has 79. The text is untouched; only the flag is wrong

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
