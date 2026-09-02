---
id: DRAFT-34
title: >-
  Four LOW findings from PR #27 round 3 — the pin mechanism's residual holes,
  and one maintenance trap
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-38
  - '`tasks/reviews/pr27-r3.json` findings R12/R14/R15/R16'
  - >-
    evidence and acceptance verbatim; all four re-reproduced independently by
    the orchestrator at `fa846e5` before filing
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Four LOW findings from PR #27 round 3 — the pin mechanism's residual holes, and one maintenance trap** (added 2026-08-22, Origin: PR #27 R12/R14/R15/R16) — (a) **R12** the wired-but-unreachable check tests `\bchecked\b` and `\bdisabled\b` only, so `<input type="checkbox" id="exclude-bp" hidden>` passes at **0 failures** — every hop intact, the box can never be ticked. A stylesheet `.opt{display:none}` is the same shape; (b) **R14** the pins require each expression *exactly once*, but no case asserts the uniqueness half: mutating `if n != 1:` to `if n < 1:` leaves invariant **37/37** and fast **79/79** green, so nine of the eleven pinned expressions are unprotected against duplication (only the two `UNIQUE_UI` tokens are); (c) **R15** a behaviour-neutral edit turns the gate red with a diagnostic that contradicts the file — adding `tabindex="0"` to the pinned `<pre class="text">` gives **2 failures**, one reading "`<pre class="text">` occurs 0 times, expected 1" while that exact text is on screen, because the `UNIQUE_UI` branch does not carry `pin`'s "update the pin" guidance; (d) **R16** the pair A fixture's header comment says "five ways" then enumerates six (the UI half contributes 6 of the case's 9 failures, the `.py` half 3)

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
