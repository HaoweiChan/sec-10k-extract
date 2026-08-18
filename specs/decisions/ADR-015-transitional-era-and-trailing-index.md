# ADR-015 — The Sarbanes-Oxley interim era, and the trailing index that ate two filings

Date: 2026-08-17. Status: accepted. Amends ADR-007 (the TOC-cluster rule),
ADR-010 ruling 3 (the IBR remainder), ADR-013 (which declined the era-model
fix), and ADR-014 §2 (the sentence splitter). Closes the `gs-2002` debt row.

Driven by three real, unmutated EDGAR filings fetched for T9 tranche 2 and
authored as goldens **from the documents, before any code moved** (hard rule 2):
`intc-2002`, `tgt-2002`, `ba-2003`. Two of the four rulings below are for
defects nobody predicted; the tranche was aimed at the era model and hit
something much worse on the way.

## 0. The finding that matters most: a trailing index, and 0.47% of a filing

Intel FY2002 reported `doc_status: success_with_warning` with **every one of its
fifteen items resolved to an 18-to-490-character stub at the very end of the
file** — 1,445 chars of a 309,085-char document, 0.47%. Target FY2002 reported
plain **`success`**, no warnings at all, with item 4 swallowing 26,861 chars
(81% of the document) and items 5 through 14 resolved to stubs.

Neither of the two would have been caught by any assertion this eval set had
before today. `no_empty_success` passed: its floor is 1,000 chars **summed
across all items**, and 1,445 clears it. `no_overlap_ordered` passed: the stubs
are ordered and disjoint. `verbatim` passed: the offsets are in range. Eight
label-free validators ran and produced one warning on Intel
(`unattributed_content`, which is deliberately non-escalating) and **zero** on
Target. The shallow-tier checks `item_present("1", "extracted")` passed on an
18-character item 1.

**Cause.** `_toc_runs` drops a candidate from a dense run when its code "turns
up again further down", because a contents page is a manifest of things that
appear later. Both filings close with a compact cross-reference index that
repeats every item code. That echo made *every* real body heading recur —
including the front TOC's trailing member, which is the first real body heading
and the one entry the rule explicitly exists to protect (its own docstring says
so). With item 1's body heading dropped, greedy ordered assignment resolved code
1 to the echo at the end of the file, and the cursor took every later code with
it.

**Ruling.** An occurrence buried inside another dense run is not evidence that a
code recurs. It counts only if it is that run's **last member** — the position
the escaped first real heading occupies when a contents page runs straight into
the body.

The last-member exemption is not a patch on the patch: NIKE 2006 and
premier-pacific-2016 both have exactly that layout, and without the exemption
their item 1 span starts on the contents page. It was found by measuring, not by
reasoning — an earlier draft of this ruling turned `nike-2006`'s item 1 span red
and the fixture scan caught it before the suite did.

No new threshold. "Dense" is exactly the `TOC_CLUSTER_MIN` / `TOC_GAP_MAX` test
already used here, and the recurrence direction is unchanged.

**Blast radius, measured over all 28 dev fixtures** by diffing the complete
envelope (`doc_status`, every warning code, and every item's status and both
offsets) against `HEAD`: only the four filings named in this ADR changed at all.
Twenty-four fixtures are byte-identical.

**What this says about the eval set, and it is not flattering.** Two filings
lost essentially all of their content and the suite's own invariants were
satisfied. The gap is not that a validator had a bad threshold; it is that
**nothing measures whether extracted spans cover the document**. `unattributed_content`
measures only the complement of the outer hull (before the first item, after the
last), so a run of stubs at the end of a file scores 99.5% outside — and that
code is not in `AMBIGUOUS_CODES`, by an ADR-008 decision taken for IBR-heavy
filings that is still correct for its own reasons. Target scored 9% and drew no
warning at all. This is the "mis-assigned rather than missing" blind spot
ADR-013 named and did not close. It is **still not closed** — see §5.

## 0a. What counts as an echo — two wrong answers before the right one

§0's ruling was implemented as **"an occurrence inside another dense run does not
count, unless it is that run's last member"**. Code review found that this is not
what §0 says it is, and produced a document where the difference is fatal. The
review's proposed correction was also incomplete. The rule below is the third
attempt and the first that survives every document tried against it.

