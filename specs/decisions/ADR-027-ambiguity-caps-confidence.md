# ADR-027 — T5 findings disposed: an `ambiguous` document caps every item, `method` tells the truth, and every threshold is pinned inside its measured band

Date: 2026-08-22. Status: accepted. Disposes the 12 T5 findings in
`tasks/reviews/gates-2026-08-22.json` (`T5_cold_reviewer` T5-1..T5-5 +
`vacuous_coverage`, `T5_spec_drift` SD-1..SD-7). Amends ADR-008 (confidence
range and four stale figures, in place), ADR-007 (the meaning of
`heading_lenient`, in place) and ADR-018 (the span-coverage sentence and the
population of its published table, in place). Implements layer 9
(`src/sec10k/validate.py::score`, `src/sec10k/extract.py`).

**Ruling**: a document whose `doc_status` is `ambiguous` caps every item's confidence at `BASE_WEAK` (0.75); `method` is derived from the same `STRICT_SIM` cut that pays `BASE_STRICT` vs `BASE_WEAK` (`heading_lenient` below it); the dead `FLOOR` clamp is deleted; `boundary_hygiene` reads headings with `segment.HEADING_RE` itself; and each of the five validator thresholds is pinned from both sides of its measured empty band by a committed case.
**Because**: the orchestrator verified an envelope that said "we could not resolve this document" over a column of 0.95s, and the milestone's own gate ("thresholds derived from measured distributions") was met by one constant in twelve — the rest were either unmeasured or free to move across a wide green band.
**Enforced by**: `evals/adversarial/items-stripped-escalation.json` (+ `jpm-2024-structure`, `heading-unnumbered`, `malformed-html`, `xom-2021-shallow`: `confidence max 0.75` with no item), `evals/adversarial/spaced-letter-heading.json`, `evals/golden/ba-2003-shallow.json` / `msft-2013-structure.json` / `intc-2002-shallow.json` (`STRICT_SIM` edges + `method`), the five threshold pins listed in §c, `src/sec10k/eval_adapter.py::envelope_shape` on all five `doc_status` paths, `src/sec10k/validate.py::_demo`, `src/sec10k/test_eval_adapter.py::test_envelope_shape`

---

Every finding below is quoted from the gate file, then disposed as exactly one
of **fix-with-case** (the case is named and its red line at `origin/main`
`4cb2128` is copied) or **debt** (a row in `tasks/TODO.md` §Open debt). Gate
after the whole batch: `invariant 42/42 = 1.000`, `fast 84/84 = 1.000`
(`+4 enumerated debt, unscored`), `.eval-baseline.json` untouched.

## a) T5-1 (HIGH, orchestrator-verified) — the document verdict now bounds every item

> "No document-level warning ever moves any item's confidence, so a document
> can say 'we could not resolve this' while every item in it says 95% sure."
> Evidence: `validate.py:213` filters `w['item']==item['item']`, and all three
> `AMBIGUOUS_CODES` are emitted with `item=None`. On `items-stripped`:
> `doc_status='ambiguous'` while the set of extracted-item confidences is
> exactly `{0.95}`.

**Decision.** `score(item, warns, doc_ambiguous)` takes the ladder's verdict as
its one non-item input and clamps with `min(BASE_WEAK if doc_ambiguous else
CEIL, base − 0.15·hits)`. `extract.py` decides `ambiguous` (no extracted item,
or any `AMBIGUOUS_CODES` warning) *before* scoring — the ladder itself is
unchanged, only its position relative to layer 9 moved. Every status is
capped, not just `extracted`: an IBR or omitted claim inside a document the
pipeline could not resolve is not better evidence than a weak-title heading in
one it did.

Why `BASE_WEAK` and not a penalty: the smaller-looking alternative (count the
`item=None` escalating warnings against every item) leaves `jpm-2024` and
`xom-2021` — whose escalating code `last_item_dominates` *is* item-targeted —
exactly where they were, so "`ambiguous` ⇒ no item at 0.95" would still be
false on two of the five ambiguous fixtures. The cap makes it a theorem, and
the theorem is what the case states: `{"type": "confidence", "max": 0.75}`
with no `item` key (the adapter now applies an item-less `confidence` bound to
every item).

