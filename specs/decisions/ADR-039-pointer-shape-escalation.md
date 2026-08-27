# ADR-039 — D16: an internal-pointer item in a mostly-unplaced document warns at the item that carries it

Date: 2026-08-28. Status: accepted. Implements D16 (TD-5, promoted
2026-08-28). Sanctioned exception to the T8 feature freeze on the
ADR-020/026/029/030/031/035 pattern — §a runs the three tests. Amends
[ADR-035](ADR-035-item-level-escalation.md) (a second item-level escalation
code, reaching the item codes `SPAN_FLOOR` structurally cannot — dated note in
its §c), [ADR-038](ADR-038-internal-pointer-adjudication.md) (its §f row 1
fires: the named instrument goes green and the three `defect` verdicts become
`correct` in that table's own terms — dated note in that row),
[ADR-008](ADR-008-validation-battery.md) (validator count 10 → 11, in place)
and [ADR-016](ADR-016-validator-provability.md) (its warning-code table gains
one row). Does **not** amend ADR-004 (no `status` changes anywhere — the
external-document exclusion is aligned with `segment.EXTERNAL_DOC_RE`, which
is ADR-004's own instrument), ADR-005, or ADR-027 §c (`vacuous_coverage`
stays closed: `SPAN_FLOOR`'s item set is untouched and no length floor is
widened — §b3 is the argument). TD-12 (internal-pointer RESOLUTION) stays
open and declined; nothing here resolves a page reference.

**Ruling**: one new layer-8 validator, `internal_pointer_unreached`, fires on an `extracted` item exactly when all three prongs hold: **(1) shape** — the body (span minus its heading line) matches `INTERNAL_PTR_RE` (a page/index locator: `pages? <digit>`, `FS-<digit>`, `see index`), does NOT match `segment.EXTERNAL_DOC_RE` (proxy statement / annual report to holders — ADR-004 shape 1 territory), and is at most `PTR_BODY_MAX = 1200` chars; **(2) silence** — no warning already carries this item's code and no `AMBIGUOUS_CODES` warning fired on the document (ADR-038 R3's "already said it" bullet); **(3) unreached proxy** — the placed fraction `coverage(text, items)` is below `PTR_COVERAGE_MIN = 0.60`, so a large region of the document lies outside every span and an internal pointer's target is plausibly in it. The warning carries the item code, so the EXISTING `WARN_PENALTY` takes the item 0.95 → 0.80 and `review_required` derives true — `score()` and the `review_required` derivation are untouched. The code does NOT join `AMBIGUOUS_CODES` and changes no `status`. Deterministic, stdlib-only, $0, offline.
**Because**: ADR-038 rules `cvx-2015` items 2, 6 and 7A `defect` at the escalation layer — internal page pointers published at 0.95 with `review_required: false` while their targets sit in the 294,291-char region outside every span — and no warning could carry their codes: `item_span_near_empty` reaches items 1/7/8 only, "a discriminator that cannot discriminate" (`tasks/reviews/d13-auditor-verdicts.md` §2.2), and TD-5's measured counter-evidence forbids widening `SPAN_FLOOR`'s item set (items 1A/7A/1B/4/6/9/9B/9C/16 are legitimately one sentence) while length alone cannot discriminate (item 7A is 453 chars, longer than several correctly-flagged items). The trigger is the pointer SHAPE plus the unplaced mass, and both bands are measured with both edges pinned (§c).
**Enforced by**: `evals/adversarial/cvx-2015-silent-pointer-items.json` (PROMOTED `debt` → `fast`+`invariant`, the instrument ADR-038 §f row 1 names; red-first record `tasks/reviews/d16-red-first.txt`), `evals/golden/bac-2006-shallow.json` (coverage-band high edge, `warning_absent` ×3), `evals/adversarial/ge-1994-oldformat.json` (external-document exclusion, `warning_absent` item 6), `evals/golden/ibm-1997-shallow.json` (its existing `confidence item 12 = 0.95` pin — see §c4), `src/sec10k/validate.py::_demo` (layer echo, all three prongs), the census instrument `tasks/reviews/d16_census.py` + `tasks/reviews/d16-census.txt`, mutation transcript `tasks/reviews/d16-threshold-mutations.txt`, snapshot enumeration `tasks/reviews/d16-snapshot-diff.txt`.

