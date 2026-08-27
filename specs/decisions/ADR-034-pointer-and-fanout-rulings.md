# ADR-034 — D9: the internal-pointer class splits in two and neither half becomes a milestone; the combined-heading fan-out is subsumed by D11, narrowing ADR-020's stated preference

Date: 2026-08-26. Status: accepted, **repaired 2026-08-26 under PR #56 review round 1**
(3 MEDIUM, 4 LOW; `tasks/reviews/pr56-r1.json`, red evidence captured before every fix
in `tasks/reviews/pr56-r1-red.txt`). Amended by:
[ADR-038](ADR-038-internal-pointer-adjudication.md) (2026-08-27, D13 — §e2
reason 1 is SETTLED and §f row 2 is TRIPPED; §b3's class test is corrected).
What the repair changed: §b2/§b3/§b3a — A1's item
count corrected from 23 to **13 of 23** and the coverage figure named as the
load-bearing one (R2); §c1 — a false bolded claim about `c-2025` replaced with the
causal claim it meant (R1), the hit denominator corrected 17→18 (R4) and every hit
enumerated including the synthetics (R5); §g — the burn-rule ground **withdrawn** as
falsified, the burn-or-amend choice escalated, and the owner's ruling of
2026-08-26 to **amend the rule rather than apply it** recorded — neither
held-out case is burned and D11's exam survives (R3/R8);
§d — the sonnet-5 row re-dated (R7); Verification — suite sizes dropped (R6). None of
the three rulings moved. **Repaired again 2026-08-26 under PR #56 round 2**
(3 MEDIUM, 3 LOW; `tasks/reviews/pr56-r2.json`): §g's New-Debt list still
carried a settled negative answer to the burn question, fifty lines below the
text withdrawing its ground (R8); §c1 claimed a string-plus-missing
co-occurrence unique to `axp-2008` that its own `c-2025` paragraph contradicted
and `xom-2021` falsifies independently (R9); the bucket arithmetic summed
fixtures while claiming to account for all 39 hits, and filed `gs-2002` and
`xom-2021` under one bucket each when their hits fall in two (R10); plus R11-R13.
The recurring defect across both rounds was correcting the cited line and leaving
a restatement alive elsewhere, so round 3 swept each claim repo-wide —
`tasks/reviews/pr56-r2-red.txt` carries the sweep. Again no ruling moved.
Implements D9, the decision row
"promote internal-pointer resolution and combined-heading fan-out, or decline
with evidence" (`tasks/TODO.md`). Rules on two Debt rows —
"Internal pointer to a paginated section" (ADR-019 §e) and "Combined
multi-item heading" (ADR-020 §c row 7). **Narrows
[ADR-020](ADR-020-fallback-not-justified.md) §b/§c row 7 in place, with a
dated note** — its escalation ladder and its no-unconditional-fallback ruling
both stand; what falls is the specific claim that the `axp-2008` fan-out is a
$0 regex producing identical output, which §c below falsifies by running it.
**No capability is built here.** The T8 freeze guard is untouched: this
document decides, and every ruling it reaches is "do not build a milestone for
this", so it is not a sanctioned freeze exception and does not need to be.

**Cross-referenced 2026-08-26 at the PR #57 (D8) merge**: §f's third
falsifier row — "the D8 trigger, once built, fires on any of the five A2
filings" — is **TRIPPED**, 4 fires against a threshold of one. §d1's own
figures reproduce exactly; what moved is that D8 shipped a WIDER trigger
(items 1/7/8, not item 1) than §d1 measured. No ruling here is changed —
§e2 reason 2 carries the measurement and the re-read is escalated as Debt.

**Ruling**: the ADR-019 §e class splits — **A1**, a whole document collapsing onto a cross-reference index (`intc-2025`, 0.3% of the text inside any span; 13 of 23 item bodies are internal page pointers, §b3a), is **subsumed by D11** and gets no milestone of its own; **A2**, a few pointer-bodied items inside an otherwise well-extracted filing (`cvx-2015`, `jpm-2024`, `bac-2006`, `ge-1994`, `spatz-2014` — 14 items, 5 real filings), is **DECLINED and stays Debt**, because two independent reads still disagree that it is a defect and no measured trigger reaches it. The `axp-2008` combined-heading fan-out is **subsumed by D11**, not promoted.
**Because**: A1 is exactly the shape D11's own row already commits to passing, and the D8 trigger it needs fires on 0 of 42 dev fixtures; A2 has no trigger and an unsettled auditor disagreement, so promoting it would build a capability to fix something not agreed to be broken; and the fan-out's premise is false — heading-stripped, `segment.classify` returns `incorporated_by_reference` on the item-10 partition body, `axp-2008` item 9B's span runs straight through the Part III block, the class has exactly one member in 49 documents, and `axp-2008` is no longer the only real-filing recall gap now that `c-2025` reports 21 `missing` items the fan-out cannot touch.
**Enforced by**: `tasks/TODO.md`'s two Debt rows, which cite this ADR's ruling lines and are verified against them by `evals/adversarial/ledger-line-refs.json` (`invariant` + `fast`); `evals/adversarial/cvx-2015-internal-pointer.json` and `evals/adversarial/axp-2008-combined-part-iii.json`, whose triage notes name this ruling as why they are permitted to stay red; `evals/adversarial/ledger-table-shape.json`, `evals/golden/adr-header-and-index.json` (`adr_headers`, `adr_index`). §h states, without softening it, what this ADR's figures are NOT gated by.

---

## a) What was measured, and with what

Everything below is a measurement taken on this branch unless it is labelled
**ESTIMATE**. Two commands reproduce all of it:

```bash
python3 tasks/reviews/d9_class_scan.py            # corpus prevalence, both classes
python3 -m evals.run --suite fast --dir evals/heldout
```

`tasks/reviews/d9_class_scan.py` is a throwaway measurement script, not a
pipeline stage and not on any gate path — the same call ADR-020 §g made when
it declined to add a metric for its addressable-surface count, for the same
reason. Its two detectors are deliberately **over-broad**, and it prints its
knobs and every hit with context so a reader adjudicates rather than trusts:
a regex cannot tell a body heading from a cover sentence, and that distinction
is the whole question for the fan-out class. §b and §c do the adjudication in
the open, hit by hit, including the hits this ADR rejects.

**The corpus, re-derived** (ADR-020 §b's table, recomputed — it has grown):

| | fixtures | items | normalized chars |
|---|---|---|---|
| dev (`evals/fixtures/`) | 42 | 744 | 8,860,388 |
| held-out (`evals/heldout/fixtures/`) | 7 | 147 | 3,229,509 |
| **total distinct** | **49** | **891** | **12,089,897** |

ADR-020's denominator was 768 items over 42 fixtures. Every ratio it published
is stated against that corpus and is not rewritten here; where this ADR needs
the same ratio it re-derives it against 891 and says so.

**The held-out run, re-derived rather than quoted.** The D6 ledger row records
`intc-2025` and `c-2025`'s outcomes. This ADR re-ran them rather than restating
the summary, because restating a ledger line as one's own measurement is how
this repo's recurring error starts. The run agrees with the ledger exactly —
`fast` 5/7 = 0.714 over `evals/heldout` (report committed at
`evals/report/20260826-141545-fast.json`), `c-2025` and `intc-2025` red, the
other five green. Per-item:

| filing | doc_status | items | what the pipeline produced |
|---|---|---|---|
| `intc-2025` | `success_with_warning` | 23 | **all 23 `extracted` at 0.95**, spans totalling 1,727 chars of 517,976 — 0.3% of the document. One warning: `unattributed_content`, "100% of the document lies outside every item" |
| `c-2025` | `ambiguous` | 23 | **21 `missing` at 0.40**, **2 `omitted` at 0.75** (items 9C and 16), every span null. 21 `expected_item_missing` warnings plus `expected_items_mostly_missing` |

No disagreement with the ledger was found. That is a result, not an absence of
one: the D6 row's numbers are reproducible.

## b) Class A — the row's premise is wrong, and the class is two classes

### b1) `c-2025` is NOT the internal-pointer class

The D9 row says the ADR-019 §e class is "expected on C". **It is not there.**

The internal-pointer shape, as ADR-019 §e defines it, requires all three of: a
heading is found; a span is attached; the body is a short, well-formed sentence
naming a page location inside this same document, reported `extracted` at 0.95
while the real content sits outside every span. `c-2025` has **none** of them.
It produces no heading candidates at all — 21 codes `missing` with null offsets
at `BASE_MISSING` 0.40, two `omitted`, zero chars in spans. There is no pointer
body because there is no body.

Its root cause is a different one, and the held-out case's own frozen
provenance already named it before any run: this filer writes a
`FORM 10-K CROSS-REFERENCE INDEX` whose rows are **bare codes with no `Item`
prefix** — `1. Business 4–36, 121–127, 129, 160–164, 299–300`,
`1A. Risk Factors 49–62` — which is the `axp-2008` no-`Item`-prefix shape (the
same reason `axp-2008`'s `toc_manifest` comes back empty), carried for *every*
item rather than for four.

**The premise is corrected here rather than carried forward**, which is what
the ledger exists for. A ruling that inherited "expected on C" would have
promoted a capability on the strength of a filing that does not exhibit it.

### b2) The class IS on the held-out set — on the filing the row does not name

`intc-2025` is the internal-pointer class, at the highest severity either set
contains. **13 of its 23 item bodies** are a page reference into this same
document — adjudicated item by item in §b3a below, on the same rule §b3 applies
to the dev filings, because the first draft of this ADR said "all 23" and that
was wrong (PR #56 R2):

```
Item 1A. Risk Factors / Pages 37-51                          (35 chars)
Item 8. Financial Statements and Supplementary Data / Pages 56-108   (66 chars)
Item 7. Management's Discussion and Analysis ... /
    Liquidity and capital resources  Pages 29-32
    Results of operations            Pages 18-29 ...        (226 chars)
```

That is `cvx-2015`'s "presented on page FS-1" shape, for 13 items instead of 2.
All 23 items report `extracted` at 0.95. **The figure that carries the A1
ruling is not the item count — it is the coverage: 1,727 chars in spans of
517,976, 516,249 outside them, 0.3%.** That figure is a property of the whole
document and is unchanged by how any individual body is classified, which is
why re-adjudicating 23 down to 13 leaves §e1 standing. The item count was
never load-bearing and should not have been the headline.

One compounding fact, established from the raw bytes rather than inferred: the
23 headings the pipeline matched are **not body headings**. The literal
`Item 1.` occurs exactly once in the 3,320,720-byte fixture, and all 23
item-code-with-dot hits sit at offsets above 3,251,505 — the trailing
cross-reference index. `intc-2025` has no body item headings at all. So
`intc-2025` and `c-2025` share a root cause (the filing maps items to page
ranges through an index instead of writing headings) and differ only in
whether the index rows carry the literal `Item` prefix: Intel's do, so all 23
headings match onto index rows — that count is headings matched, not Class-A
bodies — and the failure is silent at 0.95; Citi's do
not, so nothing matches and the failure is honest at 0.40. The postmortem's
two faces of the same sensor problem, and the pointer bodies on Intel are the
*symptom* of that, not the `cvx-2015` mechanism.

### b3) Prevalence, adjudicated hit by hit

The scan flags an `extracted` item whose span is under 700 chars and whose
body matches an internal-page-reference pattern. It returns **15 fixtures**.
**This section adjudicates the 13 real-EDGAR hits.** The two remaining hits are
synthetic and are named here as out of scope rather than left silent (PR #56
R5): `ibr-pointer-first` items 6/8 and `ibr-security-holders` item 12 are
mutations of `ge-1994` and `ibm-1997` and inherit those filings' verdicts
exactly — item 6/12 rejected as external-document pointers, item 8 confirmed —
so they add no filing and no item to any count below. The rejections among the
real hits matter as much as the confirmations.

**Class A confirmed — pointer target is inside this document, body is a stub:**

| fixture | set | kind | items | span chars |
|---|---|---|---|---|
| `cvx-2015` | dev | real EDGAR | 2, 6, 7, 7A, 8 | 534 / 119 / 280 / 453 / 189 |
| `jpm-2024` | dev | real EDGAR | 1C, 7, 7A, 8 | 172 / 398 / 274 / 372 |
| `bac-2006` | dev | real EDGAR | 3, 6, 7A | 229 / 202 / 175 |
| `ge-1994` | dev | real EDGAR | 8 | 86 |
| `spatz-2014` | dev | real EDGAR | 8 | 241 |
| `intc-2025` | held-out | real EDGAR | 1, 1A, 1C, 2, 3, 5, 7, 7A, 8, 9A, 9B, 10, 15 (13 of 23 — §b3a) | 33 to 226 |

**Rejected — the body carries substantive standalone prose, so the pointer is
an addition to a real answer, not the whole of it:** `ba-2003` item 5 (NYSE
listing plus a holder count, 587 chars), `intc-2002` item 5 (approximately
240,000 registered holders, 629 chars), `textron-2001` item 5.

**Rejected — the pointer names an EXTERNAL document, which is ADR-004's IBR
territory and a different class:** `mrk-1995` items 5 and 7 and `ge-1994` item
6 (the Annual Report to shareholders), `ibm-1997` item 12 and `gs-2002` item 10
(the proxy statement), `xom-2021` item 15 (no page number at all).

*(2026-08-27, D13: **`xom-2021` item 15's rejection is overturned** by
[ADR-038](ADR-038-internal-pointer-adjudication.md) §e3. "No page number at
all" was the scan regex's shape, not a rule — `ge-1994` item 8 ("See index
under item 14.") has no page number either and is admitted two rows above.
Under ADR-038's R1 a titled section or an index is a locatable position, which
puts `xom-2021` items 7, 7A, 8 **and** 15 in class — four items this scan could
not see, because `PAGE_PTR` required a digit. The dev total below moves from 14
items across 5 filings to 17 across 6 (corrected from 18 the same day; see the
note below). The other rejections in this paragraph
stand on prong 3, the external-document test, unchanged. Conversely ADR-019
§e's amendment named `nvda-2024` item 8 a class member; ADR-038 §c6 rules it
OUT on the same ground this paragraph rejected `xom-2021` item 15 on, so the
two ADRs stop using two different class tests.)*

*(2026-08-27, same day, PR #60 R3 — **this note's own figure is corrected
before it was ever relied on.** `xom-2021` item **8** does NOT join the class:
its body closes with "Financial Statement Schedules have been omitted because
they are not applicable…", a sentence that disposes of part of what the item
requires without the pointer, which is this paragraph's OWN prong-1 rejection
ground. ADR-038 §e3 adjudicates it and the readmission is **items 7, 7A and 15
only** — dev total **14 items across 5 filings → 17 across 6**, not 18. Item 8
was also outside `d9_class_scan.py`'s `BODY_MAX = 700` at 737 chars, so the
scan missed it twice over. §e3 also records that ADR-007's
`IBR_REMAINDER_MAX = 300` does not reproduce this paragraph's three
rejections — `intc-2002` item 5's standalone content is **111** chars, and
that figure is a hand sub-split inside a 359-char splitter sentence, disclosed
in §e3 — so prong 1 is a test of kind, not of length. Under the instrument's
own segmentation a threshold in 177..190 WOULD sort these four; §e3 refuses it
on band width and stability, not on impossibility.)*

So the class is **14 items across 5 real dev filings** — 1.9% of 744 dev items
— plus **13 items on one held-out filing**, 8.8% of 147 held-out items.

Two of those five filings were **never enumerated anywhere**: `bac-2006` items
3, 6 and 7A, and `spatz-2014` item 8. The Debt row names `cvx-2015`, `ge-1994`
and `jpm-2024`. The row understates its own class by two filings and, on
`cvx-2015` and `jpm-2024`, by five items beyond the ones it lists. That is
logged as Debt (§g), not fixed here.

### b3a) `intc-2025`, adjudicated on the same rule — 13 of 23, not 23

The first draft asserted "all 23" and applied §b3's rejection rules to the dev
filings but not to the held-out filing that carries the A1 ruling. Corrected
here rather than quietly (PR #56 R2). Every one of the 23 bodies, bucketed:

| bucket | n | items | verdict |
|---|---|---|---|
| **internal page pointer** | **13** | 1, 1A, 1C, 2, 3, 5, 7, 7A, 8, 9A, 9B, 10, 15 | **Class A confirmed** — `Pages 37-51`, `Pages 56-108`, `Page 109`: a location inside this same document |
| status keyword | 6 | 1B, 4, 6, 9, 9C, 16 | **Not a failure at all.** The bodies read `None` or are empty under `[Reserved]`. For Intel FY2025 that is the complete and correct answer to those items; nothing is pointed at and nothing is missing |
| external proxy pointer | 4 | 11, 12, 13, 14 | **Rejected out of Class A**, on §b3's own external-document rule. Each body is the marker `(a)`, resolved at normalized offset 516118 by "Incorporated by reference to the applicable section of the 2026 Proxy Statement" — ADR-004 IBR territory, the same verdict `mrk-1995` 5/7, `gs-2002` 10, `ibm-1997` 12, `ge-1994` 6 and `xom-2021` 15 already get above |

13 + 6 + 4 = 23. Item 10 is a **mixed** body — `Page 52 (a)`, both an internal
page reference and the external proxy marker — and is counted in the 13 on the
internal reference, which is the reading the scan takes; a reader who counts it
as external gets 12 and no ruling moves.

**What the correction does and does not cost.** It removes an overstatement:
`intc-2025` is not a filing where 23 items each hold the wrong text, it is one
where 13 do, 4 are IBR-shaped and 6 are right. It does **not** touch §e1, which
rests on coverage — 1,727 chars of 517,976, 0.3% — a whole-document figure
independent of any per-item verdict, and on the D8 trigger's measured 0-of-42
dev fire rate. The load-bearing number was always the coverage; the item count
was decoration, and stating it wrong is exactly the defect this repo's review
loop exists to catch.

**The 4 proxy-`(a)` bodies are a live question this ADR does not answer**: they
report `extracted` over pointer-only bodies naming an external document, which
is the same shape as the `mrk-1995` items already logged as Debt in §g. That
Debt row is widened to name them rather than a second row being opened.

### b4) What the recall actually is, per document

"Items lost" is the wrong unit for this class, because the item is not lost —
it is present, `extracted`, at full confidence, holding the wrong text. The
honest unit is how much of the document ends up inside any span:

| filing | doc chars | in spans | coverage |
|---|---|---|---|
| `intc-2025` | 517,976 | 1,727 | 0.3% |
| `c-2025` | 1,163,303 | 0 | 0.0% |
| `ge-1994` | 362,717 | 83,654 | 23.1% |
| `cvx-2015` | 417,517 | 113,501 | 27.2% |
| `spatz-2014` | 65,197 | 43,237 | 66.3% |
| `axp-2008` | 351,503 | 283,924 | 80.8% |
| `bac-2006` | 705,848 | 655,376 | 92.8% |
| `jpm-2024` | 1,213,284 | 1,204,938 | 99.3% |

`jpm-2024`'s 99.3% is not health: item 15's span has swallowed the tail and
`last_item_dominates` has already fired, so its pointer-bodied items 7 and 8
are **misattributed** rather than unreached. The A1/A2 split is visible in this
table as a gap, not a gradient — A1 sits at 0.3%, A2's worst at 23.1%.

## c) Class B — the fan-out class has one member, and its cost premise is false

### c1) Prevalence: one filing in 49

The scan's multi-code detector returns hits on **18 fixtures** (PR #56 R4: the
first draft said 17 and, downstream, "sixteen other"). Adjudicated, **one is a
body heading over item content**: `axp-2008` at normalized offset 328679,
`ITEMS 10, 11, 12 and 13`, the heading ADR-020 enumerated. The other seventeen
**fixtures**, enumerated in full rather than swept (PR #56 R5). **The buckets
below are over the 18 hit FIXTURES, not over the 39 individual hits the scan
emits** (PR #56 R10 — the first draft's closing sum said it accounted for
"every hit" while adding up fixtures). Several filings hit in more than one
bucket and are listed under each; the buckets group by shape and do not
partition the hits:

- **a cover-page Documents-Incorporated-by-Reference sentence** — `jpm-2024`,
  `wfc-2008`, `gs-2002`, `ba-2003` and `c-2025` all carry
  `Items 10, 11, 12, 13 and 14`-shaped proxy pointers on their cover or in a
  footnote. **None of those filings loses a Part III item _to the multi-code
  string_** — which is the causal claim this section actually needs, and is not
  what the first draft wrote. It wrote "every one of those filings reports zero
  `missing` Part III items", and **that is false for `c-2025`, whose items 10,
  11, 12, 13 and 14 are all `missing` at 0.40 with null offsets** (PR #56 R1;
  the ADR contradicted its own §a table, which already reports 21 `missing`).
  `c-2025` loses those five items to having no body headings anywhere — the
  bare-code index of §b1 — and a fan-out over its cover sentence reaches none
  of them, as the paragraph below spells out. On the other four the string is
  boilerplate and no Part III item is missing.
- **a financial-statements index heading** — `gs-2002` again, at offset 135012:
  `ITEMS 14(a)(1) AND 14(a)(2)`, heading the exhibit/financial-statement index.
  It names item 14 twice in sub-part form rather than several distinct codes, so
  it is not the `axp-2008` shape and `gs-2002` loses no item to it.
- **a numeric table artifact** — `Items 3,926 12,392 16` in `xom-2021`,
  `items 917 965` in `msft-2013`, `Items 2025 2024` in `aapl-2025`,
  `items. 14` in `cat-2023`, `items 119 80` in `ge-1994`. Digits from adjacent
  columns, not item codes.
- **a prose cross-reference inside an item body** — `intc-2002`
  (`items 5 and 6`), `textron-2001` (`Items 5 and 7`), `wmt-2010`
  (`Items 1, 2, 3, 5, 6, 7, 7A`), and `xom-2021` again at offset 39731
  (`Items 1, 1A, 2, 7 and 7A`, inside forward-looking-statement prose). A
  sentence referring to sibling items, not a heading introducing them.
- **a table-of-contents line** — `nvda-2024`.
- **synthetic fixtures, out of scope for a real-filing ruling** —
  `heading-unnumbered` (a TOC line in an `nvda-2024` mutation),
  `ibr-pointer-first` (a `ge-1994` mutation, inherits its table artifact), and
  `interior-span-dominates`, which carries `Items 1, 2, 3, 5, 6, 7, 7A` at
  offset 105383 **with items 1A/1B/2/3 missing**. It is a hand-built fixture for
  ADR-030's dominance rule, so it is not evidence about real filers.

**The claim this section defends, stated in the only form it can bear.**
`axp-2008` is **the only filing in 49 whose multi-code string is a body heading
over item content** — that is the class, and it is what the 1-in-49 count and
the ruling rest on. It is **not** true that `axp-2008` is the only filing where
a multi-code string and missing items co-occur; **two real filings falsify
that** (PR #56 R9):

| filing | the string | items missing | causal link? |
|---|---|---|---|
| `c-2025` (held-out, real) | `Items 10, 11, 12, 13 and 14` on the cover, offset 4054 | 10, 11, 12, 13, 14 — and 16 more | **No.** They are missing because the filing writes no body item headings anywhere (§b1's bare-code index). The cover sentence is the boilerplate every proxy-incorporating filer writes |
| `xom-2021` (dev, real) | `Items 1, 1A, 2, 7 and 7A` in forward-looking prose, offset 39731 | 6 | **No.** Item 6 is not in the document at all — ADR-020 §b measured `Selected Financial Data` at zero occurrences. The string does not name item 6 |

Co-occurrence is not the class; a **body heading** that names several codes and
takes their content with it is. The first draft asserted the weaker
co-occurrence claim, and it was already contradicted twenty lines above by this
section's own `c-2025` paragraph — a self-contradiction introduced by the
round-1 R1 repair and caught by round 2.

**No entry-count arithmetic is published here, deliberately** (PR #56 R15). The
scan returns **39 hits across 18 fixtures**; several fixtures hit in more than
one bucket, and the buckets above group them by shape rather than partitioning
them. A summed entry count was published twice and was wrong twice — first as
18, then as 20 on the claim that only `gs-2002` and `xom-2021` were multi-bucket,
which the scan falsifies (`ba-2003` @56848, `gs-2002` @21527, `jpm-2024` @197103
and `axp-2008` @334794 are further multi-bucket hits). Two facts carry this
section and neither needs a sum: **39 hits over 18 fixtures**, and **exactly one
of those hits is a body heading over item content** — `axp-2008` at 328679. That
single adjudication is what the ruling rests on.

Recall at stake: **4 items, 1 real filing, 0.45% of 891** (ADR-020's 4 of 768 =
0.52%, re-derived on the grown corpus; the ruling does not turn on the third
decimal place). **Zero held-out items.** The class does not generalize:
seventeen other fixtures carry the string and none loses an item to it.

`c-2025` deserves an explicit negative, because it is the one filing where a
reader might expect the fan-out to help. Its only multi-code string is the
cover sentence at offset 4054 — `... incorporated by reference in this Form
10-K in response to Items 10, 11, 12, 13 and 14 of Part III` — followed by the
cross-reference index, not by Part III content. **A combined-heading fan-out
contributes zero of `c-2025`'s 21 missing items.**

### c2) The deterministic fix is not the regex ADR-020 costed

ADR-020 §c row 7 rules the fan-out cheaper than a model because "a regex
produces the identical output" at $0, resting on `segment.classify` returning
`extracted` on all four partition bodies. **That is false**, and this ADR ran
it rather than citing the correction:

```
segment.classify('10', body,  True)  ->  incorporated_by_reference   # heading-stripped
segment.classify('10', span,  True)  ->  extracted                   # heading included
```

The pipeline passes the heading-stripped form (`src/sec10k/extract.py` derives
`body` as the span minus its heading line). So the debt case
`evals/adversarial/axp-2008-combined-part-iii.json` asserts a status set no
contract-valid fan-out produces, and its "NOW GREEN — promote it" contract is
unreachable. The 1,139 chars of Reg S-K prose the `extracted` reading rests on
begin at offset 331084, after item 13's span ends at 330343.

A second obstacle, also re-run rather than quoted: `axp-2008` item **9B's span
is [326876, 331942)** — it contains the entire Part III block and the Reg S-K
prose. A fan-out must therefore truncate a neighbouring `extracted` item or
`no_overlap_ordered` fails on the pair "9B and 10".

So the real cost of the deterministic fix is: choose a fan-out design; re-derive
the debt case's asserted status set; truncate an adjacent item's span; decide
what `heading_text` means for a shared heading, since the `verbatim` check
requires a span to open with its own heading and items 11-13's do not; and
carry that past the 17 other fixtures the same detector matches — five of them
real filings whose cover sentences it hits, which are the ones a fan-out could
actually damage. That is a capability with a live blast radius, not a regex.
(The first draft wrote "16 other fixtures whose cover sentences the same
detector matches", which was both the stale denominator of PR #56 R4 and an
overstatement — only 5 of the hits are cover sentences.)

### c3) `axp-2008` is no longer the only real-filing recall gap

ADR-020's ruling leans on `axp-2008` being unique — "the only real-filing
recall gap in either set", so closing the class deterministically closes
everything a fallback could have reached. On the current corpus that is no
longer true. `c-2025` is a real EDGAR filing reporting **21 `missing` items**
whose content a reader can point to in the document, and no heading-shape
change reaches it: there are no headings to reshape.

This does not overturn ADR-020's ruling — the escalation-ladder argument
survives, and D11 is the milestone that answers `c-2025`. It does remove the
uniqueness that made "close the whole class at $0" the obviously cheaper move.
A fan-out now closes 4 items on 1 filing while the larger real gap beside it
stays open and is routed elsewhere.

## d) Cost: the deterministic fixes against D11 — one measurement, one ESTIMATE

**Price basis**: Anthropic first-party API list price as of **2026-06-24** (the
`claude-api` skill's cached model table), the same basis and the same date
ADR-020 §d cited, so the two are comparable: `claude-opus-5` $5.00/MTok input,
1M context; `claude-sonnet-5` $2.00/MTok input, 1M context; `claude-haiku-4-5`
$1.00/MTok input, 200K context. Prices move; re-check the list before
publishing again.

**Token figures are an ESTIMATE**, chars/4, exactly as ADR-020 §d's were.
ADR-020 said T13 should firm them with `count_tokens`; that has still not been
done, and this ADR does not do it either — `count_tokens` needs a live
endpoint, and the D9 ruling does not turn on a 20% token error. Every figure in
the next table is an estimate and is labelled one wherever it is quoted.

**Today's cost is a measurement, not an estimate**: $0.00 per filing,
structurally, because no paid dependency exists.

| filing | chars | ≈tokens (EST) | opus-5 (EST) | sonnet-5 (EST) | haiku-4-5 (EST) |
|---|---|---|---|---|---|
| `axp-2008` | 351,503 | ~87,900 | ~$0.44 | ~$0.18 | ~$0.09 |
| `intc-2025` | 517,976 | ~129,500 | ~$0.65 | ~$0.26 | ~$0.13 |
| `cvx-2015` | 417,517 | ~104,400 | ~$0.52 | ~$0.21 | ~$0.10 |
| `c-2025` | 1,163,303 | ~290,800 | ~$1.45 | ~$0.58 | does not fit 200K |
| whole 49-fixture corpus, one uncached pass | 12,089,897 | ~3,022,500 | ~$15.11 | ~$6.04 | — |

**One input to ADR-020 §d is corrected here rather than inherited — and the
correction is to ADR-020's reading of the table, not to the table.** ADR-020
argued that cheaper tiers "do not simply divide the problem", because Haiku's
200K context cannot hold the largest filings, forcing either a 1M-context model
or a chunking subsystem. That argument skipped the mid tier:
**`claude-sonnet-5` carries 1M context at $2.00/MTok on the same cached table,
at the same 2026-06-24 date ADR-020 §d cites** — ADR-020 §d's price paragraph
simply enumerates only `claude-opus-5` and `claude-haiku-4-5` and does not
mention it. The first draft of this section said the tier "now exists", which
implied it post-dated ADR-020 and is not supported by anything (PR #56 R7).
Nothing about the price basis changed; ADR-020 did not enumerate a row that was
already there. It holds every filing in this corpus.
That cuts the counterfactual by 2.5x. It does not reverse ADR-020's ruling —
$6.04 per uncached corpus pass against a structural $0.00 is still an
order-of-magnitude argument — and it is not evidence for a fallback. It is
recorded because a cost argument that quietly keeps a superseded price basis is
the thing this section exists to prevent.

### d1) The escalation rate, which is the number that actually decides this

D11's cost is dominated not by per-document price but by how often the trigger
fires on documents that are fine. D8 does not exist, so that rate cannot be
measured — but the **trigger D8's row names** can be, and was:

| candidate trigger | dev (42) | held-out (7) |
|---|---|---|
| **item 1's span under 2,000 chars** (the postmortem §5 figure D8's row cites) | **0 fires — 0%** | 1 fire — `intc-2025` |
| any `extracted` item's span under 2,000 chars | 38 fires — 90% | 6 fires |

The first is the D8 trigger as its row specifies it, and on this corpus it has
a **zero dev false-positive rate** and catches `intc-2025` exactly. D11's row
requires "dev escalation rate stays near zero so the default cost stays $0";
this is the measurement that says that requirement is satisfiable. The second
row is what a naively broadened floor costs, and is included so the first is
read as a tuned result rather than a lucky one.

Two documents need no new trigger at all:

- **`c-2025`** is already `ambiguous` with `expected_items_mostly_missing`.
- **`axp-2008`** is already `success_with_warning` with `expected_item_missing`
  on all four Part III codes — an honest miss that announces itself.

So all three filings this ADR rules on are reachable by signals that exist
today or are measured free on dev. **The escalated population is 1 to 3
documents; the estimated bill is under $1 at sonnet-5 rates and under $3 at
opus-5 rates.** That is the cost comparison the D9 row demanded, and it is what
makes "subsumed by D11" cheaper than either deterministic capability — not the
per-token price, which was never the deciding term.

**And the limit, stated rather than smoothed:** the item-1 floor is measured
**silent** on `cvx-2015`, `jpm-2024`, `bac-2006`, `ge-1994` and `spatz-2014` —
item 1 is full-length on all five. D11 as specified will therefore **not**
reach the A2 sub-class. A2 is declined below on its own evidence, not swept
into D11 and quietly counted as handled.

## e) The rulings

### e1) A1 — whole-document collapse onto a cross-reference index: SUBSUMED BY D11

Not promoted, no milestone row, no ADR of its own. `intc-2025` is the D8/D11
shape as those rows already define it: D11's ledger row names the D6 held-out
filings as its success criterion, and D8's item-level span floor is the trigger
that routes it, at 0 of 42 dev false positives. A separate
"internal-pointer resolution" milestone would build a second instrument aimed
at a document D11 is already committed to passing.

The Debt row keeps A1 as an enumerated instance and points at D11.

### e2) A2 — a few pointer-bodied items in an otherwise sound filing: DECLINED

Stays in the Debt table. Two reasons, both evidential, neither a preference:

1. **It is not agreed to be a defect.** ADR-019 §e records a standing,
   unresolved disagreement: the extraction-auditor's independent blind sample
   adjudicated `cvx-2015` item 6 — a member of this exact sub-class, `Selected
   Financial Data`, a pointer to page FS-60 — **CORRECT**. Items 7 and 8 were
   never independently adjudicated. Promoting a capability milestone to fix a
   shape that two independent reads disagree is broken inverts the order: the
   adjudication comes first. **This ADR does not settle that disagreement
   either**, by assertion or otherwise — doing so is what the auditor's charter
   forbids and what ADR-019 §e deliberately declined.

   **SETTLED 2026-08-27 (D13, [ADR-038](ADR-038-internal-pointer-adjudication.md)).**
   Reason 1 no longer holds: the disagreement was adjudicated item by item on
   a stated rule, with the extraction-auditor re-run blind on a nine-item
   sample. `cvx-2015` item 6 is ruled **`defect`**, together with items 2 and
   7A — and items 7 and 8, the two this sub-class's `debt` case actually
   asserts, are ruled **`correct`**, because ADR-035's `item_span_near_empty`
   already carries them. **The A2 decline's OUTCOME is unchanged and this is
   not a promotion**: the adjudicated defect is the envelope reporting three
   items clean at 0.95 with `review_required: false`, which is the escalation
   layer's item set (TD-5), not internal-pointer resolution. ADR-038 §e1 says
   what TD-12 keeps and what it loses; §d of that ADR records where the blind
   auditor still disagrees.
2. **Nothing reaches it.** The D8 trigger is measured silent on all five
   filings (§d1), so A2 is not subsumed by D11 and saying it were would be
   false. Declining it is the honest verdict; "subsumed" would have been the
   comfortable one.

   **CROSS-REFERENCE, added 2026-08-26 at the PR #57 (D8) merge — this reason
   is FALSIFIED by D8's shipped trigger, and §f row 3 is the instrument that
   says so.** §d1 measured the trigger *as the D8 row specified it* — item 1's
   span under 2,000 chars — and that measurement REPRODUCES exactly on the
   merged tree: item 1 is full-length on all five, and the only dev filing it
   reaches is `xref-index-collapse`, the synthetic D8 itself adds. What D8
   actually SHIPPED ([ADR-035](ADR-035-item-level-escalation.md) §c) is
   `item_span_near_empty` — `SPAN_FLOOR` 1,500 chars over items **1, 7 and
   8**, not item 1 alone — and re-running §d1's table against it, as §f row 3
   directs, gives **4 fires of 5, against a stated threshold of one**:
   `cvx-2015` (items 7, 8), `jpm-2024` (items 7, 8), `ge-1994` (item 8),
   `spatz-2014` (item 8); only `bac-2006` is silent. `low_item_coverage`
   fires on none of the five (coverages 0.9285, 0.2718, 0.2306, 0.9931,
   0.6632, all at or above `COVERAGE_MIN` 0.13). **No figure in §d1 is wrong
   and no ruling is changed here** — the gap is that reason 2 generalised a
   measurement of item 1 to "the D8 trigger", and the trigger that shipped is
   wider. Reason 1 (the unadjudicated `cvx-2015` item-6 disagreement) is
   untouched and still stands on its own. Re-reading the A2 ruling is D9's
   call, not D8's, and is escalated as a Debt row in `tasks/TODO.md`
   (`Origin: PR #57 merge cross-check`) rather than settled here.

### e3) B — combined Part III heading fan-out: SUBSUMED BY D11

Not promoted. `axp-2008` escalates today on a warning it already emits; one
slow-tier pass costs an estimated ~$0.18 at sonnet-5 rates for the whole
filing. Against that, the deterministic fan-out costs the four-part capability
§c2 enumerates, on a class with one member in 49 documents and none held out.

**This narrows ADR-020, and says so.** ADR-020 §c row 7 preferred the
deterministic fix over a metered call on two grounds, and both have moved: the
fix is not the identical-output regex it was costed as (§c2, verified by
running the classifier), and `axp-2008` is not the only real-filing recall gap
(§c3, `c-2025`). ADR-020's ruling — no unconditional LLM fallback ships, the
escalation ladder governs — is **unchanged**, and D11 is a triggered tier, not
the unconditional fallback ADR-020 rejected. ADR-020 §c row 7 and §b gain a
dated pointer to this section rather than being rewritten, per this repo's
amend-in-place convention.

## f) What would reopen each ruling

Each names an instrument and a threshold, so a future reader can falsify it
rather than re-argue it.

| ruling | what reopens it | instrument | threshold |
|---|---|---|---|
| **A1 subsumed** | D11's ADR declines the model tier, or D8's ADR adopts no item-level span floor. Either leaves A1 without an owner and it must be re-ruled standalone | the D8 and D11 ADRs when written | either one |
| **A2 declined** | the `cvx-2015` item-6 disagreement is adjudicated as WRONG by both reads; or the plain-text stratum gets the independent cross-check ADR-019 §c/§g still says it lacks, and finds the shape where the pointer target is demonstrably unreachable | an extraction-auditor pass over `cvx-2015` items 6, 7, 8 and the `bac-2006` / `spatz-2014` instances this ADR adds | **one** instance both reads agree is wrong |
| **A2 declined** | the D8 trigger, once built, fires on any of the five A2 filings — then A2 *is* reachable by D11 and "declined" becomes "subsumed" | re-run §d1's table against D8's shipped trigger | **one** fire |
| **A2 declined** — ↑ **TRIPPED 2026-08-27** at D13. [ADR-038](ADR-038-internal-pointer-adjudication.md) ran the named instrument and **the threshold is MET**: `cvx-2015` item 6 is adjudicated WRONG by both reads (ADR-038 §d2). Stated as this row's own finding, not deferred — an amendment that says "met or not, see elsewhere" is the amendment failing to do its job (PR #60 R2). **What the blind pass actually covered**, against the four instances this row names: `cvx-2015` **6** and **8**, `bac-2006` **3** and **6**, `spatz-2014` **8** — plus `cvx-2015` 2 and 7A, `jpm-2024` 7 and `mrk-1995` 5, which this row does not name. `cvx-2015` item **7** and `bac-2006` item **7A** were NOT put to the auditor, and cvx 7 is the item ADR-019 §e read WRONG and ADR-038 §c1 calls "the sharpest concession the rule makes"; ADR-038 §d6 records the omission. **The decline's OUTCOME still stands**: the adjudicated defect is an escalation-layer one (ADR-038 §e1) that a capability milestone would not fix | — | — |
| **A2 declined** — ↑ **TRIPPED 2026-08-26** at the PR #57 (D8) merge: the shipped `item_span_near_empty` fires on 4 of the 5 (`cvx-2015`, `jpm-2024`, `ge-1994`, `spatz-2014`), threshold was one. §e2 reason 2 carries the measurement; the ruling is left standing for D9 to re-read | — | — |
| **B subsumed** | a second real EDGAR filing whose **body** heading names several item codes and loses items to it — the class stops being a single instance | `tasks/reviews/d9_class_scan.py`'s multi-code hits, adjudicated by hand as §c1 does | **one** filing |
| **B subsumed** | D11's ADR declines to escalate on `expected_item_missing`, leaving `axp-2008` with no owner; the fan-out then returns as the only route and must be costed again against §c2's real scope | the D11 ADR when written | that decision |

Explicitly **not** sufficient to reopen any of them: the debt cases still being
red (that is what this ADR permits); a filing merely being large, old, or
foreign; the fan-out being cheap to write, which §c2 shows it is not.

## g) Consequences

**The held-out burn rule fires on this ADR under the rule as it stood; the owner
ruled to amend the rule rather than apply it, so neither case is burned.** The first draft answered
that question in the negative and gave a ground that PR #56 **R3** falsified —
that answer is withdrawn, and no part of this document now carries it. The ground
is withdrawn here rather than patched, and the withdrawal is stated before the
question, because the wrong reason is the more instructive half.

**The withdrawn ground, and why it was wrong.** The first draft argued that the
`gs-2002` and `axp-2008` burns *both* authored a new adversarial case from the
fixture *and* moved the fixture into the dev corpus, so a decline that does
neither is distinguishable. That is a conjunctive test the precedents
explicitly disclaim, and it is false on its face for one of them:

- `evals/heldout/README.md:278-280`, on the `axp-2008` burn, reads "The burn
  rule names both of those as influence" — **both, each independently**, not a
  required pair. The draft inverted trigger and remedy: authoring a case and
  moving the fixture are consequences of a burn, not preconditions for one.
- `evals/heldout/README.md:222-225`, the `gs-2002` precedent the draft leaned
  on hardest, burned on "a documented decision to decline a fix" **alone** and
  names no new case at all. So the sentence "the `gs-2002` and `axp-2008` burns
  both authored a new adversarial case" was simply not true of `gs-2002`. I
  built a distinguishing ground on a precedent I did not read.

**The sentence the first draft never addressed**, and which names D9 by name —
the D6 H4 entry — quoted here **as it read before the 2026-08-26 amendment**,
because the amendment narrowed it and the string below no longer appears in the
file. Today's text is at `evals/heldout/README.md:401-404`; what it said when
this finding was raised was:

> Both cases stay **untouched** — D8/D9/D11 must not read
> their labels while iterating, and the first fix, threshold or declined fix
> taken with either outcome in hand burns that case under the rule above.

**This ADR is that declined fix.** It read both outcomes (§a) and made them
load-bearing: §e1 rests A1's subsumption on `intc-2025`'s outcome, and §c3
rests ADR-020's narrowing on `c-2025`'s 21 `missing` items. Under the rule as
written, both cases are burned.

**What that cost, and why the choice was not the loop's to take.** Applying the
burn means moving `evals/heldout/{c,intc}-2025-heldout.json` to
`evals/adversarial/` and both fixtures to `evals/fixtures/`, and budgeting two
replacement filings. That deletes the exam D11's own ledger row and `c-2025`'s
provenance each demand it sit — "D11 must pass this filing WITHOUT ever having
trained on it". The alternative was amending the README's rule and its D6 H4
sentence. Both are decisions about the eval set's own integrity, they trade off
against each other, and neither was a decision-row implementer's or a review
loop's to make. The question was escalated.

**OWNER DECISION, 2026-08-26: amend the rule. Neither case is burned.** This is
recorded as a decision taken by the owner on the escalation, not as a ground
this document reasoned its way to — the ground it originally reasoned to was
withdrawn above as falsified, and nothing here revives it. The burn does not
fire on this ADR **because the rule was changed**, not because the original
no-case-authored argument was sound. Those are different claims; this
document asserts only that the rule was changed, and never that the withdrawn
ground was sound.

The amendment lands in `evals/heldout/README.md`'s Burn-rule section and in the
D6 H4 entry quoted above, both dated and both pointing here. Its substance: a
decision that cites a held-out outcome but **authors no case, moves no fixture,
changes no threshold and ships no code** does not burn the case. Influence still
burns; a ruling is not influence. The reasoning the owner accepted is that the
rule exists to stop labels being *tuned against*, and a ruling that shapes no
extraction behaviour tunes nothing.

**D9's own two artifacts are adjudicated against that clause rather than assumed
past it** (PR #56 R14) — D9 did raise a threshold and did ship a committed
`.py`, so the earlier claim here that "there is no artifact in the tree that
could have absorbed the labels" was **false as written** and is withdrawn. The
adjudication is in `evals/heldout/README.md`'s amendment block, so a reader who
reaches the rule first gets the same answer this section publishes, and it is:

- **`evals/adversarial/ledger-line-refs.json` `min_refs` 9 → 11** — a ledger
  citation floor. Not an extraction threshold, reads no filing, unrelated to any
  held-out label. Not the influence the rule targets.
- **`tasks/reviews/d9_class_scan.py::BODY_MAX = 700`** — 700 lies in a plateau
  whose **both edges are dev values** (`intc-2002` item 5 at 629 below,
  `ibm-1997` item 5 at 805 above), so every bound in 630..805 gives an identical
  dev result and no held-out value defines that interval. The single held-out
  span inside it, `mrk-1995` item 8 at 738, is an external-document pointer the
  class rule rejects regardless — the same verdict its siblings 5 and 7 already
  get. **Every figure this ADR publishes is invariant across that whole
  plateau**, and the constant was written once and never revised. Not the
  influence the rule targets. The README records the one part that does not
  fully close: the dev plateau extends past 738, so a different in-plateau
  choice would have changed the *candidate list* though not any published
  number.

**What it costs, stated because the amendment weakens a rule this repo wrote
deliberately.** It now permits a future decision row to cite `intc-2025`'s and
`c-2025`'s outcomes, and the next one to do it again, without either case ever
being burned. Repeated often enough that is a slow leak: the labels become
common knowledge to whoever writes the milestones even though no code was
touched, and the exam decays without any single ruling being wrong. The owner
took that risk against the alternative of destroying D11's exam outright.

**Consequence for D11, which is the point of the call.** `intc-2025` and
`c-2025` stay in `evals/heldout/`, unseen by every code path. D11's held-out
exam survives intact and its ledger row's success criterion — pass both filings
having never trained on them — remains satisfiable.

**What would make the amendment wrong** (also recorded in the README): a
decision that cited a held-out outcome turning out to have carried an
**extraction** threshold or a change under `src/` — the falsifier as first
written said "a threshold or code change after all", which this ADR itself trips
at the moment of writing via `min_refs` and `d9_class_scan.py`, both adjudicated
above as outside what the rule targets (PR #56 R14); D11 passing either filing by a route that traces to a
decision document rather than to the dev proxies `cvx-2015` and `jpm-2024`; or
the number of rulings leaning on an unburned held-out outcome growing past a
handful — the amendment assumes that is rare and stops being safe when it is
not. Instrument for the last: `grep -rl 'intc-2025\|c-2025' specs/decisions/`.

**Two Debt rows are updated, and neither is closed.** The internal-pointer row
gains the A1/A2 split, the two filings it never named, and a pointer to this
ruling. The combined-heading row gains the subsumption and the pointer. Both
debt cases stay in the `debt` suite, unscored and permanently red; their triage
notes gain one line each naming this ADR as why that is permitted — so a reader
who hits a red case can find out why, which is what a permanently-red case owes
its reader.

**Two ADR-020 sections gain a dated narrowing note** (§b and §c row 7), in
place. Its headline figures are not rewritten: they were measured on the corpus
that existed at their SHA and remain valid for it.

**New Debt logged, not fixed here** (§d of the D9 brief's debt rule):

1. The internal-pointer Debt row and ADR-019 §e both understate the class —
   `bac-2006` items 3/6/7A and `spatz-2014` item 8 are unenumerated instances,
   and `cvx-2015` items 2/7A and `jpm-2024` items 1C/7A are unnamed members of
   named filings.
2. ~~The held-out burn rule question~~ — **CLOSED 2026-08-26 by owner decision**,
   recorded above in this section and in `evals/heldout/README.md`. The rule was
   amended, so neither held-out case is burned; this is not debt and is not
   carried as a ledger row. It is listed here only so the numbering of items 1
   and 3 is stable across revisions. (Through PR #56 R8 this list instead
   carried a settled negative answer resting on the ground this section
   withdraws as falsified — it survived the round-1 repair unedited, because
   that repair was applied to §g's prose and not to §g's own list fifty lines
   below it. The superseded phrasing is described rather than quoted, so a
   reader grepping this file for the withdrawn ground finds nothing.)
3. `mrk-1995` items 5 and 7 **and `intc-2025` items 11, 12, 13 and 14** report
   `extracted` over bodies that are pure external-document pointers — the
   Annual Report in the first case, the 2026 Proxy Statement in the second
   (bodies read `(a)`, resolved at normalized offset 516118). Whether those
   should be `incorporated_by_reference` is an ADR-004 question this ADR
   rejected out of Class A (§b3, §b3a) and did not answer. Widened to name the
   `intc-2025` four under PR #56 R2 rather than opening a second row.
4. `core.hooksPath` is set repo-wide to a **deleted** worktree's `.githooks`, so
   `.githooks/pre-commit` — the eval gate CLAUDE.md rule 5 names as the
   enforcement layer — cannot fire for any commit in any worktree. Found while
   committing this milestone, whose gate was therefore run by invoking
   `sh .githooks/pre-commit` directly (exit 0). Repairing it writes shared git
   config that concurrent sessions depend on, which is the human's call.

**Not done, deliberately**: no new metric, no new green-from-birth eval case
asserting the prevalence counts. ADR-020 §g declined exactly this and gave the
reason — a second way to compute a number the corpus already carries is the
speculative instrument the ADR-010 sin and this repo's laziness rule both argue
against. §h names what that costs.

## h) What this ADR's numbers are NOT gated by

Stated plainly rather than left for a reviewer to find.

`python3 -m evals.bench --check-docs` verifies fixture-attributed decimals in
`DOC_FILES` — `specs/decisions/ADR-021-benchmark-instrument.md`,
`docs/analysis-report.md`, `README.md`, `tasks/TODO.md`,
`prompts/009-t13-perf-cost-scalability.md`. **This ADR is not in that list**, so
**none of its figures is machine-checked**. It also only matches decimals of the
form `\d+\.\d+`, so integers — every char count, item count and offset above —
are outside its reach even in the files it does cover. This ADR's numbers are
reproducible only by re-running the two commands in §a.

That is the same standing ADR-019's and ADR-020's figures have, which is an
explanation and not an excuse. What *is* gated:

- **The Debt rows' pointers to this ruling**, by
  `evals/adversarial/ledger-line-refs.json` (`invariant` + `fast`): each row
  cites this file by line and quotes the sentence it means, and the check
  fails if the quotation stops matching — so the ledger cannot drift away from
  the ruling silently.
- **This document's ruling-block shape and its single INDEX entry**, by
  `adr_headers` and `adr_index` (`invariant` + `fast`).
- **The two edited Debt rows' table shape**, by
  `evals/adversarial/ledger-table-shape.json` (`invariant` + `fast`).
- **That `extract_items` did not change**: no file under `src/` or `evals/*.py`
  is touched by this milestone, and `evals/snapshot.py` reports identical dev
  and held-out digests before and after —
  `d6f7b81e16e6c9767e01ec53f7e5125919f2d629604f97d4838ddbce228ff1a8` (dev, 57
  files) and `dd67647b16369ac309a43ad856c3358cc3da8bdd00f08e7b526ad81e38ccbd26`
  (held-out, 7 files).

**No case was watched red for this milestone, and none should have been.** The
red-first rule binds a fix; this ADR fixes nothing. The two cases that carry
this class were watched red when they were authored and are still red — which
is the state this ruling ratifies rather than changes.

## Verification

- `python3 -m evals.run --suite invariant` — **score 1.000, baseline untouched.**
- `python3 -m evals.run --suite fast` — **score 1.000, baseline untouched.**
  Suite sizes are deliberately NOT quoted here: they move with every merge, and
  the first draft published "67/67, 130/130" which was already stale at its own
  merge SHA (PR #56 R6). `tasks/DONE.md`'s D6 entry names quoting them as the
  R8 defect and declines to; this ADR now does the same.
- `python3 -m evals.run --suite fast --dir evals/heldout` — 5/7 = 0.714,
  `c-2025` and `intc-2025` red as D6 recorded. Re-derived, not quoted (§a).
  Report committed at `evals/report/20260826-141545-fast.json`; its own
  `git_sha` reads `edb935ae0375d1b080022eba44dc12164db84ec0-dirty` — the branch's
  parent commit plus the ledger status edit that was already uncommitted in the
  tree when the run started, disclosed rather than left for a reader to notice.
- `python3 -m evals.bench --check-docs evals/report/20260823-185707-bench.json`
  — 68 fixture-attributed decimals checked, 0 unmatched, unchanged by this
  milestone's `tasks/TODO.md` edits.
- `python3 evals/snapshot.py . <out>` before and after — digests in §h.
- `python3 tasks/reviews/d9_class_scan.py` — the prevalence tables in §b3 and
  §c1.
