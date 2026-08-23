# ADR-019 — T11: the silent-failure rate, measured, and three rulings it forced

Date: 2026-08-19. Status: accepted. Implements T11/A3. Amends ADR-015 §5 (the
mis-specified span-coverage debt row), ADR-018 (its consequences still named
the span-coverage validator as the live post-freeze candidate — marked in place
2026-08-22, ADR-027 §g) and ADR-004 (records, does not resolve,
a standing disagreement over `cvx-2015` item 6). Ships the Executive-Officers
boundary fix (`src/sec10k/segment.py`, `EXEC_OFFICERS_RE`). Amended by:
ADR-030 (§d's successor built, noted in place 2026-08-23).

**Ruling**: measure the silent-failure rate at 1/30 sampled (3.3%, CI [0.1%, 17.2%]) over the 447 confident-but-unchecked items; fix the Executive-Officers boundary bleed across 7 fixtures; retire the mis-specified span-coverage debt row; leave the internal-pointer-to-paginated-section class as recorded, unresolved debt.
**Because**: metric 6 reads 0.0 by construction (the gate forces every declared check green), so the only way to see the real rate was to sample outside the checked population with an instrument the gate doesn't control.
**Enforced by**: `docs/evals/audits/2026-08-19-t11-silent-failure-sample.md`, `evals/oracle.py`, `evals/oracle_oss.py`, `src/sec10k/segment.py` (`EXEC_OFFICERS_RE`), `evals/adversarial/cvx-2015-internal-pointer.json`

---

## a) The definition, and why metric 6 could not measure it

A **silent failure** is an item reported at confidence ≥ 0.8, inside a
document the pipeline called `success`/`success_with_warning`, whose
extraction is wrong when judged against the filing by an instrument the
pipeline does not control.

`evals/metrics.py`'s metric 6 has always read **0.0** — not evidence of
correctness, but a property of what it counts: its denominator is items a
*declared eval check* targets, and the pre-commit gate requires every scored
check to pass, so a check that could fail and doesn't gets fixed or removed,
and a check that structurally can't fail (four of them, ADR-016) inflates the
pass rate without adding evidence. Of **781** confident items in the T10-era
report, **447** were targeted by no check at all — T11 exists to look at those
directly, by an instrument the gate does not control.

## b) The measured rate, with its method

**Sampled rate: 1 WRONG / 30 adjudicated = 3.3%**, 95% Clopper-Pearson CI
**[0.1%, 17.2%]**. Population 447 (confidence ≥ 0.8, `success`/
`success_with_warning`, targeted by no existing check); sample drawn with
`random.Random(11).sample(population, 30)`, seed recorded in
`docs/evals/audits/2026-08-19-t11-silent-failure-sample.md`; adjudicated blind
by the extraction-auditor against the fixture. Interval re-derived here
(stdlib `math.comb`) and matches the audit's figures. Applied to the
population: **~15 items** (447 × 1/30), CI **[0, 77]** (447 × [0.1%, 17.2%],
rounded).

`docs/evals/evaluation-strategy.md` set an aspirational target of < 5% before
any data existed. **Ruling: the point estimate meets it; the CI upper bound of
17.2% means the target is not demonstrated, only not contradicted.** n=30 is
small and one confirmed defect in 447 doesn't license a tighter claim — the
interval is the honest statement, not the point, the same discipline ADR-018
applied to calibration.

**Sensitivity: 1/30 (auditor) vs. 2/30 = 6.7% (mine)**, over `cvx-2015` item 6
(`"Item 6. Selected Financial Data ... presented on page FS-60."`, 111 chars,
an internal pointer whose real data sits in the tail). The auditor ruled it
CORRECT — the pointer sentence is the entirety of what the filing labels here,
nothing else to call wrong at `classify()`'s single-item level. I read it as
the same shape as items 7/8 in the same filing (§e, never independently
adjudicated) and call it WRONG. Both readings are published, not adjudicated
to one number here — see §e.

**Screen (stdlib `evals/oracle.py`)**, four independent-of-the-pipeline
signals (coverage floor, short-span floor, an independent heading locator,
missing-but-located): flags **224/521 = 0.4299** confident items post-fix,
matching the artifact's own `screened_rate`
(`evals/report/20260819-014559-oracle.json`, committed). Net **zero** new
confirmed silent failures — the one real defect it catches (`ba-2003` items
11/13) was already known debt. Coverage and largest-interior-gap are
algebraically redundant with `unattributed_content` on 29 of 36 fixtures
(verified by direct computation, §d); on the other 7 (EO-clip fixtures) the
redundancy breaks by design (§d). 58 of 60 short-span flags and all 48
coverage flags were traced by hand to a legitimate, already-disclosed cause.

| what | value | population |
|---|---|---|
| screened, pre-fix (superseded) | 107/521 | confident |
| screened, post-fix = `screened_rate` | 224/521 (0.4299) | confident |
| excluding self-induced `large_interior_gap` | 110 | confident |
| flagged *only* by `large_interior_gap` (224 − 110) | 114 | confident |
| newly flagged post-fix (224 − 107) | 117 | confident |
| `short_span`, pre-fix → post-fix | 58 → 61 | confident |
| `low_span_coverage` / `heading_divergence`, unchanged | 48 / 8 | confident |
| per-check hits, confident population | gap 127 / short_span 61 / coverage 48 / heading 8 | confident |
| per-check hits, CLI's printed tally (`by_check`) | gap 131 / short_span 63 / coverage 48 / heading 11 | all items |

The last two rows disagree only on denominator — the CLI sums hits over
**all** items, `screened_rate` and the rows above filter to the confident
population. *(2026-08-19: the screen moved from 107/521 pre-fix to 224/521
post-fix because of the EO fix, §f, and the gap-check mechanics it interacts
with, §d — not because the screen itself changed.)* Conclusion unchanged: net
zero new confirmed silent failures.

**OSS cross-check (`evals/oracle_oss.py`, `edgartools==5.50.0`):** 25/574
item-level disagreements (4.4%) over 28 of 30 HTML/iXBRL fixtures (2 excluded
as doc-level refusals). Two of the 25 are the `jpm-2024` items 7/8 finding
this ADR adopts (§e); the rest trace to edgartools' own defects (a `bac-2006`
boundary over-run; non-canonical Item 4/14 titles this repo's fuzzy matching
already tolerates) or expected disagreement by design. **Six plain-text
fixtures have zero OSS coverage**, by edgartools' own design.

