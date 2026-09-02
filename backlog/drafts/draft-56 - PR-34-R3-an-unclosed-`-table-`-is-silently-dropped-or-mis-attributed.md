---
id: DRAFT-56
title: 'PR #34 R3: an unclosed `<table>` is silently dropped or mis-attributed'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-73
  - '`tasks/reviews/pr34-r1.json` R3; ADR-029 §e does not yet name the limit'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**PR #34 R3: an unclosed `<table>` is silently dropped or mis-attributed** (added 2026-08-23, Origin: PR #34 R1/R2/R3; **R1 and R2 CLOSED by L1 (2026-08-23)** — (a) R1: the two recording-run `history.jsonl` lines exist on no branch (`git log --all -S20260823-002950 -- evals/report/history.jsonl` → empty; the committed file at 1efc457 ends at 20260822-173510), so ADR-029 §h now says the lines lived only in the working tree that made the move and the time series starts with the first run after the merge; verified `grep -c 'only in the working tree that made the move' specs/decisions/ADR-029-structured-tables-annotation.md` → 1; (b) R2: `_tables_shape` (`src/sec10k/eval_adapter.py`) now refuses records out of document order and cells outside their table's span, so the contract sentence 'envelope_shape refuses any other shape' is true as written — watched red first in `src/sec10k/test_eval_adapter.py::test_table_checks` (a cell-outside-table envelope under `envelope_shape` returned None at 1efc457; `[eval_adapter self-check] 18/18 passed` after) and exercised by every committed table case — five of the seven ran `envelope_shape` before PR #35 round 1, and R1 added it to the two that ran `tables_sane` only (`tables-layout-bullet`, `tables-cell-div`; `grep -c envelope_shape` over the seven table cases: 5/7 → 7/7, both cases green, no red-first needed for a tightening already watched red in `test_eval_adapter`); gate unchanged, invariant 48/48, fast 96/96, fidelity 1.0/1.0) — (c) **R3 stays open**: a `<table>` left open at end of input, or an inner table whose `</table>` is missing, is silently dropped or mis-attributed (`_Plain` appends a record only on `</table>`, `close()` does not flush `_open`): `<p>x</p><table><tr><td>a</td><td>b</td></tr><p>after</p>` → 0 records; a nested inner table without its close swallows the outer record — all 38 committed HTML fixtures have balanced tags and zero nesting, so no eval case can go red on it

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
