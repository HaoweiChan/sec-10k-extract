---
id: DRAFT-104
title: >-
  `boilerplate_applied` and the Markdown pane use two different definitions of
  "removed"
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-121
  - >-
    `src/sec10k/web/view.py` (`bp_applied` in the item loop vs the `to_markdown`
    call beside it); `evals/adversarial/blocks-omit-chrome.json` covers `omit`
    alone
  - '`ui-exclusion-note-trigger` covers the flag alone'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`boilerplate_applied` and the Markdown pane use two different definitions of "removed"** (added 2026-08-24, Origin: D5 merge) — in `blocks` mode the flag is computed from `strip_chrome(text, spans, s, e) != raw` while the body the reader sees comes from `to_markdown(..., omit=spans)`. Both implement ADR-026 s.d, but nothing pins them to each other, so a divergence would show as a note firing over a Markdown pane with no visible change, or the reverse

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
