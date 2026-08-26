# ADR-034 — D8: a stub or pointer span is flagged at the item that carries it, and a document whose items hold almost none of it escalates

Date: 2026-08-26. Status: accepted. Implements D8 — the item-level half
[ADR-019](ADR-019-silent-failure-rate.md) §e named and did not build, and the
per-item near-empty validator [ADR-031](ADR-031-footnote-marker-ibr.md) §i
listed as NOT built. Sanctioned exception to the T8 feature freeze
(`tasks/TODO.md`, **Freeze guard**), on the pattern
[ADR-020](ADR-020-fallback-not-justified.md) established for T12 and
[ADR-026](ADR-026-boilerplate-chrome-exclusion.md) /
[ADR-029](ADR-029-structured-tables-annotation.md) /
[ADR-030](ADR-030-non-last-span-dominance.md) /
[ADR-031](ADR-031-footnote-marker-ibr.md) applied for S6/S7/D3/D4. Amends
ADR-008 (validator count, `AMBIGUOUS_CODES` size, and the
`unattributed_content` escalation paragraph — in place, each with its marker),
ADR-016 (its warning-code table gains two rows), ADR-019 §e (its "only the
first is defended" sentence gets a dated note), ADR-031 §i (its "NOT built"
row gets a dated note) and `specs/001-sec10k-contract.md` (two new required
fields). Narrative: `docs/evals/audits/2026-08-25-demo-intel-citi-postmortem.md`
§§1, 2, 7, 8.

