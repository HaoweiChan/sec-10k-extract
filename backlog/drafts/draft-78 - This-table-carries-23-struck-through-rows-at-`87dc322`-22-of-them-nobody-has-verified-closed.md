---
id: DRAFT-78
title: >-
  This table carries 23 struck-through rows at `87dc322`; 22 of them nobody has
  verified closed
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-95
  - >-
    `tasks/reviews/pr40-r0-audit.json` — the five-row audit as committed
    evidence
  - 'per row: what was proposed'
  - what was checked against what
  - and the outcome
  - >-
    including the two refusals; for the D3 exception
    `specs/decisions/ADR-030-non-last-span-dominance.md`
  - >-
    `tasks/reviews/pr41-r1.json` and `item_dominates` / `ITEM_MAX` in
    `src/sec10k/validate.py`; this table; the D2 sweep commit
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**This table carries 23 struck-through rows at `87dc322`; 22 of them nobody has verified closed** (added 2026-08-23, Origin: D2; **count re-derived 2026-08-23 after the PR #41 merge**) — D2 deleted exactly the three rows its audit had verified and was bound not to widen the sweep on its own initiative. Every other row whose title is struck through is a candidate for the next pass. **Re-derive the count, do not trust the integer**: `grep -c '^. ~~' tasks/TODO.md` (a caret, a pipe, a space, two tildes) answers 23 at this commit. It is a snapshot with no mechanical guard — `--check-docs` reads decimals within 60 chars after a backticked fixture name, so a bare integer in a ledger row is outside its window by construction, exactly as the ADR-021 DOC_ALLOW row in this table argues — and it has already been falsified once: written as 22, then made stale by the merge of PR #41, which struck a 23rd row between the sweep commit and its review. **One of the 23 is not like the others.** The non-last-span dominance row was *live* when the D2 audit ran, then promoted and closed by D3 / PR #41 with its own review trace, ADR, and shipped code — so it needs no verification pass, it has one, and it is excluded from the count of unverified rows rather than absorbed by it. It stayed out of this sweep because the audit never saw it, not because anyone doubts its closure. For the other 22 the word CLOSED is not evidence on its own: of the five rows the D2 audit put forward — four to delete outright and one to trim — two turned out to be **live**, the PR #11 R22 row, whose part (3) is still open and whose title names that open part, and the `evals/bench._demo` row, whose durable assertion is still unwritten, because in both the CLOSED marker covered sub-parts while the row title named the remainder. Those two counterexamples are about **markers, not strike-throughs**, and they are not among the 23: neither row is struck through — both open with a bold title, not tildes — so a reader hunting for them inside the struck population will not find them. What they establish is that an inline CLOSED needs checking; whether a struck-through title is any safer is exactly what the next pass has to find out. One further oddity for that pass: two rows carry the identical title "`repo_hygiene` is listed and served as a filing fixture", one struck and promoted to D1, one open

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
