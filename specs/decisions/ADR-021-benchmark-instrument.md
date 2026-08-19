# ADR-021 — T13: what the performance benchmark measures, and why the old §3/§4/§5 numbers had to be thrown away

Date: 2026-08-20. Status: accepted. Implements T13/A5. Adds one dev-only
instrument, `evals/bench.py`. Changes no pipeline code, no eval case, no
baseline. Supersedes the measurements — not the structure — of
`docs/analysis-report.md` v3 §3, §4 and §5, which v4 replaces.

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

**Eleven** measurement choices, each of which could reasonably have gone the
other way, so each is recorded rather than left in the code. (Seven at first
draft; 8 and 9 added in PR #12 repair round 1, where the reviewer showed that
the population boundary and the sub-millisecond ratio noise were decisions the
code was making silently; 10 and 11 in round 2, where it turned out that *which
statistics are asserted* and *how many digits of any of them mean anything*
were also being decided by accident.)

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
   the median. Measured spread on the run of record
   (`derived.repeat_spread_*`): median **0.8%**, maximum **2.4%**.

   *(Corrected, PR #12 R12. This choice previously read "median 1.4%, worst
   8%" and attributed it to the run of record; those were the **superseded**
   first artifact's values, left standing when round 1 regenerated the
   artifact — and the 8% was a figure round 1's own report text had already
   retracted. The wider lesson is §b10's: a number in a spec attributed to an
   artifact must be read out of that artifact. The stability conclusion also
   no longer rests on this statistic — the per-run maximum ranges 2.4–7.5%
   across three clean runs and is not published; §3.1 of the report states the
   instrument's precision from the cross-run spread instead.)*

3. **The throughput denominator is raw bytes on disk, not normalized chars.**
   The pipeline reads and normalizes the whole file, so bytes-in is the
   work-in; normalized chars are an output of that work. Both are recorded per
   fixture, so either ratio can be recomputed from the artifact.

4. **The batch pass is timed as a unit, separately from the per-fixture
   medians.** A real batch pays per-file open and allocator churn that a
   median-of-3 loop amortizes. §5's projection divides into the *batch*
   number. On the run of record the two agree closely (batch **3.942 s** vs
   sum-of-medians **3.925 s**), which is itself the evidence that no batch
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

   The `SYNTHETIC` set is nine explicit names in `evals/bench.py` rather than a
   parse of `evals/fixtures/README.md`, because that README marks only eight —
   `items-stripped` has no row there at all and its provenance lives in its
   case file. `run_all` raises if any name in the set stops existing, so a
   fixture rename fails loudly instead of silently reclassifying the
   population. (Two real fixtures, `gs-2002` and `jnj-2016`, also have no
   README provenance row. That gap predates T13 and filling it properly needs
   the source URLs, i.e. a network call; noted here, not fixed.)

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
    **golden corpus** and compares the **entire** `perf` block against a
    hand-derived expected dict. A newly published field fails the check until
    someone computes its expected value by hand; the failure names it
    (`derived.brand_new_unasserted_stat: got 42, expected <UNASSERTED FIELD>`).
    The corpus is built so no statistic sits on a degenerate value that could
    hide a mutation: percentile indices are fractional before `ceil`, the
    throughput spread is 2.0 rather than 1.0, R² is exactly 0.892857 from a
    hand-derived three-point fit, a refused row carries the extreme rate, a
    sub-millisecond row would poison the ratio statistics, and one row is
    synthetic. Three boundary cases a single corpus cannot reach keep their own
    two-line blocks: largest-row-last, already-at-peak, and a perfectly
    proportional set.

    The corollary, adopted at the same time: **the artifact emits only fields
    that are published or that back a published claim.** Two fields were
    deleted rather than given expected values — `all_fixtures_size_vs_time_r2`
    and `n_first_repeat_was_fastest`. An unpublished field is not free; it is
    an unasserted number waiting to be quoted.

    What this does **not** claim: that no bug can survive. It claims that no
    *field* is unasserted, and that the 19 mutations in §e are red. Those are
    different statements, and the difference is written down here because
    overclaiming this check is precisely what R2 and R18 caught.

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

    This also disposes of R15. The previous artifact of record stamped
    `30b001a…-dirty` — run while `evals/bench.py` was itself uncommitted
    mid-edit — while the report claimed a clean `20f8be0`, which was the
    *earlier* artifact's sha. `src/` was in fact unchanged (it is byte-identical
    from `20f8be0` to head), so the pipeline claim was true in substance and
    false as a stamp. ADR-018 added the `-dirty` suffix precisely so this would
    be visible, and it was visible, and nothing read it. The remedy is a
    clean-tree re-run, not a footnote.