**The document.** A dormant shell answers "None." to most of its items, so its
bodies sit closer than `TOC_GAP_MAX` and the item list forms a dense run of its
own.

| | before ADR-015 | as first implemented | with the review's fix | this ruling |
|---|---|---|---|---|
| contents page runs into the body | `success` | **every code → a TOC row** | fixed | fixed |
| cover furniture between them | `success` | **every code → a TOC row** | **still broken** | fixed |

In the first layout the contents page and body are one run, so every body heading
but the run's last landed in `echoed`. The review's `or c["start"] in here`
exempts same-run occurrences and fixes that. But the **second layout is the
ordinary one** — a real 10-K has a cover page between its contents page and Part
I — and there the body is a *separate* dense run, so `here` never applies, nothing
in the body counts as recurring, the contents page is not dropped at all, and
greedy assignment resolves every code to a contents row. Reproduced against
`main` for the first layout and against the review's own patch for the second.

**Ruling.** An echo is defined by what it **repeats**, not by where it sits:

> A dense run is an echo when most of the codes it names already appeared as a
> heading **outside any dense run**.

```python
pre = {codes in this run that also occur EARLIER, at a non-clustered position}
if len(pre) * 2 >= len(codes): echoed |= this run
```

Intel's trailing block repeats codes whose real headings sit isolated in the body,
so it is an echo. A shell's body run repeats nothing — its codes appear earlier
*only* in the contents page, which is itself dense and therefore excluded — so it
is not. No new threshold: the majority test is the same shape as the forward one
three lines below, and "dense" is the existing
`TOC_CLUSTER_MIN`/`TOC_GAP_MAX` pair.

**This also repairs a regression the review measured and the review's own patch
did not.** Survivor counts after the TOC filter had risen on six dev fixtures —
the drop was getting weaker, which is the same weakening that produced the bug.
They are now **identical to `main`**, verified fixture by fixture:

| | `main` | as first implemented | this ruling |
|---|---|---|---|
| `aapl-2025` | 23 | 29 | **23** |
| `jpm-2024` | 22 | 27 | **22** |
| `msft-2013` | 28 | 31 | **28** |
| `sandston-2021` | 20 | 24 | **20** |
| `fy2021-item9c` | 21 | 25 | **21** |

`sgrp-2019` (24 → 20) and `wfc-2008` (27 → 20) go with them, which closes the
specific fragility the review flagged: four of `sgrp-2019`'s five body headings
were invisible to recurrence, and its contents rows survived as candidates that
happened to sit before the cursor.

**No fixture binds it, and that is a real gap rather than a shrug.** The path
needs five distinct codes within 400-char gaps in the body *and* a dense contents
page. Nothing in either set reaches it: all 42 fixtures were re-scanned, and three
further real dormant shells were fetched and checked specifically for this shape
(`eight-2015`, `newcent-2015`, `forest-2017` — the first two have an isolated body
Item 1, the third has no contents page at all). Manufacturing one means deleting
most of a real filing's content, which makes the fixture a test of the code path
rather than a model of a filer, and `items-stripped` already occupies that shape
for another purpose. So it is bound by two `segment._demo` assertions — one per
layout, because each layout caught a different wrong rule — written as siblings of
§0's trailing-index assertion and using the same synthetic-document instrument
the review used to find the bug. If a real filing of this shape turns up it
becomes a fixture that day.

**Verified**: `segment` self-check green including all three synthetic assertions;
fast 44/44; invariant 12/12; the original cases still bind the original fix
(removing only the `echoed` exclusion turns `intc-2002-shallow` red on 5 checks
and `tgt-2002-shallow` on 6); and **zero** change to `doc_status`, warnings,
statuses, offsets, confidences, titles or parts across all 42 fixtures, dev and
held-out, other than the new `whole_submission_fallback` warning on `ksb-2007`
that ADR-016 §6 adds deliberately.

## 1. Item 14 and Item 15 have a third era, 2002-08-29 → 2003-08-14

