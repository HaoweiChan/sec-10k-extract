# ADR-020 — T12: the LLM fallback stage is not justified, and what would change that

**SUPERSEDED 2026-08-26 by [ADR-036](ADR-036-tiered-escalation.md) (D11).** The
headline ruling below — "no LLM fallback ships" — no longer holds: a model tier
now ships behind D8's `low_item_coverage`, opt-in and off by default. What
survives, and is kept rather than reversed, is this document's *principle*: the
deterministic pipeline is the default and the only path on a clean filing, a
paid tier is triggered and never unconditional, and a run in which nothing
escalated still costs $0.00 — measured, not asserted, at 0 of 28 real dev
filings. ADR-036 §a re-checks both of the reasons below and records which
still hold. Read the text that follows as the record of what was true on the
2026-08-19 corpus, not as current policy.

Date: 2026-08-19. Status: accepted, **§b and §c row 7 NARROWED 2026-08-26 by
[ADR-034](ADR-034-pointer-and-fanout-rulings.md) (D9)** — see the dated notes
in each. The ruling below (no unconditional LLM fallback ships; the escalation
ladder governs) is unchanged. Implements T12/A4. Rules on the candidate
design recorded in `docs/architecture/overview.md` §10. Closes the open
question that `README.md`, `docs/evals/evaluation-strategy.md` metric 11 and
`docs/analysis-report.md` §4 currently point at. Enumerates one new debt class
(`combined-multi-item-heading`) and burns one held-out case (`axp-2008`).

**Ruling**: no LLM fallback ships; `method: llm_fallback` stays in the contract enum, unemitted, and the pipeline stays stdlib-only at $0.00 cost.
**Because**: six of the seven residual-failure classes are precision failures a recall-only fallback can't reach, and the one real recall gap (`axp-2008`'s combined Part III heading, 4 of 768 items) is closed identically and deterministically by a heading-shape fix at $0.
**Enforced by**: `specs/001-sec10k-contract.md` (method enum), `evals/adversarial/axp-2008-combined-part-iii.json` (`debt` suite), `evals/adversarial/axp-2008-combined-heading-burned.json`

---

