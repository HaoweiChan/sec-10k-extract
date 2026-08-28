# Held-out set — frozen, not run

**Do not run these to see how they do.** They exist to estimate generalization
once, at a milestone, and a casual run spends that. The rules are in
`docs/evals/evaluation-strategy.md`; this file is the inventory and the
provenance.

Why this is structural and not honour-system:

- `evals/run.py` `CASE_DIRS` covers `golden/` and `adversarial/` only, so
  `--suite fast|all` **cannot** reach this directory. Reaching it takes an
  explicit `--dir evals/heldout`.
- `--dir` runs ignore `--no-report`: the runner writes a report with the git
  SHA embedded, every time. A held-out run cannot be traceless.
- Reports are committed **before** any fix, so run-before-fix ordering is
  provable from history rather than asserted.

## Burns taken

**2026-08-28 — TWO cases burned in one sweep** (ADR-042 §h), during a directed
run of a curated list of eight deliberately hard recent filings. Both burns
are influence, both are declared, and the moved case files carry the full
record plus every provenance claim they had.

1. **`c-2025-heldout` → `evals/adversarial/c-2025-cross-reference-index.json`.**
   Measured pre-fix: `doc_status ambiguous`, `meta.coverage 0.0000`, all 23
   items `missing`, ZERO candidates in 1,163,303 chars — because Citi's
   cross-reference index writes `1. Business 4–36` with neither the word Item
   nor the word Page. That outcome drove the Citi extension of
   `src/sec10k/xref.py`, which is influence by any reading. Ordering stated
   rather than implied: the measurement preceded the fix, but this was a
   directed sweep and not a milestone run, so no report was committed between
   the two. The frozen item-1A anchor written on 2026-08-26 lands inside the
   resolved region, which is the case's own strongest evidence and the reason
   it is worth keeping as debt.
2. **`spg-2019-heldout` → `evals/adversarial/spg-2019-item16-annex.json`.** The
   rarer route: the FIX made a FROZEN LABEL WRONG. `min_chars: 16 >= 100`,
   authored 2026-08-17 and never run, was being cleared only because the
   trailing-annex bug inflated item 16's span with 23 KB of exhibit index.
   SPG FY2019's item 16 body is the word "None." — no floor above ~35 is
   satisfiable. Adjudicated in the open: the pipeline is right and the label
   is wrong. Changing the label is influence, so the case cannot stay here.

**REPLACEMENTS ADDED 2026-08-28, same day, labels frozen before either filing
met the pipeline** — the debt is paid rather than carried:

* **`aig-2025-heldout`** — AIG FY2024, 12.3 MB. A RUNNING-HEADER filing: every
  page of an item reprints that item's name as page furniture
  (`TABLE OF CONTENTS / ITEM 1A | Risk Factors`), so the blind reader counts
  `Item 7` 52 times and `Item 8` 95 times in one document, against 2 apiece for
  a conventional filer. Nothing in the corpus has that shape — it is a
  competing copy of the heading at the top of every page of its own section,
  not one TOC block in the front matter.
* **`smci-2025-heldout`** — Super Micro FY2024, fiscal year ended **June 30**
  (a non-December year end, which the set is thin on), and the LATE one: a
  Form 12b-25 NT 10-K preceded it. Part III is inline rather than incorporated
  by reference, which is what a filer does when the proxy does not exist yet.

Both were read with `tasks/reviews/heldout_blind_scan.py`, which imports
nothing from `src/` — that independence is what makes "frozen before the first
run" mean something rather than being an honour-system claim. Every anchor's
occurrence count is recorded in the case's `provenance`.

The set is six cases again (aig-2025, cost-2022, csco-2016, mrk-1995,
pgr-2023, smci-2025).

## Burn rule

A case is burned the moment its labeled outcome influences implementation — a
fix, a threshold, a new case written because of it. **Re-running does not burn
it; influence does.** A burned case goes through `failure-triage`, moves to
`evals/adversarial/`, and is replaced with a fresh filing at the next
expansion. Budget 2 spare filings per milestone for that cycle.

