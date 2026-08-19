# ADR-020 — T12: the LLM fallback stage is not justified, and what would change that

Date: 2026-08-19. Status: accepted. Implements T12/A4. Rules on the candidate
design recorded in `docs/architecture/overview.md` §10. Closes the open
question that `README.md`, `docs/evals/evaluation-strategy.md` metric 11 and
`docs/analysis-report.md` §4 currently point at. Enumerates one new debt class
(`combined-multi-item-heading`) and burns one held-out case (`axp-2008`).

## a) The ruling

**A layer-10 LLM fallback stage is NOT justified on the evidence T11 produced.
No fallback ships. `method: llm_fallback` stays in the contract's enum,
unemitted, and the pipeline stays stdlib-only (ADR-003 untouched, cost stays
structurally $0.00).**

Scope of the ruling: it judges *the* candidate on record in §10 — an LLM
returning verbatim anchor quotes that the pipeline re-locates to offsets,
cached by content-hash + prompt-version, budget-capped, `full`-suite only. It
rules on that design against the residual failures this repo has actually
measured. It does not rule that no LLM could ever help this problem, and §e
states exactly what would flip it.

The one-sentence reason: **every residual failure this project has measured is
a precision failure — a confidently wrong or wrongly-classified span — and a
fallback is a recall instrument; it fires where the pipeline produced nothing,
and the pipeline has essentially nowhere left where it produces nothing on a
real filing.**

## b) Disposing of metric 11's circularity

`docs/analysis-report.md:101-102` and `:330` already concede the problem:
metric 11 (`share of extracted items with method != llm_fallback`) reads
**1.0 (n=636)** because no code path emits `llm_fallback`. "100% deterministic
coverage kills the fallback stage" is circular, and a ruling that leans on it
is not an argument. This ADR does not lean on it.

The circularity is structural, not a measurement bug: metric 11 measures an
**output** of a stage that does not exist, so it is necessarily vacuous, and it
will stay vacuous until a fallback exists — at which point it becomes a useful
*dependence monitor* and nothing more. It was never capable of being the number
that decides this question.

**The non-circular substitute is an input, not an output: the
fallback-addressable surface** — the count of items on which any honest trigger
policy would invoke a fallback at all. That is measurable today, with zero
fallback code, from committed reports, because it counts what the stage would
be *offered*, not what it would *produce*.

Three candidate trigger policies, counted over the committed dev report
`evals/report/20260819-134001-all.json` (47 cases, 868 items, 36 fixtures,
1993–2026) and the committed held-out report
`evals/report/20260817-224952-fast.json` (6 cases, 121 items):

| trigger policy | dev | held-out |
|---|---|---|
| `status == missing` | 11 / 868 = 1.27% | 4 / 121 = 3.3% |
| `confidence < 0.8` | 35 / 868 = 4.03% | — |
| `doc_status ∈ {ambiguous, unsupported, failed}` | 9 / 47 cases | 0 / 6 |

Then subtract the items a fallback could not help, item by item:

| item(s) | why a fallback cannot help |
|---|---|
| `xom-2021` item 6 | The item **is not in the document**. `Item 6` and `Selected Financial Data` occur zero times in 388,862 normalized chars — FY2021 filings no longer contain it. There is nothing to find; an LLM offered this filing can only invent. |
| `malformed-html` item 1A | `RISK FACTORS` occurs exactly once, in the table of contents. The body does not survive the corruption this fixture exists to model. Nothing to find. |
| `heading-unnumbered` item 8; `items-stripped-escalation` items 5/6/7/7A/8/9/9A/9B (9 items, 2 synthetic fixtures) | Content is present but de-numbered — and **the committed cases assert `missing` is the CORRECT answer**, with `doc_status: ambiguous` and `expected_item_missing`. These fixtures exist to prove the pipeline refuses rather than guesses (`README.md`: "it never emits a best-effort parse of a document it could not identify"). A fallback here does not fix a failure; it deletes a guarantee. |
| all 35 `confidence < 0.8` items | ADR-019 §b/§e/§f measured where the residual defects actually live: **at 0.95**. `textron-2001` item 4 (0.95), `cvx-2015` items 7/8 (0.95), `jpm-2024` items 7/8 (0.95), `ba-2003` items 11/13 (0.95/0.75). A confidence trigger structurally cannot reach the population that is actually wrong. |
| `axp-2008` items 10–13 | The one real-filing item-recall gap in either set — see §c row 7. The candidate design would locate this text and then report the **wrong status** at high confidence. It makes this case worse. |