---

## a) Why this is a sanctioned exception and not scope creep

The three tests ADR-026 §a set and ADR-030/031/035 §a re-ran:

1. **The human asked for it in writing, on the record.** The D16 row of
   `tasks/TODO.md` (TD-5, promoted 2026-08-28) demands "a deterministic, $0,
   offline pointer-SHAPE validator that fires a warning carrying the item's
   code", with its own ADR as a sanctioned freeze exception. This is that ADR.
2. **The post-freeze pattern is followed: a written ruling with its cost
   named.** ADR-038 §f row 1 named this exact build as the instrument that
   overturns its three `defect` verdicts — the reopener was designed before
   the capability, and this ADR is the capability answering it.
3. **What it changes on committed filings is small, enumerated and argued.**
   §e is the measured blast radius: across 62 dev + 6 held-out documents,
   exactly ONE filing changes in any field `evals/snapshot.py` reads —
   `cvx-2015`, items 2/6/7A, warnings + confidence only. No span, `status`,
   `method`, `heading_text`, `normalized_text` or `doc_status` moves anywhere.

## b) The rule, stated before it is applied

The check is ADR-038 §b's rule made executable to the extent a $0
deterministic layer can, prong by prong. What each prong approximates, and
what it deliberately does not claim, is stated here so §c's census is read
against the right standard.

### b1. Prong 1 — shape (ADR-038 R1, approximated)

R1's class gate is: pointer-only body, naming a locatable position, inside
the filed document. The deterministic proxy is three regex/length tests on
the body (the span minus its heading line, the same slice
`tasks/reviews/d9_class_scan.py` and `d13_span_dump.py` read):

