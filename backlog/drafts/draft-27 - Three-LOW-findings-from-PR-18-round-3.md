---
id: DRAFT-27
title: 'Three LOW findings from PR #18 round 3'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-29
  - '`tasks/reviews/pr18-r3.json` findings R23–R25'
  - evidence and acceptance verbatim
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Three LOW findings from PR #18 round 3** (added 2026-08-21, Origin: PR #18 R23–R25) — (a) **R23** the `bg_from` block in `css_contrast._demo` is pasted twice verbatim, so the self-check runs 16 identical lines of assertions a second time; (b) **R24** the `body` ground stacks list the four `background-image` layers in declaration order, which is the reverse of CSS paint order — the modelled dark ground is `rgb(24.1, 38.2, 48.9)` where the page paints `rgb(23.1, 32.6, 42.8)`, so `dark/sha-dim` reads 5.21 where it renders 5.53. **The error is conservative in both schemes and no pair flips**, but the provenance sentence claiming the stacks follow real paint order overstates fidelity; (c) **R25** `check_button_specificity` only inspects selectors containing `:hover`, so `button:focus{background:var(--amber)}` — the same specificity rank as the rule the check exists to stop — is not flagged, and R17's proposed combinator fix would not catch it either

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