Release 33-8124 (effective 2002-08-29) inserted "Controls and Procedures" as
**Item 14** and pushed Exhibits to **Item 15**. Release 33-8238 (effective
2003-08-14) then moved Controls to **Item 9A** and made Item 14 "Principal
Accountant Fees and Services". Filings whose period ends between those dates use
a numbering the era table did not model: it dated Item 15 to 2003-08-14, so
`expected_items` never expected it, `find_candidates` skipped it, it could not
reach the TOC manifest to raise a mismatch, and its exhibit section was annexed
to item 14 — while item 14 rendered the label "Exhibits, Financial Statement
Schedules, and Reports on Form 8-K", Part IV, over Controls-and-Procedures text.

**This is the same finding `gs-2002` recorded, and ADR-013 read it wrong.** That
ADR called Goldman an early adopter and inferred that the only fix was the
general one — letting any physically present heading surface regardless of era —
which conflicts with INV-S3 and is a spec change. Two more filings from the same
window, from different sectors and different filing agents, show the window is a
**regulatory era**, not one filer's choice. Modelling it is a table correction of
exactly the kind this repo has made three times before (ADR-010 ruling 2,
ADR-014 §1, and §2 below), not an invariant amendment.

Rulings:

- `ADDED["15"] = 2002-06-01`. The rule keys on filing date and this table keys
  on period end, so the boundary is the earliest period end whose report
  necessarily lands after the effective date under the then-90-day deadline —
  the ADR-010 ruling-2 convention. It sits inside the empty band the fixtures
  measure: `textron-2001` ends 2001-12-29 on the old numbering, and `gs-2002`,
  the earliest interim filing in the set, ends 2002-11-29.
- `TITLES["14"]` gains the alias `"Controls and Procedures"`; matching stays
  era-blind, as everywhere else here.
- `item_label` gains an interim window returning `("III", "Controls and
  Procedures")`, the exact shape of ADR-014's Item 4 Reserved window. A label is
  not cosmetic: the inspector renders it over the item's text.

`gs-2002` went green **with no edit to a single assertion**, which is the whole
point of having written its failing check against the document rather than
against the era table. It is promoted from unscored debt to the scored suite.

## 2. Item 9B is not Item 9A's twin — it arrived a year later

The table dated both to 2003-08-14. Item 9B "Other Information" was created by
Release 33-8400 (adopted 2004-03-16, effective 2004-08-23). Boeing FY2003 has
`Item 9A. Controls and Procedures` and **zero** occurrences of "Item 9B", and the
pipeline reported item 9B `missing` at confidence 0.55 with an
`expected_item_missing` warning — the INV-S4 distinction between "not in the
filing" and "the extractor missed it", resolved the wrong way, on an item that
did not exist when the document was written.

**Ruling**: `ADDED["9B"] = 2004-05-23`, by the same earliest-period-end
convention. The empty band here is wide (`ba-2003` at 2003-12-31 has none; the
next fixture with a 9B is `nike-2006`), so the regulation is the authority and
the fixtures only bound it — stated plainly rather than dressed up as a measured
threshold.

## 3. A semicolon is not a sentence end

Target's pointer bodies are enumerated: *"Leases, Page 32; Owned and Leased Store
Locations, Page 32, and the list of store locations … of Registrant's 2002 Annual
Report to Shareholders are incorporated herein by reference."* `_sentences` split
on `;`, leaving `sents[0]` as "Leases, Page 32;" — so `EXTERNAL_DOC_RE` failed on
a sentence that was not one, and a whole-item pointer reported `extracted`.

Third instance of the family (the pre-B finding was an item caption, ADR-014 §2
was the ordinal "Proposal No. 2"). This one **removes a splitter** rather than
adding a rejoin, which is the smaller change and the more defensible claim: a
semicolon never ended an English sentence.

Measured over every fixture: this flips exactly one dev item, `tgt-2002` item 2,
the one it was written for.

**Item 1 of the same filing is deliberately NOT flipped, and that is the check
on the ruling.** It opens with the identical semicolon-list pointer and then
carries ~1,300 chars of real inline prose — state of incorporation, 306,000
employees, Competition, Available Information. It is a mixed item and stays
`extracted` per ADR-010 ruling 3. A fix that flipped it would have been a worse
answer wearing the same green tick.

## 4. A pointer to another item of the same report is navigation, not content

ADR-010 ruling 3 made a body `extracted` when its non-pointer remainder exceeds
300 chars. Intel item 12 is three sentences: one pointer to the proxy statement,
then two that say "see Item 7 of this Form 10-K" and "see Item 7 and Item 8 of
this Form 10-K". None of them is the beneficial-ownership content the item is
named for, but the two internal ones carried no external-document trigger words,
counted as 530 chars of "inline prose", and the item reported `extracted` — telling
a consumer the content was in the span when the span says it is not.

