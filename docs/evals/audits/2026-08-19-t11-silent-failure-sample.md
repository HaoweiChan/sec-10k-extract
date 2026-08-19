# 2026-08-19 — T11 silent-failure sample audit

## Scope

Independent adjudication of a random sample of 30 extraction results, drawn
with `random.Random(11).sample(population, 30)` from a population of 447
items that satisfied: confidence >= 0.8, inside a document reported
`success`/`success_with_warning`, and not targeted by any existing eval
check. Sample manifest:
`/private/tmp/claude-501/-Users-willy-Documents-sec-10k-extract--claude-worktrees-todo-t11-planning-audit-ae0735/97c7f80c-4b61-4341-8e82-305f1b1cd552/scratchpad/t11-sample.json`.

This is an output audit: no implementation plans, ADRs, or
`docs/architecture/overview.md` were read. Verdicts were formed by reading
each span against the fixture text with fresh eyes, per
`specs/001-sec10k-contract.md` (item boundary/status rules) and
`specs/000-invariants.md` (INV-S1/S2/S3/S4/S5).

## What I ran

For each of the 30 sampled `(fixture, item)` pairs, ran
`src.sec10k.extract.extract_items(path)` and inspected:
- the reported `status`/`confidence` vs. a fresh read of the item's actual
  text,
- head and tail of the span (not just the opening) against the neighboring
  item boundaries,
- for the three `incorporated_by_reference` items, whether the span is
  actually the pointer sentence and whether IBR is the right call at all,
- for `toc-titled` items, whether the span anchored to the real body heading
  or the earlier table-of-contents listing (checked by finding all
  occurrences of the heading string in `normalized_text`),
- for long spans, a regex scan for any `Item \d+[A-Z]?\.` pattern appearing
  *inside* the span (a signal of run-on into a neighboring item) followed by
  a full read of the span when the scan was inconclusive,
- for `spans-transposed`, dumped every item in the fixture to confirm the
  full item sequence is monotonic and non-overlapping around item 2.

Full raw dumps (head/tail/before/after for all 30) live in this audit's
working notes; offsets below are quoted directly from the pipeline run
against the committed fixtures in `evals/fixtures/`.

## Verdict table

| # | case | item | reported status | reported conf | verdict |
|---|------|------|------------------|----------------|---------|
| 0 | spatz-2014-shallow | 4 | extracted | 0.95 | CORRECT |
| 1 | toc-titled | 12 | extracted | 0.95 | CORRECT |
| 2 | fy2021-item-9c | 10 | extracted | 0.95 | CORRECT |
| 3 | toc-titled | 8 | extracted | 0.95 | CORRECT |
| 4 | ixbrl-hidden-metadata (aapl-2025) | 13 | incorporated_by_reference | 0.85 | CORRECT |
| 5 | spatz-2014-shallow | 10 | extracted | 0.95 | CORRECT |
| 6 | caps-cover-taxonomy | 1B | extracted | 0.95 | CORRECT |
| 7 | toc-titled | 7A | extracted | 0.95 | CORRECT |
| 8 | gs-2002-transitional-numbering | 3 | extracted | 0.95 | CORRECT |
| 9 | ko-1997-shallow | 2 | extracted | 0.95 | CORRECT |
| 10 | intc-2002-shallow | 3 | extracted | 0.95 | CORRECT |
| 11 | jnj-bare-headings | 10 | extracted | 0.95 | CORRECT |
| 12 | caps-cover-taxonomy | 3 | extracted | 0.95 | CORRECT |
| 13 | textron-2001-content | 4 | extracted | 0.95 | **WRONG** |
| 14 | html-source-wrap (msft-2013) | 9 | extracted | 0.95 | CORRECT |
| 15 | html-source-wrap (msft-2013) | 2 | extracted | 0.95 | CORRECT |
| 16 | jnj-bare-headings | 7A | extracted | 0.95 | CORRECT |
| 17 | intc-2002-shallow | 6 | extracted | 0.95 | CORRECT |
| 18 | bac-2006-shallow | 15 | extracted | 0.95 | CORRECT |
| 19 | sgrp-2019-shallow | 14 | extracted | 0.95 | CORRECT |
| 20 | nvda-2024-shallow | 4 | extracted | 0.95 | CORRECT |
| 21 | cvx-2015-shallow | 6 | extracted | 0.95 | CORRECT |
| 22 | bac-2006-shallow | 12 | incorporated_by_reference | 0.85 | CORRECT |
| 23 | fy2021-item-9c | 1B | extracted | 0.95 | CORRECT |
| 24 | spans-transposed | 2 | extracted | 0.95 | CORRECT |
| 25 | ibr-pointer-window (wmt-2010) | 9B | extracted | 0.95 | CORRECT |
| 26 | html-source-wrap (msft-2013) | 9B | extracted | 0.95 | CORRECT |
| 27 | aapl-2025-structure | 3 | extracted | 0.95 | CORRECT |
| 28 | gs-2002-transitional-numbering | 7 | incorporated_by_reference | 0.85 | CORRECT |
| 29 | sandston-2021-shallow | 4 | extracted | 0.95 | CORRECT |

29 CORRECT, 1 WRONG, 0 UNDECIDABLE.

## Detailed evidence

### #13 — textron-2001-content / item 4 — WRONG (confidence 0.95)

`evals/fixtures/textron-2001/filing.txt`, reported `start=32627 end=36358`
(span_len=3731), `status=extracted`, `confidence=0.95`.

The span opens correctly on the real Item 4 heading and its actual answer:

```
ITEM 4.   SUBMISSION OF MATTERS TO A VOTE OF SECURITY HOLDERS

     No matters were submitted to a vote of our security holders during the last
quarter of the period covered by this Annual Report on Form 10-K.
```

