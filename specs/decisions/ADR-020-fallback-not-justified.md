# ADR-020 — T12: the LLM fallback stage is not justified, and what would change that

Date: 2026-08-19. Status: accepted. Implements T12/A4. Rules on the candidate
design recorded in `docs/architecture/overview.md` §10. Closes the open
question that `README.md`, `docs/evals/evaluation-strategy.md` metric 11 and
`docs/analysis-report.md` §4 currently point at. Enumerates one new debt class
(`combined-multi-item-heading`) and burns one held-out case (`axp-2008`).

**Corrected twice under review (PR #11, findings R1 and R8) — see §h.** The
headline number moved twice, in both directions, and the derivation is stated
in full below so the movement can be checked rather than trusted. Round 0
claimed **0** improvable items on a status label the classifier contradicts;
round 1 corrected that to **4**; round 2 found that three of those four cannot
be given a span-carrying status at all without amending INV-S1, leaving **1**
contract-reachable improvable item of 768. The ruling is unchanged across all
three, and now rests on two independent grounds: the escalation ladder for the
one reachable item, and an invariant no extraction method can buy past for the
other three.

## a) The ruling

**A layer-10 LLM fallback stage is NOT justified on the evidence T11 produced.
No fallback ships. `method: llm_fallback` stays in the contract's enum,
unemitted, and the pipeline stays stdlib-only (ADR-003 untouched, cost stays
structurally $0.00).**

Scope: it judges *the* candidate on record in §10 — an LLM returning verbatim
anchor quotes that the pipeline re-locates to offsets, cached by content-hash +
prompt-version, budget-capped, `full`-suite only. It rules on that design
against the residual failures this repo has actually measured. It does not rule
that no LLM could ever help this problem, and §e states what would flip it.

The ruling in two clauses, because one is not enough:

1. **Six of the seven residual-failure classes are precision failures** — a
   confidently wrong or wrongly-classified span at 0.95 — and a fallback is a
   recall instrument. It fires where the pipeline produced nothing. Five of the
   six never trigger at all; the sixth is structurally impossible for this
   candidate to fix.
2. **The seventh class is real, and mostly unreachable by any extraction
   method.** `axp-2008` names four item codes in one heading, and all four come
   back `missing` with content present to find. But only **one of the four can
   be given a span-carrying status at all** under the current contract: INV-S1
   requires span-carrying ranges to be non-overlapping *and* in document order,
   ADR-011 gives `incorporated_by_reference` real offsets (only
   `missing`/`omitted` may be span-free), and the block's caption bullets
   address items in the interleaved order 10, 10, 11, 10, 11, 12, 10, 11, 13,
   10 — so no document-ordered disjoint partition into 10 < 11 < 12 < 13
   exists. Items 11–13 are blocked by an **invariant**, which a model cannot
   buy past any more than a regex can. That leaves **1 contract-reachable
   improvable item of 768 (0.13%)** — attach the block to item 10, the first
   code the heading names — and a heading-shape change produces the *identical*
   span and the *identical* status through the *same* classifier,
   deterministically, at $0, for every filing of that shape rather than the
   instances a model happens to be invoked on. That is rung 1 of the escalation
   ladder answering a rung-4 proposal.

## b) Disposing of metric 11's circularity

`docs/analysis-report.md:101-102` and `:330` already concede the problem:
metric 11 (`share of extracted items with method != llm_fallback`) reads
**1.0 (n=636)** because no code path emits `llm_fallback`. "100% deterministic
coverage kills the fallback stage" is circular, and a ruling that leans on it
is not an argument. This ADR does not lean on it.

The circularity is structural, not a measurement bug: metric 11 measures an
**output** of a stage that does not exist, so it is necessarily vacuous until
one exists — at which point it becomes a useful *dependence monitor* and
nothing more. It was never capable of deciding this question.

**The non-circular substitute is an input: the fallback-addressable surface** —
the count of items on which any honest trigger policy would invoke a fallback.
It is measurable today with zero fallback code, from committed reports, because
it counts what the stage would be *offered*, not what it would *produce*.

Counted over `evals/report/20260819-213224-all.json` and the current held-out
set (`evals/report/20260819-213804-fast.json`), **deduplicated by fixture** —
12 dev fixtures carry 2–4 cases each (`aapl-2025` ×3, `msft-2013` ×4,
`wmt-2010` ×3, `ba-2003`, `cvx-2015`, `jpm-2024`, `textron-2001`, `axp-2008`
×2), so a per-case sum double-counts them:

| | fixtures | items |
|---|---|---|
| dev set (`golden/` + `adversarial/`) | 37 | 667 |
| held-out set | 5 | 101 |
| **total distinct** | **42** | **768** |

*(Repair round 2, R7: this table previously read 888 dev / 989 total, which was
the per-**case** sum — 908 minus the duplicate `axp-2008` debt row — presented
under the word "deduplicated" and paired with a fixture column. The
self-check that catches it: 888/37 = 24 items per fixture, while the largest
`n_items` of any case in the report is 23. The numerator was already
deduplicated, so a deduplicated numerator was being divided by an
undeduplicated denominator. Reproduce the corrected figure by grouping every
case's `n_items` by the fixture directory in its `input.path` and taking one
row per fixture.)*

Three candidate trigger policies, and the disposal of each:

**Policy 1 — `status == missing`.** 15 of 768 items (1.95%), deduplicated:

| item(s) | disposal |
|---|---|
| `xom-2021` item 6 | The item **is not in the document**. `Item 6` and `Selected Financial Data` occur zero times in 388,862 normalized chars — FY2021 filings no longer contain it. Nothing to find; an LLM offered this filing can only invent. **Not addressable.** |
| `malformed-html` item 1A | `RISK FACTORS` occurs exactly once, in the table of contents. The body does not survive the corruption this fixture exists to model. **Not addressable.** |
| `heading-unnumbered` item 8; `items-stripped-escalation` items 5/6/7/7A/8/9/9A/9B (9 items, 2 synthetic fixtures) | Content is present but de-numbered — and **the committed cases assert `missing` is the CORRECT answer**, with `doc_status: ambiguous` and `expected_item_missing`. These fixtures exist to prove the pipeline refuses rather than guesses (`README.md`: "it never emits a best-effort parse of a document it could not identify"). A fallback here does not fix a failure; it deletes a guarantee. **Not addressable.** |
| `axp-2008` item 10 | **ADDRESSABLE — and the whole of it.** A real EDGAR filing, content present, and the candidate would produce a contract-valid `extracted` span. See §c row 7 for what that costs and why it still loses. |
| `axp-2008` items 11, 12, 13 | **Real recall gaps, but unreachable by any extraction method.** Giving them a status other than `missing` means giving them offsets (ADR-011), and there is nowhere to put those offsets: sharing item 10's span breaks INV-S1's non-overlap rule, and partitioning the block breaks its document-order rule, because the caption bullets address items in the order 10, 10, 11, 10, 11, 12, 10, 11, 13, 10. The blocker is the **contract**, not the extractor — an LLM whose safety property is one contiguous verbatim slice hits it identically. Closing this needs an INV-S1 amendment (a shared or joint span kind), which is its own ADR and a bigger decision than the fallback question. Same family as `msft-2013`, which needs a discontiguous span kind. **Not addressable.** |

**Policy 2 — `confidence < 0.8`.** **31 items** deduplicated by fixture (43 as a
per-case sum over `results` + `debt`, 34 over `results` alone — the dedup basis
is the one used everywhere in this section). All excluded for one structural
reason: ADR-019 §b/§e/§f measured where the residual defects actually live, and
it is **at 0.95** — `textron-2001` item 4, `cvx-2015` items 7/8, `jpm-2024`
items 7/8, `ba-2003` items 11/13. A confidence trigger cannot reach the
population that is actually wrong. It adds nothing to policy 1. *(Repair round
2, R12: this read 35, which is the figure from `20260819-134001-all.json` — the
pre-branch report — and does not reproduce from the report this section cites.)*

**Policy 3 — `doc_status ∈ {ambiguous, unsupported, failed}`.** 9 cases:
`jpm-2024-content`, `jpm-2024-structure`, `xom-2021-shallow`,
`heading-unnumbered`, `items-stripped-escalation`, `malformed-html`,
`10q-unsupported`, `ksb-unsupported`, `truncated-download`. Six are already
dispositioned above (they are the filings whose `missing` items policy 1
counted, plus `jpm-2024`, whose items 7/8 are `extracted` at 0.95 — §c row 4).
The remaining three are the maximal recall surface a doc-level policy offers,
and are the clearest refusals in the repo:

| case | `doc_status` | items emitted | disposal |
|---|---|---|---|
| `10q-unsupported` | `unsupported` | 0 | Not a 10-K. The pipeline identified the form and refused. |
| `ksb-unsupported` | `unsupported` | 0 | Form 10-KSB. Same: identified and refused. |
| `truncated-download` | `failed` | 0 | The document is truncated. The pipeline refused rather than parse a fragment. |

All three emit **zero items by design**, which makes them the largest surface a
doc-level trigger would hand a model and simultaneously the place where firing
is most clearly wrong: `README.md` states that "`unsupported` and `failed` mean
the pipeline refused", and each of these is a committed case asserting exactly
that refusal (`ksb-unsupported` asserts `only_items: []`). A fallback invoked
here is an LLM asked to extract 10-K items from a document that is not a 10-K
or not complete — the maximal hallucination surface in the corpus, bought by
deleting the refusal guarantee that is the product's headline honesty property.
**Not addressable.**

**Net addressable surface: 1 of 768 items = 0.13%** — `axp-2008` item 10. Two
numbers matter here and collapsing them into one is how this ADR went wrong
twice, so both are stated: **4** items are genuine recall gaps (real filing,
content present, a reader can point to it), and **1** of those four can be
converted into a **contract-valid** output by any extraction method at all. The
gap between 4 and 1 is INV-S1, not the extractor.

The number is non-circular (it needs no fallback to compute), falsifiable, and
recomputable from any committed report by counting `status: missing` in
`items_summary` and checking each against the filing and the contract — no new
metric, no new code.

## c) The residual-failure classes, one at a time

`tasks/TODO.md`'s "Open debt, carried deliberately" table, plus the class this
ADR adds. For each: would the §10 candidate fire, would it fix it, at what
cost, with what new failure mode?

| # | residual failure | would the candidate fire? | would it fix it? | the cheaper instrument, or the new failure mode |
|---|---|---|---|---|
| 1 | **Non-last span dominating the document** + the escalation-policy question (ADR-019 §d) | **No.** The item is `extracted` with a span at full confidence. No trigger exists. | No. | A validator: deterministic, $0, already named as the real successor. |
| 2 | **Era table is a single point of silent failure** (ADR-010/013/015 §5) | Only if the item came back `missing`. | Possibly, on a filing where a well-titled heading is physically present. But **no fixture in either set can demonstrate this firing** — every filing that would have is covered by a corrected table entry. | Shipping a paid code path whose triggering condition no committed case can produce is the ADR-010 sin twice over: untestable *and* metered. |
| 3 | **Cross-item footnote IBR** — `ba-2003` items 11/13 | **No.** `extracted` at 0.95/0.75 over 34/59-char spans. Confidently wrong, not empty. | No. | — |
| 4 | **Internal pointer to a paginated section** — `cvx-2015` 7/8, `ge-1994` 8, `jpm-2024` 7/8 | **No** at item level (`extracted`, 0.95; ADR-004/005 rule that call correct). `jpm-2024` is the one place a *doc-level* trigger exists (`last_item_dominates` → `ambiguous`). | Under a doc-level policy it would have to relocate a **431,755-char** span from anchor quotes on a **12.8 MB** filing. | Two short quotes bounding a 431 KB span is a relocation problem with real ambiguity; a wrong `end` anchor yields a confidently wrong span carrying `llm_fallback` provenance — the silent-failure shape T11 exists to hunt, with a bill attached. |
| 5 | **`msft-2013` Executive-Officers/website-block interleaving** (ADR-019 §f) | Only under a doc-level or heuristic trigger — the item is `extracted` at 0.95 inside its length band. | **Structurally impossible.** The fix needs a discontiguous span. The candidate's entire safety property is one contiguous verbatim slice (INV-S2 by construction). What makes the design safe makes it useless here. | — |
| 6 | **`EXEC_OFFICERS_RE` has no TOC awareness** (ADR-019 §f) | **No.** If it fired it would clip an item to near-nothing while still reporting `extracted`. | No. | TOC routing: deterministic, $0. |
| 7 | **`axp-2008` combined Part III heading** — *new, this ADR* | **Yes.** Items 10–13 come back `missing` at 0.40. The only real-filing recall gap in either set. | **For item 10, yes. For items 11–13, no — and neither would a regex.** It would locate the Part III block, and feeding that span to the existing classifier returns `extracted`, correct under ADR-004 (see below). But only one item can hold that span: INV-S1 forbids the other three from sharing it and forbids the partition that would separate them (see below). | **A regex produces the identical output on the reachable half, and hits the identical wall on the other.** The heading is present, bold, machine-readable, and names its codes: `ITEMS 10, 11, 12 and 13.` Fan-out is a heading-shape change that closes the class deterministically at $0, versus a metered call closing the instances it is invoked on and happens to get right — and for items 11–13 the blocker is an invariant, which neither instrument can spend its way past. |

**Row 7's status, corrected.** The first draft of this ADR asserted the correct
status was `incorporated_by_reference` and that the candidate — which emits
`extracted` — would therefore make this case *worse*. That was wrong, and the
repo's own rules say so. ADR-004 reserves IBR for bodies that are *solely*
pointers; ADR-007's remainder rule implements it as
`rest <= IBR_REMAINDER_MAX (300)`. This body is not pointer-only: after the
proxy-IBR lead-in and its ten caption bullets it carries **1,139 chars** of
substantive standalone prose — the Corporate Governance Principles / Code of
Conduct paragraph, genuine Reg S-K Item 406 code-of-ethics disclosure, which
explicitly says the linked website material "is not incorporated by reference
into this report". That is ADR-004 **shape 3**, ruled `extracted`, and
`segment.classify('10', body, True)` returns `extracted` on it today. So the
candidate would get item 10 *right*, not wrong.

**Row 7's scope, corrected again (round 2, R8).** Re-labelling the debt case to
`extracted` ×4 moved the error rather than removing it. Four items cannot share
one span: INV-S1 requires span-carrying ranges to be non-overlapping **and** in
document order, and ADR-011 makes `incorporated_by_reference` span-carrying too,
so `missing`/`omitted` are the only span-free statuses. Nor can the block be
partitioned into four ordered pieces — its caption bullets address items in the
order **10, 10, 11, 10, 11, 12, 10, 11, 13, 10**, and a partition satisfying
`10 < 11 < 12 < 13` would have to un-interleave text the filing wrote
interleaved. The debt case asserted this against its own `no_overlap_ordered`
check. **What is reachable without amending anything is item 10 alone** — one
span, no overlap, `classify` returns `extracted` — and that is what the case now
asserts, with items 11–13 explicitly *not* asserted and their blocker named.

**The second deterministic route, disposed of (round 2, R10).** This filing does
have a table of contents, and it lists all four Part III codes individually — so
in principle the TOC manifest is a second instrument. It is not one here, for
two reasons. Mechanically, `toc_manifest` comes back **empty** on this filing
(trace layer `candidates`): the contents entries are bare `10.` / `11.` / `12.` /
`13.` with no `Item` prefix, so they generate no heading candidates — the same
root cause as the combined heading, which is that this filer writes Part III
item codes without the word "Item" in both places it names them. Substantively,
even a populated manifest yields item codes and *page numbers*, not body
offsets; converting a page number into a span is the intra-document pagination
capability ADR-019 §e already enumerates as debt (`cvx-2015`). So the TOC route
confirms which items are expected — which the era table already does, which is
why `expected_item_missing` fires — and locates nothing. It changes neither the
count nor the ruling.

**Score: 1 of 7 partially fixed — one item of four, and by the more expensive of
two instruments that produce identical output on it. 5 of 7 never trigger. 1 of
7 is structurally impossible for this design. And the unreachable 3 items in row
7 are blocked by the same kind of thing that blocks row 5: an invariant, not an
extraction method.**

The general form of the finding still holds and is what carries the ruling:
**a fallback fires on absence, and six of this pipeline's seven residual
defects are presence.** ADR-019 §b measured the silent-failure rate on the
*confident* population precisely because that is where the defects are; a
fallback cannot reach that population without a detector that already knows the
answer is wrong — and any such detector would be the fix, deterministically,
without the model. The one absence that remains is a heading-shape gap, which
is the cheapest kind of fix this repo has.

**A fourth cost the candidate carries, worth naming**: ten committed cases
assert `{"type": "deterministic"}`, which re-runs `extract_items` and requires
byte-identical output. A model in the extraction path satisfies that only for
inputs whose responses are already cached and committed. The deployed service
takes arbitrary EDGAR URLs (§d.2), which is exactly the mode where the cache is
cold — so the candidate trades a checked invariant for 4 items that a
deterministic change already reaches.

## d) Cost, and why the candidate is most expensive exactly where it is needed

Measured from the committed dev corpus (`select_and_normalize` over all **37**
fixtures — 37, not 36, because `axp-2008`'s fixture moved into `evals/fixtures/`
when its held-out case was burned, §g). Character counts are exact; token
figures are a **chars/4 approximation** — T13 should firm them with
`count_tokens`, not with a live extraction run.

| | chars | ≈ tokens |
|---|---|---|
| whole dev corpus (37 fixtures) | 8,450,478 | ~2,113,000 |
| median fixture (n=37, true median) | 108,938 | ~27,000 |
| `jpm-2024` (largest, 12.8 MB raw) | 1,213,298 | ~303,000 |
| `bac-2006` | 705,899 | ~176,000 |

Price basis: Anthropic first-party API list price, **as of 2026-06-24** (the
`claude-api` skill's cached model table) — `claude-opus-5` $5.00/MTok input,
1M context; `claude-haiku-4-5` $1.00/MTok input, 200K context. Cited rather
than assumed so a grader can check the counterfactual the way every other
number in this repo can be checked; prices move, and T13 should re-check the
list before publishing.

Two consequences the candidate cannot design around:

1. **A locate-an-item fallback must see the whole document**, because if we knew
   which region to send we would not need it. The unit of spend is the filing,
   not the item: ~$1.52 for one `claude-opus-5` pass over `jpm-2024`, ~$0.14 for
   the median filing, ~$10.56 for one pass over the dev corpus. Cheaper tiers do
   not simply divide the problem — `claude-haiku-4-5`'s 200K context does not
   hold `jpm-2024`'s ~303K tokens at all, so the largest filings (the ones with
   the hardest boundaries and the only doc-level `ambiguous` in the set) force
   either a 1M-context model or a chunking/retrieval subsystem far larger than
   "a fallback stage".
2. **Caching bounds the eval bill and not the product bill.** Content-hash +
   prompt-version caching makes the second `full`-suite run ~$0, which is the
   right discipline and why `cost-discipline` rule 2 exists. But this project
   ships a deployed service accepting arbitrary EDGAR URLs
   (`docs/analysis-report.md` §3, Zeabur). Cache hit rate on an unseen filing is
   zero by definition. The fallback's cost is bounded in the mode where it does
   not matter and unbounded in the one where it does — while today's answer to
   "cost per filing" is a *reported result* of $0.00, not an estimate
   (metric 10).

Against a benefit of 4 items that a $0 heading-shape change reaches identically,
any of these numbers is too large.

## e) What would flip this ruling

Unchanged by the round-1 correction — condition 1 already excluded `axp-2008`
for exactly the reason §c row 7 now gives, which is why the corrected surface
of 4 does not overturn the decision. Any one of these reopens T12 with its own
ADR:

1. **An addressable item appears that a deterministic change cannot reach *and*
   a fallback can.** Both halves are required, and round 2 showed why: a real
   EDGAR filing produces an item reported `missing` whose content a reader can
   point to, whose location is *not* reachable by a heading-shape or table
   change, **and** which a single contiguous verbatim slice could carry without
   violating INV-S1. `axp-2008` item 10 fails the first half (a heading-shape
   change reaches it); `axp-2008` items 11–13 fail the second (no span-carrying
   status is available to them at all, so the fallback is as blocked as the
   regex). An item failing *only* the first half is an argument for the
   deterministic fix; an item failing *only* the second is an argument for
   amending INV-S1, not for buying a model. Instrument: count `status:
   "missing"` in any committed report's `items_summary`, then check each against
   the filing **and** the contract. Threshold: **one** such item.
2. **A residual precision failure acquires an honest trigger.** If the
   escalation-policy successor named in ADR-019 §d ships and gives non-last span
   dominance a doc-level signal, rows 4 and 5 acquire a trigger they lack today,
   and "should the fallback fire on it" becomes live — with the row 4/5
   objections (relocation ambiguity, INV-S2 contiguity) still to answer.
3. **The plain-text stratum gets an independent read and it disagrees.**
   ADR-019 §c/§g flag that six plain-text fixtures have **zero** OSS
   cross-check; their only evidence is auditor sampling. If a second instrument
   covering that stratum finds a recall class the HTML stratum lacks, §b's count
   is understated and must be recomputed before this ruling stands.
4. **The CI, not the point estimate, moves.** ADR-019's sampled silent-failure
   rate is 1/30, 95% CI [0.1%, 17.2%]. A larger sample pushing the *lower* bound
   up materially means more defects than the debt table accounts for — but that
   reopens the *precision* problem, so it argues for the escalation policy and
   the auditor loop first, and for a fallback only if the new defects are
   absences.

Explicitly **not** sufficient: metric 11 reading 100% (circular, §b); the
deployed service being asked for an LLM; a filing merely being large or old.

## f) What T13's cost model should contain instead

T12's ledger row says a shipped fallback's cost model lands in T13. Nothing
ships, so T13's §4 should carry, in its place:

1. **The reported result, unchanged**: $0.00 per filing, structurally — no paid
   dependency exists (metric 10). Stated as a measurement, not an estimate.
2. **The counterfactual from §d**, as the price of the road not taken: ~$0.14
   per median filing, ~$1.52 for the largest, ~$10.56 for one uncached pass over
   the 37-fixture corpus, with the chars/4 caveat, the as-of-2026-06-24 price
   basis, and the note that the Haiku tier cannot hold the largest filings. This
   is what makes "$0" a *decision* rather than an absence.
3. **The addressable-surface count** (§b): of 768 distinct items, 4 are real
   recall gaps and **1** is convertible into a contract-valid improvement by any
   extraction method — carry both numbers, not one, since collapsing them is how
   this ADR went wrong twice. Metric 11 demoted in the prose from "the number
   that justifies or kills a fallback stage" to "a dependence monitor, vacuous
   while no fallback exists".
4. **The §e reopening conditions**, so the report says what would change the
   answer rather than implying the answer is permanent.

T13 must not run a live extraction over the corpus against a paid endpoint to
firm the token figures — `count_tokens` or an offline tokenizer only. The spend
decision is the human's.

## g) Consequences

**New enumerated debt: `combined-multi-item-heading`.** `axp-2008` addresses
Part III under one heading naming four codes — verified in the **raw bytes**
(one `ITEMS\b` match in 1,296,375 bytes, at offset 1225493):
`<B>ITEMS&nbsp;10,&nbsp;11,&nbsp;12&nbsp;and&nbsp;13.</B>` + the four-item
title, then a ~3,000-char body. Every heading path in `src/sec10k/segment.py`
matches one code per heading, so all four come back `missing`. Fan-out is a new
capability, forbidden by the T8 freeze without its own ADR — the same reasoning
that leaves `ba-2003` and `cvx-2015` unfixed. Committed as
`evals/adversarial/axp-2008-combined-part-iii.json` (`debt` suite, unscored,
permanently red), watched red before this ADR was written and again after the
round-1 re-labelling, with no fix attempted (hard rule 2). Its four checks
assert `extracted` — what fan-out plus the existing classifier would produce —
plus a `min_chars` floor on item 10 pinning that the real block is attached and
not the heading line alone.

**`axp-2008` is burned, and moved.** `evals/heldout/README.md`'s burn rule names
"a new case written because of it" as influence, and the `gs-2002` precedent
(2026-08-17) established that a documented decision *declining* a fix burns a
case as surely as a fix does. This ruling rests in part on `axp-2008`'s outcome
and authored a case from it, so it is burned as of 2026-08-19. Per the rule and
the `gs-2002` precedent it is **moved in this milestone, not deferred**:
`evals/heldout/axp-2008-heldout.json` →
`evals/adversarial/axp-2008-combined-heading-burned.json`, fixture
`evals/heldout/fixtures/axp-2008/` → `evals/fixtures/axp-2008/`. The held-out
set is **5 cases / 101 items**, enforced by the file system rather than asserted
in prose. A replacement filing for the crisis-era stratum rides T14's expansion.

**Its four Part III labels were wrong and are gone.** The moved case asserted
`item_present 10/11/12/13 = missing` on the authority of a provenance scan that
searched only the **singular** strings `Item 10`…`Item 13`, found zero, and
concluded Part III had no headings at all. It has one, combined. `missing` is
what the pipeline produces today but is not the correct label, so the four
assertions were dropped in the move rather than re-enshrined;
`expected_set_complete` still requires all twenty codes to be reported with some
status, and the desired state is asserted — and kept red — by the debt case. The
original held-out provenance is preserved verbatim inside the moved case, because
its frozen pre-run predictions are the point of a held-out case. This is the
**sixth** time the verification instrument rather than the pipeline was at fault
(`evals/heldout/README.md` counts the first five); the round-1 correction in §h
is the seventh, and it was mine.

**Docs that promised a future decision are closed**, not left pointing at an open
question: `docs/architecture/overview.md` §10 **and its "Built so far" summary at
the top of the same file**, `README.md`'s deferred-LLM bullet,
`docs/evals/evaluation-strategy.md` metric 11, and `docs/analysis-report.md` §4
all now point here. `evals/metrics.py` metric 11 gains a `note` stating its
vacuity in the one place a reader meets it in code — the only code change this
milestone makes.

**The corpus move shifted the T11 oracle instrument, and that is disclosed here
rather than left for someone to trip over** (round 2, R11). Moving a 37th
fixture into `evals/fixtures/` changed the distributions `evals/oracle.py`
reports and, with them, a present-tense claim in its docstring. At the
36-fixture corpus the interior-gap check was nonzero **only** on the 7
`EXEC_OFFICERS_RE` fixtures, ceiling 0.0971, and that fact is load-bearing in
ADR-019 §d's argument that checks 1 and 2 are redundant with
`unattributed_content`. `axp-2008` is an **8th** non-contiguous fixture, is
**not** an EO fixture, and its gap is **0.1264** — above the stated ceiling. Its
gap is the un-found Part III block, i.e. this ADR's own subject. Other shifted
figures: screened rate 224/521 = 0.4299 → **240/537 = 0.4469**; span-length
distribution 529 → **545** items; the `COVERAGE_FLOOR` provenance's "28 such
fixtures" → 29. **ADR-019's numbers are not rewritten** — they were measured on
the corpus that existed at their SHA and remain valid for it; `oracle.py`'s
docstring is dated to that corpus and names `axp-2008` as the new exception, so
no present-tense falsehood is left in code. Whether an 8th, non-EO gap source
weakens ADR-019 §d's redundancy argument is a question for whoever revisits that
row; it is named here, not answered, because answering it is not T12's decision.

**Fixture provenance** (round 2, R14): `evals/fixtures/README.md` gains a row for
`axp-2008` — source URL, accession, filed date, format, bytes, and its
burned-from-held-out note — as `CLAUDE.md`'s layout requires. Three pre-existing
fixtures (`gs-2002`, `jnj-2016`, `items-stripped`) are still missing rows,
including `gs-2002`, which this ADR cites as the burn precedent and which did not
add one either; those are noted, not fixed here, as they predate this branch.

**Not done, deliberately**: no new metric for the addressable surface. It is a
count of `status: "missing"` in a report the runner already writes every run;
adding a second way to compute a number the reports already carry is the
speculative instrument the ADR-010 sin and the repo's laziness rule both argue
against. §e names where to look instead.

## h) Repair round 1 (PR #11) — what the review caught

The reviewer, with no access to this session's reasoning, found that the debt
case and §c row 7 asserted `incorporated_by_reference` for `axp-2008` items
10–13 while `segment.classify` returns `extracted` for that body, and that the
"0 of 989" headline therefore rested on a label the pipeline's own classifier
contradicts. **Confirmed and accepted.** The error was mine and it was the kind
this repo exists to catch: I read a proxy-IBR lead-in, matched it to ADR-004
shape 1 from memory, and did not run the classifier or count the non-pointer
remainder (1,139 chars against a 300-char threshold). Consequences:

- The surface is **4 of 989**, not 0, and the candidate would get that row
  **right**, not worse. §a, §b and §c row 7 are rewritten; every propagated
  number is updated (`README.md`, `evals/metrics.py`, `docs/analysis-report.md`
  §4, `docs/evals/evaluation-strategy.md`, `tasks/TODO.md` ×2 rows).
- The debt case's assertions were unreachable — it could never have gone green
  even after the capability it names shipped, breaking its own
  "NOW GREEN — promote it" contract. Re-labelled to `extracted` and watched red
  again.
- **The ruling was re-derived, not preserved.** It stands, because the argument
  that actually carries it is the escalation ladder — a heading-shape change
  produces the identical output at $0 and closes the class — and because §e
  condition 1 had already, correctly, excluded `axp-2008` on exactly that
  ground. The first draft's headline was stronger than its evidence; the
  corrected one is weaker and true.

Four further findings were accepted and fixed in the same round: the burned case
was actually moved (§g) rather than deferred; `overview.md`'s "Built so far"
summary was corrected; the held-out inventory row's overreaching clause was
corrected; §b's third trigger policy is now dispositioned exhaustively; and §d's
median and price basis are recomputed and cited.

## h2) Repair round 2 (PR #11) — the correction that moved the number back

Round 2 returned eight findings. All eight were confirmed by running their
repros; none was rejected. Two changed the substance:

- **R8** found that round 1's fix relocated the error instead of removing it.
  Asserting `extracted` ×4 requires four items to share one span, which the debt
  case's own `no_overlap_ordered` check forbids (INV-S1), and the block cannot be
  partitioned because its caption bullets interleave the four items. The
  consequence is larger than the finding stated: **no extraction method** —
  deterministic fan-out or LLM — can give items 11–13 a non-`missing` status
  without amending INV-S1, because ADR-011 makes every non-`missing` status
  span-carrying. The debt case is now scoped to item 10, which is reachable, and
  the surface is **1 of 768**.
- **R7** found the denominator was a per-case sum labelled "deduplicated" and
  paired with a fixture column; the true distinct count is **768**, not 989.

**This moved the headline in my favour, immediately after round 1 moved it
against me, and that deserves to be flagged rather than buried.** The derivation
is written out in §a clause 2 and §b so it can be checked: the movement comes
entirely from applying INV-S1 and ADR-011 to items 11–13, both of which are
committed specs, and the interleaved bullet order is a fact about the document
that anyone can print. If that reasoning is wrong, the surface returns to 4 and
the ruling still holds on the escalation ladder alone — the conclusion does not
depend on which of the two numbers is right, which is the honest summary of
three rounds of correction.

The other six were presentation defects with no pipeline behaviour to pin: R9
(the burned case kept `warning_present: expected_item_missing`, which is true
only because items 10–13 are `missing` — the same reason its four `item_present`
checks were dropped, so it is dropped too, otherwise the two committed cases
were mutually unsatisfiable); R10 (the "no table of contents" claim is false, and
the TOC route is now disposed of in §c row 7); R11 (oracle shift, disclosed in
§g); R12 (the low-confidence figure cited the wrong report); R13 (an ordinal
disagreed across four artifacts); R14 (missing fixture provenance row).

Three rounds, three headline numbers — 0, 4, 1 — and one unchanged ruling. The
first was wrong because I read a status from memory instead of running the
classifier. The second was wrong because I checked the status rule and not the
span rule. Both are the same failure: reasoning about an executable contract in
prose. What survived every round is the part that was never a number — that a
fallback fires on absence, that six of seven residual defects are presence, and
that the seventh is cheaper to reach with a regex than with a model.

## Verification

New case watched **red first**, before this ADR existed and with no fix
attempted, and red again after the round-1 re-labelling:
`axp-2008-combined-part-iii` — `[DEBT] STILL RED — combined-multi-item-heading`,
five failures (`item 10/11/12/13 not extracted: missing`, plus the item-10
`min_chars` floor reporting no span), three hygiene checks green.

`--suite invariant` 12/12 = 1.000 (+4 enumerated debt, unscored).
`--suite fast` 45/45 = 1.000 (+ the same 4 debt rows) — 45, not 44, because the
burned held-out case moved into `evals/adversarial/`.
`.eval-baseline.json` untouched (`{"fast": 1.0}`; the gate compares score, and
the score is unchanged at 1.0). No `--update-baseline`, no `--no-verify`.
**No paid API call was made in this milestone**, and no code path capable of
making one exists.