**Corrected three times under review (PR #11, findings R1, R8 and R15) — see
§h, §h2 and §h3.** The headline carried four figures across those three
corrections — **0 of 989 → 4 of 989 → 1 of 768 → 4 of 768** — and three of the
four were wrong. The final number
is **4 of 768**, and the derivation is written out below so it can be checked
rather than trusted. The ruling is unchanged across every round, and rests on
the escalation ladder: the same deterministic fan-out reaches all four items at
$0 and closes the whole class.

**Correction, 2026-08-20 (PR #11 round-4 verification, finding R19) — a fourth
defect, uncorrected in the text below.** Where this ADR says `segment.classify`
returns `extracted` on **all four** partition bodies — §a clause 2, §b's
policy-1 table row, §c row 7, and §h3's code block — **that is false, and the
claim is left standing in place rather than rewritten.** The computation behind
it passes the combined heading line inside `body`; the pipeline never does
(`src/sec10k/extract.py:111` derives `body = text[c["heading_end"]:c["end"]]`,
and `segment.py:508` documents `body` as "the span minus its heading line").
Heading-stripped, item 10's partition body is pointer-only and classifies
**`incorporated_by_reference`** (remainder 0 ≤ `IBR_REMAINDER_MAX` 300); the
1,139 chars of Reg S-K prose the `extracted` reading rests on sit at absolute
331084, *after* item 13's span end 330343, so no ordered partition that gives
items 11–13 their own spans can place it inside item 10's body.

Consequence: `evals/adversarial/axp-2008-combined-part-iii.json` asserts a
status set no contract-valid fan-out produces — under the partition
`item_present 10 = extracted` fails, under whole-block items 11–13 stay
`missing` — so its "NOW GREEN → promote it" contract is **unreachable**, the
fourth survival of the defect R1 first raised. Full statement, and the five
documentation defects found with it, in `tasks/TODO.md`'s open-debt table.

**The ruling and the 4-of-768 headline are unaffected**: all four items still
go `missing` → span-carrying under a combined-heading fan-out, which is the
only property the decision rests on. Choosing which design the case pins, and
re-deriving its asserted status set, is T13/T14 work.

**This is the fifth instance of this milestone's recurring error — reasoning
about an executable contract in prose instead of running it — and the first
committed by the review loop's orchestrator**, which ran the heading-inclusive
computation and relayed it as already adjudicated, foreclosing the check it
existed to perform. §h3's count is one short and is not rewritten here.

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
2. **The seventh class is real, and the fallback would fix it — but so would a
   regex.** `axp-2008` names four item codes in one heading, and all four come
   back `missing` with content present to find: **4 improvable items of 768
   (0.52%)**, one filing, one root cause. All four are contract-reachable. The
   block's ten caption bullets address items in the interleaved order 10, 10,
   11, 10, 11, 12, 10, 11, 13, 10, and what that interleaving forecloses is
   narrow: **no partition gives item 10 the *complete* block AND items 11–13
   their own spans.** Item 10 keeps 956 of the block's 3,263 chars under the
   partition — the cost is the other 2,307, and nothing else. It does not put items 11–13 beyond the contract:
   the four caption regions sit at strictly increasing, disjoint offsets,
   `no_overlap_ordered` passes on that assignment, and `segment.classify`
   returns `extracted` on each of the four bodies. A combined-heading fan-out
   produces the *identical* spans and the *identical* statuses through the
   *same* classifier, deterministically, at $0, for every filing of that shape
   rather than the instances a model happens to be invoked on. That is rung 1
   of the escalation ladder answering a rung-4 proposal.

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
| `xom-2021` item 6 | The item **is not in the document**. `Item 6` and `Selected Financial Data` occur zero times in 388,862 normalized chars (as of this ADR; 388,848 since the T3 `<title>` skip — `20260823-185707-bench.json`, D2) — FY2021 filings no longer contain it. Nothing to find; an LLM offered this filing can only invent. **Not addressable.** |
| `malformed-html` item 1A | `RISK FACTORS` occurs exactly once, in the table of contents. The body does not survive the corruption this fixture exists to model. **Not addressable.** |
| `heading-unnumbered` item 8; `items-stripped-escalation` items 5/6/7/7A/8/9/9A/9B (9 items, 2 synthetic fixtures) | Content is present but de-numbered — and **the committed cases assert `missing` is the CORRECT answer**, with `doc_status: ambiguous` and `expected_item_missing`. These fixtures exist to prove the pipeline refuses rather than guesses (`README.md`: "it never emits a best-effort parse of a document it could not identify"). A fallback here does not fix a failure; it deletes a guarantee. **Not addressable.** |
| `axp-2008` items 10, 11, 12, 13 | **ADDRESSABLE — and the whole of it.** A real EDGAR filing, content present, and all four are contract-reachable: the caption regions are disjoint and in order, `no_overlap_ordered` passes, `classify` returns `extracted` on each. The interleaved bullet order costs only item-10 *coverage* (item 10 keeps 956 of the block's 3,263 chars; the cost is 2,307), not the other three items' spans. See §c row 7 for what fixing them costs and why the fallback still loses. |

**Policy 2 — `confidence < 0.8`.** **32 items** across both sets, deduplicated
by fixture — 31 dev (43 as a per-case sum over `results` + `debt`, 34 over
`results` alone) plus 1 held-out (`cost-2022` item 7, 0.75). All excluded for one structural
reason: ADR-019 §b/§e/§f measured where the residual defects actually live, and
it is **at 0.95** — `textron-2001` item 4, `cvx-2015` items 7/8, `jpm-2024`
items 7/8, `ba-2003` items 11/13. A confidence trigger cannot reach the
population that is actually wrong. It adds nothing to policy 1. *(Repair round 2, R12: this read 35, the figure from
`20260819-134001-all.json` — the pre-branch report — which does not reproduce
from the report this section cites. Round 3, R18: it then read 31, a dev-only
count inside a section whose stated basis is both sets.)*

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

**Narrowed 2026-08-26 (ADR-034 §c3, D9).** The count below is correct for the
corpus at this ADR's SHA and is not rewritten. What no longer holds is the
word *only*: the held-out `c-2025`, authored under D6 after this ADR, is a real
EDGAR filing reporting **21 `missing` items** whose content a reader can point
to, and no heading-shape change reaches it — it has no headings to reshape. The
addressable surface is therefore larger than one filing, and `axp-2008`'s
uniqueness is no longer available as an argument. The T12 ruling is unaffected:
ADR-034 routes both to D11's triggered tier, not to the unconditional fallback
this ADR rejected.

**Net addressable surface: 4 of 768 items = 0.52%** — `axp-2008` items 10–13,
one filing, one root cause. Every other `missing` item in either set is either
absent from its document or asserted `missing` on purpose.

The number is non-circular (it needs no fallback to compute), falsifiable, and
recomputable from any committed report by counting `status: missing` in
`items_summary` and checking each against the filing and the contract — no new
metric, no new code. Check it against **both**, and by running the checks rather
than reading them: §h3 is what happens otherwise.

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
| 7 | **`axp-2008` combined Part III heading** — *new, this ADR* | **Yes.** Items 10–13 come back `missing` at 0.40. The only real-filing recall gap in either set. | **Yes, all four.** It would locate the Part III block, and feeding the four caption regions to the existing classifier returns `extracted` on each — correct under ADR-004 (see below), and INV-S1-clean (see below). | **A regex produces the identical output.** The heading is present, bold, machine-readable, and names its codes: `ITEMS 10, 11, 12 and 13.` Combined-heading fan-out is a heading-shape change that closes the class deterministically at $0, versus a metered call closing the instances it is invoked on and happens to get right. |

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

**Row 7's scope, and what the interleaving actually costs (round 3, R15).**
Round 2 claimed the block admits no ordered disjoint partition and narrowed this
row to item 10. That claim was false, and the way to see it is to build a
partition and run the check: item 10 `[328690,329646)` 956 chars, item 11
`[329646,330009)` 363, item 12 `[330009,330085)` 76, item 13 `[330264,330343)`
79 — strictly increasing, disjoint, and `no_overlap_ordered` returns `None`
(pass). Items 12 and 13 land on precisely their own content. `classify` returns
`extracted` on all four bodies. INV-S1's only executable form checks exactly
`s2 < e1` over spans in item order and nothing more.

What the interleaved bullet order *does* foreclose is narrower and real: **no
partition gives item 10 the complete block AND items 11–13 their own spans.**
Item 10 takes 956 of the block's 3,263 chars under the partition above. So the
fan-out design has a genuine choice — whole block to item 10, or four
sub-spans — and it costs item-10 coverage, not items 11–13's reachability. The
debt case pins the four-way partition (that is what stops a *partial* fan-out
from satisfying it) and its item-10 `min_chars` floor is 500, cleared by both
designs, rather than round 1's 2,000, which silently encoded the whole-block
design alone.

One design constraint found while validating the partition, recorded so the
eventual fix does not trip on it: the adapter's `verbatim` check requires a span
to open with its own `heading_text`, so a fan-out must not copy the combined
heading string onto all four items. That is a question about what `heading_text`
means for a shared heading, not a reachability problem.

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

**Row 7's cost premise is NARROWED 2026-08-26 (ADR-034 §c2, D9), and the row is
left standing rather than rewritten.** Row 7 rules the fan-out cheaper because
"a regex produces the identical output" at $0. That rests on `classify`
returning `extracted` on the four partition bodies — the claim the R19
correction at the top of this file already falsified for item 10, and which
ADR-034 re-ran rather than cited: heading-stripped, item 10 classifies
`incorporated_by_reference`. ADR-034 adds a second obstacle measured the same
way — `axp-2008` item 9B's span is `[326876, 331942)`, containing the whole
Part III block, so a fan-out must also truncate a neighbouring `extracted` item
or `no_overlap_ordered` fails. The deterministic fix is a four-part capability,
not a regex, and D9 rules it **subsumed by D11** rather than promoted. The
escalation ladder and this ADR's ruling stand.

**Score: 1 of 7 fixed, and by the more expensive of two instruments that produce
identical output. 5 of 7 never trigger. 1 of 7 is structurally impossible for
this design.**

The general form of the finding still holds and is what carries the ruling:
**a fallback fires on absence, and six of this pipeline's seven residual
defects are presence.** ADR-019 §b measured the silent-failure rate on the
*confident* population precisely because that is where the defects are; a
fallback cannot reach that population without a detector that already knows the
answer is wrong — and any such detector would be the fix, deterministically,
without the model. The one absence that remains is a heading-shape gap, which
is the cheapest kind of fix this repo has.

**A fourth cost the candidate carries, worth naming**: **13** committed cases
assert `{"type": "deterministic"}` (11 dev + 2 held-out), which re-runs
`extract_items` and requires byte-identical output. A model in the extraction path satisfies that only for
inputs whose responses are already cached and committed. The deployed service
takes arbitrary EDGAR URLs (§d.2), which is exactly the mode where the cache is
cold — so the candidate trades a checked invariant for 4 items that a
deterministic change already reaches at $0.

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

*(Figures as of this ADR's date, reproduced to the character by ADR-021 §d2 on
`20260820-031540`; re-measured 2026-08-23 in
`evals/report/20260823-185707-bench.json` (D2, ADR-021 §g) after the `<title>`
skip (T3) and four added fixtures: corpus 8,751,495 over 41; median 102,453;
`jpm-2024` 1,213,284; `bac-2006` 705,848. The ruling does not move — the
counterfactual is an order-of-magnitude argument — so the table above is left
as the dated input it was.)*

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
   a fallback can.** Both halves are required: a real EDGAR filing produces an
   item reported `missing` whose content a reader can point to, whose location
   is *not* reachable by a heading-shape or table change, **and** which a single
   contiguous verbatim slice could carry without violating INV-S1. All four
   `axp-2008` items fail the first half — a heading-shape change reaches every
   one of them — which is the whole of §c row 7. An item failing *only* the
   first half is an argument for the deterministic fix; an item failing *only*
   the second is an argument for amending INV-S1, not for buying a model.
   Instrument: count `status: "missing"` in any committed report's
   `items_summary`, then check each against the filing **and** the contract —
   by running the checks, not by reading them. Threshold: **one** such item.
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
3. **The addressable-surface count** (§b): **4 of 768** distinct items, one
   filing, one root cause, all four reachable by a deterministic heading-shape
   change at $0. Metric 11 demoted in the prose from "the number that justifies
   or kills a fallback stage" to "a dependence monitor, vacuous while no
   fallback exists".
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

- **R8** found that round 1's fix relocated the error instead of removing it:
  asserting `extracted` ×4 requires four items to share one span, which the debt
  case's own `no_overlap_ordered` check forbids. **That much was correct under
  round 1's 2,000-char item-10 floor** — in general four items can each be
  `extracted` on the disjoint spans of a four-way partition, which is why §h3
  lowered the floor to 500 (qualified 2026-08-23, L1, PR #11 R23). What I then
  built on it was not — see §h3.
- **R7** found the denominator was a per-case sum labelled "deduplicated" and
  paired with a fixture column; the true distinct count is **768**, not 989.
  This one holds.

**This moved the headline in my favour, immediately after round 1 moved it
against me, and I flagged the pattern at the time rather than letting it read as
vindication.** Round 3 showed the flag was warranted: the round-2 reasoning was
itself wrong. What I wrote next — "if that reasoning is wrong, the surface
returns to 4 and the ruling still holds on the escalation ladder alone" — is
exactly what happened.

The other six were presentation defects with no pipeline behaviour to pin: R9
(the burned case kept `warning_present: expected_item_missing`, which is true
only because items 10–13 are `missing` — the same reason its four `item_present`
checks were dropped, so it is dropped too, otherwise the two committed cases
were mutually unsatisfiable); R10 (the "no table of contents" claim is false, and
the TOC route is now disposed of in §c row 7); R11 (oracle shift, disclosed in
§g); R12 (the low-confidence figure cited the wrong report); R13 (an ordinal
disagreed across four artifacts); R14 (missing fixture provenance row).

## h3) Repair round 3 (PR #11, R15) — the round-2 correction was itself wrong

Round 2's claim, in §a, §b, §c row 7, §h2 and four other files, was that "no
document-ordered disjoint partition into 10 < 11 < 12 < 13 exists". **It is
false.** One exists, and the way to find out is to build it and run the check —
which is what the reviewer did and I had not:

```
item 10  [328690,329646)  len 956  -> extracted
item 11  [329646,330009)  len 363  -> extracted
item 12  [330009,330085)  len  76  -> extracted
item 13  [330264,330343)  len  79  -> extracted
no_overlap_ordered -> None      # pass
```

Items 12 and 13 land on precisely their own captions. INV-S1's only executable
form checks `s2 < e1` over spans in item order and nothing else; nothing in it
forbids this. The true claim is narrower than the one I made: **no partition
gives item 10 the *complete* block AND items 11–13 their own spans.** The
interleaving leaves item 10 with 956 of the block's 3,263 chars — the cost is
2,307 — and does not put items 11–13 beyond the contract. The surface returns to **4 of 768**, and the
debt case is back to four `extracted` assertions with its item-10 floor lowered
from 2,000 (which silently encoded the whole-block design) to 500 (cleared by
both designs). Watched red again.

**The headline has now carried four figures across three corrections: 0 of 989
→ 4 of 989 → 1 of 768 → 4 of 768. Three of those four figures were wrong, and two
of the three wrong ones — rounds 0 and 2 — were the same error: reasoning about
an executable contract in prose instead of running it (round 1's 4 of 989 was the
denominator, R7; counts corrected 2026-08-23, L1, PR #11 R21).** Round 0: read a status rule from memory without running `classify`.
Round 2: read the span rule without running `no_overlap_ordered` on a candidate
assignment. Round 3 corrected round 2 by doing the one thing neither earlier
round did — constructing the object under discussion and executing the check
against it. The pattern is not incidental to this ADR; it is the thing this repo
exists to prevent, committed twice inside the document arguing that
correctness must be executable rather than asserted. The number in this ADR
should be read as the fourth attempt, not as a result that arrived correctly.

What survived every round, unchanged, is the part that was never a number: a
fallback fires on absence, six of seven residual defects are presence, and the
seventh is cheaper to reach with a regex than with a model. The ruling never
depended on which of the four figures was right — which is why it is still the
ruling, and also why it was worth four rounds to get the figure honest.

## Verification

`axp-2008-combined-part-iii` was watched **red before this ADR existed**, with
no fix attempted, and watched red again after each of the three review re-scopes
(rounds 1, 2 and 3). As it ships, at the commit this section describes:
`[DEBT] STILL RED — combined-multi-item-heading`, **5 failures** — `item
10/11/12/13 not extracted: missing`, plus `item has no span` from the item-10
`min_chars` floor — with both hygiene checks green. That reproduces from the
report of record for this commit, `evals/report/20260820-013206-fast.json`
(its `git_sha` is `c5af644…-dirty`, the parent commit plus the uncommitted tree
that became this one — content reproduces exactly; labelling noted 2026-08-23,
L1, PR #11 R24, the `a670e8b` precedent).
*(Round 3, R16: this section previously reported the round-1 case's failure
count, which the round-2 re-scope had already made wrong.)*

`--suite invariant` 12/12 = 1.000 (+4 enumerated debt, unscored).
`--suite fast` 45/45 = 1.000 (+ the same 4 debt rows) — 45, not 44, because the
burned held-out case moved into `evals/adversarial/`.
`--suite fast --dir evals/heldout` 5/5 = 1.000 — 5, not 6, because `axp-2008`
was burned and moved (§g).
`.eval-baseline.json` untouched (`{"fast": 1.0}`; the gate compares score, and
the score is unchanged at 1.0). No `--update-baseline`, no `--no-verify`.
`src/` is untouched by this milestone: the only code change is a `note` on
metric 11 in `evals/metrics.py` and a dated docstring correction in
`evals/oracle.py`. **No paid API call was made in this milestone**, and no code
path capable of making one exists.