**Measured blast radius** (`extract_items` at `4cb2128` vs this branch, all 41
committed fixtures, `evals/report/20260822-164458-all.json` for the scored
view): exactly the five `ambiguous` fixtures move, **100 items** in total —
heading-unnumbered 22 (18 extracted 0.95→0.75, 4 IBR 0.85→0.75),
items-stripped 13 (12 extracted, 1 omitted 0.80→0.75), jpm-2024 23 (21
extracted 0.95→0.75, item 15 0.80→0.75, item 16 omitted 0.80→0.75),
malformed-html 20 (19 extracted, 1 omitted), xom-2021 21 (17 extracted, 3
IBR, item 16 0.80→0.75). No `doc_status`, warning, offset or `normalized_text`
moved on any fixture; 30 of 41 fixtures are byte-identical in every field the
determinism check reads. Missing items (0.40) sit below the cap and are
untouched, so `heading-unnumbered`'s `confidence item 8 = 0.4` pin stands.

**Asserted values that changed, and why each is correct now:**
`jpm-2024-structure` item 15 `0.8 → 0.75` and item 1A `0.95 → 0.75`. Both
sat in a case that in the same breath asserts `doc_status: ambiguous` and
`warning_present last_item_dominates`; a 0.95 on item 1A of that document was
asserting the defect, not a property of the filing. No other committed case
pinned a value on an ambiguous document. Provenance in the case cites this
section.

**Red at main** (cases added, pipeline at `4cb2128`):
`items-stripped-escalation` / `heading-unnumbered` / `malformed-html` /
`xom-2021-shallow`: `item 1 confidence 0.95 > 0.75`; `jpm-2024-structure`:
`item 1 confidence 0.95 > 0.75`, `item 15 confidence 0.8 != 0.75`, `item 1A
confidence 0.95 != 0.75`. Layer echo in `validate._demo` (strict / IBR /
omitted capped, missing untouched).

**T5-4 (MEDIUM), disposed here.** `CEIL` now has a job — it is the cap the
ambiguity rule replaces, and the `min()` binds on 100 items — so it stays as
the "never 1.0" guard ADR-018 §7 already ruled on. `FLOOR = 0.20` is deleted:
reaching it needs four item-targeted hits on a weak item, and
`boundary_hygiene` cannot fire on pipeline output (ADR-016 §2), so the worst a
real item can read is 0.30 (three hits) — the clamp was decorative, as stated.
`_demo` asserts the honest 0.15 on a hand-built four-warning item. ADR-008's
"clamped to [0.20, 0.95]" is amended in place.

## b) T5-2 (HIGH) and SD-1 (HIGH) — the 0.8 cut, measured, and `method` bound to it

> T5-2: "The 0.8 title-similarity cut at `validate.py:203` decides 0.95 vs
> 0.75 for every extracted item in the corpus and has no derivation in any
> ADR… Mutating 0.8 → 0.4 is green."
> SD-1: "`method` is a normative contract enum … that is a hard-coded
> constant … an item accepted at similarity 0.37 still publishes
> 'heading_strict' while validate.score simultaneously pays it BASE_WEAK. No
> eval check reads method."

**The measurement** (2026-08-22, every committed fixture, scratch script over
`extract_items`; 40 fixture directories, 553 `extracted` spans):
`title_similarity` min 0.5, median 1.0, max 1.0; decile histogram
`0.5: 2, 0.7: 3, 0.8: 9, 0.9: 71, 1.0: 468`. Below 0.8 there are exactly five
spans — ba-2003 item 8 (0.5), textron-2001 item 1 (0.593), jnj-2016 item 7
(0.718), ko-1997 item 9 (0.727), msft-2013 item 1A (0.727) — and the next
value up is intc-2002 item 5 at 0.841. Four of the five weak spans are
case-asserted correct extractions (`item_present … extracted`), the fifth
(ko-1997 item 9) is unlabelled; none is a known mis-assignment. So the cut is
an **evidence-strength tier, not a correctness boundary** — it separates
headings whose title matches an era alias closely from headings that merely
clear `SIM_FLOOR` — and 0.8 sits inside the measured empty band **(0.727,
0.841)**. The band midpoint (0.784) would move zero items; 0.8 stays and is
now named `STRICT_SIM` with this derivation at its definition.

