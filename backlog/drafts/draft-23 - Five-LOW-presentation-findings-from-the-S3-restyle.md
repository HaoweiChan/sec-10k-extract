---
id: DRAFT-23
title: Five LOW presentation findings from the S3 restyle
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-24
  - '`tasks/reviews/pr18-r1.json` findings R7–R11'
  - with evidence and acceptance verbatim
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Five LOW presentation findings from the S3 restyle** (added 2026-08-21, Origin: PR #18 R7–R11) — (a) **R7** amber is now simultaneously brand chrome and the warn/ambiguous status color (`--warn`/`--amb` both resolve to `--amber-ink`), so `.b.lo`'s "look here" flag is the same hue as the `.it .code` item number one line above it, and `.s-success_with_warning` vs `.s-ambiguous` differ only by 10% vs 12% background alpha of an identical color; (b) **R8** the `incorporated_by_reference` badge is painted `--accent`, whose own comment in the file says cyan is "interactive only", while `summary` — which does have a cyan hover — is missing from the 150ms transition selector list; (c) **R9** `h1::before{content:"> "}` joins the accessible name, so the page's only h1 announces as "greater-than sec10k inspector"; (d) **R10** `:focus-visible`'s 2px outline at `outline-offset:2px` is clipped on item rows by `#sidebar{overflow:hidden}`, so keyboard focus shows only horizontal segments; (e) **R11** `.it:hover` in dark mode is a 1.09:1 background delta (effectively invisible, and marginally worse than main's 1.15:1), and because `.it:hover` and `.it[aria-current=true]` have equal specificity with aria-current declared later, hovering the selected row gives no feedback at all

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
