---
id: DRAFT-25
title: What the contrast check does NOT guard
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-26
  - '`src/repo_hygiene/css_contrast.py` module docstring'
  - >-
    which now enumerates the same three holes; `_demo` pins the `fg_from`
    binding
  - the rule-boundary anchoring and the `color-scheme` non-leak
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What the contrast check does NOT guard** (added 2026-08-21 round-1, corrected 2026-08-21 round-2 after review falsified the original wording, Origin: PR #18) — `src/repo_hygiene/css_contrast.py` guards the numbers S3 publishes, so its holes are the holes in that guarantee. It reads token **values** live; every colour-carrying ground layer is `{"from": "<selector>"}` and read from that rule's `background` (round-2b — they had been literal copies of the CSS, so the round-2 banner fix could be silently reverted while the case stayed green at a rendered 4.47:1); and for the 39 of 46 pairs carrying `fg_from` it asserts the named rule still paints the token the pair measures. It does **not** resolve the CSS cascade, so it is blind to: (a) an element/ground combination nobody added to the pair list, and `body`'s gradient overlay layers, which come from `background-image` rather than a `background` colour and so stay literals (the `var(--grid)` inside them is still live); (b) the 7 pairs with no `fg_from` (inherited-color elements) — repointing their rule passes green; (c) any *other* rule winning the cascade for a pair's element — a later `#sidebar span{color:…}`, an `opacity` on an ancestor, an inline style. `rule_opacity`/`rule_color` read one literal selector each and nothing else. Separately, `parse_tokens` assumes dark-default plus a `prefers-color-scheme:light` override and raises `ValueError` on any other shape. The round-1 version of this row claimed the pair list was the only hole and that 'a color that moves is caught' — round-2 R13 falsified both

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
