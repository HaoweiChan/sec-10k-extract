# ADR-038 — D13: the internal-pointer disagreement, adjudicated item by item

Date: 2026-08-27. Status: accepted. Implements D13. Amends
[ADR-019](ADR-019-silent-failure-rate.md) §e (which recorded the disagreement
and declined to settle it) and
[ADR-034](ADR-034-pointer-and-fanout-rulings.md) §e2 reason 1 and §f row 2
(the A2 decline that rests on it). Does **not** amend ADR-004 or ADR-005:
both are re-affirmed below, against the reading that would have overturned
them. No extractor behaviour changes — `extract_items` is byte-identical to
`origin/main` (§h).

**Ruling**: a pointer body is judged at two layers, not one — the SPAN is correct on every in-class item (ADR-004 shape 2 stands), and the DEFECT, where there is one, is the envelope reporting such an item clean: `cvx-2015` items 2, 6 and 7A are `defect`, the other 11 enumerated in-class items `correct` (plus `xom-2021`'s 4, readmitted in §e3, also `correct`), and `mrk-1995` 5/7 + `nvda-2024` 8 `out-of-class`.
**Because**: the only thing `extracted` claims is INV-S2 (`normalized_text[start:end]` is the item's text verbatim), which holds everywhere here; what the contract can be dishonest about is content the output does not contain, and that is measurable — the three defects are exactly the in-class items whose named target lies outside every span AND whose `review_required` is `false` at 0.95.
**Enforced by**: `evals/adversarial/cvx-2015-silent-pointer-items.json` (`debt`, watched red), `evals/adversarial/cvx-2015-internal-pointer.json` (`debt`, amended note), `evals/adversarial/ledger-line-refs.json` (floor 11 → 14), `tasks/reviews/d13_span_dump.py`, `tasks/reviews/d13-span-dump.txt`

---

## a) The question, and why it had to be answered before anything is built

ADR-019 §e recorded a disagreement and said so in those words: the
extraction-auditor's blind sample adjudicated `cvx-2015` item 6 **CORRECT**;
the T11 author read the same shape **WRONG**; neither was adopted. ADR-034
§e2 then declined the whole A2 class with that unresolved disagreement as its
reason 1 — "a milestone would fix what two independent reads disagree is
broken" — and §f row 2 named the instrument that would reopen it: an
extraction-auditor pass over the instances, threshold **one instance both
reads agree is wrong**. Reason 2 of that decline was falsified at the PR #57
merge (ADR-034 §e2's dated cross-reference, `tasks/TODO.md` TD-1), so reason 1
has been carrying the decline alone since 2026-08-26.

This ADR settles reason 1. It rules on what is broken. It builds nothing, and
it does not decide whether anything should be built — see §f.

**The evidence instrument.** `tasks/reviews/d13_span_dump.py` runs
`extract_items` with default flags over each filing and prints, per item, the
span text verbatim, `status`/`confidence`/`review_required`, `meta.coverage`,
every contiguous region of `normalized_text` outside every span, and — for
each location the item's body names — a hand-chosen anchor for the content at
that location together with a count of that anchor's matches per owning item
and outside every span. Its output is committed at
`tasks/reviews/d13-span-dump.txt`. Every figure below is printed by that
script; none is retyped. The script deliberately does **not** emit a
"reached" boolean: a regex cannot tell the content itself from a
cross-reference to it, so it prints the distribution and §c adjudicates it,
the same concession `tasks/reviews/d9_class_scan.py` makes for its Class B
hits.

## b) The rule, stated before it is applied

Three questions, in order. Each is answered on measurement, and each belongs
to a different layer of the pipeline. The rule is applied uniformly in §c,
including where it produces a verdict this ADR would rather not have.

**R1 — the class gate.** An item is in the internal-pointer class iff all
three hold:

1. its body is **pointer-only** — it names where an answer is and gives no
   substantive standalone answer of its own (ADR-034 §b3's `ba-2003` item 5 /
   `intc-2002` item 5 / `textron-2001` item 5 rejections are this prong);
2. it names a **locatable position** — a page, a page range, an index, a
   table of contents, or a titled section — as opposed to merely asserting
   that the answer exists somewhere;
3. that position is **inside the filed document**. A pointer naming a
   different document — a proxy statement, a separately furnished Annual
   Report to shareholders, a separately filed exhibit — is out of class and
   belongs to ADR-004 shape 1, whose question is `status`, not span.

**Out-of-class is not a synonym for correct.** It means this ADR is not the
document that rules on the item. §e4 says what to do with the two out-of-class
items whose status looks wrong under a different ADR.

**R2 — span fidelity, the segmentation layer.** Does
`normalized_text[start:end]` equal the text the filing placed under that
heading? That is INV-S2 and it is the *only* thing `status: extracted`
claims: `specs/001-sec10k-contract.md` publishes no field asserting that a
span contains the substance responsive to the item, and deliberately has no
separate `text` field to drift from the offsets. R2 failing is a defect at
the segmentation layer.

**R3 — envelope honesty, the escalation layer.** With R2 passing, resolve the
target the item's own body names — **one hop only**; chasing a target's own
targets is unbounded and, on this corpus, walks straight out of the document
(§c, `ge-1994`). Then:

- **target inside some span** — the responsive content is in the output,
  under another item's code. Nothing the filing contains is absent from the
  envelope; the mis-location is the filing's own labelling, which ADR-004
  forbids the extractor to second-guess. → `correct`.
- **target outside every span** — the responsive content is in
  `normalized_text` and inside no span; the envelope does not contain the
  answer. Whether that is a *defect* turns on whether the envelope says so.
  `confidence` "must be honest" (`specs/001-sec10k-contract.md`) and
  `review_required` is "true exactly when some warning in `warnings` carries
  this item's code". An item reported at 0.95 with `review_required: false`
  is asserting a clean read of an item whose answer the output does not
  hold. → `defect`. An item already carrying an item-level warning, or
  capped by an `ambiguous` document verdict, has already said it. →
  `correct`.
- **any named target outside every span** counts, not just the principal
  one. The strict form is chosen over "the principal target is reached"
  because the strict form needs no judgement about which target is principal,
  and judgement is where a rule bends toward the headline. §g records the one
  item that flips under the lenient variant.

**What the rule refuses to be.** It is not "a pointer body is wrong because
it is a pointer" — phrasing does no work anywhere in §c. It is not "a short
span is wrong" — `ge-1994` item 8, at 86 chars the shortest item here, is
`correct`. And it is not a coverage threshold — the three
highest-coverage filings in the class (`jpm-2024` 0.9931, `xom-2021` 0.9799,
`bac-2006` 0.9285) contribute eleven `correct` verdicts and nothing else,
while all three defects come from `cvx-2015` at 0.2718; but §c reaches every
one of those from the per-target measurement, and `ge-1994` at 0.2306 — lower
than `cvx-2015` — is `correct`.

## c) The adjudication, item by item

Span text is quoted verbatim from `tasks/reviews/d13-span-dump.txt`; heading
line and body are the two halves of the span. "target" is what the body
names; "matches" is that target's anchor, counted by the item whose span
contains each match and by matches inside no span at all, excluding the
pointing item's own span (which contains the pointer sentence, not the
content).

### c1) `cvx-2015` — 5 items, 3 defects

`doc_status` `success_with_warning`; `meta.coverage` **0.2718**; 417,517
normalized chars, 113,501 inside some span; the regions outside every span
are `[0, 9725)` and **`[123226, 417517)` = 294,291 chars** — the whole FS-
paginated section, MD&A and financial statements included.

**Item 2 — `defect`.** Span 534 chars, `extracted`, **0.95**,
`review_required` **false**.

> `Item 2. Properties`
>
> `The location and character of the company's crude oil and natural gas properties and its refining, marketing, transportation and chemicals facilities are described on page 3 under Item 1. Business. Information required by Subpart 1200 of Regulation S-K ("Disclosure by Registrants Engaged in Oil and Gas Producing Activities") is also contained in Item 1 and in Tables I through VII on pages FS-61 through FS-71. Note 16, "Properties, Plant and Equipment," to the company's financial statements is on page FS-41.`

R1: pointer-only, three locatable positions, all inside this document → in
class. R2: passes. R3: three targets. "page 3 under Item 1. Business" is
item 1's span, 82,907 chars → reached. "Tables I through VII on pages FS-61
through FS-71" — anchor `FS-61\b`, 2 matches inside item 1 (item 1's own
prose referring to the tables) and **1 outside every span**, at 127,268: the
tables themselves are in the tail. "Note 16 … page FS-41" — anchor
`(?i)properties, plant and equipment`, **0 matches inside any span and 22
outside**. Two of three targets unreached, and the envelope reports the item
clean at 0.95. → `defect`.

**Item 6 — `defect`.** This is the item the whole disagreement is about. Span
119 chars, `extracted`, **0.95**, `review_required` **false**.

> `Item 6. Selected Financial Data`
>
> `The selected financial data for years 2011 through 2015 are presented on page FS-60.`

R1: in class. R2: passes — the span is exactly what the filing put under that
heading, and on this the auditor's ADR-019 read was right. R3: anchor
`FS-60\b` gives 1 match inside item 15 and **1 outside every span**. The
item-15 match is at 122,087, inside the 1,868-char exhibit index, and is a
*reference* to page FS-60, not the five-year table; the table is the match at
127,200, in the 294,291-char tail. The selected financial data are in no
span, and the envelope reports the item clean at 0.95. → `defect`.

**Item 7 — `correct`.** Span 280 chars, `extracted`, **0.80**,
`review_required` **true** (`item_span_near_empty`, ADR-035).

> `Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations`
>
> `The index to Management's Discussion and Analysis of Financial Condition and Results of Operations, Consolidated Financial Statements and Supplementary Data is presented on page FS-1.`

R3: target unreached — anchor `(?i)consolidated statement of income` gives 1
match inside item 15 (the exhibit index again) and **18 outside every span**.
The answer is not in the envelope. But the envelope says so: the item carries
its own warning, its confidence is off the clean value, and `review_required`
is true. Under R3 that is `correct`. **This is the sharpest concession the
rule makes**, and it is the same item ADR-019 §e read as WRONG: the reading
that item 7 is defective was written before ADR-035 shipped
`item_span_near_empty`, and ADR-035 closed the half of the complaint that was
about the envelope. What remains — that resolving `page FS-1` would put real
content in the span — is a capability, not a defect (§f).

**Item 7A — `defect`.** Span 453 chars, `extracted`, **0.95**,
`review_required` **false**.

> `Item 7A. Quantitative and Qualitative Disclosures About Market Risk`
>
> `The company's discussion of interest rate, foreign currency and commodity price market risk is contained in Management's Discussion and Analysis of Financial Condition and Results of Operations — "Financial and Derivative Instrument Market Risk," on page FS-15 and in Note 10 to the Consolidated Financial Statements, "Financial and Derivative Instruments," beginning on page FS-35.`

R3: both targets unreached and unambiguously so — `FS-15\b` gives **0 matches
inside any span, 2 outside**; `FS-35\b` gives **0 inside, 1 outside**. Clean
at 0.95. → `defect`. Note this item is 453 chars — the longest of the three
defects and nearly four times item 6 — which is why length is not the
discriminator and why `SPAN_FLOOR` alone would not have caught it (§f's
closing note).

**Item 8 — `correct`.** Span 189 chars, `extracted`, **0.80**,
`review_required` **true**.

> `Item 8. Financial Statements and Supplementary Data`
>
> `The index to Management's Discussion and Analysis, Consolidated Financial Statements and Supplementary Data is presented on page FS-1.`

Same measurement as item 7, same verdict, same reason.

### c2) `ge-1994` item 8 — `correct`

`meta.coverage` 0.2306; outside-span regions `[0, 4020)` and
**`[87674, 362717)` = 275,043 chars**. Span 86 chars, `extracted`, **0.80**,
`review_required` **true**.

> `Item 8.  Financial Statements and Supplementary Data`
>
> `      See index under item 14.`

R1: pointer-only; "index under item 14" is a locatable position inside this
document → in class (prong 2 is satisfied by an index, not only by a page
number; §g1 records what that costs). R2: passes. R3, one hop: the target is
item 14's index, and item 14 is `extracted` with a 10,377-char span — anchor
`(?i)statement of financial position` matches at 78,112, inside item 14. The
named target is reached. → `correct`.

The one-hop rule earns its keep here. Item 14's index resolves onward to "the
GE Annual Report to Share Owners for the fiscal year ended December 31,
1993", and the 275,043-char tail is that Annual Report inline in the same
`.txt`. The second hop therefore leaves the document under R1 prong 3 — which
is exactly how this filing's own item 7 is already ruled
(`incorporated_by_reference`, "Reported on pages 32-43 … of the Annual Report
to Share Owners"). Chasing hops would have made item 8 external, i.e. a
different class again; stopping at one hop keeps it in this one and rules it
correct.

### c3) `jpm-2024` items 1C / 7 / 7A / 8 — all `correct`

`doc_status` **`ambiguous`** (`last_item_dominates` on item 15), so ADR-027 §a
caps every item at **0.75**; `meta.coverage` 0.9931; the region outside every
span after the last is 1,564 chars.

> item 1C (172 chars): `Refer to the Operational Risk Management section of Management's discussion and analysis on pages 153–156 for a discussion of cybersecurity risk.`
>
> item 7 (398): `Management's discussion and analysis of financial condition and results of operations, entitled "Management's discussion and analysis," appears on pages 52–167. Such information should be read in conjunction with the Consolidated Financial Statements and Notes thereto, which appear on pages 172–321.`
>
> item 7A (274): `Refer to the Market Risk Management section of Management's discussion and analysis on pages 141–149 for a discussion of quantitative and qualitative disclosures about market risk.`
>
> item 8 (372): `The Consolidated Financial Statements, together with the Notes thereto and the report thereon dated February 14, 2025, of PricewaterhouseCoopers LLP, the Firm's independent registered public accounting firm (PCAOB ID 238), appear on pages 169–321.`

R3: every target lands inside item 15's 1,010,422-char span and **zero
matches fall outside any span** — 7 for item 1C's anchor, 33 for item 7's,
19 for item 7A's, 33 for item 8's, all owned by item 15. The content is in
the envelope, misattributed to item 15 rather than absent; `last_item_dominates`
and `doc_status: ambiguous` publish exactly that. ADR-034 §b4 called these
"misattributed rather than unreached" and the per-target measurement agrees.
→ `correct`, all four.

### c4) `bac-2006` items 3 / 6 / 7A — all `correct`

`doc_status` **`success`**, **no warnings at all**; `meta.coverage` 0.9285;
all three items `extracted` at **0.95** with `review_required` **false**.

> item 3 (229 chars): `See "Litigation and Regulatory Matters" in Note 13 of the Consolidated Financial Statements beginning on page 137 for Bank of America's litigation disclosure which is incorporated herein by reference.`
>
> item 6 (202): `See Table 5 in the MD&A on page 21 and Table XII of the Statistical Financial Information on page 95 which are incorporated herein by reference.`
>
> item 7A (175): `See "Market Risk Management" in the MD&A beginning on page 72 which is incorporated herein by reference.`

R1: pointer-only, page-numbered, internal → in class. The words "incorporated
herein by reference" do not make these ADR-004 shape 1: the target is Note 13
and the MD&A of this same 10-K, and ADR-004 turns on the target document, not
the phrasing. R2: passes. R3: **zero matches outside any span for all three
targets** — item 3's anchor is owned by items 1A and 8, item 6's by items 7,
8 and 15, item 7A's by items 1, 1A and 7; items 7 and 8 here are 333,940 and
270,737 chars, i.e. the MD&A and the financial statements are fully labelled
in this filing. → `correct`.

**This is the verdict the rule is least comfortable with, and it is taken
anyway.** These three are the only in-class items in the corpus that are
silent at 0.95 in a document with **no warning of any kind**, and a consumer
asking this envelope for Item 6 gets 202 chars of pointer. The rule says
`correct` because nothing the filing contains is missing from the output —
the answer is in item 7's span. If the standard were "the span holds the
substance responsive to the item", these three would be defects and so would
all four `jpm-2024` items; §f's second and third rows name that as the
reopener, and §d3 and §g8 record that this is the ruling's weakest joint —
the blind auditor rules exactly these three WRONG.

### c5) `spatz-2014` item 8 — `correct`

`meta.coverage` 0.6632; regions outside every span `[0, 4653)` and
**`[47890, 65197)` = 17,307 chars**. Span 241 chars, `extracted`, **0.80**,
`review_required` **true** (`item_span_near_empty`).

> `Item 8.`
>
> `Financial Statements and Supplementing Data`
>
> `The financial statements of the Company and the related report of the Company's independent registered public accounting firm thereon are included in this report on pages 15 through 22.`

R3: target unreached, and the least ambiguously of any item here — anchor
`(?i)report of independent registered public accounting firm` matches
**exactly once in the document, at 48,815, inside no span**, i.e. in the
17,307-char tail that begins after item 15 ends at 47,890 (the tail opens
with `SIGNATURES`). The financial statements this item points at are in the
document and in no span. But the item carries its own warning at 0.80. →
`correct`, on the same reasoning as `cvx-2015` items 7 and 8.

Two things noted and not ruled on: this filing's `heading_text` is the bare
`Item 8.` with the title `Financial Statements and Supplementing Data`
falling into the body, and its item 15 body says `Financial Statements: as
referenced in Item 8 hereof` — a two-hop cycle between items 8 and 15 with
the statements in neither. Neither changes the verdict under R2 or R3; the
cycle is logged as debt (TD-157, named in §e3).

### c6) `nvda-2024` item 8 — `out-of-class`

ADR-019 §e's 2026-08-26 amendment names this item as "a fourth member of the
class". Under R1 it is not one. Span 209 chars, `extracted`, 0.80,
`review_required` true.

> `Item 8. Financial Statements and Supplementary Data`
>
> `The information required by this Item is set forth in our Consolidated Financial Statements and Notes thereto included in this Annual Report on Form 10-K.`

R1 prong 2 fails: the body names **no position**. It asserts that the answer
is somewhere in this document and nothing more — there is no page, no page
range, no index, no titled location to resolve. That is the identical ground
on which ADR-034 §b3 rejected `xom-2021` item 15 ("no page number at all"),
and the two ADRs cannot classify the same shape differently. "This Annual
Report on Form 10-K" is a self-reference, not an external document, so prong 3
is not what excludes it.

Recorded because it matters for how the class was counted: ADR-019 §e found
this item through ADR-035's `item_span_near_empty` measurement, while
ADR-034 §b3 found its members through a page-reference regex. **The two ADRs
have been using different class tests**, which is how one of them acquired a
member the other's rule rejects. R3 would rule it `correct` in any case —
its anchor matches 13 times inside item 15 and once inside item 7, **zero
outside any span**.

### c7) `mrk-1995` items 5 and 7 — `out-of-class` (the calibration check)

Held-out fixture, `evals/heldout/fixtures/mrk-1995`. Both `extracted`; item 5
at 0.95 `review_required` false, item 7 at 0.80 `review_required` true.

> item 5 (231 chars): `ITEM 5.  MARKET FOR THE REGISTRANT'S COMMON EQUITY AND RELATED STOCKHOLDER MATTERS.` / `     The information required for this item is incorporated by reference to pages 37 and 51 of the Company's 1995 Annual Report to stockholders.`
>
> item 7 (247 chars): `ITEM 7.  MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS.` / `     The information required for this item is incorporated by reference to pages 28 through 37 of the Company's 1995 Annual Report to stockholders.`

R1 prong 3 fails: the named document is the Company's 1995 Annual Report to
stockholders, not this 10-K. Out of class, cleanly and on the rule's own
first question — which is what TD-150 asked for and what a rule that could
not do this would have failed.

**TD-150's open sub-question is answered, and it does not change the verdict.**
TD-150 records that "whether the Annual Report is physically inside these same
bytes is itself unestablished". It is inside them: the committed
`filing.txt` is a 322,618-char full submission whose `<DOCUMENT>` blocks are
`10-K405` at raw offset 1,358 and then nine exhibits, of which **`EX-13` at
raw offset 145,400** is the Annual Report; `(?i)consolidated statement of
income` matches at raw 320,256, inside `EX-27`, and at 66,716, inside the
10-K405 block itself. The extractor selects the 10-K405 document, so
`normalized_text` is 81,842 chars and the Annual Report is not in it at all.
Physical co-location in one submission does not make it the same document:
EDGAR's own `<DOCUMENT>`/`<TYPE>` framing says it is a separately furnished
exhibit, and `ge-1994` item 7 is already ruled `incorporated_by_reference`
over exactly this shape with exactly this reasoning (ADR-004 shape 1, "a
separately printed exhibit").

## d) The blind re-audit

*(Section written after the ruling above was fixed; §c was not shown to the
auditor and is unchanged by what follows.)*

The `extraction-auditor` subagent was re-run on a nine-item sample —
`cvx-2015` 2/6/7A/8, `bac-2006` 3/6, `spatz-2014` 8, `jpm-2024` 7,
`mrk-1995` 5 — chosen to straddle every distinction §b turns on without
naming any of them. The blind input is committed verbatim at
`tasks/reviews/d13-auditor-input.txt` and is generated by
`d13_span_dump.py --auditor-input`, so what the auditor saw can be
regenerated: per item, the document's `doc_status` / `meta.coverage` /
warning list and the item's own `status`, `confidence`, `review_required`,
offsets and span text. It was asked one question — is the pipeline's output
for this item RIGHT or WRONG — and was instructed not to read `specs/decisions/`,
`tasks/`, `docs/`, the eval case files or git history, so it saw neither this
ruling, nor §b's rule, nor ADR-019 §e's or ADR-034's prior verdicts.

Its full output is committed verbatim at
`tasks/reviews/d13-auditor-verdicts.md`. It confirms it read the contract, the
invariants and the fixtures and none of the forbidden material.

### d1) The comparison

| filing | item | ADR-038 §c | auditor | agree? |
|---|---|---|---|---|
| `cvx-2015` | 2 | `defect` | WRONG (held weakly) | **yes** |
| `cvx-2015` | 6 | `defect` | WRONG | **yes** |
| `cvx-2015` | 7A | `defect` | WRONG | **yes** |
| `cvx-2015` | 8 | `correct` | WRONG (held weakly) | **no** |
| `bac-2006` | 3 | `correct` | WRONG ("the most severe of the nine") | **no** |
| `bac-2006` | 6 | `correct` | WRONG | **no** |
| `spatz-2014` | 8 | `correct` | WRONG (held weakly) | **no** |
| `jpm-2024` | 7 | `correct` | WRONG (held weakly) | **no** |
| `mrk-1995` | 5 | `out-of-class` | WRONG | not comparable — see §d4 |

**Three of nine agree. Five diverge. One is not a like-for-like comparison.**
Nothing below adopts the auditor's answer, argues it down, or re-runs it for a
better one.

### d2) `cvx-2015` item 6 — the threshold in ADR-034 §f row 2 is MET

The item the whole disagreement was about is now adjudicated **WRONG by both
reads**, which is exactly the reopener ADR-034 §f row 2 names ("one instance
both reads agree is wrong"). The reads also agree on the *reason*, reached
independently: the auditor's ground is that item 6 at 119 chars publishes
`0.95 / review_required=False` while item 8 in the same filing at 189 chars —
longer — publishes `0.80 / review_required=True`, so "the shorter, equally
contentless item is published as the *more* trustworthy of the two". That is
§c1's finding arrived at from the opposite direction, and it is the first
time in this class's history that two independent reads have converged.

It also reverses ADR-019 §b's sensitivity note in the direction ADR-019
declined to choose: that ADR published **1/30 (auditor) vs 2/30 = 6.7%
(author)** and adopted neither, the difference being item 6 alone. Both reads
now hold item 6 wrong, so **2/30 is the rate both reads support**. ADR-019 §b's
published 1/30 point estimate is superseded by that, and its CI is not
re-derived here — n is unchanged, and re-deriving an interval is not what a
decision row is for.

**What this does NOT do is promote A2.** The reopener fires; the ruling it
reopens to is §e1's. Both reads locate the defect in what the envelope says
about item 6, not in the FS pages being absent from its span.

### d3) The five divergences, as divergences

The auditor's rule and this ADR's differ at exactly one joint, and it is a
joint §b names: whether an item whose named target is inside **another item's
span** is correct. §b's R3 says yes — the content is in the envelope. The
auditor says no, on a ground §b does not weigh: `confidence` is an *item-level*
field, and a consumer thresholding on it per item cannot see that the answer
was filed under a neighbouring code. In its words: "no consumer reading
`status` can tell a complete Item 3 from a pointer Item 3."

- **`bac-2006` 3 and 6** are where that bites hardest, and the auditor is
  making a stronger argument than §c4 anticipated. It is not "the consumer
  did not get the substance"; it is that this same output classifies the same
  speech act two ways — `bac-2006` item 3 is `extracted` at 0.95 while item 10
  is `incorporated_by_reference` at 0.85, and "the only thing that differs is
  where the target physically sits, which is not something the consumer's
  threshold can see". **The reply this ADR has is narrow and is stated as
  narrow**: that difference is precisely what ADR-004 rules on, deliberately,
  and the auditor could not read ADR-004 — it says so itself (§5 of its
  report: "I cannot say whether my reading contradicts a settled decision").
  So on `status` the divergence is a challenge to ADR-004, not to this
  adjudication. **On `confidence` it is not**, and there this ADR has no
  reply: `bac-2006` 3/6/7A publish 0.95 with `review_required: false` on a
  `doc_status: success` envelope with `warnings: []`, which is the same
  silence §c1 convicts `cvx-2015` 2/6/7A for. The two verdicts differ only
  because R3 asks about the target first and the confidence second. **A rule
  that asked in the other order would convict them, and this ADR does not
  claim to have shown that order wrong.** §f's third row is the reopener; it is
  written as one instance of demonstrated consumer-visible harm, and the
  auditor's argument is an argument for that harm rather than a
  demonstration of it, which is the whole of the remaining gap.
- **`cvx-2015` 8, `spatz-2014` 8, `jpm-2024` 7** are the auditor's own three
  weakest calls, and it names the exact ruling that would flip them: "If an
  ADR rules that an intra-document pointer stays `extracted` and that item
  spans are heading-to-heading with no obligation to resolve internal
  references, I would concede all three to RIGHT." That ruling is ADR-004
  shape 2, which predates both reads and which §b R2 re-affirms. It would
  **not** concede the 0.95 group on the same ruling — and on the 0.95 group
  the two reads already agree. So the residue is: the auditor holds a
  status-layer objection to ADR-004 that this row has no mandate to settle,
  and once ADR-004 is granted, four of the five divergences reduce to
  `bac-2006` 3/6's confidence complaint.

### d4) `mrk-1995` item 5 — an answer to TD-150, not a disagreement with §c7

§c7 rules item 5 **out-of-class**, i.e. not this ADR's question. The auditor
rules the *output* WRONG on ADR-004 grounds it reached independently: item 5
and item 6 of the same filing are five lines apart, carry the same sentence
template naming the same external Annual Report, and come back `extracted` at
0.95 and `incorporated_by_reference` at 0.85 respectively. It also establishes
the EDGAR framing directly (`<TYPE>EX-13`, `<DESCRIPTION>PAGES 28-51 1995
ANNUAL REPORT` at line 2799 of the raw file), independently reproducing §c7's
finding, and it widens the count: items **7 and 8** are ARS pointers coming
back `extracted` as well, so **three of Merck's four Annual-Report pointers
are misclassified**, not two. The two reads do not conflict — §e4 already
holds that this is an open ADR-004 question — and D13 does not adopt the
answer, because adopting it changes `status` on real items and D13 changes no
behaviour. TD-150 carries it, widened.

### d5) What the auditor found that this ADR did not

Recorded because it is evidence this ruling did not produce, not because it
was asked for.

1. **The escalation layer's item set, measured corpus-wide.**
   `item_span_near_empty` is emitted for exactly three item codes across all
   45 dev fixtures plus the held-out set: `{'7': 7, '8': 15, '1': 2}`.
   Therefore `review_required` is "structurally incapable of firing on a
   near-empty Item 2, 3, 5, 6, 7A or 9" — "a discriminator that cannot
   discriminate". That is independent, quantified corroboration of §f's
   routing to TD-5, arrived at without reading TD-5, and it is a stronger
   statement of the mechanism than §c1 makes.
2. **A control this ADR's sample lacked.** The auditor supplied its own:
   `spatz-2014` items 2, 3 and 6 (`None.`, `None.`, `Not applicable.`) are
   also 0.95 / `review_required: false` and it judges them **correct**,
   showing "my objection is to pointer items specifically, not to short
   items". That is ADR-005 re-derived blind, and it closes off the reading
   that the auditor is simply penalising short spans.
3. **`jpm-2024` items 11, 13 and 14** are `Refer to Item 10.` at 0.75,
   `review_required: false`, `status: extracted`, while item 10's span is
   executive-officer biography — a two-hop internal pointer chain that returns
   an entire Part III as `extracted`. Not in the enumerated class, not
   adjudicated here; logged as debt (TD-155).
4. **`COVERAGE_MIN` bounded behaviourally** to (0.0303, 0.2718] from outputs
   alone, with the observation that a 27%-coverage document currently leaves
   as `success_with_warning` rather than a verdict. Consistent with ADR-035's
   0.13; no finding, recorded so the bound is not re-derived a third time.

### d6) Weaknesses in how this comparison was run

- **The sample had no negative control.** All nine items handed to the auditor
  are pointer-bodied, so a uniform WRONG was available without discriminating
  anything, and the auditor says so itself. Its verdicts are usable only
  because it supplied its own controls (§d5.2) and its own weak/strong
  grading. A sample designed by this row should have carried two or three
  non-pointer items; it did not.
- **One run, not repeated.** The auditor was invoked once and its answer taken
  as given. Re-running it would be tuning a judge, so the alternative was not
  available — but the consequence is that its verdicts have no variance
  estimate, exactly as ADR-019 §b's n=30 had none.
- **Anchors differ between the two reads and the agreement survives it.** For
  `cvx-2015` item 6 this ADR resolves "page FS-60" with the anchor `FS-60\b`
  (match at 127,200, outside every span); the auditor used
  `Five-Year Financial Summary` (offset 363,489, also outside every span).
  Different anchors, same conclusion — which is the strongest thing that can
  be said for §c's anchor method, and is said here rather than in §g3 because
  it is the auditor's evidence, not this ADR's.

## e) What this does to each Debt row

### e1) TD-12 — internal pointer to a paginated section: **stays open, re-scoped**

**ADR-034 §f row 2's reopener is TRIPPED**, and saying so is the point of
having written a threshold down: it reads "the `cvx-2015` item-6 disagreement
is adjudicated as WRONG by both reads … threshold: one instance both reads
agree is wrong", and §d2 records that both reads now hold item 6 wrong. Both
of A2's declining reasons have now fallen — reason 2 at the PR #57 merge
(TD-1), reason 1 here.

**A2 does not become a capability milestone anyway, and the reason is the
ruling rather than the row's inertia.** The reopener asks "is this agreed to be
a defect"; the adjudication answers yes for three items and locates that defect
at the escalation layer. Internal-pointer resolution does not fix it: what
makes `cvx-2015` items 7 and 8 correct today is a warning carrying their code
(ADR-035), not the FS pages being pulled into their spans, and the same
instrument is what items 2, 6 and 7A lack. A milestone that resolved `page
FS-60` would close the three defects as a side effect of building something
much larger, and would leave every other in-class item — all eleven `correct`
ones — untouched. So the A2 **outcome** stands, its **reason 1 is superseded**,
and TD-12's next move is TD-5's trigger design, not TD-12's own capability.

What the row gains: the adjudicated verdict per item; the fact that the
defect it names for items 7/8 is the one part of the class ADR-035 has
already closed; and the fact that the two items it does NOT name (2 and 7A)
plus item 6, which it explicitly excluded, are the three that are actually
broken. **The `debt` case's assertion set no longer matches the adjudicated
defect** — `cvx-2015-internal-pointer.json` asserts `min_chars` on items 7 and
8, i.e. a capability outcome on the two items ruled correct. That case is not
re-authored here (doing so changes what is red, and D13's spec is to rule);
its triage note gains the ruling, and the new
`cvx-2015-silent-pointer-items.json` carries the defect that was actually
found. Re-authoring the older case is logged as debt (TD-156).

### e2) TD-14 — combined multi-item heading: **untouched**

`axp-2008` is ADR-034's Class B and is governed by §e3 of that ADR, which its
`debt` case already cites. Nothing in D13's rule reaches a heading that names
four item codes: R1 prong 1 fails immediately, because the `axp-2008` Part III
body is not pointer-only (ADR-034 §c2 measures ~1,139 chars of standalone
Reg S-K Item 406 prose in the item-10 partition). The row is left alone and
its `debt` case is not edited, because adding a D13 citation to a case D13
does not govern is decoration, not coverage.

### e3) TD-149 — the row and ADR-019 §e understate their own class: **widened, still open**

The census is understated by more than TD-149 records, and by a mechanism
TD-149 does not name. ADR-034 §b3's scan required a digit
(`pages?\s+(?:FS-)?\d`, `FS-\d`, or the literal `see index`), so it could only
ever find page-numbered pointers. Under R1 prong 2 a titled section is a
locatable position too, and `xom-2021` — a filing §b3 names only in its
rejection list — carries **four** in-class items its scan could not see:

> item 7 (267 chars): `Reference is made to the section entitled "Management's Discussion and Analysis of Financial Condition and Results of Operations" in the Financial Section of this report.`
>
> item 7A (413): `Reference is made to the section entitled "Market Risks" in the Financial Section of this report. …`
>
> item 8 (737): `Reference is made to the following in the Financial Section of this report: …`
>
> item 15 (209): `(a)(1) and (2) Financial Statements:` / `See Table of Contents of the Financial Section of this report.` / `(b)(3) Exhibits:` / `See Index to Exhibits of this report.`

All four are `correct` under R3 — every target's anchor lands inside item 16's
span with **zero matches outside any span**, and `doc_status` is `ambiguous`
so all four are capped at 0.75. But `xom-2021` item 15 was *rejected out of
the class* by ADR-034 §b3 for having "no page number at all", while
`ge-1994` item 8 — `See index under item 14.`, also with no page number — was
*admitted*. That inconsistency was the scan regex's shape, not a rule, and
this ADR overturns the rejection: **`xom-2021` items 7, 7A, 8 and 15 are
in class and correct.** The adjudicated dev total moves from ADR-034 §b3's
**14 items across 5 filings to 18 across 6** — §b3's 14 (`cvx-2015` 5,
`jpm-2024` 4, `bac-2006` 3, `ge-1994` 1, `spatz-2014` 1) plus `xom-2021`'s 4.
`nvda-2024` item 8 does not enter and leaves the count unchanged: §b3's 14
never contained it — it was ADR-019 §e's own addition — and §c6 rules it out.

Two further findings for the row, neither ruled on here: `spatz-2014` items 8
and 15 point at each other with the financial statements in neither span
(§c5), and `ge-1994` item 6 — `appearing on page 43 of the Annual Report to
Share Owners` — is out of class on prong 3 but is then the same shape as
`mrk-1995` 5/7 in the *same filing whose item 7 is already IBR*, i.e. the §e4
inconsistency below has a second instance nobody has enumerated. They are
carried by TD-157 and TD-150 respectively.

### e4) TD-150 — `mrk-1995` 5/7 over external pointers: **sharpened, still open, and widened**

D13 confirms both items are out of the internal-pointer class (§c7) and
answers the sub-question TD-150 left open — the Annual Report *is* physically
inside the same `.txt`, as a separate `EX-13` `<DOCUMENT>`, and that does not
make it the same document.

What D13 does **not** do is rule on their `status`. That is an ADR-004
question and it now has a sharper form than TD-150 states: within one filing,
`ge-1994` item 7 ("Reported on pages 32-43 … of the Annual Report to Share
Owners") is `incorporated_by_reference` while `ge-1994` item 6 ("appearing on
page 43 of the Annual Report to Share Owners") is `extracted` at 0.95. The
same output classifies the same shape two ways. TD-150 is widened to name
`ge-1994` item 6 alongside `mrk-1995` 5/7 and ADR-034 §b3a's four `intc-2025`
proxy-`(a)` bodies. It stays open because fixing it changes `status` on real
items, which is behaviour, and D13 changes none.

## f) What would overturn this ruling

Each names an instrument and a threshold.

| what is overturned | what overturns it | instrument | threshold |
|---|---|---|---|
| the three `defect` verdicts (`cvx-2015` 2/6/7A) | the escalation layer starts carrying those items — a warning naming their code, or an `ambiguous` document verdict. Then R3's second bullet no longer applies and they become `correct` without anything being "fixed" in the sense TD-12 means | `evals/adversarial/cvx-2015-silent-pointer-items.json` going green | all three |
| the eleven `correct` verdicts | the contract gains a clause, or a case gains an assertion, that a span must hold the substance responsive to its item and not merely the labelled text. R2's premise — that INV-S2 is all `extracted` claims — is then false and every in-class item is a defect | `specs/001-sec10k-contract.md` + the golden set | one clause |
| `correct` on `bac-2006` 3/6/7A specifically (§c4, the weakest joint) | a consumer-visible harm from content being labelled under a neighbouring item's code, demonstrated on a filing rather than argued: an item whose named target is inside another span AND whose absence from its own span is shown to break a stated downstream use | a case, or an audit finding on a real filing | one instance |
| `out-of-class` on `nvda-2024` 8 and `xom-2021` 15 under the old rule | R1 prong 2 is rewritten to admit "the answer is somewhere in this document" with no position named. That also readmits `xom-2021` 15 the other way, so the rewrite must handle both or it is not a rule | R1 as stated in §b | either |
| the whole rule | an in-class item is found where R2 fails — a pointer-bodied item whose span is NOT the verbatim labelled text. The two-layer split assumes segmentation is sound on this shape; it is measured sound on all 18 here and asserted by the `verbatim` check on both `debt` cases | `evals/adversarial/cvx-2015-*.json` `verbatim` checks, or a new fixture | one instance |

**Explicitly not sufficient**: a pointer body being short; a filing having low
coverage; the `debt` cases still being red, which is what this ADR permits.

**Not decided here, and named so it is not read in.** Whether the escalation
layer *should* be widened to reach `cvx-2015` 2/6/7A is TD-5's question, not
this ADR's, and TD-5 already records measured counter-evidence against the
obvious fix: items 1A/7A/1B/4/6/9/9B/9C/16 are legitimately one sentence on
real filings, so widening `SPAN_FLOOR`'s item set alone would fire on every
2021+ `[Reserved]` item 6 and re-open the `vacuous_coverage` finding ADR-027
§c closed. The trigger this ruling implies is the pointer *shape*, not the
length — item 7A is 453 chars, longer than several correctly-flagged
items — and designing it is capability work with its own ADR and its own
freeze exception.

## g) What this ADR did not establish

1. **R1 prong 2 has a soft edge.** "A locatable position" admits `See index
   under item 14.` and `See Table of Contents of the Financial Section` while
   excluding `set forth in our Consolidated Financial Statements … included
   in this Annual Report on Form 10-K`. The line is real — the first two name
   a thing a reader turns to, the third names only the answer's existence —
   but it is a line drawn in prose and two of the corpus's items sit close to
   it. The ruling is unchanged either way for both (`nvda-2024` 8 and
   `xom-2021` 15 are `correct` under R3 if readmitted), so nothing here
   turns on it; a case that did would need the prong made executable first.
2. **`cvx-2015` item 2 flips under the lenient variant of R3's third bullet.**
   Its principal target — the properties description at "page 3 under Item 1.
   Business" — *is* reached; only the Reg S-K Subpart 1200 tables and Note 16
   are not. Under "the principal target is reached → correct" item 2 is
   `correct` and the defect count is two, not three. It is the only item in
   the corpus that moves. The strict form is chosen in §b for a stated
   reason and this is what that choice costs.
3. **The anchors are hand-chosen.** §c's reached/unreached calls rest on one
   regex per target, picked by hand and printed with the output so a reader
   can move it. `bac-2006` item 6 is the loosest of them (`consolidated
   statement of income` for "Table 5 in the MD&A on page 21"): it names the
   financial statements rather than Table 5, and it is defensible only
   because the MD&A and the statements are both fully inside spans on that
   filing, so no anchor choice could produce an outside match. On a filing
   where the two diverged it would be the wrong anchor.
4. **Only `cvx-2015` was adjudicated at document level.** The three defects
   are all in one filing. Whether the silent-at-0.95 shape occurs elsewhere
   was not censused — TD-149's widening (§e3) found four more in-class items
   on `xom-2021` by reading four bodies, not by a corpus scan, and no scan
   for the *silent* sub-shape has ever been run.
5. **No held-out filing was adjudicated in class.** `mrk-1995` is held out
   and is out of class; the in-class corpus here is entirely dev-side. The
   ruling's generality to unseen filings is asserted, not measured.
6. **The rule is not executable.** R1 and R3 are applied by a human reading
   §c against a printed measurement. Nothing in the gate can apply them to a
   new filing, and `cvx-2015-silent-pointer-items.json` pins the *outcome* on
   three items, not the rule.
7. **Almost nothing in this ADR is gated.** `evals/bench.py --check-docs`
   reads only ADR-021 among the ADRs and matches decimals only, so every
   integer here is unchecked — ADR-034 §h says the same of itself. The one
   executable tie is `ledger_line_refs`, which verifies the `path:line`
   citations `tasks/TODO.md` makes to this file against the sentence they
   quote (floor raised 11 → 14). A figure inside §c that no ledger row quotes
   can go stale silently; the mitigation is that
   `tasks/reviews/d13_span_dump.py` regenerates all of them in one command.
8. **The auditor's confidence objection to `bac-2006` is unanswered, not
   answered.** §d3 says so plainly. This ADR rules those three `correct` on a
   rule fixed before the sample was run, and it does not claim the auditor's
   ordering of the two questions was shown wrong — only that R3 asks them in
   the order §b states and was applied uniformly. A reviewer who thinks the
   other order is right should read §d3 and §f's third row, not §c4 alone.

## h) Byte-identity

D13 changes no code. `python3 evals/snapshot.py <tree> <out>` over
`origin/main` at `d83b8a21ca2735afc59edc636ed2ca24532db798` and over this
branch, default flags, 62 dev + 6 held-out filings:

| corpus | digest, both trees |
|---|---|
| dev, 62 files | `365da1ce8e9522df279dde64251f8fad5fb839115e4d37a3459700695d790f35` |
| held-out, 6 files | `4d2a7128b06a328b201a25314c4568146a6913e8cc508fa7b35d638a7abc1784` |

`cmp` over the two snapshot files exits **0**; both files hash to
`ed15a09eecc025dd09759a35035786812f09aae82ab9039d821ba4c3e67cbb19`. The
`origin/main` tree was materialised with `git archive origin/main | tar -x`
into a scratch directory rather than a second worktree.

## Verification

- `python3 -m evals.run --suite invariant` — score 1.000, baseline untouched.
- `python3 -m evals.run --suite fast` — score 1.000, baseline untouched.
  Suite sizes deliberately not quoted, per ADR-034's Verification note.
- `python3 tasks/reviews/d13_span_dump.py --table` and
  `--auditor-input` — every span, figure and blind-audit input in §c and §d.
  Committed output: `tasks/reviews/d13-span-dump.txt`,
  `tasks/reviews/d13-auditor-input.txt`.
- `python3 evals/snapshot.py --self-check` — passes; the two tree snapshots
  and their `cmp` are §h.
- `evals/adversarial/cvx-2015-silent-pointer-items.json` — watched RED before
  commit: the three `item_field` assertions fail
  (`item N review_required False != True`), the six hygiene and
  `item_present` checks pass, and `--suite invariant` reports
  `[DEBT] cvx-2015-silent-pointer-items: STILL RED` with the scored total
  unchanged.