- `INTERNAL_PTR_RE` = `(?i)\b(?:on\s+)?pages?\s+(?:FS-)?\d|\bFS-\d|\bsee\s+index\b`
  — `d9_class_scan.py`'s `PAGE_PTR`, verbatim. It requires a *position*, so
  `nvda-2024` item 8 ("set forth in our Consolidated Financial Statements …
  included in this Annual Report on Form 10-K" — no page, no index) does not
  match, which is R1 prong 2's rejection of that item (ADR-038 §c6)
  reproduced mechanically.
- NOT `segment.EXTERNAL_DOC_RE` — the pipeline's own external-document
  recogniser (proxy statement, information statement, annual report to
  share/stock/security holders/owners). A body naming one is ADR-004 shape 1
  territory whatever else it names; this keeps every proxy-pointer and
  ARS-pointer body out (R1 prong 3). Reusing the constant means the two
  layers cannot drift apart on what "a different document" is.
- body ≤ `PTR_BODY_MAX = 1200` chars — the stand-in for "pointer-only".
  A pointer-only body is necessarily short; a substantive body that merely
  *mentions* a page (`cvx-2015` item 1, 82,890 chars, references the same
  FS tables item 2 points at) is not in class. §c2 measures the band.

**What prong 1 is not.** It is not ADR-038 §e3's kind test ("does the
sentence dispose of any part of what the item requires, on its own") — that
test is adjudicated by hand and stays non-executable, exactly as ADR-038 §g6
records. §c2 discloses the consequence: corpus-wide, body length alone does
NOT separate pointer-only from mixed bodies (`ba-2003` item 5's mixed body is
508 chars, *shorter* than `cvx-2015` item 2's 515-char pointer-only body).
The conjunction with prong 3 is what carries that separation on the measured
corpus, and §f row 2 names the input that would break it.

### b2. Prong 2 — silence (ADR-038 R3, second bullet)

"An item already carrying an item-level warning, or capped by an `ambiguous`
document verdict, has already said it." Executable at `validate()` time as:
skip any item whose code some warning in the list already carries, and skip
the whole check when any `AMBIGUOUS_CODES` warning is present (the document
verdict that caps every item at 0.75 — ADR-027 §a — is decided from exactly
that membership, four lines later in `extract.py`). This is what keeps
`cvx-2015` 7/8, `ge-1994` 8, `spatz-2014` 8 (already at 0.80 under
`item_span_near_empty` — their confidence must not move, and does not) and
`jpm-2024` 1C/7/7A/8 + `xom-2021` 7/7A/15 (`ambiguous` documents) out, with
their current outputs untouched.

### b3. Prong 3 — unreached, by proxy (ADR-038 R3, first vs second branch)

The rule's honest limit: a $0 layer cannot resolve "page FS-60" (that is
TD-12, declined). What it can measure is the mass of `normalized_text`
outside every span, which `coverage()` already computes (ADR-035 §d): if
(almost) nothing lies outside any span, the pointed-at content is necessarily
inside some span and the envelope holds the answer — ADR-038's `bac-2006`
ground (§c4: coverage 0.9285, every target inside another item's span) and
its `xom-2021` ground (0.9799). If a large region lies outside, an internal
pointer's target is plausibly unreached — the `cvx-2015` ground (0.2718, all
three targets measured outside every span). The FRACTION is the right
measure, not the absolute count: `bac-2006`'s outside region is ~50K chars —
more than double `spatz-2014`'s entire 17K tail — yet `bac-2006` is the
must-NOT-fire filing, so an absolute threshold cannot order the corpus and a
fractional one does. §c3 measures the band.

**Why the fraction is document-level and the warning item-level.** This is
ADR-038 §g8's scope choice inherited, not resolved: "is the target reached"
is asked document-wide (via coverage), the honesty fix is item-level (via the
warning). §d1 states what that leaves unanswered.

### b4. What fires, mechanically

`internal_pointer_unreached`, carrying `item=<code>`. It enters `score()`'s
existing `hits` list — 0.95 − `WARN_PENALTY` = 0.80 — and `review_required`
derives true from the same list, "so the two can never disagree"
(`specs/001-sec10k-contract.md`). Not in `AMBIGUOUS_CODES`, on ADR-035 §c's
own argument re-applied: one pointer item is a fact about that item, not a
verdict on the document, and the three filings this could ever escalate are
already `success_with_warning` or better for other reasons; `item_span_near_empty`
is the precedent and this code is its exact peer. No `status` moves: ADR-004
shape 2 stands re-affirmed, and the D16 row's Out-of-scope forbids it.

## c) The measurement

Instrument: `tasks/reviews/d16_census.py` — every dev + held-out fixture
through `extract_items` with default flags, every `extracted` item whose body
matches `INTERNAL_PTR_RE` printed with body length, `meta.coverage`, external
match, item-level-warning state, document-escalation state, and the prong-by-
prong verdict. Committed output: `tasks/reviews/d16-census.txt`. Every figure
below is printed by that script; none is retyped.

### c1. The candidate population

50 documents (44 dev fixtures + 6 held-out, derivatives included); 104
extracted spans corpus-wide have a body matching `INTERNAL_PTR_RE`. All but
three are excluded by a single named prong: 37 name an external document
(`EXTERNAL_DOC_RE`), 24 sit on escalating documents (`intc-2025`,
`jpm-2024`, `xom-2021`), 8 already carry an item-level warning, 27 are
substantive bodies over `PTR_BODY_MAX` (running to 333,846 chars — text that
mentions a page), and 5 are short pointer-shaped bodies on documents at or
above `PTR_COVERAGE_MIN` (`bac-2006` 3/6/7A, `intc-2002` 5, `ba-2003` 5).
The census prints every row with its excluding prong; §c2/§c3 walk the
contested ground.

### c2. `PTR_BODY_MAX` — the band, and its honest scope

Population: items passing every OTHER prong (extracted, locator match, no
external name, silent, non-ambiguous document, coverage < 0.60). Their body
lengths, dev + held-out:

| chars | fixture · item | disposition |
|---|---|---|
| 87 | cvx-2015 · 6 | pointer-only — ADR-038 `defect`, must fire |
| 385 | cvx-2015 · 7A | pointer-only — ADR-038 `defect`, must fire |
| 515 | cvx-2015 · 2 | pointer-only — ADR-038 `defect`, must fire |
| 1,814 | cvx-2015 · 5 | substantive Part II answer that cites pages — must not |
| 1,819 | cvx-2015 · 15 | exhibit list — must not |
| 1,895 | cvx-2015 · 9A | controls prose citing a page — must not |
| 2,402 | cvx-2015 · 3 | legal proceedings prose — must not |
| 9,703 | ibm-1997 · 1 (+ its `ibr-security-holders` derivative) | substantive — must not |
| 14,382 / 82,890 | cvx-2015 · 1A / 1 | substantive — must not |
| 17,186 | ge-1994 · 3 (+ its `ibr-pointer-first` derivative) | substantive — must not |

**Band (515, 1,814), midpoint 1,164.5 → `PTR_BODY_MAX = 1200`**, two
significant figures, the `SPAN_FLOOR` convention. Margins: **2.33×** above
the largest must-fire body and **1.51×** below the smallest must-not.

**The disclosure this band owes.** Measured corpus-WIDE — ignoring prong 3 —
the populations overlap and no such band exists: `ba-2003` item 5 (coverage
0.9849) is a mixed body of 508 chars, *below* `cvx-2015` item 2's 515, and
`intc-2002` item 5 (0.9545) is 567, inside what would be the fire range. Both
are ADR-034 §b3's own prong-1 rejections — bodies with substantive standalone
content — and no length constant separates them from the three defects. They
are excluded by prong 3 (their documents place ~95%+ of themselves), not by
this constant. So `PTR_BODY_MAX` is a band *within the sub-`PTR_COVERAGE_MIN`
population*, where the split is clean and wide, and is NOT presented as a
pointer-only discriminator at large. A pointer-only body over 1,200 chars in
a low-coverage filing would be missed; §f row 2 carries that as the reopener.

### c3. `PTR_COVERAGE_MIN` — the band

Population: documents carrying at least one item that passes prongs 1 and 2
(shape + silence, body ≤ 1200). Their coverages:

| coverage | fixture | items | disposition |
|---|---|---|---|
| 0.2718 | cvx-2015 | 2, 6, 7A | ADR-038 `defect` ×3 — must fire |
| 0.9285 | bac-2006 | 3, 6, 7A | ADR-038 `correct` (§c4, targets inside other spans) — must not |
| 0.9545 | intc-2002 | 5 | ADR-034 §b3 rejection (holders count) — must not |
| 0.9849 | ba-2003 | 5 | ADR-034 §b3 rejection — must not |

**Band (0.2718, 0.9285), midpoint 0.6002 → `PTR_COVERAGE_MIN = 0.60`**, two
significant figures. Margins: **2.21×** above the fire edge and **1.55×**
below the no-fire edge. The band is wide because the corpus is bimodal on
exactly the property ADR-038 R3 turns on: filings whose internal pointers
point at *placed* content place nearly everything (0.9285+), and the one
filing whose pointers point at *unplaced* content places 27%. No committed
document, dev or held-out, sits between 0.2718 and 0.9285 while carrying a
prong-1-passing silent item. Documents that sit in the range on coverage
alone (`tgt-2002` 0.561, `ibm-1997` 0.4692, `wfc-2008` 0.6668, `ko-1997`
0.734, `spatz-2014` 0.6632, `mrk-1995` 0.7593 held-out) carry no such item —
every candidate they have is external-named, already-warned, or a substantive
body over the cap — and the census prints each one's exclusion.

Both edges are pinned by committed cases: the fire edge by
`cvx-2015-silent-pointer-items.json` (`warning_present` ×3, promoted to
`fast`+`invariant`), the no-fire edge by `bac-2006-shallow.json`
(`warning_absent` ×3 on items 3/6/7A). `evals/golden/bac-2006-images.json`'s
exact-`success` pin already made ANY fire on `bac-2006` red doc-wide; the
named per-item pins are added so a mutation failure names the constant's
edge, not just a collateral doc_status flip — both are quoted red in
`tasks/reviews/d16-threshold-mutations.txt`. Interior points (`intc-2002`,
`ba-2003`) are not separately pinned: bands are pinned at edges (ADR-035 §i
convention), and both already carry `confidence`/`doc_status` pins that a
fire would break.

### c4. The exclusion pins

- **External document** (R1 prong 3): `ge-1994` item 6 — "appearing on page
  43 of the Annual Report to Share Owners", body 408 chars, coverage 0.2306,
  silent at 0.95. It passes prong 2, prong 3 and both other prong-1 tests;
  the `EXTERNAL_DOC_RE` exclusion is the ONLY thing keeping it out, which
  makes it the sharpest committed pin the exclusion can have —
  `warning_absent` added to `evals/adversarial/ge-1994-oldformat.json`.
  (Whether its `extracted` status is itself right is TD-150's open ADR-004
  question, widened by ADR-038 §e4; this ADR inherits and does not touch it.)
- **Proxy pointer**: `ibm-1997` item 12 (body 386 chars, proxy-statement
  pointer, coverage 0.4692 — in range on every axis but the external name).
  `evals/golden/ibm-1997-shallow.json` already pins `confidence item 12 =
  0.95`, which a fire would move to 0.80, so the no-fire is already
  case-bound and no duplicate check is added — recorded here instead of
  duplicated, per the D16 spec's own instruction.
- **No locatable position**: `nvda-2024` item 8 never matches
  `INTERNAL_PTR_RE`; `evals/golden/nvda-2024-shallow.json`'s existing
  `item_span_near_empty`-era pins (confidence 0.80, `review_required` true
  from THAT code alone) hold unchanged, and the census prints the non-match.

### c5. The fire census — the whole of it

Over all 62 dev + 6 held-out documents, `internal_pointer_unreached` fires on
**exactly three items in one filing: `cvx-2015` items 2, 6 and 7A** — the
three ADR-038 rules `defect`, no more, no fewer, dev and held-out. The
committed census prints every candidate and its excluding prong; there is no
unexplained fire and no explained-away miss. `spatz-2014` item 15 — the live
possibility the D16 spec names — does not fire on prong 1: its body ("as
referenced in Item 8 hereof") names an item, not a page or index, so it never
enters the class; it is the same no-position shape as `nvda-2024` 8 one hop
shorter, and its two-hop cycle with item 8 stays where ADR-038 §c5 left it
(TD-157, untouched).

## d) What this ADR does not establish

1. **The `bac-2006` §d3 objection is answered only partially, and the
   partial part is stated.** The blind auditor's confidence objection had two
   instances: `cvx-2015` 2/6/7A and `bac-2006` 3/6/7A, both "0.95 with
   `review_required: false` on an envelope with no warning carrying them".
   This ADR closes the first three. The `bac-2006` three remain published at
   0.95, `review_required: false`, on a `doc_status: success` envelope —
   deliberately: prong 3 is ADR-038's document-wide scope choice (§g8) as a
   threshold, and on a 0.9285-coverage document the envelope holds the
   answer. The item-scoped reading — a per-item consumer cannot see that
   Item 6's answer was filed under Item 7 — is NOT refuted here, and ADR-038
   §f row 3 (demonstrated consumer-visible harm) remains the live reopener
   for it. What this ADR adds to that standing disagreement is only
   mechanism: if that row ever fires, the check built here reaches those
   items by lowering one measured constant, not by new capability.
2. **Prong 1 is a proxy, not ADR-038's rule.** The kind test stays
   non-executable (§b1); `INTERNAL_PTR_RE` is `d9_class_scan.py`'s page-digit
   shape plus `see index`, so a titled-section pointer with no page number
   ("the section entitled X of this report") does not match — on the
   committed corpus every such body sits on an `ambiguous` document
   (`xom-2021`) and prong 2 makes the miss moot, but that is a fact about
   this corpus, not the regex.
3. **The bands generalize by assertion, not measurement.** Both constants are
   dev-pinned (`cvx-2015`, `bac-2006`); the held-out set contributes only
   no-fire confirmations (census). A held-out filing placing 70% of itself
   with a silent internal pointer would not fire, and whether it should is
   exactly the adjudication ADR-038 §g5 already says has never been done on
   held-out data.
4. **No claim that a fired item is wrong.** As with `item_span_near_empty`
   (ADR-035 §j), the warning asserts a review flag: the body is an internal
   pointer and most of the document is unplaced. The strong claim — the
   target is outside every span — was made item by item in ADR-038 §c on
   hand-adjudicated anchor evidence, and this check inherits its verdicts
   without re-deriving them.

## e) Blast radius — `origin/main` (`0b87705`) vs this branch

Instrument: `python3 evals/snapshot.py <tree> <out>` over both trees
(origin/main materialised with `git archive | tar -x` into a scratch
directory), 62 dev + 6 held-out files, plus a field-by-field diff committed
at `tasks/reviews/d16-snapshot-diff.txt`. origin/main advanced past this
branch's base during the work (`b04068a` → `0b87705`, the D14 merge — a
web-UI keyboard-focus change whose only snapshot-visible effect is its own
edit to the `repo_hygiene/boilerplate-wire-values.html` fixture), so main
was merged into `task/D16` and the committed comparison is merged tree vs
`0b87705`: the D14 fixture then reads identical from both sides and every
remaining difference is this ADR's own.

- **Held-out: byte-identical**, both files hash equal (`d16-snapshot-diff.txt`
  prints the shas).
- **Dev: exactly one document differs — `cvx-2015/filing.htm`**, and within
  it exactly: `warnings` gains three `internal_pointer_unreached` entries
  (items 2, 6, 7A) and those three items' `confidence` reads 0.80 where it
  read 0.95. Every other field of every other item — and every `start`,
  `end`, `status`, `method`, `heading_text`, `norm_chars`, normalized-text
  sha and `doc_status` on every document including `cvx-2015` — is
  byte-identical. (`review_required` moves false → true on the same three
  items; snapshot's `FIELDS` does not read it, and the promoted case pins it
  by value.)
- `doc_status` moves NOWHERE: `cvx-2015` was already `success_with_warning`.

## f) What would overturn this ruling

| what is overturned | what overturns it | instrument | threshold |
|---|---|---|---|
| `PTR_COVERAGE_MIN = 0.60` | a filing adjudicated under ADR-038 §b whose in-class silent pointer items are `correct` at coverage below 0.60, or `defect` above it — either forces re-measuring the band | a new fixture + an ADR-038-rule adjudication with the anchor method | one filing |
| `PTR_BODY_MAX = 1200` / prong 1 | a pointer-only body over 1,200 chars, or a substantive body at or under 515, in a sub-0.60-coverage filing — the clean split in §c2 breaks | `tasks/reviews/d16_census.py` over the new fixture | one body |
| the external exclusion | `EXTERNAL_DOC_RE` mis-sorts a body — an internal pointer it matches, or an external-document pointer it misses that then fires | `evals/adversarial/ge-1994-oldformat.json`'s pin, or a new fixture | one mis-sort |
| the silence prong | an item whose existing warning is shown NOT to have "already said it" for a consumer — i.e. ADR-038's R3 second bullet is itself overturned | that is ADR-038 §f's second row, inherited, not this ADR's own | — |
| the whole check | `internal_pointer_resolution` ships (TD-12): a resolved span moves the content inside the item and the pointer shape stops being a defect signal | a TD-12 ADR | that ADR |

**Explicitly not sufficient**: `cvx-2015-internal-pointer.json` still being
red — its `min_chars` checks encode the TD-12 capability outcome on items
7/8 and this ADR is (correctly) invisible to them; the assertions are not
touched, per D16's Out-of-scope and TD-156.

## g) Threshold pins and the red line

| constant | value | measured empty band (low, high) | pins | mutation → red line |
|---|---|---|---|---|
| `PTR_COVERAGE_MIN` | 0.60 | (0.2718 cvx-2015, 0.9285 bac-2006) | `cvx-2015-silent-pointer-items` `warning_present` ×3; `bac-2006-shallow` `warning_absent` ×3 | **0.25**: cvx case RED (`expected warning 'internal_pointer_unreached'` ×3, `review_required False != True` ×3); **0.95**: bac-2006-shallow RED (`unexpected warning` ×3) + `bac-2006-images` RED (`doc_status 'success_with_warning' != 'success'`) |
| `PTR_BODY_MAX` | 1200 | (515 cvx item 2, 1,814 cvx item 5) | fire edge: the same `warning_present item 2`; no-fire edge: `cvx-2015-silent-pointer-items` `warning_absent item 5` | **500**: cvx case RED (item 2's checks); **1900**: cvx case RED (`unexpected warning … item 5`) |
| escalation policy | code ∉ `AMBIGUOUS_CODES` | — | `cvx-2015-shallow` `doc_status in [success, success_with_warning]`; `validate._demo` assert | adding it → cvx-2015-shallow RED (`doc_status 'ambiguous' not in [...]`), cvx-2015-silent-pointer-items RED ×3 (`confidence 0.75 != 0.8` — ADR-027 §a's cap replaces the penalty), `_demo` assert fires |
| the external exclusion | clause present | — | `ge-1994-oldformat` `warning_absent item 6`; `ibm-1997-shallow` `confidence item 12 = 0.95` | deleting the `EXTERNAL_DOC_RE` clause → ge-1994-oldformat RED (`unexpected warning … item 6`), ibm-1997-shallow RED (`item 12 confidence 0.8 != 0.95`) |

Full transcript: `tasks/reviews/d16-threshold-mutations.txt`.

**Red-first.** `evals/adversarial/cvx-2015-silent-pointer-items.json` was
already red as `debt` (watched at its authoring, ADR-038's Enforced-by). For
this ADR it was promoted to the scored suites and extended (three
`warning_present`, three `confidence 0.8`, two `warning_absent`) and the
scored red was watched BEFORE the validator existed: invariant 81/82, fast
144/145, the failing checks being exactly the three `item_field`, three
`warning_present` and three `confidence` assertions, with every hygiene and
`warning_absent` check passing. Record with sha:
`tasks/reviews/d16-red-first.txt`.

## Verification

- `python3 -m evals.run --suite invariant` — 82/82 = 1.000 (+4 enumerated
  debt, unscored).
- `python3 -m evals.run --suite fast` — 145/145 = 1.000, `.eval-baseline.json`
  untouched (`{"fast": 1.0}`, matches). No `--update-baseline`, no
  `--no-verify`.
- `python3 -m src.sec10k.validate` — self-check ok, including the four new
  ADR-039 assertions (fire; external no-fire; high-coverage no-fire;
  already-warned no-fire, no double penalty).
- `python3 tasks/reviews/d16_census.py` — regenerates every figure in §c;
  committed at `tasks/reviews/d16-census.txt`.
- `python3 evals/snapshot.py` over both trees + the diff enumeration — §e;
  committed at `tasks/reviews/d16-snapshot-diff.txt`.
