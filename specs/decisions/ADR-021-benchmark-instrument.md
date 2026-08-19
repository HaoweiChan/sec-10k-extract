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

Seven measurement choices, each of which could reasonably have gone the other
way, so each is recorded rather than left in the code:

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
   the median. Measured spread on the run of record: `(max-min)/median` has
   median **1.4%**, worst **8%** — the median is stable at the precision
   published.

3. **The throughput denominator is raw bytes on disk, not normalized chars.**
   The pipeline reads and normalizes the whole file, so bytes-in is the
   work-in; normalized chars are an output of that work. Both are recorded per
   fixture, so either ratio can be recomputed from the artifact.

4. **The batch pass is timed as a unit, separately from the per-fixture
   medians.** A real batch pays per-file open and allocator churn that a
   median-of-3 loop amortizes. §5's projection divides into the *batch*
   number. On the run of record the two agree closely (batch 4.072 s vs
   sum-of-medians 4.13 s), which is itself the evidence that no batch overhead
   is hiding.

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
   The instrument's own arithmetic (median, throughput, projection round-trip,
   cost, the Haiku-context flag) is covered by `python3 -m evals.bench
   --self-check`, an assert-based `_demo` on synthetic inputs — the same
   "proved at the layer, not by a fixture" treatment ADR-016 gives
   `boundary_hygiene` and ADR-019 gives the oracle.

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

## c) What the measurement falsified

Four claims in v3 §3/§5 are wrong at 37 fixtures. They are corrected in v4 with
a dated note rather than restated, on the ADR-019/ADR-020 precedent.

| v3 said | measured (`evals/report/20260820-020815-bench.json`) |
|---|---|
| aggregate throughput **18.9 MB/s** (37.8 MB in 2.00 s, 21 fixtures) | **14.34 MB/s** (58.4 MB in 4.072 s, 37 fixtures) |
| latency **p95 0.249 s** | **p95 0.533 s** (`bac-2006`); max 0.578 s (`jpm-2024`) |
| "throughput is roughly flat across two orders of magnitude (8–37 MB/s)" | **6.34–42.8 MB/s**, a 6.7× spread, and size explains only **R²=0.78** of the variance in elapsed time |
| "peak RSS scales with the single largest document … 12.8 MB of raw input produced a 110 MB process peak" | the largest filing alone reaches **96.4 MB**; the corpus peak is **122.1 MB** |

The third and fourth deserve more than a row.

**Throughput is not flat.** `bac-2006` (4.5 MB) takes 0.533 s while `xom-2021`
(6.2 MB) takes 0.248 s — 2.1× longer on 27% *less* input. Bytes are the first
order term and nothing else comes close, but v3's stronger reading — "cost
tracks bytes, not item count or document complexity" — is not what the data
says. The low-throughput end is normalization-heavy markup (`tgt-2002` 6.3,
`intc-2002` 6.5, `gs-2002` 7.0, `ba-2003` 7.2, `msft-2013` 7.2 MB/s) and the
high end is text-like input (`ksb-2007` 42.8, `ibm-1997` 32.8 MB/s). v3 named
`msft-2013`'s source wraps as the one outlier; there are five, and they share a
cause. The operational consequence is unchanged — everything is fast — so this
corrects the *explanation*, not the capacity planning.

**Peak RSS does not track the largest document alone.** Processing in
descending size order, `jpm-2024` (12.8 MB, the largest) brings the process
high-water to 96.4 MB from a 25.8 MB baseline. Twenty-six more MB accrue over
the following fixtures, reaching 122.1 MB by roughly the tenth and then staying
flat for the remaining 27 — a plateau, not a leak. A per-worker budget still
sits comfortably at 256 MB, so the v3 sizing advice survives; the reason given
for it did not.

## d) What the measurement confirmed

Recorded because a benchmark that only ever falsifies is as suspect as one that
only ever confirms.

1. **No warm-up effect beyond module import.** First-repeat vs fastest-repeat
   ratio has median **1.007** and worst case **1.04** across 37 fixtures, and
   11 fixtures were fastest on their first run. v3 asserted this from one
   filing; it holds corpus-wide, and `first_s` is in the artifact so it can be
   re-checked rather than believed.

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

The runnable check the new logic does leave behind is
`python3 -m evals.bench --self-check` (choice 6 above), which fails if the
median, throughput, projection round-trip, RSS high-water, cost arithmetic, the
Haiku-context flag or the no-network property breaks. It was watched fail
during authoring — the AST no-network assertion is the second version of that
check, because the first grepped the module's own source and matched its own
banned-strings list.

## f) Consequences

- `docs/analysis-report.md` goes to **v4**: §3, §4 and §5 rewritten against
  `evals/report/20260820-020815-bench.json` and
  `evals/report/20260820-020944-all.json`, each citing its input by filename.
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
python3 -m evals.bench --self-check      # ok
python3 -m evals.run --suite invariant   # 12/12 (+4 enumerated debt)
python3 -m evals.run --suite fast        # 45/45 (+4 enumerated debt)
python3 -m evals.metrics --self-check    # ok
```

`.eval-baseline.json` untouched at 1.000. No paid API call was made and no code
path capable of making one was added.