**Ruling**: a remainder sentence that directs the reader to another **item of
this same report** does not count toward `IBR_REMAINDER_MAX`. ADR-004 already
rules that an internal pointer cannot by itself make an item IBR; this is the
other side of the same coin — it cannot make one `extracted` either.

Blast radius: one dev item, `intc-2002` item 12. `ibr-pointer-first`'s 3,186-char
officer table is untouched, which is the case that matters — that fixture exists
to stop this exact threshold from being loosened.

## 5. What is NOT fixed, and is now larger than what is

- **The era table is still a single point of silent failure.** ADR-010 recorded
  it; this tranche is its fourth and fifth confirmation. Three separate date
  errors have now been found by three separate fixtures, each fixed by editing
  the table. The general fix — letting a physically present, well-titled heading
  for a canonical code surface regardless of era expectation — is **still not
  taken**. It contradicts INV-S3 as written, and, more to the point, no case in
  this repo can demonstrate it firing: every filing that would have exercised it
  is now covered by a corrected table entry instead. Shipping a code path no
  eval can turn red is the specific sin ADR-010's consequences section is about.
  It stays open, and the honest statement of the risk is that the *next*
  mis-dated item repeats this exactly.
- **Nothing measures span coverage.** §0's failure was invisible to eight
  validators. A coverage validator — extracted spans as a fraction of the
  document, or the maximum gap between consecutive spans — is the obvious
  missing member of the battery and is *not* added here, because adding a
  validator is a capability and the T8 freeze forbids one. It is the strongest
  candidate for the first post-freeze exception and is recorded as such in
  `tasks/TODO.md`.

  **Correction (T11, 2026-08-19, ADR-019 §d) — both halves of the paragraph
  above are wrong, and the row built on them is retired.** Coverage is
  already measured, exactly: `coverage ≡ 1 − unattributed_content`'s own
  "outside" fraction, identity holds to float equality on 33 of 33 span-
  bearing fixtures, verified by direct computation. The largest inter-span
  gap is structurally always 0.0 on every fixture with no exception —
  `assign_boundaries` sets each accepted span's end to the next accepted
  span's start, so two accepted spans can never have daylight between them;
  a gap validator built on this architecture could never fire on real
  pipeline output. And "invisible to eight validators" overstates §0 itself:
  `unattributed_content` fired on Intel (0.47% coverage,
  `success_with_warning`) — detected and non-escalating, a severity gap not
  a detection gap. Target's failure was a different shape again (item 4 at
  81%, not the last span; `last_item_dominates` only inspects the last one).
  The planned capability would have caught neither filing cited above. See
  ADR-019 §d for the full evidence and the correctly-specified successor —
  a non-last span dominating the document, plus the escalation-policy
  question — that replaces this row in `tasks/TODO.md`.
- **Cross-item footnote conventions.** Boeing marks five items IBR with a bare
  asterisk resolved once, inside item 14's body; items 11 and 13 therefore
  report `extracted` at confidence 0.95 over empty spans. Carried as the
  enumerated-debt case `ba-2003-asterisk-ibr` on the `gs-2002` precedent.
- **Held-out contamination, disclosed.** The blast-radius scan for §3 was run
  over every fixture on disk, held-out included, and so observed that the
  semicolon change moved three held-out item *statuses* (`ko-1997` items 11/13,
  `xom-2021` item 13). No held-out case file was opened and no labelled outcome
  was consulted, so this is weaker than a burn — but it is contamination, and
  the remedy is to retire `ko-1997` and `xom-2021` at the next held-out refresh
  rather than to argue the distinction. Both had already been run twice and H2's
  triage had already assessed their generalization content as near zero.

## Verification

All three goldens watched red first (`32/35` at the red commit, with ten, eleven
and two failing checks respectively); each ruling above landed with the
remaining reds still visible. Final: **fast 36/36 = 1.000**, invariant 10/10,
all three module self-checks green, `gs-2002` promoted, one enumerated debt
carried. The complete-envelope diff against `HEAD` shows four changed fixtures
out of twenty-eight.
