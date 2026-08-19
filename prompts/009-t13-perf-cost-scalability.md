# 009 — T13: making the performance numbers reproducible (2026-08-20)

A pr-loop cycle whose deliverable looked like a documentation refresh and was
not. The ledger row asked for "large-filing + batch benchmarks, projection to N
filings"; the report already had all three. What it did not have was an *input*.
Outcome: [ADR-021](../specs/decisions/ADR-021-benchmark-instrument.md), one dev
instrument (`evals/bench.py`), analysis-report v4, and four published numbers
retracted.

## The prompt decisions that mattered

- **The validation gate was quoted at the implementer as the hard part, not as
  boilerplate.** "*every number measured from committed `evals/report/` runs,
  none guessed; the report cites its inputs*" — and then, explicitly: today's
  §3 numbers "came from ad-hoc timing that left nothing committed — a reviewer
  cannot reproduce or even locate them. Closing that gap is the substance of
  this milestone." Without that sentence the obvious reading of T13 is "re-run
  the timings and update the table", which would have reproduced the same
  uncitable numbers one corpus later. The gate was the task.

- **A precedent was named instead of a design.** "*Precedent for a committed
  measurement instrument that is not part of the scored suite: `evals/oracle.py`
  … Follow that shape if you add one.*" Pointing at an existing artifact rather
  than specifying an interface is what kept the instrument stdlib-only, dev-only
  and C7-safe without any of that having to be re-argued. Rung 2 of the ladder —
  reuse what is already here — applied to *process*, not just code.

- **The unavailable measurement was pre-disposed, with the fallback written
  out.** ADR-020 §f had asked T13 to firm the token estimates with
  `count_tokens`. The prompt closed that loop in advance: no paid call, no new
  dependency, "*and if neither is available without adding a dependency … or
  making a network call, keep the existing chars/4 estimate and say so
  explicitly in the prose, with the caveat.*" That converts an impossible
  instruction into a reportable non-result. The temptation it defused is real:
  an inherited "~$0.14" reads better without the word *estimate* next to it.

- **The recurring failure mode of this project was named by its shape.** "*do
  not assert a property of an executable contract in prose without running
  it*" — the error PR #11 caught four separate times in T12. In this milestone
  it bit twice anyway, once in the instrument's own self-check (chain entry 4)
  and once in the descending-size-order reading of memory (chain entry 2). Both
  were caught by *running* the thing rather than by re-reading it, which is the
  only reason they are chain entries and not shipped claims.

- **The instrument was told to make one specific question falsifiable.**
  Fixtures are timed in descending size order for a single reason: it turns
  "peak RSS scales with the largest document" from an assumption into a fact
  readable off the artifact. Designing the measurement around the claim most
  likely to be wrong is what found the one memory claim that was.

## What the instrument confirmed, and why that is recorded

A benchmark that only ever falsifies its predecessor is as suspect as one that
only ever confirms it. ADR-021 §d records three confirmations alongside §c's
four retractions — the no-warm-up property (v3 asserted it from one filing; it
holds across 37, with `first_s` in the artifact), ADR-020 §d's character counts
reproducing to the character, and ADR-020's four-times-corrected
addressable-surface arithmetic reproducing exactly. The last one matters most:
768 distinct items, 15 `missing`, the four improvable ones exactly `axp-2008`
10–13, recomputed from today's reports by a different person on a different
day. A headline that moved four times under review lands where §h3 left it.

## Assumption → Eval contradiction → Correction

- Assumed: §3's numbers were stale — measured over 21 fixtures instead of 37 —
  and a re-run at the current corpus would restate them larger.
