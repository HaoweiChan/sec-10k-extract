# ADR-034 — D9: the internal-pointer class splits in two and neither half becomes a milestone; the combined-heading fan-out is subsumed by D11, narrowing ADR-020's stated preference

Date: 2026-08-26. Status: accepted. Implements D9, the decision row
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

**Ruling**: the ADR-019 §e class splits — **A1**, a whole document collapsing onto a cross-reference index (`intc-2025`, 23 of 23 items, 0.3% of the text in spans), is **subsumed by D11** and gets no milestone of its own; **A2**, a few pointer-bodied items inside an otherwise well-extracted filing (`cvx-2015`, `jpm-2024`, `bac-2006`, `ge-1994`, `spatz-2014` — 14 items, 5 real filings), is **DECLINED and stays Debt**, because two independent reads still disagree that it is a defect and no measured trigger reaches it. The `axp-2008` combined-heading fan-out is **subsumed by D11**, not promoted.
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
contains. Every one of its 23 item bodies is a page reference into this same
document:

```
Item 1A. Risk Factors / Pages 37-51                          (35 chars)
Item 8. Financial Statements and Supplementary Data / Pages 56-108   (66 chars)
Item 7. Management's Discussion and Analysis ... /
    Liquidity and capital resources  Pages 29-32
    Results of operations            Pages 18-29 ...        (226 chars)
```

That is `cvx-2015`'s "presented on page FS-1" shape, for 23 items instead of 2.
All 23 report `extracted` at 0.95. The recall at stake is the whole filing:
1,727 chars in spans, 516,249 outside them.

One compounding fact, established from the raw bytes rather than inferred: the
23 headings the pipeline matched are **not body headings**. The literal
`Item 1.` occurs exactly once in the 3,320,720-byte fixture, and all 23
item-code-with-dot hits sit at offsets above 3,251,505 — the trailing
cross-reference index. `intc-2025` has no body item headings at all. So
`intc-2025` and `c-2025` share a root cause (the filing maps items to page
ranges through an index instead of writing headings) and differ only in
whether the index rows carry the literal `Item` prefix: Intel's do, so 23
headings match onto index rows and the failure is silent at 0.95; Citi's do
not, so nothing matches and the failure is honest at 0.40. The postmortem's
two faces of the same sensor problem, and the pointer bodies on Intel are the
*symptom* of that, not the `cvx-2015` mechanism.

### b3) Prevalence, adjudicated hit by hit

The scan flags an `extracted` item whose span is under 700 chars and whose
body matches an internal-page-reference pattern. It returns 15 fixtures. Each
is adjudicated below; the rejections matter as much as the hits.

**Class A confirmed — pointer target is inside this document, body is a stub:**

| fixture | set | kind | items | span chars |
|---|---|---|---|---|
| `cvx-2015` | dev | real EDGAR | 2, 6, 7, 7A, 8 | 534 / 119 / 280 / 453 / 189 |
| `jpm-2024` | dev | real EDGAR | 1C, 7, 7A, 8 | 172 / 398 / 274 / 372 |
| `bac-2006` | dev | real EDGAR | 3, 6, 7A | 229 / 202 / 175 |
| `ge-1994` | dev | real EDGAR | 8 | 86 |
| `spatz-2014` | dev | real EDGAR | 8 | 241 |
| `intc-2025` | held-out | real EDGAR | all 23 | 20 to 226 |

**Rejected — the body carries substantive standalone prose, so the pointer is
an addition to a real answer, not the whole of it:** `ba-2003` item 5 (NYSE
listing plus a holder count, 587 chars), `intc-2002` item 5 (approximately
240,000 registered holders, 629 chars), `textron-2001` item 5.

**Rejected — the pointer names an EXTERNAL document, which is ADR-004's IBR
territory and a different class:** `mrk-1995` items 5 and 7 and `ge-1994` item
6 (the Annual Report to shareholders), `ibm-1997` item 12 and `gs-2002` item 10
(the proxy statement), `xom-2021` item 15 (no page number at all).

So the class is **14 items across 5 real dev filings** — 1.9% of 744 dev items
— plus **23 items on one held-out filing**, 15.6% of 147 held-out items.

Two of those five filings were **never enumerated anywhere**: `bac-2006` items
3, 6 and 7A, and `spatz-2014` item 8. The Debt row names `cvx-2015`, `ge-1994`
and `jpm-2024`. The row understates its own class by two filings and, on
`cvx-2015` and `jpm-2024`, by five items beyond the ones it lists. That is
logged as Debt (§g), not fixed here.

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