**Amendment, 2026-08-26 — owner decision, taken on the D9 escalation
(PR #56 R3/R8; `specs/decisions/ADR-034-pointer-and-fanout-rulings.md` §g).**
A **decision that cites a held-out outcome but authors no case, moves no
fixture, changes no threshold and ships no code does NOT burn the case.**
Influence still burns; a *ruling* is not influence.

**D9's own two artifacts, adjudicated** (PR #56 R14). D9 did raise a threshold
and did ship a `.py` file, so the clause above is applied to it in the open:

1. **`evals/adversarial/ledger-line-refs.json` `min_refs` 9 → 11.** A
   ledger-hygiene floor: how many `<file>:<line>` citations `tasks/TODO.md` must
   carry before the check fails closed. Not an extraction threshold, reads no
   filing, no relationship to any held-out label, fixture or outcome.
   **Not the influence this rule targets.**
2. **`tasks/reviews/d9_class_scan.py`, and its `BODY_MAX = 700`.** This one
   needs an argument, not a dismissal — the file reads
   `evals/heldout/fixtures` directly and its knob is a number someone chose.
   *Why it reads held-out at all*: D9's ledger row required measuring both
   classes' prevalence **including on the held-out set**; reading a fixture to
   report a count about it is the assignment, not tuning against it.
   *Why `BODY_MAX` is not fitted to held-out labels*: 700 sits in a plateau
   whose **both edges are dev values** — nearest below `intc-2002` item 5 at
   629, nearest above `ibm-1997` item 5 at 805 — so every bound in 630..805
   gives an identical dev result and nothing held-out defines that interval.
   One held-out span falls inside it, `mrk-1995` item 8 at 738, and that item is
   an *external*-document pointer ("incorporated by reference to pages 38
   through 49 … of the Company's 1995 Annual Report") which the class rule
   rejects anyway, exactly as its siblings 5 and 7 already are. **Every figure
   D9 published is therefore unchanged across the whole dev-determined
   plateau**, and the constant was written once and never revised
   (`git log -p -- tasks/reviews/d9_class_scan.py`).
   **Not the influence this rule targets.**

   *Stated honestly, the part that does not fully close*: the dev plateau runs
   to 805 while the held-out set is unchanged only up to 738, so a different
   in-plateau choice — 780, say — would have admitted `mrk-1995` item 8 as a
   candidate. It would then have been rejected, changing no published number,
   which is why the verdict holds; but "any in-plateau value is equivalent" is
   true of D9's *conclusions*, not of the candidate list. A reader who wants the
   stronger property should read the four bullets above as the claim and this
   paragraph as its limit.

*Why this is the right line.* The rule exists to stop labels being tuned
against — the danger is an implementation shaped, however indirectly, by
knowing what the held-out filings do. A ruling that shapes no extraction
behaviour tunes nothing: reading an outcome and writing down "we are not
building this" leaves the pipeline exactly as unable to pass the exam as it was
before. (This paragraph previously argued that no artifact in the tree could
have absorbed the labels. That was **false as written** — `d9_class_scan.py` is
such an artifact — and it is withdrawn; the two artifacts are adjudicated in the
numbered list above instead. PR #56 R14.)

*What this now permits that it did not before, stated because it is a real
loosening.* A future decision row may cite `intc-2025`'s and `c-2025`'s
outcomes, and the next one may too, without either case ever being burned.
Repeated over enough rulings that is a slow leak: the labels become common
knowledge to whoever writes the milestones even though no code was touched,
and the exam's value decays without any single decision being wrong. The
owner took that risk knowingly, against the alternative of burning both cases
and destroying D11's exam outright — D11's ledger row and `c-2025`'s own
provenance each require it to pass those filings having never trained on them.

*What would make this amendment wrong.* Any of: (a) a decision that cites a
held-out outcome is later found to have carried a threshold or a code change
after all — then it was influence and the exemption did not apply to it;
(b) D11 ships and passes `intc-2025` or `c-2025` in a way that traces back to
a decision document rather than to the dev proxies (`cvx-2015`, `jpm-2024`),
which would show the leak is real and not theoretical; (c) the count of
rulings citing an unburned held-out outcome grows past a handful — the
amendment assumes this is rare, and it stops being safe when it stops being
rare. Instrument for (c): `grep -rl 'intc-2025\|c-2025' specs/decisions/`.

## Authoring discipline

Every case here was verified by an **independent tag-strip regex scan that
imports nothing from `src/`** — used only to establish *what a document contains
at paragraph granularity*, and nothing finer. **Anything character-level must be
read from the raw bytes or not claimed.** The scan replaces tags with spaces
where the normalizer joins within a block, so the two disagree about exactly
that; it has produced a wrong claim **four** times (H1's `xom-2021` Item 9C,
H2's `pgr-2023` floating comma, a `csco-2016` Item 16 assertion declined for
this reason, and T9's `wfc-2008` heading shape — the last one at *paragraph*
granularity, which is the level this scan is supposed to be trusted at, so the
rule is now that a structural reading is a hypothesis until a run tests it). The extractor has never been invoked on any of
these files. Where a case records a prediction about how the pipeline will
behave — GS 2002's transitional numbering, Costco's em-dash separators, Exxon's
missing Item 6 — that prediction is written into the provenance *before* the
first run, so it cannot be retrofitted afterwards.

## Inventory

| Fixture | Source | Accession | Filed | Period end | Stratum | Bytes |
|---|---|---|---|---|---|---|
| `pgr-2023/filing.htm` | sec.gov/Archives/edgar/data/80661/000008066124000007/pgr-20231231.htm | 0000080661-24-000007 | 2024-02-26 | 2023-12-31 | iXBRL, **fire/marine/casualty insurance** — restores the financial-sector coverage. Sits 16 days past the Item 1C era boundary, and its cover carries a **floating comma** (`December 31 , 2023`). Replaces `gs-2002`, burned 2026-08-17 | 1,474,219 |
| `csco-2016/filing.htm` | sec.gov/Archives/edgar/data/858877/000085887716000117/csco-2016730x10k.htm | 0000858877-16-000117 | 2016-09-08 | 2016-07-30 | mid-2010s HTML, computer-communications equipment; 52/53-week FY ending in **July**. Replaces `jnj-2016`, burned by H1 | 4,476,127 |
| `cost-2022/filing.htm` | sec.gov/Archives/edgar/data/909832/000090983222000021/cost-20220828.htm | 0000909832-22-000021 | 2022-10-05 | 2022-08-28 | iXBRL, retail, **August** FY end; separates every item code from its title with an **em dash**, a heading shape no dev fixture contains | 1,861,894 |
| `mrk-1995/filing.txt` | sec.gov/Archives/edgar/data/64978/0000950130-96-000896.txt | 0000950130-96-000896 | 1996-03-20 | 1995-12-31 | pre-2001 txt, **pharmaceutical** (the sector jnj-2016 took with it when H1 burned it); form 10-K405; earliest filing in either set that predates Item 7A, so the 14-code taxonomy is exercised by a real document; **no table of contents at all** | 322,618 |
| ~~`axp-2008/filing.htm`~~ | sec.gov/Archives/edgar/data/4962/000119312509041008/d10k.htm | 0001193125-09-041008 | 2009-02-27 | 2008-12-31 | **BURNED AND MOVED 2026-08-19 (T12, ADR-020)** — now `evals/fixtures/axp-2008/filing.htm`, case now `evals/adversarial/axp-2008-combined-heading-burned.json`. legacy HTML, **crisis-era financial**. It DOES have a table of contents — raw bytes carry `<A NAME="toc"></A>TABLE OF CONTENTS` at offset 13689, and the contents page lists Part III's four items individually — but the pipeline's `toc_manifest` comes back **empty** on it, because those entries are bare `10.` / `11.` / `12.` / `13.` with no `Item` prefix and so generate no heading candidates. *(Corrected 2026-08-19, repair round 2: this row and the original case provenance both claimed 'no table of contents', and the stratum rationale — a filing that gives the TOC machinery nothing to work with — was built on it. The machinery does come back empty; the stated reason was wrong.)* The original row here also read "the strings 'Item 10' through 'Item 13' occur **zero** times: Part III is addressed without its item headings" — the first clause is true of the SINGULAR forms and the second does not follow from it. There is one combined heading, at raw offset 1225493: `<B>ITEMS&nbsp;10,&nbsp;11,&nbsp;12&nbsp;and&nbsp;13.</B>` plus the four-item title. See the burn note below. Replaced `wfc-2008`, moved to the dev set before its first run | 1,296,375 |
| `spg-2019/filing.htm` | sec.gov/Archives/edgar/data/1063761/000155837020001135/spg-20191231x10k.htm | 0001558370-20-001135 | 2020-02-21 | 2019-12-31 | iXBRL, **REIT** — Item 2 Properties runs ~101K chars of mall-by-mall tables, an order of magnitude past any other Item 2; the FY2017–FY2020 window; the first filing in either set with a **present and substantive Item 16**; 9.8 MB — third-largest committed filing anywhere in the repo since D6 added `c-2025` (16.15 MB); `jpm-2024` (12.85 MB, dev set) is second. It was second-largest when this row was written; the clause was corrected under PR #52 R3 | 9,812,403 |
| ~~`intc-2025/filing.htm`~~ | sec.gov/Archives/edgar/data/50863/000005086326000011/intc-20251227.htm | 0000050863-26-000011 | 2026-01-23 | 2025-12-27 | **BURNED AND MOVED 2026-08-27 (D11, PR #58)** — now `evals/fixtures/intc-2025/filing.htm`, case now `evals/adversarial/intc-2025-collapse-burned.json` (`debt` suite, still red). See the burn note below. iXBRL, **post-2019 Intel reorg layout** — narrative organized by Intel's own section names and mapped to SEC item codes ONLY by a trailing `Form 10-K Cross-Reference Index`. All 23 item codes occur **exactly once each**, all of them index rows in the last 0.63% of the document; there is no body item heading anywhere. Added by **D6** as one of the two 2026-08-24 demo-failing filings; the maximal form of the ADR-015 stub-collapse trap, a layout class no fixture covers (`intc-2002` is pre-reorg) | 3,320,720 |
| `c-2025/filing.htm` | sec.gov/Archives/edgar/data/831001/000083100126000011/c-20251231.htm | 0000831001-26-000011 | 2026-02-20 | 2025-12-31 | iXBRL, **money-center bank** — the postmortem's #1 known-difficult class, and Citigroup appeared in no set anywhere. Contains **zero** `Item <digit>` strings naming a 10-K item: the whole form mapping is a `FORM 10-K CROSS-REFERENCE INDEX` of BARE codes (`1.`, `1A.`, …), the `axp-2008` shape applied to every item rather than four. Added by **D6** as the second demo-failing filing. 16.1 MB, the largest file in either set | 16,150,764 |

Re-fetch pattern, same as `evals/fixtures/README.md`:

```bash
curl -H "User-Agent: Haowei Chan hwchan42@gmail.com" <url> -o <dest>
```

## T9 refresh, 2026-08-17

Two cases **retired** to `evals/golden/` rather than burned, for two reasons
each and in this order. *Exhausted*: `ko-1997` and `xom-2021` were run at H1,
H1b and H2, and both carry labels corrected after H1's triage, so from H1b
onward they measured the correction rather than the extractor — this file said
as much already. *Contaminated*: the T9 tranche-2 blast-radius scan for the
semicolon ruling (ADR-015 §3) ran the pipeline over every fixture on disk,
these included, and observed that three of their item statuses moved. No case
file was opened and no labelled outcome was consulted, which is weaker than a
burn — and the remedy is to retire the fixtures rather than argue the
distinction. Their coverage is not lost; it moved to the scored side.

One case **never entered the set**. `wfc-2008` was fetched for this refresh and
moved straight to `evals/fixtures/` because reading its scan produced a belief
about how the pipeline would resolve its headings, and that belief implied a
code change. The line this draws is worth keeping: **a prediction you would act
on is influence; a prediction you merely record is not** — freezing predictions
into provenance, as every case here does, stays fine. (For the record the
prediction was wrong, in the instrument's now-familiar way, and the filing
turned out to carry a real defect worth two ADR rulings.)

Three cases **added**, and all three carry something no held-out case has ever
carried: **length floors and cross-item exclusions**. Every earlier case here
asserted presence and status only — the pre-B audit flagged it as finding 4 and
the H2 triage repeated it: *"a TOC-collapsed extraction would clear them."* T9
tranche 2 proved that was not hypothetical. Intel 2002 resolved every item to an
18-to-490-char stub, reported `success_with_warning`, and satisfied every
structural check in the vocabulary; a floor of 2,000 chars on Item 1 would have
caught it instantly. Floors are set from the scan at paragraph granularity with
wide margins, so they cannot encode the scan's known disagreement with the
normalizer.

## Disjointness from the dev set

**One filer now appears in both sets, deliberately: Intel.** `evals/fixtures/intc-2002/`
is the 2001–2019 legacy-HTML filing whose trailing echo index produced ADR-015;
`intc-2025` here is the post-2019 reorg layout, which shares the filer and
nothing else — different format era, different item taxonomy, different
document structure, and the 2002 filing has real body item headings while the
2025 one has none at all. The owner's D6 placement call (postmortem §7) is that
the two demo-failing filings are the exam the D11 slow path must pass, and no
substitute filer files this layout. Recording it rather than asserting the old
blanket claim: filer-level leakage from `intc-2002` is possible in principle
and is the one contamination channel this set does not close. Citigroup appears
nowhere in the dev set.

Sector coverage held here that `evals/fixtures/`
does not have at all: fire/marine/casualty insurance, computer-communications
equipment, retail warehouse, pharmaceutical, real-estate investment trust,
money-center banking.
Fiscal-year ends held here: July (52/53-week) and August — every dev fixture
ends in December, June, May, January or September.

Coverage that has MOVED to the dev side rather than being lost, as cases
retired or were burned: pharmaceutical and the January 52/53-week year end
(`jnj-2016`, burned at H1 — pharma is restored here by `mrk-1995`), the
Sarbanes-Oxley interim numbering (`gs-2002`, burned 2026-08-17), beverage and
the first Item 7A cohort (`ko-1997`), petroleum and the FY2021 9C cohort
(`xom-2021`), the crisis-era two-sentence pointer (`wfc-2008`, moved before
its first run — the stratum itself stays here on `axp-2008`), and — 2026-08-27 —
the **post-2019 reorg / cross-reference-index layout and the modern
semiconductor sector** (`intc-2025`, burned by the first billed live run).

Coverage that is now LOST rather than moved, stated separately because the
distinction matters: **nothing about the reorg layout is still held out.**
`c-2025` carries a cross-reference index too, but a different one — bare codes
in a money-center bank's filing, not Intel's named-section mapping — so it does
not restore this stratum, it is its own. The dev side keeps the DOCUMENT and so
keeps the ability to test against that shape; what is gone is the ability to
measure generalization to it, which is the only thing a held-out case was ever
for. Of the two filings D11's ledger row named as its exam, one remains.

**Burn, 2026-08-27 — `intc-2025`. From a real run, and a billed one.** The first
held-out run this repo has ever paid for. D11's escalation ladder was exercised
live against `intc-2025` with `escalate=True` on 2026-08-27, and it cost
**$0.899858 over 2 calls** — rung 1 `openai/gpt-5-mini` $0.004498 (12,099 tok),
rung 2 `anthropic/claude-opus-5` $0.895360 (170,880 tok). It resolved **nothing**:
`routing.resolved` came back empty.

*What the run showed.* The deterministic half was exactly right: `meta.coverage`
0.0033, `doc_status` `ambiguous`, items 1/7/8 flagged, D8's trigger fired as
designed. Rung 1 also behaved correctly — it returned valid JSON
`{"1": null, "7": null, "8": null}`, honestly reporting that it could not locate
those items inside its 60,000-char window, and the router treated that as "no
locatable span". The failure was the **client**: rung 2 returned
`completion_tokens: 2048` — exactly the `max_tokens` being sent — with **empty
content**, and that empty string reached `json.loads` as an unexplained
`JSONDecodeError`. OpenRouter documents the cause: for Anthropic models
`max_tokens` must be strictly higher than the reasoning budget, or the whole
allowance is spent thinking and nothing is left to answer with.

*So `escalate.verify` has still never met a real model answer.* The exam tested
the transport and found it broken before the trust boundary was ever reached.
That is the honest summary of what $0.899858 bought.

*Why this burns, and why the burn is taken rather than argued around.* Fixing
the client is shipping code in response to a held-out outcome — a new
`max_tokens`/`reasoning` split, a recorded `finish_reason`, a new named
`empty_completion` outcome, and a new case
(`evals/adversarial/escalation-empty-completion.json`) built from this run's own
cached response. That is influence four times over under the rule above, and
the 2026-08-26 amendment does not reach it: the amendment exempts a *ruling*
that ships nothing, and this shipped. **Owner ruling, 2026-08-27: the burn is
taken and there is no second amendment.** Reproducing the same bug on a dev
fixture first was considered and rejected as laundering the evidence without
laundering the knowledge. Triaged under `failure-triage` before any fix
(`input-variant`; the reasoning is in the moved case's `triage` block), then
moved in the same milestone per the `gs-2002` and `axp-2008` precedents — and
like `gs-2002`, the EXISTING case was relocated rather than a new one authored:
`evals/heldout/intc-2025-heldout.json` → `evals/adversarial/intc-2025-collapse-burned.json`
(`debt` suite, still red, unscored), fixture → `evals/fixtures/intc-2025/`.

*What this costs the exam, stated plainly.* **`c-2025` stays here, unread and
unrun** — it was not touched by this run and must not be. **D11's surviving
exam is therefore one filing.** That is the honest position, and it is thin:
one document cannot estimate generalization, and D11's ledger row asks the slow
path to pass filings it never trained against.

*One more thing the burn removed.* `evals/adversarial/heldout-provenance-claims.json`
pinned 8 byte-level provenance claims against this fixture; that check scans
`evals/heldout/` only, so those 8 pins are enforced nowhere now. The floor entry
was removed rather than left to fail closed, and the removal is recorded in that
case's own provenance. Replacement obligation (this README budgets 2 spare
filings per milestone) is logged as a debt row in `tasks/TODO.md`; no
replacement was fetched here.

*And what it gave back.* Moving the fixture to the dev side changes the dev
census, which ADR-036 §c1 publishes: `low_item_coverage` now fires on **2 of 44**
dev documents and — for the first time — on a **real EDGAR filing** (1 of 29)
rather than only on the synthetic `xref-index-collapse`. The round-1 admission
that "the dev positive set has size one and is synthetic" is no longer true. The
same move roughly halves the cost argument for the narrow trigger: ADR-036 §d4's
wide-vs-narrow ratio falls from 93.6× to **7.1×**, because the narrow trigger now
escalates a 517,976-char real filing. Both figures are re-derived by
`tasks/reviews/d11_sweep_cost.py`.

## Run history

| Run | Date | Score | Outcome |
|---|---|---|---|
| **H1** | 2026-08-16 | **1/5** | `evals/report/20260816-225101-fast.json`, triaged in `docs/evals/audits/2026-08-16-h1-heldout-triage.md`. Two real extractor findings, four labels the author got wrong. `jnj-2016` burned and promoted to `evals/adversarial/`; `gs-2002`, `ko-1997` and `xom-2021` label-corrected from their source documents. |

After H1 the set is no longer pristine: `cost-2022` is the only case never
observed failing, and three carry corrected labels. H1 is the only clean
generalization estimate those three will ever provide, and later runs on them
measure regression, not generalization. `csco-2016` is fresh.

**H1b, 2026-08-16, 4/5** — re-run after the ADR-013 fixes. Read it carefully,
because the number flatters the result: of the four passes only `cost-2022`
(clean in H1) and `csco-2016` (fresh, never observed) are generalization
evidence. `ko-1997` and `xom-2021` pass because their labels were corrected,
which measures the correction, not the extractor. The single failure,
`gs-2002`, is the era-model limitation ADR-013 deliberately declined to fix and
is enumerated debt, not a surprise. The honest one-line summary is: **one fresh
unseen filing, 4.5 MB and never observed, passed on the first attempt** — and
even that is a presence-and-status result, not a boundary one: `csco-2016` and
`cost-2022` carry no anchors and no length bands, so a TOC-collapsed extraction
would clear them (pre-B audit finding 4).

**Burn, 2026-08-17** — `gs-2002` moved to `evals/adversarial/` as enumerated
debt. It had been run twice, its failure mode is published in four documents,
and ADR-013's decision *not* to fix the era model was taken with its outcome in
hand; the burn rule names "a threshold choice" as burning, and a documented
decision to decline a fix is at least as much influence. Counting it in a
held-out denominator would have overstated that denominator. Replaced by
`pgr-2023`, which carries two predictions recorded before its first run.

> **Narrowed 2026-08-26 by the Burn-rule amendment above (PR #56 R17).** The
> clause "a documented decision to decline a fix is at least as much influence"
> is **no longer the rule** — the amendment says a ruling that ships no case,
> fixture, threshold or code does not burn. This entry is left standing as the
> reasoning of its date rather than rewritten. **The `gs-2002` burn itself still
> stands, on another limb**: ADR-013 did not merely decline a fix, it shipped
> code and set thresholds — its ruling promotes a bare heading's title when it
> clears `SIM_FLOOR` and escalates `doc_status` to `ambiguous` past a 25%
> missing-item threshold. That is influence under the amended rule as squarely
> as under the original, so the burn is unaffected and no replacement decision
> is needed.

**H2, 2026-08-17, 5/5** — the T8 milestone run, triaged in
`docs/evals/audits/2026-08-17-h2-heldout.md`. Worth less than H1's 1/5: only
`csco-2016` and `pgr-2023` carry generalization content, and neither has anchors
or length bands, so passing means the right items with the right statuses and
says nothing about their boundaries. `ko-1997` and `xom-2021` pass because their
labels were corrected after H1. Of the two predictions frozen into `pgr-2023`
before its first run, the Item 1C era boundary held and the floating-comma
prediction was wrong — its premise was an artifact of the verification scan
itself, which is why the authoring rule above is now stated more tightly.

**H3, 2026-08-17, 4/6** — the T9 tranche-4 run, triaged in
`docs/evals/audits/2026-08-17-h3-heldout.md`. **Both failures were mine**, and
in the same way: a length floor derived from the gap to the next heading is
meaningless for the LAST item, because that gap runs to the end of the file and
sweeps in the exhibit index and signature block the extractor is right to cut.
`spg-2019` item 16 is the single word "None." (the ~55,700 chars I floored
against were the exhibit index annexed to it) and `axp-2008` item 15 is 745
chars of pointers. Fifth time the instrument rather than the pipeline has been
at fault. Both floors corrected from the documents and replaced with cross-item
exclusions, which assert the boundary directly instead of proxying for it; on
the H1 precedent those assertions now measure the correction. Re-run 6/6.

The honest headline is neither number: **three fresh, never-observed filings —
a 1996 pharmaceutical text submission with no contents page, a crisis-era bank
that omits four item headings outright, and a 9.8 MB REIT — came out with every
item, status, label and boundary correct on the first attempt**, and `mrk-1995`
is the first held-out pass in this project's history that says anything about
BOUNDARIES rather than only presence and status. Of three frozen predictions,
the two about the extractor held (`axp-2008`'s missing fraction of 0.20 landing
just under `MISSING_MAX`, `spg-2019`'s transposed Item 7A title resolving
normally) and the one about a document was wrong. No support for ADR-017 was
gained: AXP's pointers use the single-sentence phrasing the old rule already
matched, and that claim was checked and withdrawn rather than made.

**Burn, 2026-08-19 — `axp-2008`. Moved, not deferred.** Not from a run: from T12's ruling. Reading
H3's committed report while enumerating the fallback-addressable surface
([ADR-020](../../specs/decisions/ADR-020-fallback-not-justified.md) §b) turned
this case's outcome — items 10–13 `missing` at 0.40 — into load-bearing evidence
for a documented decision to decline a fix, and produced a new case from it
(`evals/adversarial/axp-2008-combined-part-iii.json`). The burn rule names both
of those as influence, and the `gs-2002` precedent above already established
that declining a fix burns a case as surely as fixing does. So `axp-2008` counts
in no held-out denominator from here. Per the rule above and the `gs-2002` precedent it was **moved in the same milestone**: the case to `evals/adversarial/axp-2008-combined-heading-burned.json`, the fixture to `evals/fixtures/axp-2008/`. The held-out set is **5 cases / 101 items**, enforced by the file system rather than asserted here — nothing in `evals/run.py` could have excluded a burned case that stayed in this directory, so leaving it would have meant the next `--dir evals/heldout` run scoring a contaminated, known-mislabelled case as green.

It also carries a wrong label. This case's provenance concluded that American
Express "addressed Part III without writing the item headings at all, and jumped
straight from Item 9B to Item 14". The **singular** strings `Item 10`…`Item 13`
do occur zero times, which is what the verification scan checked — but the raw
bytes contain exactly one `ITEMS\b` match, at offset 1225493:
`<B>ITEMS&nbsp;10,&nbsp;11,&nbsp;12&nbsp;and&nbsp;13.</B>` plus the four-item
title, immediately followed by an explicit proxy incorporation by reference. The
correct status for all four is `extracted` — the body is not pointer-only (ADR-004
shape 3: ~1,139 chars of Reg S-K Item 406 code-of-ethics prose after the proxy
pointers, against ADR-007's 300-char remainder threshold), which is what
`segment.classify` returns on it. Either way `missing` is not the correct label,
so the four `item_present` checks were dropped in the move rather than
re-enshrined; the desired state is asserted, and kept permanently red, by
`evals/adversarial/axp-2008-combined-part-iii.json`. **Sixth
time the instrument rather than the pipeline has been at fault** — the
authoring-discipline section above counts the first five, and this one is a
scan that checked the singular form of a string and generalized past its own
evidence. The move is done; only a replacement filing for the
crisis-era stratum rides T14's expansion.

Next refresh should retire `csco-2016` and `cost-2022`, now run three times each,
and replace `axp-2008`.

## D6 expansion, 2026-08-26 — the hard set

Two filings added: `intc-2025` and `c-2025`, the two 10-Ks that failed live at
the 2026-08-24 demo (`docs/evals/audits/2026-08-25-demo-intel-citi-postmortem.md`).
The set is now **7 cases**. These two are not a refresh and not a stratum fill;
they are an **exam**, placed here by the owner's call in postmortem §7 precisely
because they are the filings the D11 slow path exists to complete and therefore
the filings it must never train on. Development iterates on dev-side proxies
(`cvx-2015`, `jpm-2024` for the pointer class; a synthetic cross-reference-index
fixture if D11 needs one, added red-first).

**Both are expected to fail the baseline run. That is the recorded outcome of
D6, not a defect to fix in it** — the fixes are D8 (item-level escalation), D9
(the decision row) and D11 (tiered escalation).

Each case carries a prediction frozen into its provenance before the first run.
Between them they should exercise **both faces** of the D8 sensor problem
(postmortem §8): `intc-2025` is the high-confidence face (23 index rows are the
only heading candidates in the file, they match canonical titles, so spans
collapse onto them at 0.95) and `c-2025` is the low-confidence face (no
`Item <digit>` string exists in the file at all, so nothing matches and every
item lands `missing` at 0.40). Where my structural reading disagrees with what
the demo reported — it does, on Citigroup's 0.95 — the disagreement is written
into the case rather than resolved in my favour.

Both cases were authored from an independent tag-strip regex scan importing
nothing from `src/`, with **every character-level claim re-read from the raw
bytes**. That rule paid for itself immediately: `c-2025`'s cover renders as
`December 31 , 2025` in the scan — the `pgr-2023` floating comma, the second of
the six failures recorded above this section (the H4 write-up below became the
seventh; the running count is stated once, at the H4 entry, and not repeated
here) — and the raw bytes show it is a tag
boundary (`December&#160;31</ix:nonNumeric>, 2025`). The claim was withdrawn
before it was made rather than corrected after a run.

**H4, 2026-08-26, 5/7** — the D6 baseline, `evals/report/20260826-005839-fast.json`,
git SHA `9b2ace08` = the labels-only commit, so run-after-labels is provable from
history. The two new cases failed and the five incumbents passed. **No fix, no
label correction, and no triage follows in D6** — the failures are the
deliverable. For the seventh time the reader should ask whether the instrument
or the pipeline is at fault, and **the seventh time the answer is the
instrument** — not in the labels, which held, but in this very write-up, which
first reported `c-2025` as 22 items `missing` and named one deviation from its
frozen prediction when the committed report shows 21 `missing`, two `omitted`,
and TWO deviations. See the correction at the `c-2025` paragraph below; it is
the entry that takes the seventh slot in this file's tally.

What IS true, and is the reason the run is still worth what it cost, is
narrower than the sentence that used to stand here: **the extractor behaved as
both cases predicted it would** — the stub collapse at 0.95 on `intc-2025` and
the total non-resolution at 0.40 on `c-2025`, each frozen into its provenance
before the run. That is the first time a prediction about the pipeline has held
on this set. It is not the same claim as "both frozen predictions came true":
`c-2025`'s prediction also said all 23 items would be `missing` at 0.40, and two
of them were not.

`intc-2025` — **branch (a), the predicted stub collapse, and worse than
`intc-2002` was.** All 23 items `extracted`, all at confidence **0.95** via
`heading_strict`, `doc_status` **`success_with_warning`**. Every span is a row
of the trailing cross-reference index: 20 to 226 chars, **1,727 chars in
total** across the whole 10-K, against a 571,466-char tag-strip scan of the
document (~0.3%). ADR-015 closed by saying "the next mis-dated item repeats
this exactly"; it did, on the same filer, 23 years later. Note what did **not**
fire: `no_empty_success` passed, because `NO_EMPTY_SUCCESS_FLOOR` is 1,000 and
1,727 clears it — the check named for this failure mode is 727 chars short of
catching the maximal instance of it. The five red checks are the four
`min_chars` floors and the one `text_contains` anchor; every structural check
(`expected_set_complete`, `only_items`, `known_items_only`, `verbatim`,
`no_overlap_ordered`, `deterministic`) passed. That is the pre-B audit's
finding 4 demonstrated on a real filing: **a presence-and-status case would
have scored this document green.**

`c-2025` — **as predicted, the opposite face.** 23 items, **zero** extracted;
**21 `missing` at 0.40 and TWO `omitted` at 0.75 — items 9C and 16** — with
`doc_status` **`ambiguous`**. **TWO** deviations from the frozen prediction, which
said all 23 would be `missing` at 0.40. *(Corrected 2026-08-26 under PR #52 R2: this
paragraph, the `353e8f1` commit message and the `tasks/TODO.md` D6 row all read "22
`missing`" and "the one deviation", dropping item 16 — an asserted number the
committed artifact does not support, in the file whose stated purpose is that
predictions cannot be retrofitted. The seventh entry in this file's tally of the
instrument rather than the pipeline being at fault. Repro:*
`python3 -c "import json,collections; r=json.load(open('evals/report/20260826-005839-fast.json')); print(collections.Counter((i['status'],i['confidence']) for c in r['results'] if c['id']=='c-2025-heldout' for i in c['items_summary']))"`
*→ `Counter({('missing', 0.4): 21, ('omitted', 0.75): 2})`.)* Item 16 is the more
interesting of the two deviations: the case's own declination (a) called `omitted`
"the natural reading" for item 16 and declined to assert it anyway, on the
`csco-2016` precedent — and the run then produced exactly that. Declining was
still right, because the reasoning was about what the document states rather than
about what the pipeline would do; but the outcome is now on the record. The tension the case flagged is
also resolved, and not in my favour on the surface: the demo reported
`conf 0.95` on Citigroup and this run reports 0.40 — the structural reading was
right about *this* document, so either the demo ran a different Citigroup
filing or the panel number seen there came from somewhere else. Recorded as an
open discrepancy for D7/D8, not resolved here.

Together they are the postmortem §8 asymmetry on one page: same sensor, same
absence of a usable "the fast path is stuck" signal, 0.95 on one document and
0.40 on the other. Both cases stay **untouched** — D8/D9/D11 must not read
their labels while iterating, and the first fix or threshold taken with either
outcome in hand burns that case under the rule above.

**Amended 2026-08-26 by the same owner decision as the Burn-rule section.**
This sentence originally also named "declined fix" as burning, and D9
(`ADR-034`) is exactly that: a decision row that read both outcomes and ruled
on them while shipping no code. Under the sentence as first written both cases
were burned; the owner ruled to amend the rule rather than apply it, so
**neither case is burned and both remain held out**. `intc-2025` and `c-2025`
are still unseen by every code path, and D11's exam is intact. The clause is
narrowed here rather than left to contradict the Burn-rule section above it.