**Net addressable surface where the candidate fallback would strictly improve
the output: 0 of 989 items.** That number is non-circular (it requires no
fallback to compute), falsifiable (it moves the moment a real filing yields an
item the deterministic pipeline cannot locate but a reader can), and it is
recomputable from any committed report by counting `status: missing` in
`items_summary` — no new metric, no new code, no new number to maintain.

## c) The residual-failure classes, one at a time

`tasks/TODO.md`'s "Open debt, carried deliberately" table, plus the class this
ADR adds. For each: would the §10 candidate have fixed it, at what cost, with
what new failure mode?

| # | residual failure | would the candidate fire? | would it fix it? | new failure mode it introduces |
|---|---|---|---|---|
| 1 | **Non-last span dominating the document** + the escalation-policy question (ADR-019 §d) | **No.** The item is `extracted` with a span at full confidence. No trigger exists. | No. | — (the correct instrument is a validator: deterministic, $0, and already named) |
| 2 | **Era table is a single point of silent failure** (ADR-010/013/015 §5) | Only if the item came back `missing`. | Possibly, on a filing where a well-titled heading is physically present. But **no fixture in either set can demonstrate this firing** — every filing that would have is covered by a corrected table entry. | Shipping a paid code path whose triggering condition no committed case can produce is the exact ADR-010 sin, twice over: untestable *and* metered. |
| 3 | **Cross-item footnote IBR** — `ba-2003` items 11/13 (`evals/adversarial/ba-2003-asterisk-ibr.json`) | **No.** Both report `extracted` at 0.95/0.75 over 34/59-char spans. Confidently wrong, not empty. | No. | — |
| 4 | **Internal pointer to a paginated section** — `cvx-2015` 7/8, `ge-1994` 8, `jpm-2024` 7/8 (`evals/adversarial/cvx-2015-internal-pointer.json`) | **No.** `extracted` at 0.95 over a well-formed pointer sentence; ADR-004/005 rule that call correct. | No — and note `jpm-2024` is the one place a *doc-level* trigger exists (`last_item_dominates` → `ambiguous`), so a doc-level policy could fire here. It would then need to relocate a **431,755-char** span from an anchor quote, on a **12.8 MB** filing. See §d. | Two anchor quotes bounding a 431 KB span is a relocation problem with real ambiguity (a short quote can match many places); a wrong `end` anchor produces a confidently wrong span at `llm_fallback` provenance — the same silent-failure shape T11 exists to hunt, with a bill attached. |
| 5 | **`msft-2013` Executive-Officers/website-block interleaving** (ADR-019 §f) | Only under a doc-level or heuristic trigger — the item is `extracted` at 0.95 inside its length band. | **Structurally impossible.** The fix needs a discontiguous span. The candidate's entire safety property is that it produces one contiguous verbatim slice (INV-S2 by construction). The thing that makes the design safe is the thing that makes it useless here. | — |
| 6 | **`EXEC_OFFICERS_RE` has no TOC awareness** (ADR-019 §f) | **No.** If it fired it would clip an item to near-nothing while still reporting `extracted`. Confidently wrong, not empty. | No. | — |
| 7 | **`axp-2008` combined Part III heading** — *new, this ADR*, `evals/adversarial/axp-2008-combined-part-iii.json` | **Yes.** Items 10–13 come back `missing` at 0.40. This is the only real-filing recall gap in either set. | **It gets the location right and the status wrong.** The heading `ITEMS 10, 11, 12 and 13.` is followed by an explicit external proxy incorporation ("…is incorporated herein by reference"). Correct status: `incorporated_by_reference` ×4. The candidate emits `extracted`. | It converts an **honest** `missing` — 0.40 confidence, `expected_item_missing` fired, `doc_status: success_with_warning` — into a **confident misclassification**. Strictly worse output, for money. |

**Score: 0 of 7 fixed. 1 of 7 made worse. 5 of 7 never trigger at all.** Every
non-triggering row is a precision failure, and rows 1, 2, 6 and 7 all have a
deterministic fix available at $0 — a validator, a table entry, a TOC route, a
heading shape — each of which is rung 1 of the escalation ladder
(`.claude/skills/cost-discipline/SKILL.md` rule 1). Paying a model to do what a
regex does is the ladder inverted.

The general form of the finding: **a fallback fires on absence, and this
pipeline's remaining defects are all presence.** ADR-019 §b measured the silent
failure rate on the *confident* population precisely because that is where the
defects are; a fallback is architecturally unable to reach that population
without a detector that already knows the answer is wrong — and any such
detector would be the fix, deterministically, without the model.

