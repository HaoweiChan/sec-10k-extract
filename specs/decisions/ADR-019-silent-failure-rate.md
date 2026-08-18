# ADR-019 — T11: the silent-failure rate, measured, and three rulings it forced

Date: 2026-08-19. Status: accepted. Implements T11/A3. Amends ADR-015 §5 (the
mis-specified span-coverage debt row) and ADR-004 (records, does not resolve,
a standing disagreement over `cvx-2015` item 6). Ships the Executive-Officers
boundary fix (`src/sec10k/segment.py`, `EXEC_OFFICERS_RE`).

## a) The definition, and why metric 6 could not measure it

A **silent failure** is an item reported at confidence ≥ 0.8, inside a
document the pipeline called `success`/`success_with_warning`, whose
extraction is wrong when judged against the filing by an instrument the
pipeline does not control.

`evals/metrics.py`'s metric 6 has always read **0.0**. This is not evidence of
correctness — it is a property of what the metric counts. Its denominator is
items a *declared eval check* targets, and the pre-commit gate requires every
scored check to pass before a commit lands. A check that could fail and
doesn't gets fixed or removed; a check that structurally can't fail (four of
them, ADR-016) inflates the pass rate without adding evidence. Metric 6 reads
0.0 **by construction**: it measures whether the gate is green, not whether
the pipeline is right. Of 781 confident items in the T10-era report, 447 were
targeted by no check at all — the metric's own denominator excludes the
majority of what it would need to see to say anything. T11 exists to look at
those 447 directly, by an instrument the gate does not control.

## b) The measured rate, with its method

**Sampled rate: 1 WRONG / 30 adjudicated = 3.3%**, 95% Clopper-Pearson CI
**[0.1%, 17.2%]**. Population 447 (confidence ≥ 0.8, inside a
`success`/`success_with_warning` doc, targeted by no existing check); sample
drawn with `random.Random(11).sample(population, 30)`, seed recorded in
`docs/evals/audits/2026-08-19-t11-silent-failure-sample.md` so the draw is
reproducible and cannot have been cherry-picked after the fact; adjudicated
blind by the extraction-auditor, reading each span against the fixture with no
access to this ADR's reasoning. The interval was re-derived for this ADR
(stdlib `math.comb`, no scipy in this environment) and matches the audit's
figures to the reported precision.

Applied to the population: **~15 items** (447 × 1/30), CI **[0, 77]** (447 ×
[0.1%, 17.2%], rounded).

`docs/evals/evaluation-strategy.md` set an aspirational target of < 5% before
any data existed. **Ruling: the point estimate meets it, the CI upper bound of
17.2% means the target is not demonstrated, only not contradicted.** n=30 is
small, and a population of 447 with one confirmed defect does not license a
tighter claim than the interval already states. The honest statement is the
interval, not the point — the same discipline ADR-018 applied to calibration.