**Ruling**: three changes, one mechanism. (1) A new layer-8 validator, `item_span_near_empty`, fires when an `extracted` span for item **1, 7 or 8** is shorter than `SPAN_FLOOR = 1500` chars; it carries the item code, so the existing `WARN_PENALTY` takes that item from 0.95 to 0.80, and it does **not** escalate `doc_status`. (2) A second new validator, `low_item_coverage`, fires when `meta.coverage` — a newly published envelope field, the fraction of `normalized_text` inside any item span — is below `COVERAGE_MIN = 0.13`; it **does** escalate, joining `AMBIGUOUS_CODES`. (3) Every item gains a required boolean `review_required`, true exactly when a warning carries that item's code. The iXBRL numeric cross-check (scope (c)) is **declined, with its measurement** (§g).
**Because**: `score()` awards 0.95 on heading-title similarity alone and only four codes could ever pull it down, none of which can see a stub or a pointer (postmortem §1) — so the 2026-08-24 demo showed `conf 0.95` over an Intel 10-K whose every item was a cross-reference-index row and a Citigroup 10-K of pointer sentences, and the eval set's own `no_empty_success` cleared the Intel shape by three characters. Measured over the dev corpus, item 1/7/8 spans split cleanly: all 14 under 2,094 chars are pointers or stubs and every span at or above it is substantive, an empty band (930, 2094) whose midpoint is 1,512; and document coverage splits at (0.0303, 0.2306), midpoint 0.13, with an empty false-positive set on every real filing.
**Enforced by**: `evals/adversarial/xref-index-collapse.json` (stub, fast + invariant; red at `820cf0c`), `evals/adversarial/cvx-2015-pointer-flagged.json` (pointer, fast + invariant; red at `820cf0c`), `evals/golden/nvda-2024-shallow.json` (a real filing's pointer; red at `820cf0c`), the four band pins `evals/golden/ko-1997-shallow.json` / `evals/golden/tgt-2002-shallow.json` / `evals/adversarial/ge-1994-oldformat.json` / `evals/golden/cat-2023-shallow.json`, `src/sec10k/validate.py::_demo` (the layer echo), `src/sec10k/eval_adapter.py::envelope_shape` (both new contract fields, and the recomputation that binds `meta.coverage` to the published items) + its new `meta_field` check type with the two literal pins (`xref-index-collapse` 0.0303, `cat-2023-shallow` 0.982), `src/sec10k/test_eval_adapter.py::test_meta_field` — all four added under PR #57 R1, red-first record `tasks/reviews/pr57-r1-red.txt`, `evals/fixtures/xref-index-collapse/` + `evals/fixtures/README.md` row + `evals/bench.py::SYNTHETIC`. Red-first record with its sha: `tasks/reviews/d8-red-first.txt`.

---

## a) Why this is a sanctioned exception and not scope creep

Same three tests ADR-026 §a set and ADR-030 §a / ADR-031 §a re-ran:

1. **The human asked for it in writing, on the record** — the D8 row of
   `tasks/TODO.md` demands an ADR before any code and names the three scope
   items (a), (b) and (c) added on 2026-08-26 from the interviewer-feedback
   mapping. This document is that ADR, and §§d, e and g are those three
   rulings.
2. **ADR-020/026/029/030/031 set the shape: a post-freeze capability gets a
   written ruling with its cost named, whichever way it goes.** "NOT
   JUSTIFIED" was an allowed outcome for all three parts. Two rule IN, on the
   measurements in §b and §d; scope (c) rules OUT, on the measurement in §g.
3. **What it changes on committed real filings is small, enumerated and
   argued.** §f is the measured blast radius: of the 57 dev documents that
   existed before this change, 46 are identical in every field
   `evals/snapshot.py` reads, 11 gain a warning and an item-level confidence
   move, and exactly **one** changes `doc_status` — `nvda-2024`, which §e2
   argues was reporting a warning-free `success` over a 209-char pointer.

## b) The measurement — per-item span length

Instrument: `extract_items` at `820cf0c` over every filing under
`evals/fixtures` (39 span-bearing documents once the new fixture is counted;
26 real filings, 13 self-created derivatives) and, **read-only, reported
separately in §b4 and entering no derivation**, the 7 held-out filings. For
each `extracted` span: its item code and its length in `normalized_text`
chars. IBR spans are excluded, as they are from every content-shape validator
(ADR-011) — an IBR pointer is already labelled and already scores 0.85.

### b1. The census that decides the item set

The three items whose canonical answer is never one sentence are **1**
(Business), **7** (MD&A) and **8** (Financial Statements). Across the 38
span-bearing dev documents that existed at `820cf0c` those three carry **90**
extracted spans (93 once the new fixture is counted). Sorted, they split at
one gap. Every span **below 2,094 chars** — all 14 of them — is a pointer or a
stub, and here they are in full, so the claim can be checked rather than
believed:

| chars | fixture · item | what the whole span says |
|---|---|---|
| 86 | ge-1994 · 8 | "See index under item 14." |
| 86 | ibr-pointer-first · 8 | (the ge-1994 derivative — same line) |
| 125 | reac-2015 · 8 | "The required financial statements begin on page F-1 of this document." |
| 189 | cvx-2015 · 8 | "…index to MD&A, Consolidated Financial Statements and Supplementary Data is presented on page FS-1." |
| 209 | nvda-2024 · 8 | "The information required by this Item is set forth in our Consolidated Financial Statements and Notes thereto included in this Annual Report on Form 10-K." |
| 241 | spatz-2014 · 8 | "…are included in this report on pages 15 through 22." |
| 263 | fy2021-item9c · 8 | "…set forth in the Index to Financial Statements (on page F-1) of the separate financial section which follows this report" |
| 263 | sandston-2021 · 8 | (same filer, the fy2021 fixture's source) |
| 267 | xom-2021 · 7 | "Reference is made to the section entitled 'MD&A' in the Financial Section of this report." |
| 280 | cvx-2015 · 7 | "…index to MD&A … is presented on page FS-1." |
| 372 | jpm-2024 · 8 | "The Consolidated Financial Statements … appear on pages 169–321." |
| 398 | jpm-2024 · 7 | "…entitled 'Management's discussion and analysis,' appears on pages 52–167." |
| 737 | xom-2021 · 8 | a bulleted list of what is in the Financial Section, plus a schedule-omission note |
| 930 | ko-1997 · 8 | a list of the seven statements incorporated by reference from the Annual Report to Share Owners |

**Not one of the 14 is a substantive answer.** Every one is
ADR-019 §e's internal-pointer class (`ge-1994`, `cvx-2015`, `jpm-2024` are
named there; `nvda-2024`, `reac-2015`, `spatz-2014`, `sandston-2021`,
`xom-2021` are five more the class list did not have) or a
list-of-what-is-incorporated (`ko-1997`).

The next span up is **2,094 chars** — `tgt-2002` item 1, real Business prose
in a near-pure-pointer document — and from there the distribution is
continuous and substantive: 2,955 (spatz-2014 item 1), 3,164 (sandston-2021
item 1), 3,763 (sgrp-2019 item 7), up to 333,940 (bac-2006 item 7); the
per-code medians are 18,119 · 13,015 · 15,611.

**Band (930, 2094). Midpoint 1,512 → `SPAN_FLOOR = 1500`**, two significant
figures, the convention `ITEM_MAX` follows. Margins: **1.40×** below the
smallest legitimate span and **1.61×** above the largest pointer — wider than
`ITEM_MAX`'s 1.03× and `MISSING_MAX`'s 1.25×, narrower than
`LAST_ITEM_MAX`'s 2.6×.

### b2. Why items 1A and 7A are NOT floored, and no other code is either

A blanket floor across all 23 codes was the obvious first move and is
**rejected on measurement**. A smaller reporting company answers Items 1A and
7A with one true sentence — "Not required for smaller reporting companies" —
and the corpus is full of them:

| code | dev spans under 1,500 chars | what they are |
|---|---|---|
| 1A | 6 of 25 (41–129) | reac-2015 and the five 2016-shell derivatives: the smaller-reporting-company exemption |
| 7A | 20 of 27 (69–575) | the same exemption, plus "Not applicable" |
| 1B | 27 of 27 (43–307) | "None." — Item 1B is *designed* to be empty |
| 4 | 33 of 39 (18–325) | "Not applicable" (mine safety), or the pre-2011 "no matters submitted" |
| 6 | 23 of 27 (18–1,410) | "[Reserved]" since 2021 |
| 9 | 38 of 38 (101–467) | "None." / "No disagreements with accountants" |
| 9B, 9C, 16 | 25/27, 7/7, 5/6 | "None." / "Not applicable" |

Those codes have **no empty band at all** — the legitimate and the defective
overlap completely — so a floor on them would be the `vacuous_coverage`
finding ADR-027 §c closed, re-opened. Items 5 and 10–15 sit in between
(medians 786–4,800) and were measured too: their low ends are genuine
one-paragraph Part III proxy pointers, already the ADR-004 shape the corpus
treats as correct, and no gap separates them. Every count above is
reproducible from `extract_items` over `evals/fixtures`. **Three codes have a
band; three codes get the floor.**

### b3. Two alternative signals, measured and rejected

ADR-008's "rejected after measuring" pattern:

- **A floor as a FRACTION of the document** (span/`len(text)` rather than an
  absolute count). `tgt-2002` item 1 is 2,094 chars but 6.3% of a 33K
  document, while `bac-2006` item 7 is 333,940 chars and 47% of a 706K one —
  and `ko-1997` item 8's 930-char pointer is 0.96%, inside the same range as
  `sgrp-2019`'s legitimate 3,763-char item 7 (4.5%) once small filings are
  included. The absolute count separates; the fraction does not. Rejected.
- **Coupling `unattributed_content` to the items whose spans ABUT the
  unattributed region** (the D8 row's "and/or" alternative). It fails
  structurally, and the corpus confirms it. `unattributed_content` measures
  the preamble (before the FIRST span) and the tail (after the LAST) and
  deliberately not interior gaps (ADR-008, amended ADR-027 §g) — so the spans
  abutting it are, by construction, the first and the last, never an interior
  one. Measured over the 12 documents this ADR's floor fires on: the first
  span is item **1** on all 12 and the last is item 14/15/16 on all 12, so the
  coupling would name a flagged item on **1 of 12** (the synthetic, whose item
  1 is itself a stub) and would name **nothing at all** on the eleven real
  pointer filings — cvx-2015, jpm-2024 and xom-2021 included, the three the
  postmortem cites. It is a rule about item ORDER, not about item content.
  Rejected — the span floor names the right item directly, which is the whole
  requirement.

### b4. Held-out — read-only, reported, not tuned on

| fixture | coverage | item 1 | item 7 | item 8 | fires? |
|---|---|---|---|---|---|
| intc-2025 | 0.0033 | 147 | 226 | 66 | both codes |
| c-2025 | 0.0000 | — (no spans at all) | — | — | `low_item_coverage` only |
| mrk-1995 | 0.7593 | 43,165 | 247 | 738 | `item_span_near_empty` on 7, 8 |
| pgr-2023 | 0.8587 | 61,262 | 243 | 253 | `item_span_near_empty` on 7, 8 |
| cost-2022 | 0.9584 | 20,526 | 28,693 | 87,103 | no |
| csco-2016 | 0.9604 | 59,047 | 123,703 | 193,137 | no |
| spg-2019 | 0.9128 | 24,693 | 74,399 | 193,355 | no |

No threshold here is derived from this table; both bands come from dev values
alone (§b1, §d), and the constants were fixed before the table was read. It is
reported because the D8 row asks for blast radius on the held-out fixtures,
and because two of the seven move `doc_status` (§f2). **Neither `intc-2025`
nor `c-2025` was read, adjudicated, or iterated against** — their span lengths
come from the same instrument run as everything else, and no case label of
theirs was consulted. `mrk-1995` and `pgr-2023` items 7/8 are **not
adjudicated here**: whether a 1995 pharmaceutical and a 2023 insurer answer
MD&A with a legitimate pointer is a question about those documents, and
reading them to decide would burn the fixtures (`evals/heldout/README.md`),
exactly as ADR-030 §b1-held-out declined to adjudicate `mrk-1995`'s 0.5274.

## c) Ruling — the item-level code warns, it does not escalate and it does not restate the status

`item_span_near_empty` is **not** in `AMBIGUOUS_CODES`, and it does **not**
change `status`.

**Why not escalating.** One pointer item is a fact about that item, not a
verdict on the document. Escalating would take **9 real dev filings** —
`cvx-2015`, `ge-1994`, `ko-1997`, `nvda-2024`, `reac-2015`, `sandston-2021`,
`spatz-2014`, plus the already-ambiguous `jpm-2024` and `xom-2021` — and two
derivatives of them to `ambiguous`, capping every one of their items at 0.75,
including items that are perfectly resolved (`cvx-2015`'s 82,907-char Item
1). ADR-008's
F7 policy forbids a validator that cries wolf, and ADR-013's cost asymmetry
does not rescue it here: unlike a collapsed document, a filing with one
pointer item HAS been resolved, and the honest report is per-item.

**Why not a status change.** ADR-004's ruling — an internal pointer cannot make
an item `incorporated_by_reference`, because nothing is incorporated from
outside the document — is correct and untouched, and ADR-019 §e recorded a
standing, unresolved disagreement about whether such a span is "wrong" at all
(the auditor's blind sample called `cvx-2015` item 6 CORRECT). A new status
would resolve that disagreement by fiat, in one direction, in a contract enum
that consumers switch on. The warning does not: it asserts only that the span
is **too short to be this item's content**, which both readings agree on. That
is a review signal, and §e gives it its own field rather than overloading
`status`.

**What it does do.** It carries the item code, so it enters `score()`'s
existing `hits` list and `WARN_PENALTY` moves that item's number: 0.95 → 0.80
on the seven non-ambiguous real filings above (on `jpm-2024` and `xom-2021`
the number does
not move — both are already `ambiguous`, so ADR-027 §a's 0.75 cap already sat
below 0.80 — and the warning is still emitted and still sets
`review_required`). Nothing about the mechanism is new: it is the same
warning plumbing, the same penalty, the same evidence record.

## d) Ruling on scope (a) — coverage is published, and its low end escalates

The interviewer's finding (postmortem §8 gap 1): a document with roughly 37%
of its content in items and 63% unattributed came back reading as plain
success, with no coverage figure in the response.

**Two separate defects, and they need separate fixes.**

**The figure was not published.** `unattributed_content`'s message carries a
percentage, but (i) it is a message, not a field, and (ii) it is **not the
coverage number** — it counts the preamble and the tail only, and ADR-019 §d
measured it understating true non-coverage by up to 9.7 points on the 7
`EXEC_OFFICERS_RE` fixtures (ibm-1997: coverage 0.4692, `1 − unattributed`
0.5663). So `meta.coverage` is now published on every non-refusal envelope —
the fraction of `normalized_text` inside any item span, IBR spans included,
rounded to 4 dp — beside `toc_manifest` and `taxonomy_era`, which are
normative in `meta` on exactly the same terms. It is not a new top-level key:
a v3 envelope shape buys nothing that a `meta` field does not, and
`envelope_shape` enforces it either way.

**Nothing escalated on it.** ADR-008 deliberately kept `unattributed_content`
out of `AMBIGUOUS_CODES` because for IBR-heavy filings that shape is normal,
and **that ruling stands** — IBM places 46.92% of its text and Textron 66.86%,
and neither is a failure. But the argument has a floor, and nobody had found
it: a document whose items hold 3% of it has not been resolved at all.

Measured over the dev corpus, coverage on span-bearing documents runs from
**0.2306** (ge-1994 — a txt-era Exhibit-13 filer whose annual report follows
the 10-K) through 0.2718 (cvx-2015), 0.4692 (ibm-1997) and up to 0.9931.
Below 0.2306 there is nothing until the stub-collapse shape at **0.0303**
(`xref-index-collapse`, §f3). **Band (0.0303, 0.2306), midpoint 0.1305 →
`COVERAGE_MIN = 0.13`**, 1.77× below the lowest real filing and 4.3× above
the synthetic. It joins `AMBIGUOUS_CODES` on ADR-030 §c's three reasons,
re-checked: the cost asymmetry (a false `ambiguous` is inspectable, a false
`success_with_warning` on a collapsed document is the silent failure the
battery exists for), an **empty measured false-positive set** — no committed
real filing, dev or held-out, is under 0.13 — and consistency, since a
document nothing of which is inside an item is at least as unresolved as one
where a single span holds 56% of it.

The lower edge is a synthetic, and that is stated rather than dressed up: no
real filing in either set sits between 0.0303 and 0.2306, so the band's low
side is pinned by a fixture built for the purpose — the same standing
`items-stripped` has for `MISSING_MAX` (ADR-027 §c) and
`interior-span-dominates` for `ITEM_MAX`. The two historical instances of the
class read far below it, from the record rather than from a run:
`intc-2002`'s original failure at 0.0047 (1,445 of 309,085 chars, ADR-015 §0)
and held-out `intc-2025` at 0.0033 (§b4).

**On the interviewer's own 37/63 document, this code does not fire** — 0.37 is
above 0.13 — and that is the correct outcome. What that document gets is the
published `meta.coverage: 0.37`, an `unattributed_content` warning (any
coverage under ~0.83 emits one) and therefore `doc_status:
success_with_warning`, never `success`, which requires an empty warning list.
The escalation threshold is for the collapse case, not for a filer who
incorporates a lot by reference; conflating them would break IBM and Textron.

## e) Ruling on scope (b) — the consumer gets `review_required`, not silence and not a status change

The interviewer's finding (postmortem §8 gap 2): a validator-flagged item still
serves its text under an unchanged `extracted` status, so confidence moving on
its own leaves the consumer holding possibly-wrong text labelled clean.

**Ruling: a required per-item boolean, `review_required`.** True exactly when
a warning in `warnings` carries this item's code, excluding
`expected_item_missing` (which only restates `status: missing`, ADR-018) —
i.e. the same `hits` list that already moves `confidence`, so the two can
never disagree. Four lines of code, no new mechanism.

**Why not a fifth status.** §c gives the argument in full: `status` answers
"what did the filing do with this item" (ADR-004/005), a question whose answer
here is genuinely `extracted`; a fifth value would resolve ADR-019 §e's
recorded disagreement by fiat and would break `only_items`,
`expected_set_complete` and every consumer switch. **Why not leave it to
`confidence`.** A number invites a threshold, and the demo is what a
threshold on an uncalibrated near-binary scale looks like
(`docs/architecture/overview.md` §confidence: 224 of 283 items at 0.95). A
boolean is not a threshold. **Why not doc-level.** `doc_status` already
carries the document verdict, and an `ambiguous` document separately caps
every item at 0.75 (ADR-027 §a); a document-level warning (`item: null`) does
not set `review_required` on anything, which is stated in the contract so the
absence cannot be read as a bug.

Postmortem §8 records `needs_review` among the "praised mechanisms that do not
exist in this codebase". It exists now, under the name the D8 row uses, built
rather than claimed.

### e2. What this cost: NVIDIA FY2024, and the exact-success pin

`nvda-2024` is the one real dev filing whose `doc_status` moves
(`success → success_with_warning`), and `evals/golden/nvda-2024-shallow.json`
was the eval set's **only exact-`success` pin** when it was written — an audit
follow-up placed there in 2026-08-15 precisely so that gratuitous-warning
behaviour could not hide.

**The filing is not clean.** Its Item 8 is 209 chars — "The information
required by this Item is set forth in our Consolidated Financial Statements
and Notes thereto included in this Annual Report on Form 10-K." — and the
statements it points at are inside **Item 15's** span: the audit report begins
at normalized offset 230,451 and every Consolidated Statement from 230,528,
against Item 15's range 230,364–338,303. That is established by offset
containment on the pipeline's own output, not by reading the filing. So a
consumer asking this pipeline for NVIDIA's financial statements got a
sentence, at 0.95, inside a document reporting warning-free success, while the
financial statements were filed under Exhibits. It is a fourth member of
ADR-019 §e's class, and finding it is a result of this ADR, not a cost of it.

**The pin moves; the audit's purpose does not.** The premise behind the 2026-08-15
note — "no case anywhere demands a clean, warning-free success" — has not been
true since 2026-08-22: `evals/golden/bac-2006-images.json` and
`evals/adversarial/spaced-letter-heading.json` both assert `value: "success"`,
and neither moves under this change. `evals/golden/cat-2023-shallow.json` is
tightened from the in-list form to the exact one in the same commit, so a
modern full-taxonomy real filing keeps the role, with three `warning_absent`
checks on items 1/7/8. `nvda-2024-shallow` becomes the real-filing pointer
pin instead of the clean-success pin, and its provenance records the swap.

## f) Blast radius — `820cf0c` vs this branch, all 65 committed documents

Instrument: `evals/snapshot.py` (the committed byte-identity harness, ADR-033
§d), run against the tree before and after the pipeline change, over
`evals/fixtures` (58 files incl. the new one) and `evals/heldout/fixtures`
(7), and diffed field by field.

```
before:  dev sha256=b39eae8b945e932366cde5306cd08f22db5ea4c4ba299d18c5dc9a6a3c08d033
         heldout sha256=dd67647b16369ac309a43ad856c3358cc3da8bdd00f08e7b526ad81e38ccbd26
after:   dev sha256=58364186aff9dad3f7443de4b5447ae3a7894e76fc01ad1592fd03a4b4479d0f
         heldout sha256=f80025699bc34f06af6ea0fb3457106593ec858c4d89d4144870e339b00e191a
```

**No `normalized_text` sha changed anywhere. No offset, `status` or `method`
moved anywhere** — this is a validator; it reads spans and does not produce
them. No envelope key list changed (both new fields live inside `meta` and
inside each item). Table fidelity `cells 1.0000 (427/427), rows 1.0000
(34/34)`; structure fidelity `blocks 1.0000 (61/61), bounds 1.0000 (61/61)`.

### f1. Dev — 46 of 58 files identical in every field the snapshot reads

| fixture | what changed | clause |
|---|---|---|
| `xref-index-collapse` (NEW) | `success_with_warning → ambiguous`; `item_span_near_empty` ×3 + `low_item_coverage`; all 16 items 0.95 → 0.75 | §f3 (the case; red at `820cf0c`) |
| `nvda-2024` | **`success → success_with_warning`**; `item_span_near_empty` on 8; item 8 0.95 → 0.80 | §e2 |
| `cvx-2015` | `+item_span_near_empty` on 7 and 8; both 0.95 → 0.80 | §b1 |
| `ge-1994`, `ibr-pointer-first`, `ko-1997`, `reac-2015`, `sandston-2021`, `fy2021-item9c`, `spatz-2014` | `+item_span_near_empty` on 8; item 8 0.95 → 0.80 | §b1 |
| `jpm-2024`, `xom-2021` | `+item_span_near_empty` on 7 and 8; **no confidence change** — both are already `ambiguous`, so ADR-027 §a's 0.75 cap already sat below 0.80 | §c |
| every other dev fixture (46) | identical in every snapshot field | — |

No `doc_status` moves on any real dev filing but `nvda-2024`. No
`low_item_coverage` fires on any real dev filing at all.

**Two fields the snapshot cannot see**, stated rather than left implicit:
`evals/snapshot.py`'s `FIELDS` tuple is fixed and reads neither
`item.review_required` nor `meta.coverage`, so their arrival is invisible to
the harness. What binds them instead:

- `review_required` — `envelope_shape` requires the key on every item, and
  seven `item_field` checks across three cases (`xref-index-collapse`,
  `cvx-2015-pointer-flagged`, `nvda-2024-shallow`) assert it BY VALUE, true
  and false.
- `meta.coverage` — **the PUBLISHED figure only.** `envelope_shape` requires
  the key and recomputes the contract's own definition of it from the items
  the same envelope publishes, refusing any envelope whose published figure
  disagrees; two `meta_field` checks pin the literal at both ends of the range
  (`xref-index-collapse` 0.0303, `cat-2023-shallow` 0.982). **Nothing binds
  the figure `validate()` thresholds on.** `coverage()` is called twice —
  `extract.py` publishes one result, `validate.py` thresholds another — and no
  committed case reads the second. That gap is open, measured, and carried as
  debt (`tasks/TODO.md`, Origin: PR #57 R4).

*(Corrected twice, 2026-08-26, and the second correction is the one to read.*

*Under **PR #57 R1**: this paragraph first claimed `meta.coverage`'s value was
"bounded from both sides by the two `low_item_coverage` band pins". That was
false — `validate()` calls `coverage()` itself, so the band pins judge a
number `extract.py` never published, and a tree with `meta["coverage"] = 1.0`
hard-coded passed invariant 69/69, fast 132/132 and every unit self-check. The
`meta_field` check type and the `envelope_shape` recomputation above are that
repair, and the mutant is now red on 24 cases (`tasks/reviews/pr57-r1-red.txt`).*

*Under **PR #57 R4**: the replacement sentence was **also** false. It said the
two call sites were "pinned by their AGREEMENT" — they are not. The
`envelope_shape` recomputation judges the publisher and only the publisher;
`validate.py`'s `cov = coverage(text, items)` is read by no check, and
changing it to count `extracted` spans only leaves invariant 69/69 and fast
132/132 green while 24 of the 39 span-bearing dev fixtures threshold a
different number from the one they publish. That is the SAME defect class the
sentence it replaced had. The claim is withdrawn rather than replaced a third
time: what is pinned is the publication, the second call site's agreement is
not pinned, and the gap is a debt row. See that row for why the cheap fix the
finding suggests does not work and what the real one costs.)*

### f2. Held-out — read-only, reported, not acted on

| fixture | what changed |
|---|---|
| `intc-2025` | **`success_with_warning → ambiguous`**; `item_span_near_empty` on 1, 7, 8 + `low_item_coverage`; all 23 items 0.95 → 0.75 |
| `c-2025` | `+low_item_coverage` (coverage 0.0); already `ambiguous`, nothing else moves |
| `mrk-1995` | `success → success_with_warning`; `item_span_near_empty` on 7, 8; both 0.95 → 0.80 |
| `pgr-2023` | `success → success_with_warning`; `item_span_near_empty` on 7, 8; both 0.95 → 0.80 |
| `cost-2022`, `csco-2016`, `spg-2019` | identical in every snapshot field |

The first row is the demo failure, fixed: the Intel document that reported
`success_with_warning` over a column of 0.95s now reports `ambiguous` with
every item at 0.75 and three items flagged for review. **That is a measurement,
not a claim of generalization** — `intc-2025`'s case labels were not read and
nothing was iterated against them; the item-level checks its case asserts
(four `min_chars` floors and one `text_contains`) are about span CONTENT and
are untouched by this change, so the case still fails and D6's recorded
outcome stands. The exam is D11's to pass, not this ADR's.

**No held-out case flips red from this change**, and no held-out run was
performed. `mrk-1995` and `intc-2025` carry no `doc_status` check at all;
`pgr-2023`'s accepts `success_with_warning`; `cost-2022`'s does too and it
does not move. That was checked by reading the four cases' check TYPES, after
both constants were fixed, and no constant was revisited on the answer.

### f3. The new fixture

`evals/fixtures/xref-index-collapse/filing.htm` is `tgt-2002/filing.htm` with
the first raw occurrence of each of the 16 literal item labels deleted (119
bytes; the second occurrence of each — its row in the trailing cross-reference
index at raw 87068–89101 — is kept, and the derivation asserts that
re-inserting the 16 labels reproduces the source byte for byte). The index
rows become the only surviving heading candidates, so all 16 items resolve to
18–117-char stubs: **1,003 chars of 33,061 (coverage 0.0303), every item
`extracted` at 0.95 via `heading_strict`, `success_with_warning`, and the only
warning the non-escalating `unattributed_content`.** That is the demo's Intel
shape reproduced on the dev side, and it is why the class did not need
`intc-2025` to develop against. `no_empty_success` clears it by three
characters (1,003 against `NO_EMPTY_SUCCESS_FLOOR` 1,000) — the same miss
recorded for `intc-2025`'s 1,727 — which the case asserts so the gap stays on
the record.

## g) Ruling on scope (c) — the iXBRL numeric cross-check is DECLINED, with its measurement

The proposal (postmortem §8, a mechanism one interviewer believed already
existed): compare monetary iXBRL facts inside the Item 8 span against facts
outside every span, as a $0 deterministic coverage sensor.

**Ruling: declined for D8. Not "no", but "not this, and here is the number that
would change it."** Four measurements:

1. **It covers a fifth of the corpus.** Counting `<ix:nonFraction` in the raw
   bytes of every fixture: **8 of the 39 span-bearing dev documents carry any
   iXBRL fact at all** (aapl-2025 969, cat-2023 3,538, jpm-2024 7,841,
   nvda-2024 1,218, heading-unnumbered 1,218, xom-2021 2,184, sandston-2021
   134, fy2021-item9c 134). The other 31 — every txt-era filing, every
   legacy-HTML filing through 2019 — carry **zero**, so the sensor is
   structurally blind to `intc-2002`, `tgt-2002`, `ge-1994`, `ko-1997`,
   `ibm-1997`, `cvx-2015`, `wfc-2008`, `bac-2006` and the whole
   stub-collapse-era corpus. Held-out: `csco-2016` and `mrk-1995` also read
   zero. A signal that cannot fire on the class of document that produced
   ADR-015 is not the cheapest catch for that class.
2. **On the two demo filings it is redundant or vacuous.** `intc-2025` carries
   2,016 facts and would fire — but `low_item_coverage` already catches it at
   0.0033 for the price of a subtraction, on every era. `c-2025` carries 9,751
   facts and has **zero spans**, so "inside Item 8 versus outside every span"
   is 0-versus-all by construction and says nothing the coverage figure does
   not already say. The sensor's headline use case is covered twice over.
3. **It is not free, and the cost lands on the layer this repo has ruled
   about.** `normalize.py` puts `ix:header` and `ix:hidden` in `SKIP_TAGS` and
   otherwise passes fact text through as ordinary characters, so a fact has no
   identity in `normalized_text` — relating a fact to a span means carrying a
   fact→offset map through normalization, i.e. exactly the raw-to-normalized
   mapping refused in ADR-026 §a and restated as a hard boundary at D5. That
   is a normalization-layer change, and INV-S5 governs what may enter
   `normalized_text`; it is a milestone, not a validator.
4. **It has no measurable threshold today.** "What fraction of monetary facts
   outside every span is too many" would need a two-sided empty band, and only
   8 dev documents can produce a value — `xom-2021` and `jpm-2024` among them,
   both already `ambiguous` for other reasons. A threshold the corpus cannot
   pin from both sides is the `vacuous_coverage` finding ADR-027 §c closed.

**What would change the ruling**, stated so it can be checked rather than
re-argued: a filing that (i) is iXBRL, (ii) has coverage **above**
`COVERAGE_MIN` and item 1/7/8 spans **above** `SPAN_FLOOR` — so both codes here
stay silent — and (iii) is still wrong in a way the fact distribution shows.
No document in either set is such a filing today. Logged as a Debt row
(`Origin: D8`) rather than left as a sentence in a postmortem.

## h) What this gives D11 — the trigger's measured rates

Postmortem §7: "the trigger is the prerequisite… trigger precision/recall on
the dev corpus becomes ADR evidence: fire too rarely and the demo repeats, too
often and the cost story collapses." The rates, as measured, with the
denominators stated:

| | dev (39 span-bearing) | held-out (7, read-only) |
|---|---|---|
| `item_span_near_empty` fires on the document | 12 / 39 = **0.308** | 3 / 7 = 0.429 |
| `low_item_coverage` fires | 1 / 39 = **0.026** (the synthetic) | 2 / 7 = 0.286 (intc-2025, c-2025) |
| either fires | 12 / 39 = **0.308** | 4 / 7 = 0.571 |

**Recall on the shapes D11 exists for is 2 of 2**: the stub collapse
(`xref-index-collapse` dev, `intc-2025` held-out) and the total
non-resolution (`c-2025`) both fire, and both fire on the escalating code.

**Precision is not stated as a number, deliberately.** It would require
adjudicating each of the 11 real dev firings as right or wrong, and ADR-019 §e
records a live disagreement about exactly that — the auditor's blind sample
called a `cvx-2015` pointer CORRECT. What can be said without adjudicating: all
12 firings are the shape the code names (a span too short to be the item's
content, §b1's census), and 0 of them are a substantive span misjudged. If
D11 routes on `low_item_coverage` alone, the escalation rate on this corpus is
**2.6% of dev documents** and the cost story is intact; if it routes on either
code, it is 30.8%, and the per-document cost of the slow path decides whether
that is affordable. **This ADR does not choose the routing rule** — that is
D11's, with its own ADR and its own cost measurement.

## i) Threshold pins and the red line

| constant | value | measured empty band (low fixture, high fixture) | pins | mutation → red line |
|---|---|---|---|---|
| `SPAN_FLOOR` | 1500 | (930 ko-1997 item 8, 2,094 tgt-2002 item 1) | `ko-1997-shallow` `warning_present item_span_near_empty item 8`; `tgt-2002-shallow` `warning_absent … item 1` | **900**: ko-1997 RED `expected warning 'item_span_near_empty', got ['unattributed_content']`; **2100**: tgt-2002 RED `unexpected warning 'item_span_near_empty': item 1's span is 2,094 chars, under the 2,100-char floor` |
| `COVERAGE_MIN` | 0.13 | (0.0303 xref-index-collapse, 0.2306 ge-1994) | `xref-index-collapse` `warning_present low_item_coverage`; `ge-1994-oldformat` `warning_absent low_item_coverage` | **0.02**: xref-index-collapse RED `expected warning 'low_item_coverage'`, `doc_status 'success_with_warning' != 'ambiguous'`, `item 1 confidence 0.8 > 0.75`; **0.24**: ge-1994 RED `unexpected warning 'low_item_coverage': only 23.1% of the document lies inside an item span (83,654 of 362,717 chars)`, `item 7 confidence 0.75 != 0.85`, `item 10 confidence 0.75 != 0.95` |
| escalation policy | `low_item_coverage` ∈ `AMBIGUOUS_CODES` | — | `xref-index-collapse` | removing it → RED `doc_status 'success_with_warning' != 'ambiguous'`, `item 1 confidence 0.8 > 0.75` |

Full transcript of the five mutation runs above:
`tasks/reviews/d8-threshold-mutations.txt`.

**Red at `820cf0c`** (the two new cases, the four amended cases and the new
fixture present, pipeline untouched): `invariant 66/69 = 0.957`,
`fast 127/132 = 0.962`, five cases red —
`xref-index-collapse` (8 checks), `cvx-2015-pointer-flagged` (7),
`nvda-2024-shallow` (5), `ko-1997-shallow` (1), `ge-1994-oldformat` (1). The
full per-check output, with the sha, is committed at
`tasks/reviews/d8-red-first.txt`.

## j) Consequences, and what this ADR does NOT claim

- **ADR-019's structural gap is closed in mechanism.** "Document-level and
  item-level honesty are separate properties here, and today only the first is
  defended by an escalation rule" — the second is defended now. It is closed
  in mechanism, not in coverage: the item-level rule reaches items 1, 7 and 8,
  and a stub on item 2 or a mislabelled item 12 is still invisible.
- **The internal-pointer debt class stays debt.**
  `evals/adversarial/cvx-2015-internal-pointer.json` is still permanently red,
  and the D9 decision row is unaffected: nothing here resolves a page
  reference, and the disagreement over `cvx-2015` item 6 (outside the floored
  set) is untouched.
- **Not claimed**: that a flagged item is WRONG — the warning asserts only
  that the span is too short to be the item's content, and §c explains why the
  stronger claim is not this ADR's to make; that the corpus's clean 14-vs-76
  split at 2,094 chars holds beyond the 26 real dev filings measured — a
  smaller reporting company whose entire Business section is 1,200 chars will
  be flagged, and the 1.40× margin is the honest bound; that
  `low_item_coverage` catches the Citigroup shape by itself (`c-2025` was
  already `ambiguous` because it has no extracted items at all, so the code
  adds a reason, not a verdict); that either code catches a span that is the
  right SIZE and the wrong CONTENT (ADR-013's blind spot, and ADR-030 §g's —
  length measures size, not correctness); that `mrk-1995`'s or `pgr-2023`'s
  items 7/8 are correct or defective (not adjudicated, §b4); that any
  threshold was chosen on held-out data (both bands are dev-only; §b4 and §f2
  enter no derivation).
- **`extractor_version` → `0.9.0-d8`**, a minor bump rather than a patch:
  ADR-029/032/033 added OPTIONAL envelope keys, while this adds a required
  item field and a required `meta` key. An old consumer's item loop is
  unaffected; a schema check written against 0.8.x is not, and `doc_status` on
  a low-coverage document is not comparable across the bump.
- **The bench artifact of record is not re-run here.** `SYNTHETIC` names the
  new fixture so n reads 43 at the next refresh (`evals.oracle.iter_fixtures`
  yields 43 today), which `--self-check` counts.
- ADR-008's validator count now reads ten (`grep -c 'warn("'
  src/sec10k/validate.py` → 10) and `AMBIGUOUS_CODES` five
  (`len(AMBIGUOUS_CODES)` → 5); both amended in place with this ADR's marker,
  and README's "only four may escalate" is corrected to five with the same
  command behind it.

## Verification

`--suite invariant` 69/69 = 1.000 (+3 enumerated debt, unscored);
`--suite fast` 132/132 = 1.000 (+3 enumerated debt, unscored); table fidelity
cells 427/427, rows 34/34; structure fidelity blocks 61/61, bounds 61/61.
`.eval-baseline.json` untouched (`{"fast": 1.0}`, matches). No
`--update-baseline`, no `--no-verify`. Module self-checks green:
`src.sec10k.validate` (with nine new assertions), `src.sec10k.eval_adapter`
21/21, `evals/snapshot.py`, `evals/metrics.py`, `evals/bench.py`. Held-out
suite **not run** — no threshold was tuned on it; §b4 and §f2 are read-only
measurements taken with `evals/snapshot.py` and the same span instrument as
the dev corpus.
