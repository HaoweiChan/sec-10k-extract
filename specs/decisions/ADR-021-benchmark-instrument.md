# ADR-021 — T13: what the performance benchmark measures, and why the old §3/§4/§5 numbers had to be thrown away

Date: 2026-08-20. Status: accepted. Implements T13/A5. Adds one dev-only
instrument, `evals/bench.py`. Changes no pipeline code, no eval case, no
baseline. Supersedes the measurements — not the structure — of
`docs/analysis-report.md` v3 §3, §4 and §5, which v4 replaces. **Amended in
place 2026-08-23 (D2, the re-publication):** the run of record is now
`evals/report/20260823-185707-bench.json` (n=41, 13 synthetic, 4 refusals;
git `ba263ee`, clean tree; the middle of three committed runs on four of six
headlines — §b11 amendment); `20260820-031540` (n=37, `13761cc`) stays named
as the previous run of record and its figures survive here only inside dated
notes. What changed and why is §g; §b8, §b11, §b12, §c, §d and Verification
carry dated amendment notes; §b13 is new (the `tables=True` column); the
`--check-docs` fail-closed rule and its gate wiring are §b12's amendment.

**Ruling**: add `evals/bench.py` (stdlib-only, dev instrument, `evals/oracle.py` precedent) as the committed, re-runnable source of every perf/cost number in `docs/analysis-report.md`; throw away v3's §3/§4/§5 figures, which cited nothing and were measured over a stale 21-fixture corpus.
**Because**: T13's own Validation gate ("every number measured from committed `evals/report/` runs, none guessed") was not met by ad-hoc prose timing that left nothing reproducible behind.
**Enforced by**: `evals/bench.py --self-check` and `evals/bench.py --check-docs evals/report/20260823-185707-bench.json` — both run by `.githooks/pre-commit` and `.github/workflows/ci.yml` (unit-tests) since D2; `docs/analysis-report.md` v5

---

## a) The problem T13 actually had

T13's Validation gate reads: *every number measured from committed
`evals/report/` runs, none guessed; the report cites its inputs.* v3's §3 did
not clear it. Its figures — "median of 3 runs each", "peak RSS 110 MB", the
MB/s table, "18.9 MB/s aggregate" — came from ad-hoc timing that left nothing
behind. A reviewer could neither reproduce them nor locate their input. They
were also measured "over all 21 committed fixtures" and the corpus is now
**37**, so every §5 projection derived from them was derived from a corpus
that no longer exists.

`evals/run.py` does record a per-case `seconds` in every report — that is
metric 9's input — but it is one run per **case** at 2-decimal precision, over
cases rather than fixtures, with no size, throughput or memory data attached.
It cannot carry §3, and stretching it to would have been the same guess with a
citation stapled on.

So the milestone's substance is the instrument, not the prose: a committed,
re-runnable benchmark whose output lives under `evals/report/` like every
other run's does.

## b) Decision

Add `evals/bench.py`, stdlib-only, on the `evals/oracle.py` precedent: a dev
instrument that runs the real pipeline through its existing public entry point
(`extract_items`) read-only, is never imported by `src/`, is not part of any
scored suite, and writes `evals/report/<stamp>-bench.json`.

**Thirteen** measurement choices, each of which could reasonably have gone the
other way, so each is recorded rather than left in the code. (Seven at first
draft; 8 and 9 added in PR #12 repair round 1, where the reviewer showed that
the population boundary and the sub-millisecond ratio noise were decisions the
code was making silently; 10 and 11 in round 2, where *which statistics are
asserted* and *how many digits of any of them mean anything* turned out to be
decided by accident too; 12 in round 3, when the same stale-number defect
survived two sweeps that had both been claimed as complete; 13 in D2,
2026-08-23, when the re-publication added the `tables=True` column.)

1. **The unit is the fixture, not the eval case.** Several cases run the same
   fixture (`aapl-2025` appears in more than one) and some carry no fixture at
   all. A per-case population double-counts the big filings and is not a
   corpus. This is also why bench numbers and metric 9's numbers differ and
   *should* differ — same pipeline, different populations, both honest. v3
   already carried that caveat for the 21-vs-27 split; it survives at 37-vs-45.

2. **Median of N repeats, N=3 by default, single process.** Wall-clock on a
   laptop is noisy; the median of a small odd N discards one scheduler hiccup
   at minimal cost. `min`, `mean`, `max` and the **first** (cold) repeat are
   all recorded per fixture, so a reader can see the spread instead of trusting
   the median. Measured spread across the three clean runs
   (`derived.repeat_spread_median`): **0.8% – 1.0%**. The per-run *maximum* of
   that spread is **not quoted here or anywhere else** — it ranges 2.4% / 3.1%
   / 7.5% across the three runs and always lands on whichever sub-10 ms
   fixture the scheduler happened to interrupt (§b11). *(2026-08-23 trio, D2:
   median 0.7% – 1.3%; per-run maximum 5.3% / 20.7% / 6.6%, on a sub-50 ms
   fixture each time — still not published.)*

   *(Corrected twice. PR #12 R12: this choice read "median 1.4%, worst 8%" and
   attributed it to the run of record; those were the **superseded** first
   artifact's values, and the 8% was a figure round 1's own report text had
   already retracted. PR #12 R23: the round-2 repair then quoted "maximum
   2.4%" — a value §b11 and report §3.1 both declare unpublishable, and the
   **most favourable of the three runs** — three lines above its own
   correction note saying so. One ADR contradicting itself within one
   paragraph is the same defect as an ADR contradicting its artifact; both are
   now covered by §b12's mechanical check for the fixture-attributed case, and
   by not quoting the statistic at all for this one.)*

3. **The throughput denominator is raw bytes on disk, not normalized chars.**
   The pipeline reads and normalizes the whole file, so bytes-in is the
   work-in; normalized chars are an output of that work. Both are recorded per
   fixture, so either ratio can be recomputed from the artifact.

4. **The batch pass is timed as a unit, separately from the per-fixture
   medians.** A real batch pays per-file open and allocator churn that a
   median-of-3 loop amortizes. §5's projection divides into the *batch*
   number. On the run of record the two agree closely (batch **3.942 s** vs
   sum-of-medians **3.925 s**; on the 2026-08-23 run of record, n=41, batch
   **4.307 s** vs **4.309 s**), which is itself the evidence that no batch
   overhead is hiding.

   **Which rate each population divides into, precisely** — the sentence above
   is true only of `all_dev_fixtures`. After choice 8 changed the projection of
   record to a real-EDGAR population, `real_edgar_dev` and
   `real_edgar_committed` divide into a **sum-of-medians** rate computed over
   their own members, because a batch pass over a subset was never run. Every
   row carries a `rate_source` field saying which it used. *(Corrected, PR #12
   R13 and R14: the seconds quoted here were the superseded artifact's, and the
   design claim stopped being true of the row that matters when round 1 moved
   the population.)*