- Eval said: the bench artifact — aggregate throughput **14.61 MiB/s** against
  v3's 18.9, p95 **0.508 s** against 0.249, and a per-fixture spread of
  **6.62–33.68 MiB/s** against a claimed "roughly flat 8–37". `bac-2006`
  (4.31 MiB) takes 2.1× longer than `xom-2021` (5.87 MiB). *(Figures are the
  artifact of record `20260820-024620-bench.json`, after round 1 pulled the
  three refusal fixtures out of the rate statistics and put everything on
  binary units; the first run of the same instrument,
  `20260820-020815-bench.json`, read 14.34 MB/s and 6.3–42.8 with `ksb-2007`
  setting the top.)*
- Corrected: four numbers **retracted rather than replaced** — ADR-021 §c and
  report v4 §3 both print the old value beside the new one. "Cost tracks bytes,
  not document complexity" is narrowed to a first-order term plus a
  markup-density coefficient, with the R²=0.78 that licenses only that.

- Assumed: peak RSS scales with the single largest document, so the corpus peak
  and the largest filing's peak are the same number (v3 said 110 MB for both).
- Eval said: with fixtures processed in **descending** size order, `jpm-2024`
  alone takes the high-water to **94.6 MiB** and the corpus reaches its
  **122.8 MiB** peak within the first handful, then holds within 0.5 MiB of it
  for the rest. (Round 1, R11: my first write-up said "122.1 MB by roughly the
  tenth", which did not match its own artifact. The plateau index is now a
  computed field and is run-variable — 4 here, 9 on the previous run — so the
  report states the plateau, not the index.)
- Corrected: v4 §5 says *plateau*, not *largest document*. The 256 MB per-worker
  sizing survives; the reason given for it did not. Recorded because the sizing
  advice being accidentally right is not the same as it being justified.

- Assumed: ADR-020 §f's instruction to firm the token counts with `count_tokens`
  was executable at T13.
- Eval said: `count_tokens` is a network call, and neither `anthropic` nor
  `tiktoken` is importable here or listed in `requirements.txt` — checked by
  import, not assumed from the file.
