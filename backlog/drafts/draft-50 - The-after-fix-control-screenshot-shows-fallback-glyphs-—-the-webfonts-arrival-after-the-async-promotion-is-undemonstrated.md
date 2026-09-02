---
id: DRAFT-50
title: >-
  The after-fix control screenshot shows fallback glyphs — the webfont's arrival
  after the async promotion is undemonstrated
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-64
  - >-
    `tasks/reviews/pr33-r1.json` R3; the two `fonts-control.png` files side by
    side
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The after-fix control screenshot shows fallback glyphs — the webfont's arrival after the async promotion is undemonstrated** (added 2026-08-22, Origin: PR #33 R3, LOW) — verbatim from the reviewer: *The after-fix control screenshot renders the fallback monospace glyphs, not JetBrains Mono, unlike the original control shot, so the committed evidence no longer shows the webfont ever applying on an online visitor after the fix; the record claims only FCP, so no published number is false, but the row's 'DEGRADES' framing implies the font still arrives and nothing committed demonstrates it.* Evidence: `tasks/reviews/s3-browser-walk-after-font-fix/fonts-control.png` (system monospace, slashed zero absent) vs `tasks/reviews/s3-browser-walk/fonts-control.png` (JetBrains Mono); after-fix control 97752 bytes vs refused/blackholed 97847 (identical md5)

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