## d) Cost, and why the candidate is most expensive exactly where it is needed

Measured from the committed dev corpus (`select_and_normalize` over all 36
fixtures; character counts are exact, token figures are a chars/4
approximation — **T13 should firm them with `count_tokens`, not with a live
extraction run**):

| | chars | ≈ tokens |
|---|---|---|
| whole dev corpus (36 fixtures) | 8,098,964 | ~2,024,000 |
| median fixture | 108,938 | ~27,000 |
| `jpm-2024` (largest, 12.8 MB raw) | 1,213,298 | ~303,000 |
| `bac-2006` | 705,899 | ~176,000 |

Two consequences the candidate cannot design around:

1. **A locate-an-item fallback must see the whole document**, because if we
   knew which region to send we would not need it. So the unit of spend is the
   filing, not the item. On `claude-opus-5` input pricing ($5/MTok) that is
   ~$1.52 for one pass over `jpm-2024`, ~$0.14 for the median filing, ~$10 for
   one pass over the dev corpus. Cheaper tiers do not simply divide the
   problem: `claude-haiku-4-5`'s 200K context does not hold `jpm-2024`'s
   ~303K tokens at all, so the largest filings — the ones with the hardest
   boundaries and the only doc-level `ambiguous` in the set — force either a
   1M-context model or a chunking/retrieval subsystem that is a far larger
   capability than "a fallback stage".
2. **Caching bounds the eval bill and not the product bill.** Content-hash +
   prompt-version caching makes the second `full`-suite run ~$0, which is the
   right discipline and is why rule 2 of `cost-discipline` exists. But this
   project ships a deployed service that accepts arbitrary EDGAR URLs
   (`docs/analysis-report.md` §3, Zeabur). Cache hit rate on a filing nobody
   has seen is zero by definition. So the fallback's cost is bounded in the one
   mode where it does not matter and unbounded in the one where it does — while
   today's answer to "cost per filing" is a *reported result* of $0.00, not an
   estimate (metric 10).

Against a measured benefit of **zero items improved**, any of these numbers is
too large. This is the ponytail ladder's first rung answering the question:
the cheapest correct outcome is the null result, and the evidence supports it.

## e) What would flip this ruling

The ruling is conditional on measurements, so it names the measurements that
would overturn it. Any one of these is sufficient to reopen T12 with its own
ADR:

1. **The addressable surface stops being zero.** A real EDGAR filing (dev,
   held-out, or production) produces an item reported `missing` whose content
   a human reader can point to in the document, and whose location is *not*
   reachable by a deterministic heading-shape change. `axp-2008` does not
   qualify — it is reachable by a heading-shape change (§c row 7). The
   instrument already exists and needs no new code: count `status: "missing"`
   in any committed report's `items_summary`, then check each one against the
   filing. Threshold for reopening: **one** such item.
2. **A residual precision failure acquires an honest trigger.** If the
   escalation-policy successor named in ADR-019 §d ships and gives non-last
   span dominance a doc-level signal, then rows 4 and 5 of §c acquire a trigger
   they do not have today, and the question "should the fallback fire on it"
   becomes live — with the §c row 4/5 objections (relocation ambiguity, INV-S2
   contiguity) still to answer.
3. **The plain-text stratum gets an independent read and it disagrees.**
   ADR-019 §c and §g flag that six plain-text fixtures have **zero** OSS
   cross-check; their only evidence is auditor sampling. If a second
   independent instrument covering that stratum finds a recall class the
   HTML stratum does not have, the surface count in §b is understated and must
   be recomputed before this ruling stands.
4. **The CI, not the point estimate, moves.** ADR-019's sampled silent-failure
   rate is 1/30 with a 95% CI of [0.1%, 17.2%]. A larger sample that pushes the
   *lower* bound up materially would mean more defects than the debt table
   accounts for — but note this reopens the *precision* problem, so it argues
   for the escalation policy and the auditor loop first, and for a fallback
   only if the new defects turn out to be absences.

Conditions that are explicitly **not** sufficient: metric 11 reading 100%
(circular, §b); the deployed service being asked for an LLM; a filing merely
being large or old.

## f) What T13's cost model should contain instead

T12's ledger row says a shipped fallback's cost model lands in T13. Nothing
ships, so T13's §4 should carry, in place of a fallback cost model:

1. **The reported result, unchanged**: $0.00 per filing, structurally — no paid
   dependency exists (metric 10, n=44). Keep it stated as a measurement, not an
   estimate.