The scan's multi-code detector returns hits on 17 fixtures. Adjudicated, **one
is a body heading over item content**: `axp-2008` at normalized offset 328679,
`ITEMS 10, 11, 12 and 13`, the heading ADR-020 enumerated. Every other hit is:

- **a cover-page Documents-Incorporated-by-Reference sentence** — `jpm-2024`,
  `wfc-2008`, `gs-2002`, `ba-2003` and `c-2025` all carry
  `Items 10, 11, 12, 13 and 14`-shaped proxy pointers on their cover or in a
  footnote. **Every one of those filings reports zero `missing` Part III
  items.** The string is boilerplate; the failure is not.
- **a numeric table artifact** — `Items 3,926 12,392 16` in `xom-2021`,
  `items 917 965` in `msft-2013`, `Items 2025 2024` in `aapl-2025`. Digits from
  adjacent columns, not item codes.
- **a table-of-contents line** — `nvda-2024`, `heading-unnumbered`.

Recall at stake: **4 items, 1 real filing, 0.45% of 891** (ADR-020's 4 of 768 =
0.52%, re-derived on the grown corpus; the ruling does not turn on the third
decimal place). **Zero held-out items.** The class does not generalize: sixteen
other fixtures carry the string and lose nothing to it.

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
carry that past 16 other fixtures whose cover sentences the same detector
matches. That is a capability with a live blast radius, not a regex.

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

**One input to ADR-020 §d has changed and it is named here rather than
inherited.** ADR-020 argued that cheaper tiers "do not simply divide the
problem", because Haiku's 200K context cannot hold the largest filings, forcing
either a 1M-context model or a chunking subsystem. A 1M-context tier now exists
at $2.00/MTok (`claude-sonnet-5`), which holds every filing in this corpus.
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
2. **Nothing reaches it.** The D8 trigger is measured silent on all five
   filings (§d1), so A2 is not subsumed by D11 and saying it were would be
   false. Declining it is the honest verdict; "subsumed" would have been the
   comfortable one.

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
| **B subsumed** | a second real EDGAR filing whose **body** heading names several item codes and loses items to it — the class stops being a single instance | `tasks/reviews/d9_class_scan.py`'s multi-code hits, adjudicated by hand as §c1 does | **one** filing |
| **B subsumed** | D11's ADR declines to escalate on `expected_item_missing`, leaving `axp-2008` with no owner; the fan-out then returns as the only route and must be costed again against §c2's real scope | the D11 ADR when written | that decision |

Explicitly **not** sufficient to reopen any of them: the debt cases still being
red (that is what this ADR permits); a filing merely being large, old, or
foreign; the fan-out being cheap to write, which §c2 shows it is not.

## g) Consequences

**Neither held-out case is burned, and the question is answered rather than
skipped.** `evals/heldout/README.md`'s burn rule names "a declined fix
documented with its outcome in hand" as influence, and the `gs-2002` precedent
ADR-020 §g cites establishes that declining burns a case as surely as fixing
does. This ADR is a documented decline that cites both outcomes, so the rule
plainly points at it. It is ruled **not burned**, on this ground: the
`gs-2002` and `axp-2008` burns both **authored a new adversarial case from the
fixture and moved the fixture into the dev corpus**, so the declined capability
could afterwards be developed against it. D9 authors no case from either
filing, moves no fixture, and ships no code, threshold or fix — nothing in the
tree can have trained on them, which is the property the burn rule protects.
Burning them would also destroy the exam D11's own row and `c-2025`'s
provenance both demand it sit for. **The reading is recorded for challenge, not
settled** — it is logged as a Debt row so a reviewer can overturn it, and the
burn fires the moment D8 or D11 uses either filing.

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
2. Whether this ADR trips the held-out burn rule (§g above) is ruled NO on the
   no-case-authored, no-code ground. Recorded for challenge.
3. `mrk-1995` items 5 and 7 report `extracted` over bodies that are pure
   external-document pointers to the Annual Report. Whether that should be
   `incorporated_by_reference` is an ADR-004 question this ADR rejected out of
   Class A and did not answer.
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

- `python3 -m evals.run --suite invariant` — 67/67, 1.000.
- `python3 -m evals.run --suite fast` — 130/130, 1.000, `.eval-baseline.json`
  untouched.
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