**Sensitivity.** The rate is 1/30 under the extraction-auditor's reading and
**2/30 (6.7%)** under mine. The single item of difference is `cvx-2015` item
6 (`"Item 6. Selected Financial Data ... presented on page FS-60."`, 111
chars, an internal pointer to a paginated section with the real data in the
document's tail). The auditor ruled it CORRECT — the pointer sentence is the
entirety of what the filing labels under this heading, so there is nothing
else to report as wrong at the single-item level `classify()` operates at.
I read it as the same shape as items 7 and 8 in the same filing (§e), which
the auditor never adjudicated (outside its 30-case sample) and which I read as
WRONG. Both readings are published, not adjudicated to a single number here —
see §e for why this stays a standing disagreement rather than a ruling.

**Screen (stdlib oracle, `evals/oracle.py`):** 107/521 confident items flagged
across four independent-of-the-pipeline signals (coverage floor, short-span
floor, an independent heading locator, missing-but-located). Net **zero** new
confirmed silent failures; the one real defect it catches (`ba-2003` items
11/13) was already known and enumerated as debt before this milestone. Two of
the four signals (coverage, largest interior gap) turned out to be
algebraically redundant with the existing `unattributed_content` validator —
verified, not assumed, by direct computation against all 36 fixtures, 0
mismatches. This is a screen, not an estimate: it says four cheap heuristics
disagree with the pipeline on a fifth of confident items on this specific,
adversarially curated corpus, and 58 of 60 short-span flags and all 48 of the
coverage flags were traced by hand to a legitimate, already-disclosed cause.

**Correction (2026-08-19, post-commit review) — 107/521 was measured
PRE-fix.** At head, `evals/report/20260819-014559-oracle.json` (committed)
and a fresh run both read **224/521 = 0.4299** confident items flagged —
this matches the artifact's own `screened_rate` field. Excluding the
self-induced `large_interior_gap` check (§d's correction: it now fires on
the 7 EO-clip fixtures by design, not defect) leaves **110** distinct
confident items still flagged by some other check — up from the pre-fix 107
(re-derived directly, not estimated: simulating the pre-fix state by making
`EXEC_OFFICERS_RE` never match reproduces 107/521 exactly). The +3 is all in
`short_span` (58 pre-fix → 61 post-fix); `low_span_coverage` (48) and
`heading_divergence` (8) are unchanged — the EO clip shortened a handful of
spans on the 7 fixtures enough to cross `SHORT_SPAN_FLOOR` where they didn't
before, the same self-induced mechanism as the gap check, just on a
different signal. The complementary count is **114**: the number of
confident items whose *only* firing check is `large_interior_gap`
(224 − 110 = 114, and 114 + the 3 new `short_span` flags = 117, the full
gap between 224 and 107) — this is the figure obtained by counting straight
off the gap check's own hits rather than by subtracting non-gap hits from
the total, and it is what "the excluding-gap figure" means under a
CLI-style count rather than the `screened_rate`-style one. Both numbers are
correct; they answer "how many items survive if the gap check is removed"
(110) versus "how many items exist only because of the gap check" (114).
Per-check counts over the confident population: `large_interior_gap` 127,
`short_span` 61, `low_span_coverage` 48, `heading_divergence` 8. The CLI's
own printed per-check tallies read 131 / 63 / 48 / 11 — that is not a third
disagreement, it is a different denominator again: the CLI sums hits over
**all** items (`render()`'s `by_check` loop), while `screened_rate` and the
counts above filter to the confident population only. All three views are
legitimate reads of the same run; they are not comparable without saying
which is which, which prior text here did not do. **The conclusion is
unchanged**: every one of the 117 newly-flagged items (224 − 107) traces to
the self-induced `large_interior_gap` check firing on the EO clip's own
deliberate exclusion (§d), or to the same clip's boundary shift newly
crossing the `short_span` floor — net zero new confirmed silent failures,
same as the pre-fix reading.

**OSS cross-check (`evals/oracle_oss.py`, `edgartools==5.50.0`):** 25/574
item-level disagreements (4.4%) over 28 of 30 HTML/iXBRL fixtures (2 excluded
as doc-level refusals, not comparable). Of the 25: two are the `jpm-2024`
items 7/8 finding this ADR adopts (§e); the rest are traced to edgartools' own
defects (a boundary over-run on `bac-2006` cascading through four items; a
systemic title-matching gap on four fixtures using non-canonical Item 4/14
titles this repo's fuzzy matching already tolerates) or expected disagreement
by design (adversarial fixtures whose whole point is a stripped heading).
**Six plain-text fixtures have zero OSS coverage** — edgartools returns zero
sections on plain text, by its own documented design, confirmed at full-corpus
scale (the throwaway spike found this on one fixture; the full run confirms it
on all six now in the set).

## c) Ruling — the OSS oracle

`sec-parser` is **ruled out**: its taxonomy is Edgar10-Q only (`grep -rl
"10-K\|Edgar10K"` over the package: zero hits), it never classifies Items
1A/7/8 as sections on any fixture tried, has no offset concept at all, and on
plain-text filings it produces confidently mislabeled sections rather than
failing loudly — a false-agreement risk worse than a crash for a cross-check
instrument. Not worth further investment.

`edgartools==5.50.0` is **adopted as a dev instrument**, via its low-level,
network-free entry point only:

```python
from edgar.documents import HTMLParser, ParserConfig
doc = HTMLParser(ParserConfig(form="10-K")).parse(html_string)
```

not `Filing`/`TenK`, which touch the network in normal use. Confirmed
network-free in a fresh process for this deliverable (not taken on the
spike's word): `socket.socket.connect` and `socket.getaddrinfo` both
monkey-patched to raise, three fixtures including the largest committed one
(`jpm-2024`, 12.8 MB) parsed cleanly with no network call attempted.
`evals/oracle_oss.py` enforces the same guard on every run, not just this
one-time check.

Comparison is **content similarity only, never offsets** — `Section.start_
offset`/`end_offset` exist on the `'toc'` detection path used here but are
dead fields, always 0, confirmed directly. A published number depending on
this tool is reproducible only with the **full frozen dependency set**
(`evals/oracle-oss-requirements.txt`, 74 lines, captured 2026-08-19 against
Python 3.14.6), not the headline `edgartools==5.50.0` pin alone — its own
`Requires-Dist` lists loose ranges for most of 21 direct dependencies, so
pinning only the headline package does not reproduce a number six months from
now.

**C7 is satisfied**: `oracle_oss.py` is never imported by `src/`,
`evals/run.py`, or `evals/metrics.py` (verified by grep); `edgartools` is not
in `requirements.txt` or `pyproject.toml` (ADR-003's stdlib-only pipeline
stands, untouched); no CI workflow references it. It is a dev-only instrument
that never ships.

**The plain-text era — the hardest stratum — has no OSS cross-check at all**
and remains auditor-sampling-only. This is stated as a limit, not papered
over: any silent-failure number for pre-HTML-era filings rests entirely on the
extraction-auditor's judgment, with no independent second read.

## d) Ruling — the mis-specified debt row

`tasks/TODO.md`'s "No span-coverage validator" row and ADR-015 §5 claim
nothing measures span coverage or the largest inter-span gap, and rank it the
strongest candidate for the first post-freeze exception. **Both halves are
false**, and this ADR corrects the backlog on the evidence, not on argument:

1. **Coverage is already measured, exactly.** `coverage ≡ 1 −
   unattributed_content`'s own "outside" fraction. Identity holds to float
   equality on 33 of 33 span-bearing fixtures — verified by direct computation
   against all of them, not assumed from the algebra.
2. **The largest interior gap between accepted spans is structurally always
   0.0**, on every one of 36 fixtures, no exception. `assign_boundaries` sets
   each span's `end` to the next accepted span's `start`
   (`src/sec10k/segment.py:382-400`), so accepted spans are contiguous by
   construction. A gap validator built on this architecture could never fire
   on real pipeline output — proved by a `_demo` assertion against a
   hand-built input that bypasses `assign_boundaries`, the same "proved at the
   layer, not the fixture" treatment ADR-016 gives `boundary_hygiene`, because
   no fixture in this corpus can exercise it either.

ADR-015 §5 also says §0's Intel failure "was invisible to eight validators".
§0 of the same ADR records `unattributed_content` **firing** on Intel — 0.47%
coverage, `success_with_warning`. It was detected and non-escalating (not in
`AMBIGUOUS_CODES`, an ADR-008 decision that is still correct for IBR-heavy
filings) — a **severity** gap, not a detection gap. Target's uncaught shape
was different again: item 4 at 81% was **not the last span**, and
`last_item_dominates` (ADR-008) only inspects the last one.

**Ruling: the planned capability would have caught neither filing it cites.**
A validator that already exists (relabeled) cannot be the fix for a bug that
validator already flagged, and a gap check that can structurally never fire is
not a fix for anything. Retire the row. The correctly-specified successor is
**a non-last span dominating the document, plus the escalation-policy
question** (should any single-item dominance, first or last, escalate
`doc_status` the way `last_item_dominates` already does for the last item) —
named here as the real candidate, not built (T8 freeze). ADR-015 §5 is amended
with a dated correction note pointing here; its history is not rewritten.

**Correction (2026-08-19, post-commit review) — points 1 and 2 above were
verified against the PRE-fix codebase and are false post-fix, because this
same milestone's own `EXEC_OFFICERS_RE` fix (§f) is the one exception to
"contiguous by construction".** `assign_boundaries` clips a non-last span's
`end` to the EO heading's start (`src/sec10k/segment.py:assign_boundaries`),
which is exactly a case where a non-last span's `end` sits below the next
accepted span's `start` — the premise both points 1 and 2 depend on. Re-
verified at head, over all 36 fixtures:

| fixture | coverage | 1 − unattributed | max gap frac |
|---|---|---|---|
| ibm-1997 | 0.4692 | 0.5663 | 0.0971 |
| textron-2001 | 0.6686 | 0.7186 | 0.0500 |
| nike-2006 | 0.9414 | 0.9751 | 0.0336 |
| wmt-2010 | 0.8421 | 0.8757 | 0.0336 |
| msft-2013 | 0.9548 | 0.9751 | 0.0203 |
| jnj-2016 | 0.9174 | 0.9375 | 0.0201 |
| wfc-2008 | 0.6668 | 0.6687 | 0.0019 |

Exactly the 7 fixtures the EO clip touches, and no others. So: the coverage
identity now holds on 29 of 36 fixtures, not 33 of 33 (all 36 fixtures were
checked, not only the 33 span-bearing ones the original count scoped to);
the largest-interior-gap is no longer structurally 0.0 on every fixture —
it is nonzero on exactly these 7, ranging 0.0019 to 0.0971.

**The retirement still stands, but for a different, weaker reason, and that
is the reason to record, not the original one.** Post-fix, the *only* source
of an inter-span gap anywhere in the corpus is the EO clip itself, and every
one of the 7 gaps is a *deliberate* exclusion of orphaned Executive-Officer
content (§f) — not a defect. A gap validator built today would fire 7/7 on
our own intentional behaviour: it would detect the clip, not catch anything
wrong. Coverage now diverges from `unattributed_content` by up to 9.7
percentage points on these 7, and that divergence, too, *is* the deliberate
exclusion, not evidence against the retirement.

**The honest consequence, stated plainly because nobody had written it down:
the EO clip creates interior unattributed content that no item covers and no
validator reports.** That is correct behaviour — officer bios are not any
item's answer — but it is a new surface this milestone's own fix opened, and
it means a coverage/gap check would regain real value the moment a *second*,
non-deliberate gap source appears in this pipeline (something other than a
recognized, intentional clip leaving daylight between two accepted spans).
That is the condition under which this retirement should be revisited — not
"never", and not "only if `assign_boundaries` changes again", but specifically
the appearance of an unintentional gap the EO clip's own accounting cannot
explain.

## e) Ruling — the internal-pointer class (NOT fixed)

Third variant of a known pointer family:

| variant | fixture | mechanism | status |
|---|---|---|---|
| cross-item footnote | `ba-2003` | asterisk resolved once, in another item's body | enumerated debt (T9) |
| external pointer, unmatched phrasing | `wfc-2008` | "incorporated into this report by reference" defeated `IBR_RE` | fixed, ADR-017 |
| **internal pointer to a paginated section** | `cvx-2015`, `ge-1994`, `jpm-2024` | short, well-formed pointer sentence naming a page number **inside the same document** | **enumerated debt (T11, new)** |

Evidence: `cvx-2015` items 7/8 report `extracted` at confidence 0.95 over
280/189 chars ("...is presented on page FS-1"), while 294,291 chars of real
MD&A and financial-statement content sit outside every span, in the
document's tail. `ge-1994` item 8 is the same shape one era earlier: 86 chars,
"See index under item 14." `jpm-2024` items 7/8 report `extracted` at 0.95
over 398/372 chars ("...appears on pages 52–167" / "...appear on pages
169–321"), while the real MD&A and financial-statement notes — 431,755 and
559,713 chars by edgartools' independent count — sit unreached; item 15's span
holds 1,010,422 chars, which already includes the real financials because
`last_item_dominates` swallowed them into the last item instead.

**Status does not change.** ADR-004's rule that an internal pointer cannot
make an item `incorporated_by_reference` is correct and stays — nothing is
actually incorporated from outside the document, so there is nothing external
to fetch. That leaves the pointer sentence as the item's only body, which is
non-empty, well-formed prose (not the `ba-2003` empty-body shape), so ADR-005
passes it through as `extracted` at full confidence with nothing at the
single-item level `classify()` operates at to object to. Resolving an
intra-document page reference — finding "page FS-1" or "pages 52–167" and
attaching the content there — is a new capability, forbidden by the T8
freeze without its own ADR, not a defect in an existing layer. Enumerated as
debt with a committed case (`evals/adversarial/cvx-2015-internal-pointer.json`,
`debt` suite, stays permanently red).

**Standing disagreement, recorded not resolved.** The extraction-auditor's
blind sample adjudicated `cvx-2015` item 6 — the identical shape — and ruled
it CORRECT (§b). Items 7 and 8 were never independently adjudicated (outside
the 30-case sample). This ADR does not declare a winner between "the pointer
sentence is honestly the whole answer" and "a pointer to real content the
extractor cannot reach is a silent failure regardless of phrasing" — the
auditor's charter requires an ADR to settle a disagreement it raises, and this
one records the disagreement rather than resolving it by fiat. The debt case
asserts the gap for items 7/8 only, not item 6, so it does not resolve the
disagreement by assertion either.

**The sharpest distinction T11 found**: on `jpm-2024`, the *document-level*
ladder was honest — `last_item_dominates` fired and `doc_status` correctly
read `ambiguous`. The *item-level* confidence on items 7 and 8 still read
0.95. Document-level honesty and item-level honesty are separate properties of
this pipeline, and today only the first is defended by an escalation rule.
That gap — a confident, wrong item inside a document the pipeline is already
unsure about — is worth naming plainly rather than let the document-level
`ambiguous` imply the item-level numbers were caught by the same net.

## f) Ruling — Executive Officers (FIXED)

Reg S-K Item 401(b) requires an "Executive Officers of the Registrant"
disclosure but assigns it no item code, so filers place it as an unnumbered
section wherever suits their layout — end of Item 1, end of Item 4, even
mid-Item-2. It recurs across **7 fixtures spanning 1997–2016**: `textron-2001`,
`wmt-2010`, `wfc-2008`, `jnj-2016`, `msft-2013`, `nike-2006`, `ibm-1997`
(T11 recurrence scan). `textron-2001-content` item 4 was the extraction-
auditor's one confirmed WRONG verdict: `extracted` at confidence 0.95 over
3,731 chars, of which only the first 262 are Item 4's real two-sentence
answer — the remaining 3,469 chars are six executive-officer biographies, Part
III content silently attributed to Item 4.

**Fix**: `EXEC_OFFICERS_RE` (`src/sec10k/segment.py`) reuses the existing
`TAIL_RE` pattern — the unnumbered heading terminates the *preceding* item's
span exactly as `TAIL_RE` terminates the last item at Signatures. It does not
become an item of its own (INV-S3: the item registry is closed). Occurrences
inside Item 10 ("Directors, Executive Officers and Corporate Governance") are
excluded — there the heading legitimately recurs as that item's own
subsection, not orphaned content. A `(?!\.)` negative lookahead excludes a
wrapped-prose false match: `ge-1994` item 1 reads "...for information about\n
Executive Officers of the Registrant.\n\nOther" — a sentence that happens to
start a wrapped physical line, not a heading; real headings never carry a
trailing period.

**Blast radius**: exactly 7 fixtures, one `end` offset moved each, no
`doc_status`/`status`/`warnings` change on any of them, 30 fixtures byte-
identical.

**The `msft-2013` interleaving, and the trade this ADR makes explicit.** Six
of the seven fixtures have a clean layout — the unnumbered heading sits at the
true end of the item, nothing follows it before the next numbered item. On
`msft-2013` the layout is interleaved: Item 1 body → the Executive-Officers
heading and ~4,712 chars of bios → a ~1,643-char "Available Information"
website paragraph that is genuine Item 1 content → Item 1A. INV-S2 requires a
span to be one contiguous verbatim slice, so no single span can keep the
trailing website block and drop the bios sandwiched in front of it.

**Ruling: keep the clip.** Attributing 4,712 chars of Part III officer-bio
content to Item 1 at confidence 0.95 is precisely the silent-failure shape
this milestone exists to hunt; losing the 1,643-char trailing block is a
boundary-tightness loss the item's own length band already tolerates (post-fix
Item 1 measures 37,695 chars, comfortably inside the case's 30,000–65,000
band). Between two imperfect contiguous spans, prefer the one that does not
attribute another item's content. The removed anchor (`evals/golden/
msft-2013-content.json`'s old Item 1 closing anchor, "The information found on
our website is not part of this or any other report we file with") is not
deleted — it moves verbatim into `evals/adversarial/msft-2013-website-block.json`
(`debt` suite, class `spec-ambiguity`), which stays permanently red and keeps
the lost content visible until a future capability (a discontiguous or
"orphaned between items" span kind) can hold it. `evals/golden/
msft-2013-content.json`'s Item 1 closing anchor is re-anchored on its real
last sentence, "Our practice is to ship our products promptly upon receipt of
purchase orders from customers; consequently, backlog is not significant.",
grep/occurrence-verified against `normalized_text` at count 1.

**Open debt (2026-08-19, post-commit review) — `EXEC_OFFICERS_RE` has no TOC
awareness.** Every other candidate path in `segment.py` routes through
`_toc_runs` before trusting a heading-shaped match; `EXEC_OFFICERS_RE` is a
raw `text.search()` with no such filter. It already matches TOC *entries*
for the heading it is meant to clip on, confirmed directly against
`normalized_text`:

- `jnj-2016`: `"…Registrant\n\n10\n\nPART II\n\n5\n\nMarket"`
- `msft-2013`: `"…Registrant\n12\n\nItem 1A."`
- `nike-2006`: `"…Registrant\n8\n\nItem 1A."`

None of this breaks anything today — every TOC hit above falls outside the
window `assign_boundaries` searches (`c["heading_end"]` to `c["end"]` of the
*preceding* item's own accepted span), so the match is found and then simply
unused. But a filing whose table of contents sits *after* the first accepted
heading — rather than before it, as in every fixture on file — would have
its TOC hit land inside that search window and clip the item down to almost
nothing, silently. Same class of gap as the `(?!\.)` guard: that lookahead
excludes `ge-1994`'s wrapped-prose false match (a sentence ending in a
period), but not the same shape ending in a comma or continuing without
punctuation. **Not fixed here.** TOC routing is a real change to a frozen
pipeline (T8), and no fixture in this corpus can demonstrate the bug firing
— shipping an untestable code path is the ADR-010 sin. Recorded as debt in
`tasks/TODO.md`; the condition that would make it bite is a TOC placed after
the first accepted item heading, which no committed or held-out fixture
does.

## g) What T11 did not measure

30 of 447 is 6.7% of the unaudited population — most of it remains unlooked
at by anything beyond the four cheap heuristics in §b. The plain-text stratum,
the era this repo's own README already calls hardest, has no OSS cross-check
at all; its silent-failure evidence is auditor sampling alone, with nothing
independent to corroborate a CORRECT verdict the way the HTML stratum's 97.8%
agreement rate does. The screen with the widest coverage (the stdlib oracle,
107/521 flagged pre-fix, **224/521 post-fix — see the §b correction, 2026-08-19**)
found zero new confirmed defects; the judge with the
narrowest scope (30 hand-adjudicated items) found the one real defect this
milestone fixed and surfaced the one standing disagreement it didn't resolve.
That is an argument about where audit effort belongs — depth over breadth, on
this evidence — and it should be stated as such rather than implied by which
number got the bigger table.

## Verification

`--suite fast` 44/44 = 1.000 (+3 enumerated debt, unscored: `ba-2003-
asterisk-ibr`, `cvx-2015-internal-pointer`, `msft-2013-website-block`).
`--suite invariant` 12/12 = 1.000 (+ the same 3 debt rows). `.eval-baseline.json`
untouched (`{"fast": 1.0}`, matches). No `--update-baseline`, no `--no-verify`.