**Pins** (both edges, so the mutation the reviewer ran is red in both
directions): `msft-2013-structure` item 1A `confidence 0.75` +
`method heading_lenient` (0.727, top of the weak band); `intc-2002-shallow`
item 5 `confidence 0.95` (already pinned) + `method heading_strict` (0.841,
bottom of the strict band); `ba-2003-shallow` item 8 `confidence 0.75` +
`method heading_lenient` (0.5, the corpus minimum — the `BASE_WEAK` pin the
`vacuous_coverage` list said did not exist). Mutation proof on this branch:
`STRICT_SIM 0.8 → 0.7`: msft-2013-structure RED (`item 1A confidence 0.95 !=
0.75`, `method 'heading_strict' != 'heading_lenient'`); `0.8 → 0.9`:
intc-2002-shallow RED (`item 5 method 'heading_lenient' != 'heading_strict'`,
`confidence 0.75 != 0.95`); `BASE_WEAK 0.75 → 0.7`: ba-2003-shallow RED
(`item 8 confidence 0.7 != 0.75`).

**`method` (SD-1).** `extract.py` now emits `heading_lenient` when
`cand["similarity"] < STRICT_SIM` and `heading_strict` otherwise — the same
constant, so the envelope cannot say "strict" where the score says weak. Six
span items flip on the committed dev corpus (`evals/fixtures`: ba-2003 8,
jnj-2016 7, ko-1997 7 (IBR) and 9, msft-2013 1A, textron-2001 1), nothing
else there; on the held-out set one more flips the same way — cost-2022 item 7,
`heading_strict` → `heading_lenient`, confidence 0.75 unchanged, offsets
identical (PR #32 R3; re-measured 4cb2128 vs 1efc457, 2026-08-23). The contract now
defines the enum (it never had): `heading_strict` — line-anchored heading,
title similarity ≥ `STRICT_SIM`; `heading_lenient` — line-anchored heading,
similarity in `[SIM_FLOOR, STRICT_SIM)`; `status_keyword` — no heading found,
the entry exists because INV-S4 requires every expected item to appear (the
name predates the implementation and is kept for v2 additivity);
`llm_fallback` — declared, never emitted (ADR-020). ADR-007's "method already
carries `heading_lenient` in the contract for that day" (the unbuilt mid-line
candidate tier) is amended in place: that tier, if ever built, takes a new
value via ADR — the enum is extensible by its own text. **Red at main**:
`ba-2003-shallow`: `item 8 method 'heading_strict' != 'heading_lenient'`;
`msft-2013-structure`: `item 1A method 'heading_strict' != 'heading_lenient'`.
The check type that reads `method` already existed (`item_field`, ADR-010 era)
— the finding's "no check reads it" was about usage, not vocabulary; it is
used now, and `envelope_shape` (§f) additionally refuses any value outside the
enum.

## c) `vacuous_coverage` — five thresholds, five measured bands, ten pins

> "UNATTRIBUTED_MAX any value in (0.076,0.4337) green · LAST_ITEM_MAX any
> value in (0.189,0.833) green · MISSING_MAX any value in (0.048,0.381) green
> — can nearly double · SUBSTANTIVE_MIN any value in (209,20000) green ·
> BASE_WEAK any value green — no case pins 0.75"

Re-measured 2026-08-22 over every committed fixture (40 fixture directories;
36 accepted documents, every one span-bearing, carry the fractions), each
threshold is now pinned by the two fixtures that bound its empty band — the
largest value that must stay silent and the smallest that must fire — so the
green band IS the measured band and cannot be widened without a case going
red. Mutation proof (each run on this branch, all cases green at the shipped
value):

| constant | value | measured empty band (low fixture, high fixture) | pins | mutation → red line |
|---|---|---|---|---|
| `UNATTRIBUTED_MAX` | 0.17 | (0.1242 wmt-2010, 0.2646 fy2021-item9c / 0.2648 sandston-2021) | `wmt-2010-shallow` `warning_absent unattributed_content`; `sandston-2021-shallow` `warning_present` | 0.12: wmt RED "12% of the document lies outside every item"; 0.27: sandston RED "expected warning 'unattributed_content', got []" |
| `LAST_ITEM_MAX` | 0.50 | (0.1892 textron-2001, 0.7063 xom-2021) | `textron-2001-structure` `warning_absent last_item_dominates`; `xom-2021-shallow` `warning_present … item 16` | 0.18: textron RED "item 14 is 19% of the document"; 0.71: xom RED "expected warning 'last_item_dominates'" |
| `MISSING_MAX` | 0.25 | (0.20 axp-2008, 0.381 items-stripped) | `axp-2008-combined-heading-burned` `warning_absent expected_items_mostly_missing`; `items-stripped-escalation` `warning_present` (existing) | 0.19: axp RED "4 of 20 expected items (20%) have no heading"; 0.39: items-stripped RED "doc_status 'success_with_warning' != 'ambiguous'" |
| `SUBSTANTIVE_MIN` | 5000 | (930 ko-1997 item 8, 22,955 spans-transposed item 8) | `ko-1997-shallow` `warning_absent keyword_fingerprint item 8`; `spans-transposed` `warning_present` (existing) | 900: ko RED "item 8 contains none of ['total', 'net']"; 23000: spans-transposed RED "expected warning 'numeric_density_inversion', got []" |
| `BASE_WEAK` | 0.75 | — (a base, not a threshold) | `ba-2003-shallow` item 8 `confidence 0.75` | 0.70: ba RED "item 8 confidence 0.7 != 0.75" |