5. **Peak memory is `resource.getrusage(RUSAGE_SELF).ru_maxrss`, and fixtures
   are processed in descending size order.** `ru_maxrss` is a monotone
   high-water mark, so recording it after each fixture in descending order
   turns "does the largest document set the peak?" into a readable fact rather
   than an assumption. It did not: see §c. (Units differ by platform — bytes on
   macOS/BSD, kilobytes on Linux — and the code branches on `sys.platform`
   rather than assuming.)

6. **No timing assertion enters a scored suite.** A wall-clock threshold in
   `fast` would gate correctness on a laptop's thermal state and would go red
   on unrelated CI hardware. Performance regressions are read off the committed
   artifact history instead — which is what committing the artifact is *for*.
   The instrument's own arithmetic is covered by `python3 -m evals.bench
   --self-check`, an assert-based `_demo` on synthetic inputs — the same
   "proved at the layer, not by a fixture" treatment ADR-016 gives
   `boundary_hygiene` and ADR-019 gives the oracle.

   **What that check does and does not cover, stated precisely, because the
   first version of this paragraph overclaimed and PR #12 (R2) proved it.**
   The reviewer mutated `med = statistics.median(times)` to `med = max(times)`
   and `pct`'s return to `vals[0]`, and `--self-check` still printed `ok`:
   `_demo` asserted `statistics.median([...]) == x`, which tests the standard
   library, and never read `latency_p50_s` or `latency_p95_s` at all. Both
   mutations were re-run here and both reproduced. Fixed by extracting
   `make_record` out of `run_all` so `_demo` drives the real median path with a
   known list of times, and by asserting the percentile **fields `summarize`
   emits** over a 20-row synthetic set whose p50 and p95 are distinct from each
   other, from the minimum and from the maximum. All three mutations
   (`max(times)`, `vals[0]`, `vals[-1]`) now go red, and were watched red
   before this paragraph was rewritten.

   Still **not** covered, and deliberately: the wall clock itself, `run_all`'s
   fixture discovery, and whether `extract_items` is fast. Those need a real
   corpus and a real timer, which is what the committed artifact history is
   for. `--self-check` proves the arithmetic between the timer and the report,
   nothing more.

7. **Token counts stay the chars/4 estimate, and say so.** ADR-020 §d asked
   T13 to firm them with `count_tokens` or an offline tokenizer. Neither is
   available on the terms this milestone is bound by: `count_tokens` is a
   network call, and neither `anthropic` nor `tiktoken` is importable here or
   present in `requirements.txt` (checked, not assumed). ADR-020 §f forbids
   adding a dependency and forbids a live extraction against a paid endpoint,
   so the estimate is carried forward **with its caveat intact** rather than
   silently upgraded. `evals/bench.py` contains no network import at all and
   `_demo` asserts that by parsing its own AST.

   For the same reason the **price basis is carried, not re-verified**.
   ADR-020 §d asked T13 to re-check the published list before quoting it;
   re-checking requires a network call. The constants in `evals/bench.py`
   remain Anthropic list price **as of 2026-06-24** and the artifact stamps
   that date in `cost.price_basis_date` next to every dollar figure. Treat the
   date as the fact.

8. **Population boundaries, all three of them, are decisions — not defaults.**
   Added in repair round 1, where R3/R4/R5 turned out to be three objections to
   one question: which filings count.

   - **Timed population: the 37 fixtures in `evals/fixtures/` only.** Forty-two
     fixture directories are committed. The 5 in `evals/heldout/fixtures/` are
     **not run**, because this instrument writes per-fixture `doc_status` and
     `normalized_chars` into a committed artifact and doing that to the
     held-out set publishes held-out extraction outcomes — the thing
     `evals/heldout/README.md`'s burn rule exists to price. The first draft
     simply called this "all 37 committed fixtures", which is false: 42 are
     committed.
   - **Sizes, however, are read for all 33 real filings.** A byte count is not
     an extraction outcome; `heldout_sizes()` calls `stat` and never
     `extract_items`. This matters because §5's multiplier is a *size*.
   - **Throughput statistics exclude the 3 refusals.** `ksb-2007` and
     `aapl-2026-10q` (`unsupported`) and `truncated-download` (`failed`) return
     from `src/sec10k/extract.py` before segmentation, boundaries and
     validation — a shorter code path. `ksb-2007` is the *fastest* fixture in
     the corpus, so the first draft's published throughput maximum described a
     document the pipeline never parsed, and explained it as "text-like input".
     Refusals stay in the artifact flagged `refused`, and in the latency and
     memory figures; they are out of the rate range, the spread and the R².
   - **The §5 sweep multiplier is the mean over real EDGAR filings, not over
     the dev corpus.** Nine of the 37 dev fixtures are self-created copies or
     mutations of other members, and **seven of those nine derive from the
     corpus's smallest real filings**, so they drag the mean down: 1.578 MiB
     over all 37 versus 1.868 MiB over the 28 real dev fixtures and 2.104 MiB
     over all 33 real committed filings. The first draft published the 1.578
     figure and, worse, explained the drop from v3's assumed 1.8 MB as the
     corpus having grown — when in fact v3's guess was **closer** to the real
     mean than the new measurement was. The artifact now emits all three
     populations with a `rate_source` on each and names
     `real_edgar_committed` as `projection_of_record`; the EDGAR-year sweep
     moves from ~12.6 min to **~16.9 min**.

     *(Re-measured 2026-08-23, D2, `20260823-185707`: the timed population is
     **41** (every directory `evals.oracle.iter_fixtures` yields — D1 made
     discovery the rule, so the count is read, not quoted), of which **13**
     are `SYNTHETIC` and **4** are refusals (`amended-cover-2021` joined the
     three above). The 13 synthetic fixtures average 0.63 MiB against 1.87 MiB
     for the 28 real dev filings — the ordering claim "seven of nine derive
     from the smallest" is not re-stated for 13; the measured means are. All
     41: 1.477 MiB mean; `real_edgar_dev` still 28 / 1.868 MiB and
     `real_edgar_committed` still 33 / 2.104 MiB — no real filing joined the
     corpus since — and the of-record sweep reads **~17.9 min** (1,071.9 s)
     because the rate moved, ~6% down, not the multiplier. Sizes are still
     read for all 33 real filings, the 5 held-out among them by `stat`
     only.)*

   The `SYNTHETIC` set is nine explicit names in `evals/bench.py` rather than a
   parse of `evals/fixtures/README.md`, because that README marks only eight —
   `items-stripped` has no row there at all and its provenance lives in its
   case file. `run_all` raises if any name in the set stops existing, so a
   fixture rename fails loudly instead of silently reclassifying the
   population. (Two real fixtures, `gs-2002` and `jnj-2016`, also have no
   README provenance row. That gap predates T13 and filling it properly needs
   the source URLs, i.e. a network call; noted here, not fixed.) *(The set is
   13 names at D2 — twelve marked SELF-CREATED in the README plus
   `items-stripped`; `len(SYNTHETIC)` is the count of record, and `run_all`'s
   existence check is what keeps it honest.)*

9. **Ratio statistics have a 1 ms floor, and the excluded rows are named.**
   Also added in repair round 1, from a defect the new `derived` fields
   exposed rather than one the reviewer raised. `truncated-download` is 1,200
   bytes and runs in ~0.1 ms, where a single scheduler tick is a 200–300%
   "spread" and a 3.0× "warm-up ratio". Left in, it would have falsified this
   milestone's own no-warm-up finding with clock quantization. It is excluded
   from the warm-up ratio and the repeat spread **only** — never from latency,
   throughput, memory or the populations — and `derived.ratio_excluded_fixtures`
   publishes the exclusion so it is auditable rather than a quiet filter.
   `_demo` asserts that a sub-millisecond row cannot set either maximum, and
   that assertion was watched red against the unfloored version.

10. **No published field may be without an assertion pinning its value — and
    that is enforced by inversion, not by discipline.** Round 1 answered R2 by
    pinning the two statistics the reviewer named; round 2 (R18) found five
    more that mutate freely with `--self-check` green, including one whose
    mutation moves the headline p95 from 0.51 s to 0.37 s and one that silently
    reverts round 1's own refusal-exclusion fix. Pinning statistics one at a
    time does not terminate — it is the "correction that relocates the gap"
    shape ADR-020 §h3 names, and it had now happened twice.

    So `_demo` no longer asserts selected values. It runs `summarize` over one
    **golden corpus** and compares the **entire published payload** — `perf`,
    `cost`, one full `records` row, and the artifact's top-level key set —
    against hand-derived expected values.

    *(Round 2 shipped this covering `perf` only, while §b10's headline said
    "no published field". PR #12 R22 was right that this was a third
    overclaim: `cost` and `records` are published too — report §4.1's dollar
    table comes straight out of `cost`, and §3.2's selected-points table
    straight out of `records` — and four mutations survived there, one of
    which moves the published median-filing cost from $0.14 to $0.29. The
    comparison now spans all of it, and `build_payload` exists so the
    top-level key set has one definition to pin.)* A newly published field fails the check until
    someone computes its expected value by hand; the failure names it
    (`derived.brand_new_unasserted_stat: got 42, expected <UNASSERTED FIELD>`).
    The corpus is built so no statistic sits on a degenerate value that could
    hide a mutation: percentile indices are fractional before `ceil`, the
    throughput spread is 2.25 rather than 1.0, R² is exactly 0.25 from a
    hand-derived three-point fit, a refused row carries the extreme rate, a
    sub-millisecond row would poison the ratio statistics, one row is
    synthetic, the largest row's median differs from both the maximum and the
    p50, and **the slowest row is not the largest row**.

    *(Those last two are round 3's, from R21. The round-2 corpus set
    `latency_p95_s == latency_max_s == largest_median_s == 0.6` and made the
    slowest row the largest, so `pct(meds, 95)` → `max(meds)` passed the check
    while moving the published p95 — degeneracy on precisely the statistic
    R18 had been raised about. Note the structural part: **p95 == max is
    unavoidable for any n < 20** under nearest-rank, since `ceil(0.95n) == n`.
    That cannot be fixed by choosing better numbers, so it is separated in its
    own 20-row block instead of being papered over — the honest response to
    "the corpus is degenerate here" is a second corpus, not a claim that it
    isn't.)*

    Five boundary cases a single corpus cannot reach keep their own short
    blocks: percentile separation at n=20, largest-row-last, already-at-peak,
    a perfectly proportional set, and a row whose `min_s` rounds to 0.0.

    The corollary, adopted at the same time: **the artifact emits only fields
    that are published or that back a published claim.** Two fields were
    deleted rather than given expected values — `all_fixtures_size_vs_time_r2`
    and `n_first_repeat_was_fastest`. An unpublished field is not free; it is
    an unasserted number waiting to be quoted.

    What this does **not** claim: that no bug can survive. It claims that
    every field of the published payload has a hand-derived expected value,
    and that the 30 mutations in §e are red. Those are different statements,
    and the difference is written down here because overclaiming this check is
    precisely what R2, R18 and R21/R22 caught — three times, each time in the
    sentence describing the fix for the previous time.

11. **The instrument is good to ±3%, and figures are rounded to say so.**
    Round 1 withdrew two statistics as "run-unstable" while publishing a third
    that was a worse single-run outlier, and asserted that the large fixtures
    were "stable to their third decimal". Neither the withdrawal nor the
    stability claim was measured (R16, R17).

    It is measured now. **Three full runs of identical code on a clean tree at
    `13761cc`** are committed — `20260820-031501`, `-031540`, `-031620`. Across
    them, per-fixture median latency moves **2.7% at the median fixture and
    4.2% at the worst**; batch throughput spans 14.53–15.02 MiB/s, p95
    0.500–0.521 s, corpus peak RSS 119.5–123.5 MiB. Every published figure is
    therefore quoted to two significant figures, and anything whose run-to-run
    swing exceeds its own magnitude — the RSS plateau *index* (4, 9, 9) and the
    per-run repeat-spread maximum (2.4%, 3.1%, 7.5%) — is **not published**.

    The run of record, `20260820-031540-bench.json`, is the **middle of the
    three on every headline** (p50, p95, max, batch rate, peak RSS, sweep
    projection). Chosen by that rule rather than by what it says, and the rule
    is written here so the choice can be checked.

    *(Amended 2026-08-23, D2. Three new full runs on a clean tree at `ba263ee`
    — `20260823-185543`, `-185626`, `-185707` — read per-fixture median spread
    **1.5% at the median fixture, 6.9% at the worst** (40 fixtures above the
    floor), and aggregates p50 0.0432–0.0435 s, p95 0.388–0.399 s, max
    0.580–0.589 s, batch 14.04–14.23 MiB/s, corpus peak RSS 119.6–123.5 MiB.
    The ±3% aggregate claim and the two-significant-figure rule stand. **No
    run was the middle on all six headlines this time**: `-185707` is the
    middle on four (max, batch rate, corpus peak RSS, sweep projection) and
    the highest of three on p50 and p95, by 0.0002 s and 0.010 s. It is the
    run of record under the rule applied as "middle on the most headlines",
    and that extension is written here rather than the rule being quietly
    satisfied. The RSS plateau index read 4, 9, 9 again and stays unpublished;
    the per-run repeat-spread maximum read 5.3% / 20.7% / 6.6% and stays
    unpublished. One family turned out to be **worse** than ±3% and is now
    published as a range rather than a value: `peak_rss_mib_after_largest_only`
    reads 94.6, 94.6, 94.6, 102.4, 95.7, 100.5, 94.6 MiB across the seven
    committed clean-tree runs of this instrument revision — **94.6–102.4 MiB**;
    the "stable to 0.1 MiB across all three runs" in §c was true of three and
    false at the fourth, PR #12 R25.)*

    This also disposes of R15. The previous artifact of record stamped
    `30b001a…-dirty` — run while `evals/bench.py` was itself uncommitted
    mid-edit — while the report claimed a clean `20f8be0`, which was the
    *earlier* artifact's sha. `src/` was in fact unchanged (it is byte-identical
    from `20f8be0` to head), so the pipeline claim was true in substance and
    false as a stamp. ADR-018 added the `-dirty` suffix precisely so this would
    be visible, and it was visible, and nothing read it. The remedy is a
    clean-tree re-run, not a footnote.

12. **The docs' fixture-attributed numbers are checked mechanically, and the
    claim is narrowed to what the check actually covers.**

    Round 1 left withdrawn figures standing in the ADR that recorded the
    withdrawal. Round 2 swept the ADR "in full" — and §c still printed five
    per-fixture throughputs read out of the **superseded dirty-tree run**,
    digit for digit, under a header naming the run of record (R20). Two
    documents, the ledger row and `prompts/009`, recorded that sweep as done.
    A claim whose only enforcement is a human re-reading six files is not a
    claim, and asserting it a third time would be the eighth instance of this
    project's signature error.

    So: `python3 -m evals.bench --check-docs <artifact>` extracts every decimal
    printed within 60 characters of a backticked fixture name, on the same
    line, and fails unless it is a correct rounding of one of that fixture's
    values in the named artifact. On the docs as shipped it reads **52
    checked, 0 unmatched** against `20260820-031540-bench.json` and **22
    unmatched** against the superseded `20260820-024620` — which is the
    evidence that the attribution is now right, rather than another assertion
    that it is.

    **What it does not cover, stated rather than implied:** aggregate figures.
    p95, batch throughput, the sweep projections and the RSS plateau are not
    attributed to a fixture name and are invisible to this check; they are
    pinned inside the artifact by choice 10 and swept by hand in the prose.
    Integers are skipped (item codes, years and counts share their shape), and
    ratios, percentages and prices are skipped by their adjacent symbol. The
    20 remaining legitimate non-measurements are listed in `DOC_ALLOW` with a
    reason each (`len(DOC_ALLOW)` re-measured 2026-08-23, L1, PR #12 R29 — the
    count was first written as 14 from memory; **26 after D2**, same day: +13
    dated entries each naming the value that superseded it, −7 that no longer
    sat beside a fixture name or whose ledger row had moved to `DONE.md` — the
    entries and their reasons are the list itself) — historical values inside their own correction notes,
    cross-run ranges, and quantities that merely sit beside a fixture name.
    Adding an entry there is where someone has to decide "this is history";
    it is not a way to quiet a stale number.

    **The documents' claim is narrowed to match.** They no longer say the docs
    were swept in full; they say the fixture-attributed numbers are checked
    mechanically and the aggregates were checked by hand.

    *(Amended 2026-08-23, D2 — PR #12 R26/R27, the Debt row "Both T13
    mechanisms claim broader coverage than they deliver", parts (a) and (b).
    **(a) The check failed open.** `DOC_WINDOW = 0` printed "0
    fixture-attributed decimals checked, 0 unmatched" and exited 0, and a
    renamed `DOC_FILES` entry silently dropped that file's coverage — both
    reproduced against the pre-D2 code before the fix, exit 0 each. Now
    `check_docs` exits non-zero when `checked == 0` ("a vacuous run … is a
    failure, not a pass") and when any `DOC_FILES` entry does not exist, and
    `_demo` drives it on scratch docs for all four outcomes (match, unmatched,
    vacuous, missing file) so `--self-check` pins the rule. **(b) Neither
    check was wired anywhere.** Both now run in `.githooks/pre-commit` after
    the fast suite and in `ci.yml`'s unit-tests job beside `metrics
    --self-check`; `--check-docs` points at the run of record named in this
    header, and the two pointers move together. On the docs as re-published it
    reads **70 checked, 0 unmatched** against `20260823-185707` (and **35
    unmatched** when that same artifact was checked against the docs as they
    stood before re-derivation — the evidence that the re-derivation reached
    what the check reaches). `DOC_ALLOW` gained 13 entries for values that are now history by
    this ADR's own amendment — each names what superseded it — and lost 7 that
    no longer sat beside a fixture name or whose ledger row had moved to
    `DONE.md`. One more defect of the check surfaced in the same run and is
    fixed with a `_demo` pin: a decimal that *straddled* the 60-character
    window edge was sliced (`1.18×` read as `1.1`), so a literal could match —
    or fail — as a different value; a number that starts inside the window is
    now read whole (watched on the sliced version: `0.45` at the edge read as
    `0.4` and matched the golden median). (d) and (e) of that row stay open,
    re-filed as a Debt row with Origin D2: `units`' contents and `SYNTHETIC`'s
    membership are still asserted only by the top-level key set and the
    existence check.)*

13. **The `tables=True` path is timed as a thirteenth column, in a separate
    pass after every memory reading** (added 2026-08-23, D2; the Debt row "No
    bench figure for `tables=True`", Origin S7). ADR-029 §f published "+20% on
    jpm-2024" and "+6% to +20% per fixture" from its working tree — one-off
    numbers, not a committed bench field. Each record now carries
    `tables_median_s` (the same median-of-N loop with
    `extract_items(path, tables=True)`) and `tables_over_default` (its ratio to
    `median_s`), and `derived` carries the median and maximum ratio over
    processed fixtures and the fixture that sets the maximum. Two choices: the
    pass runs **after** the batch pass, so `peak_rss_mib_after` and the corpus
    peak remain default-path readings comparable with every earlier artifact
    (the annotation allocates a second envelope-sized structure; its memory is
    deliberately *not* measured here and not claimed); and the ratio population
    is **processed** fixtures only, because a refusal returns before any table
    is read. On the run of record: median **1.187×**, maximum **1.295×**
    (`wfc-2008`), `jpm-2024` 0.5821 → 0.7227 s (1.242×); across the three runs
    the median reads 1.18–1.20 and the maximum 1.27–1.30. Pinned by the golden
    record (`tables_median_s` 0.15, ratio 1.154) and three new `derived`
    fields in the golden payload (1.2 / 1.3 / `ko-1997`, a maximum set by
    neither the largest nor the slowest row), per choice 10.

## c) What the measurement falsified

Four claims in v3 §3/§5 are wrong at 37 fixtures. They are corrected in v4 with
a dated note rather than restated, on the ADR-019/ADR-020 precedent.

*(Re-measured 2026-08-23, D2, on the new run of record
`evals/report/20260823-185707-bench.json` — n=41, clean tree at `ba263ee`, the
middle of three committed runs on four of six headlines (§b11 amendment). The
per-fixture figures in this section are **re-derived in place** from that
artifact, because the four findings are what this section exists to record
and each holds again at n=41: the same five fixtures hold the low-throughput
end, the same two the high end, the same pair shows the 2.1× gap, and the
memory plateau is still not set by the largest document. The 2026-08-20 values
this section used to print — the n=37 table and its per-fixture numbers — are
in `20260820-031540-bench.json` itself and in `docs/analysis-report.md`'s
"Corrections to v3" table, relabelled "measured at v4"; they are not repeated
here. One v4 sentence in this section is **withdrawn** rather than re-derived
and is marked where it stood: "a value stable to 0.1 MiB across all three
clean runs" for the largest-filing RSS.)*

Figures below are from the run of record
`evals/report/20260823-185707-bench.json` — measured on a **clean tree** at
`ba263ee`, and quoted to the two significant figures the instrument's ±3%
run-to-run spread supports (§b11). **All rates and sizes here are binary (MiB
= 1,048,576 B); v3's were decimal MB against binary MiB/s, which was itself
one of PR #12's findings (R8) and is part of why its throughput never
reconciled with its own size table.**

| v3 said | measured now (2026-08-23, n=41; v4's n=37 values in the report's "Corrections to v3" table) |
|---|---|
| aggregate throughput **18.9 MB/s** (37.8 MB in 2.00 s, 21 fixtures) | **14.1 MiB/s** (60.54 MiB in 4.307 s, 41 dev fixtures) |
| latency **p95 0.249 s** | **p95 0.40 s** — 0.51 s at n=37, a rank effect (`docs/analysis-report.md` §3.2): the 39th of 41 medians is `cvx-2015`, the 36th of 37 was `bac-2006`; max `jpm-2024` 0.58 s |
| "throughput is roughly flat across two orders of magnitude (8–37 MB/s)" | **6.2–32.2 MiB/s** over the 37 processed fixtures — a 5.2× spread — and size explains only **R²=0.78** of the variance in elapsed time |
| "peak RSS scales with the single largest document … 12.8 MB of raw input produced a 110 MB process peak" | the largest filing alone reaches **94.6–102.4 MiB** (seven committed runs, §b11 amendment); the corpus plateaus at **119–124 MiB** |

The third and fourth deserve more than a row.

**Throughput is not flat.** `bac-2006` (4.31 MiB) takes 0.536 s while
`xom-2021` (5.87 MiB) takes 0.256 s — 2.1× longer on 27% *less* input, a gap
that holds on all three clean runs of both trios and is an order of magnitude
larger than the ±3% noise. Bytes are the first-order term and nothing else
comes close, but v3's stronger reading — "cost tracks bytes, not item count or
document complexity" — is not what the data says. The low-throughput end is
normalization-heavy markup (`tgt-2002` 6.19, `intc-2002` 6.45, `gs-2002` 6.73,
`ba-2003` 7.17, `msft-2013` 7.17 MiB/s) and the high end is real plain-text
submissions (`ibm-1997` 32.16, `ko-1997` 25.98 MiB/s). v3 named `msft-2013`'s
source wraps as the one outlier; there are five, and they share a cause. The
operational consequence is unchanged — everything is fast — so this corrects
the *explanation*, not the capacity planning.

*(Correction, PR #12 round 1, R5. The first draft of this row published the
range as **6.34–42.8 MB/s, a 6.7× spread**, and named `ksb-2007` at 42.8 as
its "text-like input" high end. `ksb-2007` is a Form 10-KSB: the pipeline
**refuses** it, returning `unsupported` from `src/sec10k/extract.py` before
segmentation, boundaries or validation ever run. The corpus's fastest number
was therefore measuring a document that was never parsed, and it was being
explained as though it had been. Per choice 8 the refusals are now out of the
rate statistics, which is where the ~5× spread and the narrower range come
from — the correction moved the number in the direction that makes this
section's own argument **weaker**, and it stands anyway.)*

**Peak RSS does not track the largest document alone.** Processing in
descending size order, `jpm-2024` (12.25 MiB, the largest) brings the process
high-water to **94.6 MiB on the run of record** from a ~26 MiB baseline —
~~a value stable to 0.1 MiB across all three clean runs~~ *(withdrawn
2026-08-23, D2, PR #12 R25: 94.6 on the three `13761cc` runs and on
`20260823-185707`, but 102.4 on `20260820-115810`, 95.7 and 100.5 on the other
two 2026-08-23 runs — a **94.6–102.4 MiB** range, the one published family
wider than ±3%)*. A further ~20–28 MiB accrues over the next several fixtures
and the process settles at a **119–124 MiB** plateau it holds for the remainder
— a plateau, not a leak. A per-worker budget still sits comfortably at 256 MiB,
so the v3 sizing advice survives; the reason given for it did not.

*(The first draft said "reaching 122.1 MB by roughly the tenth", which PR #12
R11 showed did not match its own artifact — the tenth fixture read 121.7 and
122.1 first appeared at the thirty-sixth. The plateau index is now a computed
field, `derived.rss_plateau_first_index`, defined as the first index from which
every later reading is within 0.5 MiB of the corpus peak. Across three clean
runs it reads 4, 9, 9 — and 4, 9, 9 again on the 2026-08-23 trio — so it is
**not published at all** — only that a plateau exists and roughly where it
sits, both of which are stable.)*
## d) What the measurement confirmed

Recorded because a benchmark that only ever falsifies is as suspect as one that
only ever confirms.

1. **No warm-up effect.** Over the 36 fixtures above the 1 ms ratio floor
   (choice 9), the first-repeat vs fastest-repeat ratio has median **1.004**
   and maximum **1.02** on the run of record. Across the three clean runs the
   maximum is 1.021 / 1.031 / 1.042 and lands on a different fixture each time
   — it is the noise floor, which is what "no warm-up" should look like. v3
   asserted this from one filing; it holds corpus-wide, and `first_s` is in the
   artifact so it can be re-checked rather than believed. *(2026-08-23, D2,
   n=41: 40 fixtures above the floor, median **1.005**, maximum **1.05** on the
   run of record; 1.056 / 1.048 / 1.051 across the trio, on `sandston-2021`,
   `jpm-2024` and `ko-1997` respectively — a different fixture each time,
   as before. Holds.)*

   **Correction, PR #12 R16 — and this is the worst single error in this
   milestone.** The round-1 draft of this item published a maximum of **1.40**,
   attributed to `ksb-2007` at "3.5 ms first versus 2.5 ms fastest", in the same
   paragraph where it withdrew "worst case 1.04" as run-unstable. It is the
   other way round. On all three clean runs `ksb-2007` reads
   `first_s == min_s == 0.0025` — the 3.5 ms observation **does not reproduce at
   all** — and the corpus maximum never exceeds 1.042. So round 1 retracted the
   reproducible figure and published an artefact of the dirty-tree run §b11 is
   about, while citing run-instability as the reason. The same applies to that
   draft's repeat-spread maximum of 40%, also `ksb-2007`, also from that run:
   clean runs read 2.4% / 3.1% / 7.5%. Both are withdrawn.

   The genuinely run-unstable claim withdrawn in round 1 — "11 fixtures were
   fastest on their first run" (11 → 3 → 3) — stays withdrawn, and the field
   behind it, `n_first_repeat_was_fastest`, is now **deleted** rather than
   emitted unquoted, per choice 10's rule that the artifact carries only what
   backs a published claim.

2. **ADR-020 §d's character counts reproduce exactly.** Independently measured
   here: whole corpus **8,450,478** normalized chars, median fixture
   **108,938** (`wmt-2010`), `jpm-2024` **1,213,298**. All three match §d to
   the character. The cost counterfactual in v4 §4 is therefore not an
   inherited number.

   *(Dated 2026-08-23, D2: those three are **as of `20260820-031540`**, n=37,
   before the `<title>` skip (T3, INV-S5) shortened `normalized_text` on 18
   of the 37 by 286 chars in total and four fixtures joined. On
   `20260823-185707`, n=41: corpus **8,751,495**, median fixture **102,453**
   (`amended-cover-2021` — the 21st of 41 is a synthetic derivative), largest
   `jpm-2024` **1,213,284**. ADR-020 §d keeps its 2026-08-19 figures with a
   dated note, per the ADR-024/027 convention; the report's §4.1 carries the
   new ones. The "reproduces exactly" finding is a statement about two
   2026-08-20 measurements agreeing, and it stays.)*

3. **ADR-020's addressable-surface arithmetic reproduces exactly.** Recomputed
   from today's committed reports (`20260820-020944-all.json` +
   `20260820-013515-fast.json` over `evals/heldout`), keyed on (fixture, item):
   **768** distinct items, **15** `missing`, and the four improvable ones are
   exactly `axp-2008` items 10–13. The headline ADR-020 corrected three times (four figures;
   count fixed 2026-08-23, L1, PR #35 R6 sweep) lands where §h3 left it.

   One wording refinement, not a count change: ADR-020 §b describes the nine
   synthetic-fixture items as ones "whose own committed expectations assert
   `missing` is the CORRECT answer". Only two of the nine are asserted
   item-by-item (`items-stripped` item 8, `heading-unnumbered` item 8); for the
   other seven the case asserts the aggregate consequence — `doc_status:
   ambiguous` plus `expected_items_mostly_missing` — and `missing` is correct
   by construction of the fixture rather than by a per-item check. Recorded in
   report v4 §4.2 rather than smoothed over, since "asserted in prose without
   running the check" is this project's most repeated defect.

## e) No new eval case, and why that is not a hard-rule-2 dodge

Hard rule 2 makes every new failure an `evals/adversarial/` case, watched red
before it is fixed. **This milestone found no pipeline, harness or metric
failure.** The pipeline produced the same statuses and spans it produced
before; `evals/run.py` and `evals/metrics.py` are untouched. What was wrong was
four sentences in a descriptive document, and there is no case shape for "the
report quoted 18.9 MB/s". Inventing one would be theatre.

The runnable check the new logic leaves behind is
`python3 -m evals.bench --self-check` (choices 6 and 10 above), which now fails
under each of these **thirty** mutations. Every one was applied to a copy of
the module and run — all thirty exit non-zero, none was reasoned about in
prose:

| # | mutation | what catches it | raised in |
|---|---|---|---|
| 1 | `med = statistics.median(times)` → `max(times)` | golden record | — |
| 2 | `pct` → `vals[0]` | golden `latency_p50_s` | — |
| 3 | `pct` → `vals[-1]` | golden `latency_p50_s` | — |
| 4 | `math.ceil` → `math.floor` in `pct` | golden p50 and p95 | R18 |
| 5 | drop the 1 ms ratio floor | golden warm-up/spread maxima | — |
| 6 | drop the descending-order guard | largest-row-last block | — |
| 7 | plateau scan `range(len)` → `range(1, len)` | already-at-peak block | — |
| 8 | `processed` → `list(records)` (reverts round 1's R5 fix) | golden `processed_mib_per_s_max`/`_spread` | R18 |
| 9 | `_r2` → `return 1.0` | golden R² 0.25 vs the perfect-fit block's 1.0 | R18 |
| 10 | `processed_mib_per_s_spread` → `1.0` | golden spread 2.25 | R18 |
| 11 | `n_1000_seconds` ×1000 → ×100 | golden populations | R18 |
| 12 | `n_1000_gib_read` drops its ×1000 | golden populations | R18 |
| 13 | `real_dev = list(records)` | golden `real_edgar_dev` | — |
| 14 | batch rate ↔ real-dev rate swapped | golden `all_dev_fixtures.mib_per_s` | R19 |
| 15 | `latency_max_s` → `min(meds)` | golden | — |
| 16 | `sum_of_medians_s` → mean | golden | — |
| 17 | `median_raw_bytes` → mean | golden | — |
| 18 | add a new `perf` field | golden diff → `<UNASSERTED FIELD>` | — |
| 19 | `import socket` | AST import scan | — |
| 20 | `pct(meds, 95)` → `max(meds)` | n=20 percentile-separation block | **R21** |
| 21 | `largest_median_s` → `max(meds)` | golden `largest_median_s` 0.4 ≠ max 0.6 | **R21** |
| 22 | `slowest_fixture` → `largest["fixture"]` | golden: slowest is `nvda-2024`, largest is `cat-2023` | **R21** |
| 23 | cost median chars → mean | golden `cost.counterfactual.median_filing` | **R22** |
| 24 | Haiku context 200K → 350K | golden `fits_haiku_context` (both values present) | **R22** |
| 25 | `PRICE_BASIS_DATE` changed | golden `cost.price_basis_date` | **R22** |
| 26 | Opus price $5 → $7 | golden `cost.models` | **R22** |
| 27 | add a new `cost` key | golden diff → `<UNASSERTED FIELD>` | **R22** |
| 28 | add a new `records` key | golden record diff | **R22** |
| 29 | add a new top-level payload block | `PAYLOAD_KEYS` | **R22** |
| 30 | exclusion list ≠ population complement | coarse-clock block (`min_s` rounds to 0.0) | **R24** |

Mutations 1 and 2 are **PR #12's R2 repro**; 4 and 8–12 are **R18's**; 20–29
are **R21/R22's**. Against the drafts they were raised on, every one of them
printed `[bench self-check] ok`. Mutation 30 was the last to be caught: the
predicate mismatch R24 names is real but *unobservable* on any corpus where
both predicates agree, so a row whose `min_s` rounds to 0.0 had to be built
before the check could fail. That is the difference between a finding being
fixed and a finding being demonstrated.

Mutations 18, 27, 28 and 29 are the ones that make this list finite rather than
a list: they assert that a *future* field, in any of the four published blocks,
cannot be published unasserted.

**This is still not an `evals/adversarial/` case, and the distinction is not a
convenience.** `evals/run.py` dispatches a case to `src/<task>/eval_adapter.py`
with a filing path; there is no case shape in that harness for "a dev
instrument's arithmetic is wrong", and forcing one would mean routing bench
assertions through the extraction adapter. ADR-016's precedent is exactly this:
properties that no fixture can exercise are proved at the layer, in an
assert-based `_demo`, and watched red there. That is what happened.

**Three** earlier versions of this paragraph overclaimed, each one describing
the fix for the previous one. The first said the check "fails if the median …
breaks"; it did not, and R2 proved it. The second said it "proves the
arithmetic between the timer and the report, nothing more"; also false, and R18
proved it with five surviving mutations. The third said "no published field may
be without an assertion" while covering only `perf`; R21/R22 proved it with
eight more, including one that moves the published median-filing cost from
$0.14 to $0.29. All three sentences are left corrected rather than deleted,
because the shape of the error — asserting a property of an executable thing
without running it — is the one ADR-020 §h3 says this project keeps repeating,
and it has now repeated three times *inside the correction for itself*.

Choice 10 is the structural answer for the payload and choice 12 for the
fixture-attributed prose. Neither depends on anyone remembering anything, which
is the only property that distinguishes them from the three sentences above.

## f) Consequences

- `docs/analysis-report.md` goes to **v4**: §3, §4 and §5 rewritten against
  `evals/report/20260820-031540-bench.json` and
  `evals/report/20260820-020944-all.json`, each citing its input by filename.
  Four bench artifacts are committed and none is deleted: `20260820-020815`
  (first draft, sha `20f8be0`), `20260820-024620` (round 1, sha
  `30b001a-dirty`), and the three clean-tree runs at `13761cc`
  (`20260820-031501`, `-031540`, `-031620`) of which the middle one is of
  record. The two superseded artifacts stay because they are what this ADR's
  withdrawn figures were measured from — a retraction that deletes its own
  evidence is not checkable.
- Statistics the report quotes but that were previously computed in prose — R²,
  the throughput range and spread, the warm-up ratio, the repeat spread, the
  RSS plateau index, the sum of medians, and all three sweep populations — are
  now emitted into `perf.derived` and `perf.populations`. PR #12 R7 was right
  that "every number is a field of that file" was false when a third of them
  were derivations; the fix was to make them fields rather than to soften the
  sentence.
- **Units are binary throughout** (MiB = 1,048,576 B), and the artifact's field
  names say `mib`/`gib` with a `units` block restating it. The first draft
  quoted decimal-MB sizes against binary-MiB/s rates, so dividing a published
  size by a published time missed the published rate by 4–5% (R8).
- §4 carries ADR-020 §f items 1–4 in place of the fallback cost model that
  never shipped, including metric 11's demotion in the prose.
- Two claims elsewhere in the report that T11 shipping made false are fixed:
  §6 item 4 and §7 item 5 both forward-referenced the sampled silent-failure
  rate as future work. It is ADR-019, and §1 already reports it.
- One number in §3 keeps **no** committed artifact: the deployed-instance
  latencies (Zeabur, 2026-08-16). Re-measuring them is a network call. It is
  labelled in v4 as the single uncited figure rather than quietly restated —
  the Validation gate's "none guessed" is met by disclosure, not by deletion of
  an inconvenient observation.
- `evals/bench.py` is a dev instrument under the same C7 rules as
  `evals/oracle.py`: not in `requirements.txt`, not imported by `src/`. It is
  not a new pipeline capability and does not touch the T8 freeze. *(Amended
  2026-08-23, D2: "not in CI" is no longer true of its two checks —
  `--self-check` and `--check-docs` run in CI's unit-tests job and in the
  pre-commit hook, §b12 amendment. The timing run itself is still never in
  CI, per choice 6.)*

## g) The 2026-08-23 re-publication (D2)

Added 2026-08-23. Everything above this section was written against
`20260820-031540` and is amended in place with dated notes where a figure
moved; this section is the record of the move itself.

**Why a re-run and not an edit.** Three things made the 2026-08-20 run of
record stale, none of them an error in it: the `<title>` skip (T3, INV-S5)
shortened `normalized_text` on 18 of its 37 fixtures by 286 chars in total, so
every published `normalized_chars` integer was off by the title's length; four
synthetic fixtures joined the corpus (`ibr-security-holders`,
`comma-cover-2016`, `amended-cover-2021`, `spaced-letter-heading`) and had no
bench row; and ADR-029's `tables=True` path had only one-off working-tree
numbers. Hard rule 1's spirit — never hand-edit a measurement — means the only
honest fix is the instrument re-run, which re-measures every clock figure in
the same pass; so every figure moves together, and they do.

**Run of record**: `evals/report/20260823-185707-bench.json` — git `ba263ee`
(D2's first commit: the instrument's `tables=True` column and fail-closed
`--check-docs`; `src/` is `origin/main` at `9cee5be` byte-for-byte; the one later `src/` edit in D2 is a comment in `boilerplate.py`), clean tree,
Python 3.14.6 on `macOS-26.5.2-arm64-arm-64bit-Mach-O`, median of 3 repeats,
single process. n=41 dev fixtures, 13 synthetic, 4 refusals. Three runs
committed (`20260823-185543`, `-185626`, `-185707`); the choice rule and its
one honest extension are in the §b11 amendment.

**What moved, old → new, by document** (the instrument's output, not
arithmetic; aggregates to two significant figures):

- Headlines: p50 0.041 → **0.044 s**; p95 0.51 → **0.40 s** — a rank effect
  (the 36th of 37 medians at n=37, the 39th of 41 at n=41: two different
  filings, named in §c, and both read slower today); max 0.55 → **0.58 s**
  (the largest filing, as before); batch 14.8 → **14.1 MiB/s**
  (60.54 MiB in 4.307 s); processed range 6.6–33.8 over 34 → **6.2–32.2 MiB/s
  over 37**, spread 5.1× → 5.2×, R² 0.78 → 0.78; corpus peak RSS 123 → 123 MiB
  (plateau 119–124 unchanged); largest-filing RSS "94.6, stable to 0.1" →
  **94.6–102.4 MiB** across seven runs (§b11 amendment, PR #12 R25).
- Projection of record (`real_edgar_committed`, n=33, 2.104 MiB — unchanged
  membership): rate 14.6 → **13.7 MiB/s**, 1,000 filings 144 → **153 s**,
  EDGAR year ~17 → **~18 min** (1,006 → 1,072 s). `all_dev_fixtures` 37 /
  1.578 MiB → 41 / 1.477 MiB.
- `normalized_chars`: corpus 8,450,478 → **8,751,495**; median fixture
  108,938 (`wmt-2010`) → **102,453** (`amended-cover-2021`); `jpm-2024`
  1,213,298 → **1,213,284**; the cost counterfactual's median-filing estimate
  $0.14 → **$0.13** (opus-5), corpus $10.56 → **$10.94**; the largest-filing
  row is unchanged at $1.52 / does-not-fit.
- New: `tables=True` median **1.19×**, max **1.30×** (`wfc-2008`),
  `jpm-2024` 0.58 → 0.72 s with the flag on (§b13).
- Corpus-wide the default path reads ~5–7% slower than on 2026-08-20, outside
  the ±3% spread. **Not attributed** here to the tree or the machine: `src/`
  changed between the runs (T3, D1, S7 shipped) and so did the day, and this
  instrument cannot separate the two. A clean-tree run at `9cee5be` with the
  pre-D2 instrument would have; it was not made, and is left as the obvious
  next measurement if anyone needs the attribution.

Where each figure lives: `docs/analysis-report.md` v5 §3, §3.1, §3.2, §4.1,
§5 and the version block; `README.md` §"Performance, cost, scalability" and
the large-filings row; this ADR's header, §b2, §b4, §b8, §b11, §b12, §c, §d,
§f and Verification. ADR-020 §d and ADR-010 ruling 4 carry one-line dated
notes rather than new numbers (their figures are rulings of their date); ADR-029
§f's one-off numbers stand as dated and point here for the committed column;
ADR-027 §h gets a one-line "re-published" pointer and ADR-018's header a dated
pointer to the report's calibration v3. `src/sec10k/boilerplate.py:66`'s
"38 measurable fixtures" comment — the one `src/` edit D2 makes, and it is a
comment — drops the absolute count for the walk command (PR #31 R14's own
acceptance).

**What is deliberately left historical**: the v4 repair-round notes in the
report's version block and in this ADR's §b2/§b4/§d1 (their figures are the
evidence of what each round found); the "Corrections to v3" table in report
§3.2 (relabelled "measured at v4"); `prompts/009` throughout (a record; its
stale values are in `DOC_ALLOW` with the round that produced them); ADR-020 §d
and ADR-010:138 (rulings, dated notes added); `evals/report/20260820-*` (six
artifacts, none deleted — the superseded ones are what the withdrawn figures
were measured from). The report's §1 metrics block and §4.2/§4.3 still cite
their own older runs and say so; D2 did not re-derive them (not named by any
Debt row this task promoted).

**Calibration v3**: `python3 -m evals.metrics evals/report/20260823-185915-all.json`
(97 cases, `ba263ee`) → 0.95 n=184 · 0.85 n=83 · 0.8 n=5 · 0.75 n=31 ·
0.65 n=1 · 0.4 n=2, debt 0.95 5/5, 0.4 4/4, `failed` 0 on every scored row —
the same six rows ADR-027 §h printed from `20260822-164458`; pasted verbatim
into the report's §1 as v3, with v1/v2 kept as history.

## Verification

As of 2026-08-20 (T13, PR #12):

```
python3 -m evals.bench --self-check      # ok (red first under all 30 mutations in §e)
python3 -m evals.bench --check-docs evals/report/20260820-031540-bench.json
                                         # 52 checked, 0 unmatched (22 vs the superseded run)