2. **The counterfactual from §d**, as the price of the road not taken: ~$0.14
   per median filing, ~$1.52 for the largest, ~$10 for one uncached pass over
   the 36-fixture corpus, with the chars/4 caveat and the note that the Haiku
   tier cannot hold the largest filings. This is what makes "$0" a *decision*
   rather than an absence.
3. **The addressable-surface count** (§b) as the standing justification, and
   metric 11 demoted in the prose from "the number that justifies or kills a
   fallback stage" to "a dependence monitor, vacuous while no fallback exists".
4. **The §e reopening conditions**, so the report says what would change the
   answer rather than implying the answer is permanent.

T13 must not run a live extraction over the corpus against a paid endpoint to
firm up the token figures — `count_tokens` or an offline tokenizer only. The
spend decision is the human's.

## g) Consequences

**New enumerated debt: `combined-multi-item-heading`.** `axp-2008` addresses
Part III under one heading naming four codes — verified in the **raw bytes**
(one `ITEMS\b` match in 1,296,375 bytes, at offset 1225493):
`<B>ITEMS&nbsp;10,&nbsp;11,&nbsp;12&nbsp;and&nbsp;13.</B>` + the four-item
title, immediately followed by the proxy incorporation sentence. Every heading
path in `src/sec10k/segment.py` matches one code per heading, so all four come
back `missing`. Recognizing a multi-code heading and fanning one span out to
several items is a new capability, forbidden by the T8 freeze without its own
ADR — the same reasoning that leaves `ba-2003` and `cvx-2015` unfixed.
Committed as `evals/adversarial/axp-2008-combined-part-iii.json` (`debt` suite,
runs every run, unscored, permanently red), watched red before this ADR was
written and with no fix attempted (hard rule 2).

**A held-out label is wrong, and correcting it is T14's.**
`evals/heldout/axp-2008-heldout.json`'s provenance concluded "American Express
addressed Part III without writing the item headings at all, and jumped
straight from Item 9B to Item 14." Its scan checked the **singular** forms
`Item 10`…`Item 13`, which do indeed occur zero times, and the conclusion
overreached from that. The case's four `item_present … "missing"` checks
therefore encode a label the document does not support: the correct status is
`incorporated_by_reference` ×4 (ADR-004 keyword-evidenced IBR, ADR-011 offsets
on the pointer text). This is the **sixth** time in this project that the
verification instrument rather than the pipeline was at fault
(`evals/heldout/README.md` counts the first five). The case still passes and is
left alone here; re-labelling it is taxonomy work and belongs to T14.

**`axp-2008` is burned.** `evals/heldout/README.md`'s burn rule names "a new
case written because of it" as influence, and the `gs-2002` precedent
(2026-08-17) established that a documented decision *declining* a fix burns a
case just as a fix does. This ADR's ruling rests in part on `axp-2008`'s
outcome, and §g authored a case from it. So it is burned as of 2026-08-19 and
counts in no held-out denominator from here. The physical relocation and the
replacement filing ride T14's expansion, where the held-out refresh already
lives; the fixture stays where it is in the meantime and the new debt case
references it in place, so nothing is duplicated. Held-out set is 5 effective
cases until then, recorded in that README's run history.

**Docs that promised a future decision are closed**, not left pointing at an
open question: `docs/architecture/overview.md` §10, `README.md`'s
deferred-LLM bullet, `docs/evals/evaluation-strategy.md` metric 11, and
`docs/analysis-report.md` §4 all now point here. `evals/metrics.py` metric 11
gains a `note` stating its vacuity in the one place a reader meets it in code —
the only code change this milestone makes.

**Not done, deliberately**: no new metric was added for the addressable
surface. It is a count of `status: "missing"` in a report the runner already
writes on every run, and adding a second way to compute a number the reports
already carry is the kind of speculative instrument the ADR-010 sin and the
repo's own laziness rule both argue against. §e names where to look instead.

## Verification

New case watched **red first**, before this ADR existed and with no fix
attempted: `axp-2008-combined-part-iii` — `[DEBT] STILL RED —
combined-multi-item-heading`, four failures (`item 10/11/12/13 not
incorporated_by_reference: missing`), three hygiene checks green.

`--suite invariant` 12/12 = 1.000 (+4 enumerated debt, unscored:
`axp-2008-combined-part-iii`, `ba-2003-asterisk-ibr`,
`cvx-2015-internal-pointer`, `msft-2013-website-block`).
`--suite fast` 44/44 = 1.000 (+ the same 4 debt rows).
`.eval-baseline.json` untouched (`{"fast": 1.0}`). No `--update-baseline`, no
`--no-verify`. **No paid API call was made in this milestone**, and no code
path capable of making one exists.