Two findings the re-measurement produced, recorded rather than smoothed over:
**`MISSING_MAX`'s margin is 1.25×, not 5×.** ADR-013 set 0.25 when the worst
real filing lost 0.048; `axp-2008` (burned into the dev set by ADR-020) loses
4 of 20 = 0.20 through its combined Part III heading and must not escalate.
The floor stays — a false `ambiguous` is still the cheaper error — but the
sentence "0.25 still sits 5x above the worst real filing" is dated, and
`validate.py` says so at the constant. **`SUBSTANTIVE_MIN`'s band is
(930, 22955), not a judgment without data.** With the gate lowered to 1 char,
21 would-be warnings fire across 17 fixtures, every one a pointer paragraph
(longest: ko-1997's 930-char Item 8 IBR list); the shortest span a case needs
judged is spans-transposed's 22,955-char Item 8. 5000 sits inside; ADR-008's
"judgment call, not a measured gap" is now "judgment inside a measured band".

## d) T5-3 (MEDIUM) — `boundary_hygiene` reads headings with the real regex

> "boundary_hygiene is structurally dead — it re-applies a copy of the regex
> that produced the offset, over offsets produced by that regex. Its only
> live path is a false positive on 'Item 9 A.'."

ADR-016 §2 already ruled the first half — the check is a layer-consistency
assertion, kept on purpose, and ADR-011 names it as the IBR span's enforcement
— so it is not deleted. The second half was a real defect: `segment.HEADING_RE`
allows an optional space between the item number and its letter (`Item 9 A.`),
the hand copy in `validate.py` (`item\s*9A\b`) did not, so the one heading
shape the two regexes disagreed on was located correctly upstream and then
warned against and docked 0.15 here. Fix: reuse `HEADING_RE` (one import, two
lines) — a copy cannot drift from itself. **Case**:
`evals/adversarial/spaced-letter-heading.json` on a new SELF-CREATED fixture
(sgrp-2019 with one 0x20 byte inserted at raw offset 416348; README row and
`evals/bench.py::SYNTHETIC` updated). **Red at main**: `unexpected warning
'boundary_hygiene': item 9A span does not start with its heading`, `item 9A
confidence 0.8 != 0.95`, `doc_status 'success_with_warning' != 'success'`.
Layer echo added to `_demo`. No committed filing carries the shape as a
heading (cat-2023 has `Item 1 A.` once, mid-sentence), which is why the case
needed a fixture rather than a fixture needing the case.

## e) T5-5 (MEDIUM) — three input classes that disable the battery: debt

> "a 4-5-of-21 missing filing sits under MISSING_MAX with an interior span
> swallowing the rest; an EXEC_OFFICERS_RE clip on a comma-terminated wrap
> truncates item 1 into an interior gap no validator measures; a pre-2005 txt
> filing with no dense contents page disables toc_manifest_mismatch,
> numeric_density_inversion and boundary_hygiene at once."

None of the three is a one-line defect: (1) is the interior-gap / non-last
domination validator that the standing "A non-last span dominating the
document" debt row already names as the correctly-specified successor to the
retired span-coverage row; (2) is ADR-019 §f's deliberate exclusion of orphaned
Executive-Officer content, measured there on seven fixtures; (3) is the absence
of a signal, not a bug — a txt filing without a contents page has no manifest
to cross-check, and `boundary_hygiene` is not in fact disabled by it (it runs
over every span regardless). Building any of them is a new validator under the
freeze → one Debt row, `Origin: gates-2026-08-22 T5-5`, with the
reviewer's sentence verbatim and the existing row it folds into.

## f) SD-2 (MEDIUM) and SD-6 (LOW) — `envelope_shape`

> SD-2: "Contract-mandated envelope fields meta, trace, timings, cost,
> evidence have NO enforcement in the eval vocabulary."
> SD-6: "meta.taxonomy_era and meta.toc_manifest are absent from refusal
> envelopes (set at extract.py:99,103, after both refusal returns); the
> contract's shape block declares them."

New check type `envelope_shape` (`src/sec10k/eval_adapter.py`): the eight
top-level keys present and no undeclared key (ADR-026's optional
`boilerplate` excepted), `doc_status` in its enum, `meta` ⊇ {extractor_version,
input_sha256, format_era, document_selected} on every path and additionally ⊇
{taxonomy_era, toc_manifest} on the three accepted paths, `trace` a list,
`timings.total_ms` and the three `cost` keys present, every warning
`{code,item,message}`, every item carrying all ten contract fields with
`status` and `method` inside their enums, a refusal carrying no items, and
`success` carrying no warnings. Wired on one case per `doc_status` path:
`nvda-2024-shallow` (success), `sandston-2021-shallow` (success_with_warning),
`items-stripped-escalation` (ambiguous), `10q-unsupported` (unsupported),
`truncated-download` (failed). The pipeline already emitted every field, so
these five pass at `4cb2128`'s pipeline — stated plainly; the red is at the
vocabulary: at main's adapter the check does not exist (`unknown check type
'envelope_shape'`), and `test_eval_adapter.py::test_envelope_shape` shows each
mandatory field's deletion, an out-of-enum `method`, a refusal with items and a
`success` with warnings each turning it red. SD-6 is resolved on the contract
side, the smaller honest change: a refused document has no taxonomy era and no
manifest to report, so the shape block now says the two keys are present "on
the non-refusal path", and `envelope_shape` encodes exactly that.

## g) SD-3, SD-4, SD-5, SD-7 — doc corrections, in place, before → after

- **SD-3** ADR-018:116–117 *"The span-coverage validator remains the named
  post-freeze candidate for catching it label-free."* → struck, with the note
  *"retired by ADR-019 §d (2026-08-19): coverage is already measured exactly
  as 1 − unattributed_content's own fraction, and the interior-gap half fires
  7/7 on EXEC_OFFICERS_RE's intentional exclusion; the live successor is the
  'non-last span dominating' debt row"*. ADR-018's header now reads "Amended
  by: ADR-019 (§d), ADR-027"; ADR-019's "Amends" line now names ADR-018 too;
  INDEX.md cross-references both.
- **SD-4** ADR-008, four figures + header, each number reproduced by command:
  *"ship six label-free validators"* (Ruling) → *"seven"* (`grep -c 'warn("'
  src/sec10k/validate.py` → 7; the seventh is `expected_items_mostly_missing`,
  ADR-013); *"Only `toc_manifest_mismatch` and `last_item_dominates` may push
  `doc_status` to `ambiguous`"* → *"three codes"* (`python3 -c "from
  src.sec10k.validate import AMBIGUOUS_CODES; print(len(AMBIGUOUS_CODES))"` →
  3); *"0.55 missing"* → *"0.40"* (`BASE_MISSING` → 0.40, ADR-018); *"The
  scale is uncalibrated"* → measured-with-stated-bias (ADR-018), plus the
  `[0.20, 0.95]` range → "capped at 0.95, or 0.75 under `ambiguous`; no floor"
  (this ADR §a); header "Amended by: ADR-013" → "ADR-013, ADR-018, ADR-027".
  `docs/architecture/overview.md`'s copy of the same paragraph gets a one-line
  pointer to the two amendments rather than a rewrite.
