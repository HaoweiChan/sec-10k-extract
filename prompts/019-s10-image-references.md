# 019 — S10: image references as point offsets, and the fetch half ruled out (2026-08-23)

The S10 row asked for image extraction — "performance graphs, charts,
signatures, logos" — and, unusually, wrote the split into the task itself: an
offline half that records every reference, and a fetch half that resolves the
bytes off EDGAR, with the ADR required to rule on each separately and to decide
whether any image bytes get committed as fixtures. Post-freeze, ADR first.
Ruling: [ADR-032](../specs/decisions/ADR-032-image-reference-annotation.md).

## The prompt decisions that mattered

- **The task came pre-split, and the split was the whole design.** The row had
  already measured that every `<img>` in the corpus is an external reference
  and none is an inline `data:` URI, which is the fact that decides the ADR:
  the bytes are not in the fixtures, so the only half of "extract the images"
  that this repository's spec — the eval set — can gate is the reference. The
  prompt's job was not to discover that; it was to refuse the temptation to
  ship a fetcher anyway and call the offline half a first step. Ruled out
  explicitly, with the cost written on both sides (ADR-032 §c) so "not built"
  is a decision a reader can act on.

- **`groundwork:cost-discipline` rule 4 and "commit an image fixture" turned
  out to be the same sentence.** The rule says a paid/live case is tagged
  `full` only and its cached response is committed so `full` is reproducible
  offline. For an image, the cached response IS the image. So the fetch half
  cannot be shipped honestly without committing binary fixtures, which is the
  S3 upload-fixture ruling and moves ADR-021 §b8's populations. Two rules the
  repo already had, colliding into one answer. That collision is what made the
  ruling easy; without it the argument would have been a preference.

- **A point, not a span.** ADR-029's table record is `{start, end}` because a
  table has text. An image has none — it emits nothing into `normalized_text`
  — so a span would be a fiction, and the honest record is one offset. The
  consequence had to be stated in the contract rather than discovered later:
  document order for images is **non-decreasing**, not strictly increasing,
  because two adjacent images sit at the same point. xom-2021 has three at
  once.

- **Do not build a module because the last one had a module.** ADR-029 shipped
  `src/sec10k/tables.py` for `grid()` / `to_markdown()`, and the symmetrical
  move here would be `src/sec10k/images.py`. There is nothing to derive: an
  image record's fields ARE the answer, and the two views a consumer wants
  (the images inside an item; the item an image falls in) are one comprehension
  each. Ruled: no module, and the two expressions written into the ADR so they
  are not reinvented. Likewise no `to_markdown` — the placeholder is S9's job,
  and shipping one would have created a collision with a parallel task for no
  gain.

- **A metric was NOT added, and the reason is ADR-029's own §c2.** The
  symmetrical move to ADR-029's table-fidelity keys would be an image-fidelity
  metric. ADR-029 itself argued that its metric's worth is *magnitude* — one
  lost attribute is a 21% cell loss, not a binary — and an image record has no
  partial-credit axis: a `src` is right or wrong. So the key would read 1.0 on
  every green run and fire only alongside a case already red. `.eval-baseline.json`
  is untouched by this PR, which is also the cheapest possible answer to hard
  rule 1.

- **Declared width/height: the field would have been dead if written the
  obvious way.** The plan said "declared width/height", which reads as the
  `width=`/`height=` attributes. Measured: 0 of the corpus's 53 images carry
  them and 40 declare the size in `style`. Recording only the attribute would
  have shipped a field that is `null` on every committed filing — a code path
  no case can reach, the sin ADR-010 named. The rule became: attribute first,
  then a `Npx` declaration in `style`, and `null` for a non-pixel value rather
  than a wrong number.

## Assumption → Eval contradiction → Correction

- **Assumed:** the containing item is a fact about the image, so the three
  goldens would each pin it equally well.
- **Eval said:** xom-2021 and jpm-2024 both fire `last_item_dominates`, so all
  9 and all 14 of their images fall inside one over-long span — Item 16
  covering 275k of 389k chars, Item 15 covering 1.01M of 1.21M. A constant
  would satisfy both label sets.
- **Corrected:** `bac-2006-images` is named in the ADR and in both provenances
  as the only case that proves containment discriminates (Items 7 and 8, on a
  `success` document with no warnings), the two weak label sets say so in their
  own provenance rather than being quietly presented as evidence, and a Debt
  row (Origin: S10) records that containment inherits the spans' quality.

- **Assumed:** the S10 row's own corpus figures could be quoted as given.
- **Eval said:** "15 of 38 HTML fixtures" — the 15 and its per-fixture
  breakdown reproduce exactly, but the corpus is 42 filing fixtures of which 35
  are HTML or iXBRL, not 38.
- **Corrected:** ADR-032 §j republishes the ratio as 15 of 35 and says which
  half of the row's figure was right, rather than repeating it or silently
  dropping it. (ADR-029 §i3's rule: dropping a correct measurement on a false
  premise is the same defect class as publishing a wrong one.)

- **Assumed:** the opt-in flag would be justified by payload size, as ADR-029's
  was (+98% envelope bytes).
- **Eval said:** the whole corpus's image annotation is 5,477 bytes; on
  jpm-2024 it is 1,549 bytes on a 1,267,279-byte envelope — **+0.122%**, about
  1/800th of what `tables=True` adds to the same filing. The time cost, 1.083×
  median, is not the images at all: it is the price of taking the
  marks-carrying `_tidy` branch, and a fixture with zero images pays nothing.
- **Corrected:** ADR-032 §b4 justifies opt-in on **contract consistency** and
  says outright that ADR-029's size argument does not carry here. An inherited
  justification that the measurement does not support is worse than no
  justification.

- **Assumed:** four one-line mutations would be enough to show the cases fail
  on content and not on vocabulary.
- **Eval said:** M1 (drop `alt`) left `images-offsets-invariant` green and M4
  (emit the key with the flag off) left all three goldens green — each mutation
  was invisible to some part of the set.
- **Corrected:** nothing, and that is the point: the two blind spots are
  complementary by design (the invariant case asserts the equality and the
  shape, the goldens assert the content), so the pair is recorded in ADR-032 §g
  as evidence that neither kind of case is redundant. M5 (dedupe by offset)
  added the third axis — it is red on xom-2021 and bac-2006, which have
  coincident offsets, and green on jpm-2024, which does not.

- **Assumed:** `evals/snapshot.py` would be an S10 throwaway.
- **Eval said:** the same "default output is byte-identical" claim is made by
  ADR-026 §d and ADR-029 §d, both of which stated it as a measurement with no
  committed way to re-run it.
- **Corrected:** the script is committed, written for any capability flag
  rather than for `images`, with a self-check asserting the property that makes
  the comparison meaningful — a new envelope key counts as a difference, a
  timing does not. S9 will want it.