python3 -m evals.run --suite invariant   # 12/12 (+4 enumerated debt)
python3 -m evals.run --suite fast        # 45/45 (+4 enumerated debt)
python3 -m evals.metrics --self-check    # ok
```

As of 2026-08-23 (D2, §g; the lines the pre-commit hook and CI now run):

```
python3 -m evals.bench --self-check      # ok — now also drives check_docs on scratch docs
                                         #   (match / unmatched / vacuous / missing file)
python3 -m evals.bench --check-docs evals/report/20260823-185707-bench.json
                                         # 70 checked, 0 unmatched, exit 0 (35 unmatched before re-derivation)
                                         # DOC_WINDOW=0 -> "0 … checked" + FAILED line, exit 1 (was exit 0)
                                         # renamed DOC_FILES entry -> "1 DOC_FILES entries missing", exit 1 (was exit 0)
python3 -m evals.run --suite invariant   # 49/49 (+4 enumerated debt)
python3 -m evals.run --suite fast        # 97/97 (+4 enumerated debt); table fidelity 400/400, 31/31
python3 -m evals.metrics --self-check    # ok
python3 -m evals.metrics evals/report/20260823-185915-all.json   # calibration v3, §g
```

Repair round 1 (PR #12): **11 findings raised, 11 confirmed by running their
repros, 0 rejected.** Four moved a published number — the sweep population
(R3/R4, ~12.6 → ~17 min), the throughput range (R5, 6.7× → 5.1×), the
large-filing latency copy left in `README.md` (R1), and the units (R8). Two
more, R2 and R11, showed a claim about an executable thing that had never been
executed.

Repair round 2 (PR #12): **8 findings raised, 8 confirmed by running their
repros, 0 rejected.** Round 2's finding about round 1 is the one worth
recording: **round 1 corrected the report and left this ADR behind** (R12, R13
— §b2 and §b4 still quoted the superseded artifact while naming the new one as
their source, including a figure round 1's own report text had retracted), and
**round 1's fix for R2 relocated the gap rather than closing it** (R18 — five
more unasserted published statistics). Worse, R16 showed that round 1 withdrew
a *reproducible* statistic as run-unstable and published an irreproducible one
in its place, sourced from the dirty-tree run R15 identified. Choices 10 and 11
exist so that neither failure mode depends on anyone noticing next time: the
self-check is inverted so unasserted fields cannot exist, and the instrument's
precision is measured from three committed clean runs rather than asserted.

Repair round 3 (PR #12, an extension authorized by Willy after the loop's
three-round circuit breaker fired): **5 findings raised, 5 confirmed by running
their repros, 0 rejected.** R20 is the stale-figure defect surviving a *third*
round, this time with two documents recording a sweep that had not happened —
answered with choice 12's mechanical check rather than a fourth assertion, and
the check immediately found a seventh stale figure the review had not cited
(`ksb-2007` 44.1 in report §-header, from the dirty run). R21 and R22 are
round 2's own inversion, under-reached: a corpus degenerate on p95 and a
guarantee that covered `perf` but not `cost` or `records`. R23 is one paragraph
of this ADR contradicting another. R24 is a real predicate mismatch that no
committed corpus could fire, so a corpus was built for it.

Counting the whole loop, this is the **sixth through tenth** occurrence across
PR #11 and PR #12 of asserting a property of an executable thing without
running it, and three of those occurrences are inside the correction for an
earlier one. The count is kept deliberately: it is the strongest single piece
of evidence about how this project fails, and it is the reason both remaining
guarantees are mechanical rather than editorial.

`.eval-baseline.json` untouched at 1.000. No paid API call was made and no code
path capable of making one was added.