That is the entirety of Item 4's substantive answer — it ends at offset
~32856 (right before a page-break marker `<PAGE>`). But the reported span
does not stop there; it runs another 3469 characters to offset 36358,
swallowing a distinct, separately-headed section:

```
                                       14
<PAGE>

EXECUTIVE OFFICERS OF THE REGISTRANT

     The following table sets forth certain information concerning our executive
officers as of March 14, 2002. ...
[full bios: Lewis B. Campbell, Kenneth C. Bohlen, John D. Butler,
 Theodore R. French, Mary L. Howell, Terrence O'Donnell]
...
                                       15
<PAGE>

                                     PART II
```

`EXECUTIVE OFFICERS OF THE REGISTRANT` is its own clearly-headed section (a
disclosure required by Item 401(b)/(e) of Regulation S-K, but not itself an
SEC-numbered "Item" — hence it has no slot in the item registry). A careful
reader would say Item 4's answer is two sentences long and that the six
executive-officer biographies that follow are a distinct section, not part
of "Submission of Matters to a Vote of Security Holders." The pipeline's
span attributes 3469 characters of unrelated officer-biography content to
Item 4, at confidence 0.95 — the textbook shape of a confidently-wrong
silent failure: correct opening, materially over-run closing, and nothing in
the existing eval suite exercises this item on this fixture to catch it.

Correct boundary: Item 4 should end at offset ~32856 (`"...this Annual
Report on Form 10-K.\n\n"`), before the `<PAGE>` marker and the
`EXECUTIVE OFFICERS OF THE REGISTRANT` heading at offset 32889. Where that
orphaned content should then go (attached to nothing / a new `omitted`-type
carrier / left dangling before Item 5) is a genuine open question the spec
does not currently answer — this filing shape (an unnumbered required
disclosure sitting between two numbered items) is not addressed by
`specs/001-sec10k-contract.md`.

## Rate

**1 WRONG / 30 adjudicated.**

## Notable near-misses that turned out CORRECT (worth recording since they were the intended stress points)

- **IBR calibration, same-document cross-reference vs. true external IBR**
  (`jnj-bare-headings` item 7A, index 16): the entire item is one paragraph
  reading "The information called for by this item is incorporated herein
  by reference to 'Item 7... of this Report'... and Note 1... included in
  Item 8 of this Report" — a cross-reference to *another section of the same
  10-K*, not to an external Proxy Statement. Status is `extracted`, not
  `incorporated_by_reference`. That is the right call: nothing is actually
  incorporated from outside the document, the pointer paragraph *is* the
  entirety of what the company filed under this heading, so there is nothing
  else to fetch. Contrast with the same fixture's item 10 (index 11), which
  opens with a genuine external-IBR sentence pointing at the Proxy Statement
  but then contains three further paragraphs of original Code-of-Conduct
  disclosure directly in the 10-K — there `extracted` is also correct,
  because the item is not *wholly* incorporated by reference.
- **TOC-vs-body anchoring** (`toc-titled`, items 12/8/7A, indices 1/3/7): each
  heading string (e.g. `ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY
  DATA.`) appears twice in `normalized_text` — once inside the filing's own
  table of contents (offset ~3600) and once at the real body heading (offset
  ~28338+). Independently confirmed via `re.finditer` that in all three
  sampled cases the pipeline anchored to the second (body) occurrence, not
  the TOC row.
- **`spans-transposed` fixture** (item 2, index 24): despite the fixture's
  adversarial-sounding name, dumping all 20 items in the fixture shows a
  fully monotonic, non-overlapping sequence (offsets strictly increasing
  from item 1 through item 16); item 2's own span is clean. (Item 8 in this
  same fixture carries confidence 0.65, below this sample's 0.8 floor, and
  was not part of the sampled population — noted only as context, not
  adjudicated here.)
- All three sampled `incorporated_by_reference` items (aapl item 13, bac
  item 12, gs-2002 item 7) have spans that are exactly the pointer sentence
  (or sentence-plus-one-clause), and in each case the underlying filing
  really does defer that item to an external document (Proxy Statement or
  Annual Report to Shareholders) — the IBR call is correct in all three.

## What I could not check

- I did not verify the `title`/`part` metadata fields, only `status`,
  `confidence`, and span boundaries — the task scope was span/status
  adjudication.
- I did not independently re-derive what "correct" looks like for the
  orphaned `EXECUTIVE OFFICERS OF THE REGISTRANT` content in the textron
  case beyond identifying that Item 4's own span should not include it;
  fixing this is out of scope for an output audit (no code, no case edits).
- I did not check whether the same "unnumbered Item 401(b) disclosure
  swallowed into the preceding numbered item" pattern recurs in other
  filings in the fixture set (e.g. `intc-2002`, `gs-2002` are pre-2005
  filings of the same era and commonly carry this section) — only
  `textron-2001` item 4 was in the sample, so only it was adjudicated. This
  is a plausible place to look for more instances of the same failure
  shape, but I have not gathered evidence for or against recurrence.
- A systematic, low-severity pattern was observed and *not* counted as
  WRONG: several spans include trailing page-number and `PART`-header
  boilerplate between the item's last substantive sentence and the next
  numbered Item heading (e.g. spatz-2014 item 4 ends `"...Not
  applicable.\n\n- 6 -\n\nPART II\n\n"` before `"Item 5."`). This is
  consistent "up to the next Item heading" segmentation applied uniformly
  and does not misattribute any other item's substantive content, so it was
  not treated as a boundary defect — but it is the same *shape* of gap that
  let the textron Executive-Officers section slip in, just with harmless
  (non-substantive) filler instead of a full section. Worth watching if a
  future sample turns up a case where that gap is not harmless boilerplate.
