# H1 — held-out run #1, triage

Run: `evals/report/20260816-225101-fast.json`, suite `fast --dir evals/heldout`,
git SHA `70d10f1`. Score **1/5**. Report committed in `a72d8f7` before this
document existed; nothing below has been fixed yet.

## The headline number, and why it is not the whole story

25/25 on the dev set, 1/5 on filings the implementation had never seen. That
gap is the thing this exercise exists to produce and it should not be softened.

But the six failing assertions do not all mean the same thing, and pretending
they do would be its own dishonesty. **Two are real extractor findings. Four
are labels I authored wrongly.** The extractor did better than 1/5 suggests,
and one of the two real findings is worse than 1/5 suggests.

| # | Case | Assertion | Verdict |
|---|---|---|---|
| 1 | `jnj-2016` | items 1 and 6 extracted | **extractor defect, severe** |
| 2 | `gs-2002` | item 15 present | **extractor limitation, predicted** |
| 3 | `gs-2002` | item 7A extracted | my bad label |
| 4 | `ko-1997` | item 7A extracted | my bad label |
| 5 | `xom-2021` | item 9C omitted | my bad label |
| 6 | `xom-2021` | doc_status not ambiguous | my bad label |

## Finding 1 — a filer's markup inverts the heading discriminator (severe)

JNJ 2016 returned **3 of 21 items**. Items 2, 8 and 16 extracted; eighteen
reported `missing`.

Cause, traced end to end. The segmenter's load-bearing rule is that a real body
heading carries its title on the same line — the rule that makes the TOC filter
work, recorded in ADR-007 and relied on by `toc-titled`. JNJ's markup puts the
item code and its title in separate blocks, so normalization emits:

```
Item 1.\n\nBUSINESS          <- 18 items look like this; HEADING_RE rejects them
Item 2.PROPERTIES            <- 3 items look like this; matched
```

Counted on the normalized text: **18 bare-code heading lines, 3 titled**. That
is exactly the 18 missing / 3 extracted split. The discriminator is not merely
weakened here, it is inverted — the shape that identifies a TOC entry in every
dev fixture is the shape of a real heading in this filing.

The cold review of T3–T5 named this assumption as the one it would attack next
and could not build a fixture for it. A held-out mega-cap supplied one.

**It failed loudly, which is the one good thing here**: 18 `expected_item_missing`
warnings fired and the TOC manifest cross-check had nothing to cross-check
against (`toc_manifest: []`). A consumer reading the warnings sees the problem.

## Finding 1b — but `doc_status` still said `success_with_warning`

Eighteen of twenty-one items missing, and the envelope reports
`success_with_warning`. `expected_item_missing` is not in `AMBIGUOUS_CODES`
(`validate.py`), so no volume of it can escalate. A consumer thresholding on
`doc_status` — which the contract explicitly invites, calling it "the
frontend's headline banner" — accepts this document as a qualified success.

This is a second, separate defect from Finding 1, and it would survive any fix
to the heading rule. Warning *count* and warning *proportion* carry information
that the current escalation policy discards.

## Finding 2 — the era model does not cover the 2002–2003 transitional window

`gs-2002` item 15 is absent from the envelope entirely. **Predicted before the
run**, in the case's own provenance: Goldman's FY2002 filing uses the
post-Sarbanes-Oxley numbering (Item 14 = Controls and Procedures, Item 15 =
Exhibits) ahead of the 2003-08-14 effective date that `segment.ADDED` encodes,
so `expected_items` never expects 15, `find_candidates` never makes it a
candidate, and it cannot even reach the TOC manifest to raise a mismatch.

This is the same structural weakness ADR-010 recorded as debt after the Item 9C
correction: *the era table is a single point of silent failure, and any item
mis-dated by one season repeats this exactly.* It has now repeated, on a real
filing, in a different direction.

## Findings 3–6 — four labels I got wrong

Recorded in full because the failure of an eval author is worth the same
scrutiny as a failure of the extractor.

**3 and 4 — Item 7A on GS 2002 and KO 1997.** I asserted `extracted`. Both are
genuine whole-item pointers, and the filings say so in as many words:

> GS: "...is set forth on pages 46 to 53 of the 2002 Annual Report to
> Shareholders ... and is incorporated herein by reference."
> KO: "'Financial Risk Management' on page 36 of the Company's Annual Report to
> Share Owners ... is incorporated herein by reference."

`incorporated_by_reference` is correct. I asserted 7A's *presence* to pin an era
boundary and asserted a *status* alongside it without reading the body. The
extractor was right both times.

**5 — Item 9C on XOM 2021.** I asserted `omitted` on the strength of my
independent scan finding zero `item\s*9C` hits. The filing does contain
`ITEM 9C. DISCLOSURE REGARDING FOREIGN JURISDICTIONS THAT PREVENT INSPECTIONS`
with body "Not applicable." The extractor found it and extracted it, correctly.

The lesson is about the tool, not the item. My verification scan strips tags to
spaces; the real normalizer joins within a block. A code split across markup
(`9<span>C</span>`) survives normalization and dies in my scan. **I asserted an
absence using an instrument weaker than the thing under test** — safe for
asserting presence, unsound for asserting absence, and I did not draw that
distinction when authoring.

**6 — XOM doc_status.** I allowed only `success`/`success_with_warning`. The run
returned `ambiguous` because `last_item_dominates` fired on item 16: XOM's
"ITEM 16. FORM 10-K SUMMARY None." is followed by the entire Financial Section,
which the last item's span swallowed. That is a real tail bleed, the validator
caught it, and `ambiguous` is the honest report. My assertion was simply too
narrow — I wrote it assuming a well-formed mega-cap filing would be clean.

## What the run actually measured

- The **validator battery earned its keep**: it caught the tail bleed on XOM
  unprompted, and it made JNJ's collapse loud rather than silent. Both on
  filings no threshold was tuned against.
- The **era table** is now twice-confirmed as the pipeline's most brittle
  component, in two independent directions.
- The **heading discriminator** has a real-world counterexample.
- My **authoring** produced a 4-in-6 error rate on status assertions at shallow
  tier, which is worse than the extractor's error rate on the same filings.

## Burn accounting

`jnj-2016` and `gs-2002` will drive implementation changes and are therefore
burned on any fix: they move to `evals/adversarial/` and are replaced.

`ko-1997`, `xom-2021` and `cost-2022` drive no implementation change. Their
labels were wrong and the corrections are verifiable from the source documents
rather than from extractor output — but they have now been observed, so H1 is
the only clean generalization estimate they will ever provide. Treated as
label-corrected rather than burned; the distinction and its cost are recorded
here so a reader can disagree with it.