## c) Ruling — the OSS oracle

`sec-parser` is **ruled out**: Edgar10-Q-only taxonomy (zero `10-K`/
`Edgar10K` hits in the package), never classifies Items 1A/7/8 on any fixture
tried, no offset concept, and on plain-text filings it confidently mislabels
sections instead of failing loudly — worse than a crash for a cross-check
instrument.

`edgartools==5.50.0` is **adopted as a dev instrument**, via its low-level,
network-free entry point only (`HTMLParser`/`ParserConfig`, not
`Filing`/`TenK`, which touch the network) — confirmed network-free in a fresh
process (sockets monkey-patched to raise): the largest committed fixture
(`jpm-2024`, 12.8 MB) parsed cleanly, no call attempted; `evals/oracle_oss.py`
enforces the same guard every run. Comparison is **content similarity only,
never offsets** (`Section`'s offset fields are dead on this path, always 0).
Reproducible only with the **full frozen dependency set**
(`evals/oracle-oss-requirements.txt`, 74 lines, captured 2026-08-19 against
Python 3.14.6) — the headline pin alone leaves 21 direct dependencies on loose
ranges.

**C7 is satisfied**: never imported by `src/`, `evals/run.py`, or
`evals/metrics.py`; `edgartools` not in `requirements.txt`/`pyproject.toml`
(ADR-003's stdlib-only pipeline untouched); no CI reference — dev-only, never
ships. **The plain-text era has no OSS cross-check at all**: its evidence is
auditor sampling alone, with no independent second read.

## d) Ruling — the mis-specified debt row

`tasks/TODO.md`'s "No span-coverage validator" row and ADR-015 §5 claim
nothing measures span coverage or the largest inter-span gap, ranking it the
top post-freeze candidate. **Both halves are false.** Coverage is already
measured, exactly: `coverage ≡ 1 − unattributed_content`'s own "outside"
fraction, an identity verified by direct computation on 29 of 36 fixtures (the
other 7 below). The largest interior gap is nonzero only on those same 7, and
every one is `EXEC_OFFICERS_RE`'s own deliberate exclusion of orphaned
Executive-Officer content (§f), not a defect:

| fixture | coverage | 1 − unattributed | max gap frac |
|---|---|---|---|
| ibm-1997 | 0.4692 | 0.5663 | 0.0971 |
| textron-2001 | 0.6686 | 0.7186 | 0.0500 |
| nike-2006 | 0.9414 | 0.9751 | 0.0336 |
| wmt-2010 | 0.8421 | 0.8757 | 0.0336 |
| msft-2013 | 0.9548 | 0.9751 | 0.0203 |
| jnj-2016 | 0.9174 | 0.9375 | 0.0201 |
| wfc-2008 | 0.6668 | 0.6687 | 0.0019 |

*Footnote, 2026-08-19: pre-fix, this identity held on 33 of 33 span-bearing
fixtures and the gap read structurally 0.0 on all 36; `EXEC_OFFICERS_RE` (the
sole exception, formerly guaranteed contiguous by
`src/sec10k/segment.py:382-400`) breaks it on exactly these 7 — the identity
still holds on the remaining 29.*

**A gap check today would fire 7/7 on our own intentional behaviour.** That is
known structurally, not just as a corpus snapshot: `end` is written in exactly
three places inside `assign_boundaries` — the next-span start, the EO clip,
and `TAIL_RE` (which touches only the last span, a tail, not an interior gap).
`extract.py:112` copies offsets and never nulls them for an accepted code;
`span_metrics` filters on `start is not None`, not status, so no status
demotion can open a hole either. The EO clip is provably the only interior-gap
source this pipeline has.

ADR-015 §5 also claims §0's Intel failure "was invisible to eight validators"
— but `unattributed_content` **fired** on it (0.47% coverage,
`success_with_warning`), detected and non-escalating (not in
`AMBIGUOUS_CODES`, ADR-008, still correct for IBR-heavy filings) — a
**severity** gap, not detection. Target differed: item 4 at 81% was **not the
last span**, and `last_item_dominates` (ADR-008) inspects only the last.

**Ruling: the planned capability would have caught neither filing it cites,
and today would only fire on our own deliberate exclusion.** Retire the row.
The correctly-specified successor is **a non-last span dominating the
document, plus the escalation-policy question** (should any single-item
dominance, first or last, escalate `doc_status` as `last_item_dominates`
already does for the last) — named here, not built (T8 freeze). ADR-015 §5
gets a dated correction note pointing here; its history is not rewritten.
*(Built 2026-08-23 as the sanctioned exception: ADR-030, D3 — `item_dominates`
at `ITEM_MAX = 0.55`, escalating; both halves of the question ruled there.)*

**The honest consequence: the EO clip creates interior unattributed content
that no item covers and no validator reports** — correct (officer bios aren't
any item's answer), but a new surface this milestone's own fix opened.
Coverage diverges from `unattributed_content` by up to 9.7 points on the 7
fixtures above — the exclusion, not evidence against retirement. Revisit only
if an unintentional gap appears that the EO clip's own accounting cannot
explain.

## e) Ruling — the internal-pointer class (NOT fixed)

Third variant of a known pointer family:

| variant | fixture | mechanism | status |
|---|---|---|---|
| cross-item footnote | `ba-2003` | asterisk resolved once, in another item's body | enumerated debt (T9) |
| external pointer, unmatched phrasing | `wfc-2008` | "incorporated into this report by reference" defeated `IBR_RE` | fixed, ADR-017 |
| **internal pointer to a paginated section** | `cvx-2015`, `ge-1994`, `jpm-2024` | short, well-formed pointer sentence naming a page number **inside the same document** | **enumerated debt (T11, new)** |

Evidence, the paginated-section variant:

| fixture | items | conf | span chars | pointer (excerpt) | unreached real content |
|---|---|---|---|---|---|
| `cvx-2015` | 7/8 | 0.95 | 280/189 | "...page FS-1" | 294,291 chars MD&A/financials, in the tail |
| `ge-1994` | 8 | — | 86 | "See index under item 14." | same shape, one era earlier |
| `jpm-2024` | 7/8 | 0.95 | 398/372 | "...pages 52–167" / "169–321" | 431,755 + 559,713 chars (edgartools' count); item 15's span (1,010,422 chars) already swallows it via `last_item_dominates` |

**Status does not change.** ADR-004's rule that an internal pointer cannot
make an item `incorporated_by_reference` is correct and stays — nothing is
actually incorporated from outside the document. That leaves the pointer
sentence as the item's only body, non-empty and well-formed (not `ba-2003`'s
empty-body shape), so ADR-005 passes it through as `extracted` at full
confidence, with nothing at `classify()`'s single-item level to object to.
Resolving an intra-document page reference is a new capability, forbidden by
the T8 freeze without its own ADR, not a defect in an existing layer.
Enumerated as debt with a committed case
(`evals/adversarial/cvx-2015-internal-pointer.json`, `debt` suite, permanently
red).

**Standing disagreement, recorded not resolved.** The auditor's blind sample
adjudicated `cvx-2015` item 6 — the identical shape (§b) — CORRECT. Items 7
and 8 were never independently adjudicated; I read them, and item 6, as WRONG.
This ADR does not declare a winner between "the pointer sentence is honestly
the whole answer" and "a pointer to real content the extractor cannot reach is
a silent failure regardless of phrasing" — the auditor's charter requires an
ADR to settle a disagreement it raises, and this one records rather than
resolves it. The debt case asserts the gap for items 7/8 only, not item 6.

**The sharpest distinction T11 found**: on `jpm-2024`, the document-level
ladder was honest — `last_item_dominates` fired, `doc_status` correctly read
`ambiguous` — but item-level confidence on items 7 and 8 still read 0.95.
Document-level and item-level honesty are separate properties here, and today
only the first is defended by an escalation rule.

## f) Ruling — Executive Officers (FIXED)

Reg S-K Item 401(b) requires an "Executive Officers of the Registrant"
disclosure but assigns it no item code, so filers place it wherever suits
their layout — end of Item 1, end of Item 4, even mid-Item-2. It recurs across
**7 fixtures spanning 1997–2016**: `textron-2001`, `wmt-2010`, `wfc-2008`,
`jnj-2016`, `msft-2013`, `nike-2006`, `ibm-1997` (T11 recurrence scan).
`textron-2001-content` item 4 was the auditor's one confirmed WRONG verdict:
`extracted` at 0.95 over 3,731 chars, of which only the first 262 are Item 4's
real two-sentence answer — the remaining 3,469 chars are six executive-officer
biographies, Part III content silently attributed to Item 4.

**Fix**: `EXEC_OFFICERS_RE` (`src/sec10k/segment.py`) reuses `TAIL_RE` — the
unnumbered heading terminates the *preceding* item's span exactly as `TAIL_RE`
terminates the last item at Signatures, and does not become an item of its own
(INV-S3: item registry closed). Occurrences inside Item 10 ("Directors,
Executive Officers and Corporate Governance") are excluded — there the heading
legitimately recurs as that item's own subsection. A `(?!\.)` negative
lookahead excludes a wrapped-prose false match on `ge-1994` item 1, a
heading-shaped line that is really a wrapped sentence ending in a period —
real headings never carry a trailing period. **Blast radius**: exactly 7
fixtures, one `end` offset moved each, no `doc_status`/`status`/`warnings`
change, 30 fixtures byte-identical.

**The `msft-2013` interleaving, and the trade this ADR makes explicit.** Six
of the seven fixtures are clean — the heading sits at the item's true end.
`msft-2013` interleaves: Item 1 body → the heading and ~4,712 chars of bios →
a ~1,643-char "Available Information" paragraph that is genuine Item 1 content
→ Item 1A. INV-S2 requires one contiguous verbatim slice, so no single span
can keep the trailing block and drop the bios in front of it. **Ruling: keep
the clip.** Attributing 4,712 chars of Part III content to Item 1 at 0.95
confidence is precisely the shape this milestone hunts; losing the 1,643-char
trailing block is a boundary-tightness loss the item's own length band
tolerates (post-fix Item 1: 37,695 chars, inside the 30,000–65,000 band).
Between two imperfect spans, prefer the one that doesn't attribute another
item's content. The removed anchor (the old Item 1 closing sentence, about the
company website) is not deleted — it moves verbatim into
`evals/adversarial/msft-2013-website-block.json` (`debt` suite, class
`spec-ambiguity`, permanently red), preserving the lost content until a
discontiguous/"orphaned" span kind exists. The golden case's Item 1 anchor is
re-anchored on its real last sentence, about shipping practices
(occurrence-verified against `normalized_text`, count 1).

**Open debt (2026-08-19) — `EXEC_OFFICERS_RE` has no TOC awareness.** Every
other candidate path in `segment.py` routes through `_toc_runs` first; this
one is a raw `text.search()` with no filter, and already matches TOC *entries*
for its own heading: `jnj-2016` ("…Registrant\n\n10\n\nPART
II\n\n5\n\nMarket"), `msft-2013` ("…Registrant\n12\n\nItem 1A."), `nike-2006`
("…Registrant\n8\n\nItem 1A."). Harmless today — every hit falls outside the
window `assign_boundaries` searches — but a filing whose TOC sits *after* the
first accepted heading (none in this corpus) would have the hit land inside
that window and silently clip the item to near-nothing, the same class of gap
as the `(?!\.)` guard (which catches a period-terminated wrap, not a comma or
unpunctuated one). **Not fixed here** — TOC routing is a real change to a
frozen pipeline (T8), and no fixture can demonstrate the bug firing (shipping
it untestable is the ADR-010 sin). Recorded as debt in `tasks/TODO.md`.

## g) What T11 did not measure

30 of 447 is 6.7% of the unaudited population — most remains unlooked at
beyond §b's four cheap heuristics. The plain-text stratum has no OSS
cross-check at all; its evidence is auditor sampling alone, nothing
independent to corroborate a CORRECT verdict the way the HTML stratum's 97.8%
agreement rate does. The widest-coverage screen (stdlib oracle, 224/521
post-fix, §b) found zero new confirmed defects; the narrowest-scope judge (30
hand-adjudicated items) found the one real defect this milestone fixed and
surfaced the one disagreement it didn't resolve — depth over breadth, on this
evidence, stated as such rather than implied by table size.

## Verification

`--suite fast` 44/44 = 1.000 (+3 enumerated debt, unscored: `ba-2003-
asterisk-ibr`, `cvx-2015-internal-pointer`, `msft-2013-website-block`).
`--suite invariant` 12/12 = 1.000 (+ the same 3 debt rows).
`.eval-baseline.json` untouched (`{"fast": 1.0}`, matches). No
`--update-baseline`, no `--no-verify`.