- Corrected: chars/4 carried forward **with its caveat intact**, **no margin
  quoted** — a draft of this record said "the ±20% margin stated", which was
  the opposite of what shipped and is corrected here (PR #12, R6). §4.1 says
  plainly that how far off the estimate is, is itself unmeasured, because
  quoting a margin would be the same guess wearing a confidence interval. The
  price basis is marked *carried, not re-verified*, with
  `cost.price_basis_date` stamped in the artifact next to every dollar figure.
  ADR-021 §b choice 7 records the non-result as a decision rather than leaving
  a silently unexecuted instruction in ADR-020.

- Assumed: the instrument's "this module cannot make a network call" self-check
  could be a substring scan of its own source.
- Eval said: `--self-check` failed on its first run — the scan matched its own
  banned-strings list.
- Corrected: the check parses its own AST and asserts the imported module roots
  are disjoint from the network set. Watched red first, per hard rule 2's
  spirit at the layer where this milestone had any executable logic at all.

- Assumed: v3's §6/§7 described current state.
- Eval said: both still called the sampled silent-failure rate "T11's work"
  after ADR-019 shipped it on 2026-08-19 — a forward reference to a milestone
  the same document reports on in §1.
- Corrected: both bullets closed with dated correction notes, and §7 item 5's
  successor restated honestly — the open question is the **interval**, not the
  point estimate, because n=30's upper bound is what stops the < 5% target
  being demonstrated.

- Assumed: correcting the report was enough.
- Eval said: `README.md`'s performance table carried the same retracted
  figures, plus a claim that "analysis-report v2 re-measures at T10", which it
  did not.
- Corrected: README's table rebuilt from the same artifact, with its own dated
  correction note. A number is not retracted while a copy of it is still
  published one file over.
- Then eval said it **again**, on the file I had just rewritten: `README.md`
  line 107 still published the retracted `0.53 s` large-filing latency, 77
  lines above the note retracting it, and my correction note said "four of
  those figures are wrong" while naming three — importing ADR-021 §c's count of
  four *claims* into a table that never carried the flatness claim at all
  (PR #12, R1 and R9). Corrected by grepping all four retracted figures
  repo-wide rather than fixing the line the reviewer cited: the only surviving
  uncorrected copy was line 107; every other hit is inside an explicit
  correction table or a dated audit file. The note now enumerates exactly the
  five rows that table had and what each became, including the one that did not
  change. **The rule I wrote two paragraphs above is the rule I then broke in
  the same commit**, which is the reason it is worth stating twice.

### Round 1 of PR #12 review — three more, and the pattern behind them

- Assumed: `evals/bench.py --self-check` covered the instrument's arithmetic,
  because that is what I wrote in ADR-021 §b6 and §e.
- Eval said: the reviewer mutated `med = statistics.median(times)` to
  `max(times)` and `pct`'s return to `vals[0]`, and `--self-check` still
  printed `ok`. I ran both mutations myself before touching anything: both
  reproduced. `_demo` had been asserting `statistics.median([...]) == x` — a
  test of the standard library — and never read `latency_p50_s` or
  `latency_p95_s` at all, so the p50, p95 and every per-fixture median in the
  published report were produced by code no assertion touched.
- Corrected: `make_record` extracted out of `run_all` so `_demo` drives the
  real median path with a known list of times; percentile assertions moved onto
  the fields `summarize` emits, over a 20-row set whose p50 and p95 differ from
  each other and from both extremes. Seven mutations now go red, each one
  applied to a copy and **run**, listed in ADR-021 §e. This is the fourth
  instance in two PRs of asserting a property of an executable thing without
  executing it — the shape ADR-020 §h3 named — and the first where the thing
  was mine and brand new.

- Assumed: "all 37 committed fixtures" described the benchmark's population,
  and the mean filing size of that population was the right multiplier for a
  full-EDGAR sweep.
- Eval said: three separate findings (R3, R4, R5) that turned out to be one
  question — which filings count. **42** fixture directories are committed, not
  37; the 5 held-out ones were excluded by an accident of which helper I reused
  (`evals.oracle.iter_fixtures`), not by a decision I had written down. Nine of
  the 37 are self-created derivatives, seven of them from the corpus's
  *smallest* real filings, so the mean I published (1.578 MiB) was diluted —
  and my explanation for its drop from v3's assumed 1.8 MB ("the corpus mean
  fell as the fixture set grew") had it backwards: v3's *guess* was closer to
  the real-filing mean than my *measurement*. And the top of my published
  throughput range, 42.8 MB/s on `ksb-2007`, was a document the pipeline
  refuses before segmentation — I had explained it as "text-like input".
- Corrected: resolved as one population question, not three sentences. The
  artifact now emits three populations with a `rate_source` each and names
  `real_edgar_committed` (33 real EDGAR filings, 2.104 MiB mean) as
  `projection_of_record`; the EDGAR-year sweep moves ~12.6 → ~16.9 min. Held-out
  filings contribute **sizes only**, by `stat`, never a pipeline call, so no
  held-out outcome enters a committed artifact. Refusals are flagged in the
  artifact and excluded from the rate statistics but not from latency or
  memory. All of it is ADR-021 §b choice 8 — a decision, now written down.

- Assumed: the numbers I quoted were traceable because I named the file they
  came from.
- Eval said: R7 — about a third of §3's numbers were *derivations* from
  `records`, not fields, while the section claimed "every number in this
  section is a field of that file"; and R8 — sizes were quoted in decimal MB
  against rates in binary MiB/s, so dividing a published size by a published
  time missed the published rate by 4–5%.
- Corrected: the derivations became fields (`perf.derived`, `perf.populations`)
  rather than the sentence becoming vaguer, and every unit is binary with
  `*_mib_*` field names and a `units` block. Two of my own v4 claims were
  **withdrawn as run-unstable** in the process — "11 fixtures were fastest on
  their first run" (11 → 3 → 3 across three runs of identical code) and the
  repeat-spread maximum — which only became visible once the statistics were
  computed by the instrument on every run instead of by me once.

