# 025 — D16: the pointer-shape escalation trigger (2026-08-28)

The first capability built on top of a decision row: ADR-038 ruled `cvx-2015`
items 2/6/7A `defect` at the escalation layer and named, in its own §f row 1,
the instrument that would overturn the verdicts — a warning carrying their
codes. D16's brief was to build exactly that instrument, deterministically,
for $0, without widening `SPAN_FLOOR`'s item set (TD-5's measured
counter-evidence) and without resolving any pointer (TD-12 stays declined).
The output is [ADR-039](../specs/decisions/ADR-039-pointer-shape-escalation.md),
one new validator in `validate.py`, and the promotion of
`cvx-2015-silent-pointer-items.json` out of the `debt` suite.

## The prompt decisions that mattered

- **The rule was inherited, not invented.** The brief bound the design to
  ADR-038 §b's own three-part rule (R1 class gate / R3 "already said it" /
  R3 reached-or-unreached) and demanded each prong be the closest thing to
  that rule a $0 deterministic layer can compute. That framing is what
  produced the load-bearing insight: the sound, non-fitted ground separating
  cvx (fire) from bac-2006/xom-2021 (no fire) is not the pointer, the item
  code, or the length — it is the mass of `normalized_text` outside every
  span, which `coverage()` already computes. A pointer into a document that
  places 93% of itself points at placed content; one into a document that
  places 27% plausibly does not.
- **"Measure first, and report the band honestly" was written into the brief
  before any constant existed** — including the instruction NOT to present a
  fitted threshold as a band. The census then showed the body-length
  populations OVERLAP corpus-wide (`ba-2003` item 5's mixed body is 508
  chars, under the largest pointer-only body at 515), so `PTR_BODY_MAX` is
  documented as a band only within the sub-`PTR_COVERAGE_MIN` population and
  explicitly NOT as a pointer-only discriminator at large (ADR-039 §c2).
  Without that instruction the constant would have shipped described as
  something it is not.
- **Reuse the pipeline's own boundary instruments.** The internal-locator
  regex is `d9_class_scan.py`'s `PAGE_PTR` verbatim and the external-document
  test imports `segment.EXTERNAL_DOC_RE` — the constant ADR-004's status
  layer already uses — so the two layers cannot drift apart on what "a
  different document" means. The census instrument likewise imports the
  shipped constants, so it reprints the truth after any move.
- **The census had to explain every row, both directions.** The brief's rule
  — "no unexplained fire may ship" — was symmetric: every candidate span
  (104 corpus-wide) is printed with the single prong that excludes it, and a
  self-consistency assert fails the census if its re-derivation ever
  disagrees with what the shipped pipeline emitted. The first census run
  caught its own bug this way: the new warning counted as "already warned"
  for its own items and suppressed every fire out of its own census.
- **What was deliberately NOT claimed.** ADR-039 §d1 states that the blind
  auditor's `bac-2006` confidence objection is answered only for the cvx
  three; `bac-2006` 3/6/7A stay at 0.95/`review_required: false` because
  prong 3 is ADR-038 §g8's document-wide scope choice implemented as a
  threshold, and the item-scoped reading is recorded as unrefuted with
  ADR-038 §f row 3 as the live reopener.

## Outcome

Fires on exactly `cvx-2015` 2/6/7A across 50 documents dev + held-out;
`spatz-2014` item 15 — the brief's named live possibility — never enters the
class (its body names an item, not a page or index). Both bands pinned both
edges, six threshold mutations watched red, snapshot byte-identical
everywhere except the three intended items' warnings/confidence. Gate green,
baseline untouched.
