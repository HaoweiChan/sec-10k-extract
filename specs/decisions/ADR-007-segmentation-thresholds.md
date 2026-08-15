# ADR-007 — T4 segmentation: measured thresholds and era rulings

Date: 2026-08-16. Status: accepted. Implements layers 4-7
(`src/sec10k/segment.py`) under ADR-004/ADR-005's status semantics.

Willy's standing directive: no pre-data magic numbers. Every constant below
was measured against the committed fixtures **after** the mechanism worked,
and the measurement is reproducible from the eval set.

## What actually separates a heading from a false candidate

The measured answer is simpler than the architecture doc predicted, and the
prediction was wrong in a useful way.

**A real heading carries its title on the same line.** That one rule kills
both non-heading classes at once:

- Every TOC entry in all 11 real HTML/iXBRL fixtures — the filer puts the item
  code and its title in separate table cells, so the code normalizes to a bare
  `Item 1.` line.
- Every running page header — MSFT 2013 repeats a bare `Item 8` on each page
  of its financial statements (42 occurrences), `Item 7` 24 times, `Item 1`
  12 times. Nothing else in the eval set produces that volume of noise.

**Title similarity** (difflib against the code's era aliases) then removes the
survivors that carry pseudo-titles: multi-code page headers (`Item 2, 3, 4, 5`),
cross-references (`Item 14(a)`), and template leftovers (`ITEM 9A(I).`).

Measured over all 12 10-K fixtures: accepted headings score **0.593 at worst**
(median 1.0); the best-scoring false candidate scores **0.141**. `SIM_FLOOR`
sits at 0.37, the midpoint of that empty band, biased toward accepting odd
real titles — a missed heading costs an item outright, while a false positive
still has to survive canonical-code and ordering rules.

## The TOC-cluster filter, and why it needed its own fixture

With the same-line rule doing the work, the cluster filter **never fired on any
committed fixture**. That left the repo's most-cited trap guarded by untested
code, so `evals/adversarial/toc-titled.json` was built: premier-pacific-2016
with its TOC rows merged into single cells, producing 20 extra high-similarity
(0.842–0.943) competing candidates that the same-line rule cannot touch.

The case immediately paid for itself — it proved the filter as first written
**did not work**. The original rule required *every* code in a dense run to
recur later; because a TOC sits close enough to the body it indexes, the run
swallowed the first real body heading, whose code does not recur, and the test
rescued the entire TOC. Recurrence is now judged **per candidate**: inside a
dense run of ≥5 distinct codes (`TOC_CLUSTER_MIN`, gap ≤ 400 chars), a
candidate whose own code appears again later is an index entry.

Density alone can never decide: real Part III one-line IBR items sit as close
as 43 chars apart, indistinguishable from TOC spacing. Recurrence is what
makes a manifest a manifest. The dropped run is kept as
`meta.toc_manifest` — the trap doubles as the filing's self-declared checklist,
which layer 8 cross-checks at T5.

Verified: rule ON → `toc-titled` passes; rule OFF → it fails; output on all 12
real fixtures is byte-identical either way.

## Status classification

Follows ADR-004/005 with one implementation ruling: **phrase matching runs on a
whitespace-flattened copy of the body.** Fixed-width txt filings wrap the exact
phrases the rules depend on — `definitive proxy\nstatement`,
`incorporated by\nreference` — and this silently mis-classified 5 items across
GE 1994 and Textron 2001 as `extracted`. Offsets never come from the flattened
copy; classification only.

**No length cutoff for pointer bodies.** A first draft capped IBR at 2,000
chars. Measurement killed it: IBR bodies span 93–1,875 chars while 106 of 191
extracted bodies also fall in that range, so length separates nothing here.
Shape decides — is the *first* sentence a pointer, and does it name a
different document (ADR-004 shape 1 vs 3).

## Era rulings

Expected item sets come from the period-of-report date (SGML header → iXBRL
`dei:DocumentPeriodEndDate` → cover page; all three are needed, and together
they resolve 13 of 13 fixtures). Two calls worth recording:

1. **Item 9C is dated 2022-01-01 here, 13 days later than the rule it
   encodes.** This is a genuine spec-ambiguity, resolved in favor of the eval
   set (CLAUDE.md: the eval set IS the spec). The HFCAA cutoff is fiscal years
   ending after 2021-12-18; `sandston-2021` ends 2021-12-31 — 13 days inside —
   yet its dual-passed case asserts 9C is not in the expected set at all,
   while the `sec10k-domain` skill says 9C is 2021+. Those two disagree. Had
   9C been era-valid there, ADR-005 rule 2 would require reporting it
   `omitted`, exactly as that case's own Item 16 fix reasoned. **Open for
   Willy**: settle it with an FY2022 fixture, which is the only thing that can
   distinguish the two boundaries; until then the deviation is 13 days and is
   named here rather than buried in a constant.
2. **The pre-2001 txt stop-loss is not invoked.** The milestone put the
   decision at T4 exit. GE 1994, IBM 1997 and Textron 2001 are all green with
   no era-specific code beyond the newline ruling in ADR-006 and the
   flattening above, so the txt era stays fully in scope.

## Deliberately not built

- **The lenient candidate tier** (mid-line matches for expected items that
  strict matching missed) described in architecture layer 4. Nothing in the
  eval set needs it: strict line-anchored matching finds every expected
  heading in all 13 fixtures, and the one item it legitimately cannot find
  (`malformed-html` Item 1A, whose heading tag is corrupted) *should* surface
  as `missing`, not be rescued by a looser pattern. It is added when a case
  demands it, not before — and `method` already carries `heading_lenient` in
  the contract for that day.
- **SRC 7A-relief `omitted`** (ADR-005's own noted gap): an SRC that omits the
  7A heading entirely would currently report `missing`. No fixture exhibits
  it; ADR-005 already flags it as the case to add later.

## Consequences

- 19 of 20 cases green. The one red is `nvda-2024-shallow`, which demands
  `doc_status == "success"` exactly; T4 emits a standing
  `validation_not_implemented` warning, so the honest ceiling is
  `success_with_warning` until the layer-8 battery lands. That case is now the
  T5 tripwire — it flips green when validation is real, and only then.
- Confidence values are placeholders (0.9 strict / 0.7 weak title / 0.8
  non-extracted), recomputable from each item's `evidence`. Calibration is T5,
  per the architecture doc's confidence section.