## c) What the measurement falsified

Four claims in v3 §3/§5 are wrong at 37 fixtures. They are corrected in v4 with
a dated note rather than restated, on the ADR-019/ADR-020 precedent.

Figures below are from the run of record
`evals/report/20260820-031540-bench.json` — measured on a **clean tree** at
`13761cc`, the middle of three committed runs on every headline, and quoted to
the two significant figures the instrument's ±3% run-to-run spread supports
(§b11). **All rates and sizes here are
binary (MiB = 1,048,576 B); v3's were decimal MB against binary MiB/s, which
was itself one of PR #12's findings (R8) and is part of why its throughput
never reconciled with its own size table.**

| v3 said | measured now |
|---|---|
| aggregate throughput **18.9 MB/s** (37.8 MB in 2.00 s, 21 fixtures) | **14.8 MiB/s** (58.37 MiB in 3.942 s, 37 dev fixtures) |
| latency **p95 0.249 s** | **p95 0.51 s** (`bac-2006`); max 0.55 s (`jpm-2024`) |
| "throughput is roughly flat across two orders of magnitude (8–37 MB/s)" | **6.6–33.8 MiB/s** over the 34 processed fixtures — a 5.1× spread — and size explains only **R²=0.78** of the variance in elapsed time |
| "peak RSS scales with the single largest document … 12.8 MB of raw input produced a 110 MB process peak" | the largest filing alone reaches **94.6 MiB**; the corpus plateaus at **119–124 MiB** |

The third and fourth deserve more than a row.

**Throughput is not flat.** `bac-2006` (4.31 MiB) takes 0.505 s while
`xom-2021` (5.87 MiB) takes 0.239 s — 2.1× longer on 27% *less* input, a gap
that holds on all three clean runs and is an order of magnitude larger than the
±3% noise. Bytes
are the first-order term and nothing else comes close, but v3's stronger
reading — "cost tracks bytes, not item count or document complexity" — is not
what the data says. The low-throughput end is normalization-heavy markup
(`tgt-2002` 6.6, `intc-2002` 6.8, `gs-2002` 7.1, `msft-2013` 7.5, `ba-2003`
7.6 MiB/s) and the high end is real plain-text submissions (`ibm-1997` 33.7,
`ko-1997` 26.8 MiB/s). v3 named `msft-2013`'s source wraps as the one outlier;
there are five, and they share a cause. The operational consequence is
unchanged — everything is fast — so this corrects the *explanation*, not the
capacity planning.

*(Correction, PR #12 round 1, R5. The first draft of this row published the
range as **6.34–42.8 MB/s, a 6.7× spread**, and named `ksb-2007` at 42.8 as
its "text-like input" high end. `ksb-2007` is a Form 10-KSB: the pipeline
**refuses** it, returning `unsupported` from `src/sec10k/extract.py` before
segmentation, boundaries or validation ever run. The corpus's fastest number
was therefore measuring a document that was never parsed, and it was being
explained as though it had been. Per choice 8 the three refusals are now out of
the rate statistics, which is where the 5.1× spread and the narrower range
come from — the correction moved the number in the direction that makes this
section's own argument **weaker**, and it stands anyway.)*

**Peak RSS does not track the largest document alone.** Processing in
descending size order, `jpm-2024` (12.25 MiB, the largest) brings the process
high-water to **94.6 MiB** from a ~26 MiB baseline — a value stable to 0.1 MiB
across all three clean runs. A further ~28 MiB accrues over the next several
fixtures and the process settles at a **119–124 MiB** plateau it holds for the
remainder — a plateau, not a leak. A per-worker budget still sits comfortably
at 256 MiB, so the v3 sizing advice survives; the reason given for it did not.

*(The first draft said "reaching 122.1 MB by roughly the tenth", which PR #12
R11 showed did not match its own artifact — the tenth fixture read 121.7 and
122.1 first appeared at the thirty-sixth. The plateau index is now a computed
field, `derived.rss_plateau_first_index`, defined as the first index from which
every later reading is within 0.5 MiB of the corpus peak. Across three clean
runs it reads 4, 9, 9, so it is **not published at all** — only that a plateau
exists and roughly where it sits, both of which are stable.)*

## d) What the measurement confirmed

Recorded because a benchmark that only ever falsifies is as suspect as one that
only ever confirms.

1. **No warm-up effect.** Over the 36 fixtures above the 1 ms ratio floor
   (choice 9), the first-repeat vs fastest-repeat ratio has median **1.004**
   and maximum **1.02** on the run of record. Across the three clean runs the
   maximum is 1.021 / 1.031 / 1.042 and lands on a different fixture each time
   — it is the noise floor, which is what "no warm-up" should look like. v3
   asserted this from one filing; it holds corpus-wide, and `first_s` is in the
   artifact so it can be re-checked rather than believed.

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

3. **ADR-020's addressable-surface arithmetic reproduces exactly.** Recomputed
   from today's committed reports (`20260820-020944-all.json` +
   `20260820-013515-fast.json` over `evals/heldout`), keyed on (fixture, item):
   **768** distinct items, **15** `missing`, and the four improvable ones are
   exactly `axp-2008` items 10–13. The headline ADR-020 corrected four times
   lands where §h3 left it.

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
under each of these **nineteen** mutations. Every one was applied to a copy of
the module and run — all nineteen exit non-zero, none was reasoned about in
prose:

| # | mutation | what catches it |
|---|---|---|
| 1 | `med = statistics.median(times)` → `max(times)` | `make_record`, five distinct times |
| 2 | `pct` → `vals[0]` | golden `latency_p50_s` |
| 3 | `pct` → `vals[-1]` | golden `latency_p50_s` |
| 4 | `math.ceil` → `math.floor` in `pct` | golden p50 **and** p95 (indices fractional by design) |
| 5 | drop the 1 ms ratio floor | golden warm-up/spread maxima |
| 6 | drop the descending-order guard | largest-row-last block |
| 7 | plateau scan `range(len)` → `range(1, len)` | already-at-peak block |
| 8 | `processed` → `list(records)` (reverts round 1's R5 fix) | golden `processed_mib_per_s_max` / `_spread` |
| 9 | `_r2` → `return 1.0` | golden R² 0.8929 (the perfect-fit block pins the other side) |
| 10 | `processed_mib_per_s_spread` → `1.0` | golden spread 2.0 |
| 11 | `n_1000_seconds` ×1000 → ×100 | golden populations |
| 12 | `n_1000_gib_read` drops its ×1000 | golden populations |
| 13 | `real_dev = list(records)` | golden `real_edgar_dev` |
| 14 | batch rate ↔ real-dev rate swapped | golden `all_dev_fixtures.mib_per_s` |
| 15 | `latency_max_s` → `min(meds)` | golden |
| 16 | `sum_of_medians_s` → mean | golden |
| 17 | `median_raw_bytes` → mean | golden |
| 18 | **add a new published field** | golden diff reports `<UNASSERTED FIELD>` |
| 19 | `import socket` | AST import scan |

Mutations 1 and 2 are **PR #12's R2 repro, run verbatim**; 4, 8, 9, 10, 11, 12
are **R18's**, and 14 is **R19's**. Against the drafts they were raised on, all
of them printed `[bench self-check] ok`. That is the same defect class as an
eval case that has never been seen red — twice in a row, in the one place this
milestone had executable logic at all. Mutation 18 is the one that makes the
list finite rather than a list: it is the assertion that a *future* statistic
cannot be published unasserted.

**This is still not an `evals/adversarial/` case, and the distinction is not a
convenience.** `evals/run.py` dispatches a case to `src/<task>/eval_adapter.py`
with a filing path; there is no case shape in that harness for "a dev
instrument's arithmetic is wrong", and forcing one would mean routing bench
assertions through the extraction adapter. ADR-016's precedent is exactly this:
properties that no fixture can exercise are proved at the layer, in an
assert-based `_demo`, and watched red there. That is what happened.

Two earlier versions of this paragraph overclaimed. The first said the check
"fails if the median … breaks"; it did not, and R2 proved it. The second said it
"proves the arithmetic between the timer and the report, nothing more"; that was
also false, and R18 proved it with five surviving mutations. Both sentences are
left corrected rather than deleted, because the shape of the error — asserting a
property of an executable thing without running it — is the one ADR-020 §h3 says
this project keeps repeating, and it has now repeated inside the correction for
it. Choice 10 is the structural answer: the check no longer depends on anyone
remembering to assert a new field.

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
  `evals/oracle.py`: not in `requirements.txt`, not in CI, not imported by
  `src/`. It is not a new pipeline capability and does not touch the T8 freeze.

## Verification

```
python3 -m evals.bench --self-check      # ok (red first under all 19 mutations in §e)
python3 -m evals.run --suite invariant   # 12/12 (+4 enumerated debt)
python3 -m evals.run --suite fast        # 45/45 (+4 enumerated debt)
python3 -m evals.metrics --self-check    # ok
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

Counting the whole loop, this is the **sixth and seventh** occurrence across
PR #11 and PR #12 of asserting a property of an executable thing without
running it. That count is kept deliberately.

`.eval-baseline.json` untouched at 1.000. No paid API call was made and no code
path capable of making one was added.