- **SD-5** `validate.py:111-113` *"everything outside every item"* → *"the
  preamble (before the first span) plus the tail (after the last), NOT every
  gap: interior gaps between spans are not counted"* with ADR-019 §d's 9.7-
  point figure; ADR-008:23 *"outside every item"* → *"before the first span /
  after the last"* with the same note.
- **SD-7** contract example *`{"code": "lenient_match", "message": "...",
  "item": "7A"}`* → *`{"code": "keyword_fingerprint", "message": "...",
  "item": "1A"}`*, a code a path actually produces (ADR-016's table).
- The `validate.py` docstring *"Thresholds are measured, never assumed"* — the
  headline drift — now says what is true: every threshold states its measured
  basis or names itself a judgment call, and each is pinned inside its band.

## h) ADR-018's instrument, re-run — and why the report is not re-published

The instrument is `python3 -m evals.metrics <--suite all report>` (metric 8
v2). **It could not be re-run at `4cb2128`**: every `--suite all` report since
the UI cases landed carries `repo_hygiene` rows whose `failures` are plain
strings, and the case-join read `f["check"]` on them → `TypeError: string
indices must be integers, not 'str'` at `evals/metrics.py:77`. Fixed here
(`_check_failures` skips non-dict failures, used at all three joins), watched
red first in `--self-check` with a string-failures row. Three tables, all
produced by the fixed instrument:

```
ADR-018 as published (2026-08-18, 20260818-130421-all.json, T9 population):
  0.95 n=162 · 0.85 n=66 · 0.8 n=8 · 0.75 n=14 · 0.65 n=1 · 0.4 n=2   debt: 0.95 1/1, 0.75 1/1
Today at main (20260822-162324-all.json, sha 4cb2128, main's case files):
  0.95 n=203 · 0.85 n=83 · 0.8 n=8 · 0.75 n=7  · 0.65 n=1 · 0.4 n=2   debt: 0.95 5/5, 0.4 4/4
After this ADR (20260822-164458-all.json, this branch's case files):
  0.95 n=184 · 0.85 n=83 · 0.8 n=5 · 0.75 n=31 · 0.65 n=1 · 0.4 n=2   debt: 0.95 5/5, 0.4 4/4
```

The "today at main" 0.95 n=203 reproduces only by joining that report against
4cb2128's case files; the committed instrument on the committed report at any
later tree gives n=204 (`python3 -m evals.metrics
evals/report/20260822-162324-all.json` → `conf=0.95 n_targeted=204`), the +1
being `ko-1997-shallow`'s item-8 pin that this PR added — all other rows
83/8/7/1/2 and debt 5/5, 4/4 identical either way (PR #32 R2, noted 2026-08-23,
L1). Deltas main → after: 0.95 −19, 0.8 −3, 0.75 +24, population 304 → 306. The
+2 are the two newly item-targeted pairs (`ko-1997-shallow` item 8 via its
`warning_absent … item 8`, and `spaced-letter-heading` item 9A), both at
0.95 — so the 0.95 row is −21 targeted items capped in the five ambiguous
fixtures, +2 new; the 0.8 row's −3 are jpm-2024 item 15, xom-2021 item 16
and jpm-2024's omitted item 16; and 0.75's +24 is those 21 + 3. `failed` stays 0 on every scored row — the population
moved, the upper-bound reading did not. The debt-channel rows are unchanged
(ba-2003 items are not in an ambiguous document). The `ADR-018 as published`
row already differed from today's main before this ADR touched anything (T9→
now added cases), so the published table is a dated record of its own
population; rewriting `docs/analysis-report.md` §"Confidence calibration —
before and after" would be a v3 re-publication of a document this PR does not
otherwise touch — recorded as debt with the three tables above so the next
report pass has the numbers, not a hand-edit.

*(Re-published 2026-08-23, D2: `docs/analysis-report.md` §"Confidence
calibration — before and after" now carries the table as **v3**, pasted
verbatim from `python3 -m evals.metrics evals/report/20260823-185915-all.json`
(97 cases, `ba263ee`, merged tree) — 184 / 83 / 5 / 31 / 1 / 2, debt 5/5 and
4/4, `failed` 0 on every scored row: identical to the "After this ADR" table
above. ADR-021 §g has the re-publication record.)*

## Consequences

- `extractor_version` → `0.7.0-t5d`: item confidence in ambiguous documents
  and `method` on weak-title headings are not comparable across the bump.
- Metric 6's coverage moves (capped items fall under `CONFIDENT = 0.8`): the
  after-report reads `n=272` confident targeted items, 646 unaudited — the
  metric's own note prints the counts; nothing is hidden by the cap.
- `method` now carries information: an inspector reading `heading_lenient`
  knows the title matched weakly before it reads the score.
- Debt rows added: T5-5 (three input classes), and the calibration table
  re-publication with the deltas above. Everything else in the twelve is fixed
  with a case in the gate suites.
