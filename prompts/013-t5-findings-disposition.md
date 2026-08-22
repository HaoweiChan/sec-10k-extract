# 013 — T5 disposition: when the document says "unresolved", no item may say 0.95 (2026-08-22)

Curated per hard rule 6: this pass changed the confidence policy (a document-
level verdict now bounds item-level numbers), made a normative contract enum
truthful, and re-ran a published measurement instrument that turned out to be
un-runnable. [ADR-027](../specs/decisions/ADR-027-ambiguity-caps-confidence.md)
is the record; this file keeps the correction chain.

## The prompt decisions that mattered

- **"Dispose all 12 findings; disposition per finding = exactly fix-with-case
  or debt; a `_demo`-only pin is NOT a case."** The binding part was the
  PR #30 precedent it named (R3: a fix whose only pin was `_demo` was
  rejected because a fixture could trivially carry it). That rule decided
  T5-3: the `boundary_hygiene` false positive got a one-byte synthetic fixture
  (`spaced-letter-heading`) and a gate-suite case rather than a `_demo` assert,
  even though the check itself is the ADR-016 "prove it at the layer" case.
- **"Pick the smallest policy that makes the `items-stripped` contradiction
  impossible."** Two candidates were on the table: count the `item=None`
  escalating warnings against every item (one line in `score`), or cap every
  item at `BASE_WEAK` when the ladder says `ambiguous` (reorder + one
  parameter). The first is smaller and was rejected on evidence, not taste:
  `jpm-2024` and `xom-2021` escalate through an *item-targeted* code, so under
  the penalty they stay at 0.95 with `doc_status: ambiguous` — the
  contradiction survives on two of the five ambiguous fixtures. The cap makes
  "`ambiguous` ⇒ no item above 0.75" a theorem, and the case states the theorem
  (an item-less `confidence max` bound).
- **"Every number you write must be produced by a command you paste."** This
  is why the ADR-018 instrument was actually re-run rather than described —
  and re-running it is what found the crash: `python3 -m evals.metrics` on any
  current `--suite all` report dies on the first `repo_hygiene` row
  (`TypeError: string indices must be integers, not 'str'`). The instrument
  behind a published table had been un-runnable since the UI cases landed, and
  nothing noticed because nothing re-ran it.
- **"RE-RUN it, do not hand-edit; if re-running would be a re-publication,
  say so and log debt with the exact deltas."** Followed literally: three
  tables (published 2026-08-18 / today-at-main / after) in ADR-027 §h, the
  analysis report untouched, one Debt row carrying the deltas.

## Assumption → Eval contradiction → Correction

- Assumed: the 0.8 title-similarity cut separates honest from mis-assigned
  headings (that is how the finding read it, and how the first draft of the
  measurement was framed).
  Eval said: over 553 extracted spans, all five below 0.8 are case-asserted or
  unlabelled correct extractions; the next value up is 0.841. The cut is an
  evidence-strength tier inside an empty band (0.727, 0.841), not a
  correctness boundary.
  Corrected: `STRICT_SIM` keeps 0.8 with the derivation at its definition, is
  pinned at both band edges (msft-2013 1A 0.727 → 0.75/`heading_lenient`,
  intc-2002 5 0.841 → 0.95/`heading_strict`), and `method` is derived from
  the same constant so "strict" can no longer be published over a weak score.
- Assumed: `MISSING_MAX = 0.25` "sits 5x above the worst real filing"
  (ADR-013, written when the worst was 0.048).
  Eval said: `axp-2008`, burned into the dev set by ADR-020, loses 4 of 20 =
  0.20 through a combined Part III heading and must not escalate.
  Corrected: the margin is 1.25x, recorded at the constant and in ADR-027 §c;
  the floor stays, pinned by `warning_absent` on axp-2008 and
  `warning_present` on items-stripped (0.381).
- Assumed: `FLOOR = 0.20` is a safety clamp worth keeping.
  Eval said: four item-targeted hits are needed to reach it and
  `boundary_hygiene` cannot fire on pipeline output; the worst a real item can
  read is 0.30.
  Corrected: deleted; `_demo` asserts the honest 0.15 on a hand-built
  four-warning item; ADR-008's "[0.20, 0.95]" amended in place.
- Assumed: the reviewer's "no eval check reads `method`" meant a new check
  type was needed.
  Eval said: `item_field` (ADR-010 era) reads any scalar item field; nothing
  had used it on `method`.
  Corrected: `item_field … field: method` pins on three cases, and the new
  `envelope_shape` refuses any value outside the enum — no redundant check
  type.
- Assumed: `boundary_hygiene`'s only defect was being structurally dead
  (already ruled fine by ADR-016 §2).
  Eval said: `segment.HEADING_RE` accepts `Item 9 A.`; the validator's hand
  copy did not — `spaced-letter-heading` at main: `unexpected warning
  'boundary_hygiene'`, item 9A 0.8 ≠ 0.95, `success_with_warning` ≠ `success`.
  Corrected: the validator reads headings with `HEADING_RE` itself; a copy
  cannot drift from itself.
