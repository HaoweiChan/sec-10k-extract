# Analysis report v4 — sec-10k-extract, A-track

v4 (2026-08-20): T13 performance / cost / scalability update
([ADR-021](../specs/decisions/ADR-021-benchmark-instrument.md)). §3, §4 and §5
are **rewritten, not amended**: their v3 numbers came from ad-hoc timing that
left no committed input, and were measured over 21 fixtures when the corpus is
now 37. Every figure in those three sections is now read from
`evals/report/20260820-020815-bench.json` (a new dev instrument,
`evals/bench.py`) or `evals/report/20260820-020944-all.json`, cited inline.
Four v3 claims turned out to be **wrong**, not merely stale — aggregate
throughput, p95 latency, "throughput is flat", and "peak RSS scales with the
largest document" — and each is corrected with the old value shown next to the
new one rather than silently replaced. §4 additionally carries
[ADR-020](../specs/decisions/ADR-020-fallback-not-justified.md) §f items 1–4,
which stand in for the fallback cost model T12 ruled out. Two forward
references to T11 as future work (§6 item 4, §7 item 5) are closed — T11
shipped in ADR-019. **§1 and §2 are untouched and still quote their own,
older run of record** (`20260816-234718-all.json`, 27 cases); §3–§5 quote the
current 45-case run. Both are real runs; neither is a typo for the other.

v3 (2026-08-19): T11 silent-failure update. Adds the "Silent-failure rate —
measured (T11)" section (ADR-019) and reconciles metric 6's discussion, which
previously reported 0.0 without saying it is gate-bounded; everything else
below is unchanged from v2.

v2 (2026-08-18): T10 calibration update. Adds the confidence-calibration
before/after section (metric 8 v2, ADR-018) and reconciles the sections it
touches; everything else below is unchanged from v1.

Written from committed artifacts, not from memory. Every number below is
reproducible from `evals/report/*.json` and `evals/metrics.py`; where a number
could not be measured honestly it says so rather than being estimated.

Run of record: `evals/report/20260816-234718-all.json`, git `31b07c3`,
27 cases, score 1.000.

---

## 1. Correctness verification — how we know, without public ground truth

The central constraint: `normalized_text` is extractor-owned, so **offset-level
ground truth cannot be pre-labelled** — any pre-labelled offset would freeze
the normalizer. Correctness is therefore established from five
normalization-independent sources:

1. **Boundary anchors** — a phrase from an item's first and last paragraphs,
   grep-verified against the raw fixture with its occurrence count recorded in
   the case.
2. **Presence / status / era assertions** — cheap, and they carry most of the
   signal at shallow tier.
3. **Length bands** measured from the real spans.
4. **Cross-item exclusions** guarding known bleed directions.
5. **A label-free validator battery** that needs no annotations and therefore
   runs on filings the eval set has never seen.

Plus two independent-observer layers: a **cold-reviewer** agent that reads the
implementation without the author's reasoning, and an **extraction-auditor**
that re-verifies anchors and outputs.

### Metrics (verbatim from `python3 -m evals.metrics`)

```
suite=all  score=1.0  cases=27  git=31b07c3

 1. item presence recall             1.0   (n=108)
 2. status accuracy                  1.0   (n=108)
 3. anchor-containment accuracy      1.0   (n=45)
 4. boundary tightness (proxy)       1.0   (n=47)
 5. false-positive extraction rate   0.0   (n=63)
 6. silent-failure rate              0.0   (n=109)
 7. doc-level success rate (golden)  0.8571   (n=14)
 8. confidence calibration
         [0.0,0.60)  n=2    pass=1.0
         [0.6,0.80)  n=5    pass=1.0
         [0.8,0.90)  n=37   pass=1.0
         [0.9,1.01)  n=92   pass=1.0
 9. latency p50 / p95 (s)            [0.08, 0.54]   (n=27)
10. cost per filing (USD)            0.0   (n=27)
11. deterministic coverage           1.0   (n=410)
```

### What these numbers do **not** mean

This section matters more than the table, and it is deliberately placed
immediately after it.

- **Metric 6 is the headline honesty number, and it reads 0.0 by construction,
  not by correctness.** Its denominator is items a *declared eval check*
  targets, and the pre-commit gate requires every declared check to pass
  before a commit lands — so metric 6 measures whether the gate is green, not
  whether the pipeline is right. 109 audited items out of 490 confident ones
  — 22% coverage. 280 are targeted by no check at all, and a further **101
  sit in non-success documents and fall outside the metric's definition**,
  among them the JPM item 15 that §6 of this report names as wrongly bounded.
  An earlier version of this section quoted 27% by counting only the first
  exclusion; the pre-B audit caught it, and `metrics.py` now publishes both.
  **T11 measured the real rate by sampling the untargeted population this
  metric excludes** — see "Silent-failure rate — measured (T11)" below.
- **Metric 8 v2 is a real measurement channel, not the placeholder v1 was.**
  It now reports per distinct confidence value, with debt columns alongside
  the scored ones, and states plainly that the scored side is an upper bound.
  See "Confidence calibration — before and after (T10, ADR-018)" below for the
  table and what it does and does not license.
- **Metric 4 is a proxy.** It is the length-band pass rate. True IoU is
  impossible without offset ground truth, which the design forbids.
- **Metric 7 is reported for goldens only.** Pooled it reads 0.7407, and that
  figure is misleading: five non-golden cases *deliberately* refuse or flag.
  Even the golden 0.857 is depressed by JPM, which reports `ambiguous`
  correctly.
- **Four eval checks cannot fail by construction** — `no_overlap_ordered`,
  `verbatim`, `known_items_only`, `boundary_hygiene` (ADR-010). `verbatim`
  asserts bounds and never compares text. **27/27 green means less than it
  appears**, and the metrics above inherit that weakness.
- **Metrics 1, 2, 3, 4 and 6 are pass-rates over the same declared checks**, and
  the commit gate requires 27/27 with the baseline armed at 1.000. On the dev
  set they therefore *cannot* report anything but 1.0/0.0: they confirm the gate
  is green, they do not independently measure capability. Metric 2 is
  byte-identical to metric 1 for the same reason. Metric 11 is likewise true by
  construction — no code path emits `llm_fallback`, so "100% deterministic
  coverage kills the fallback stage" is circular until a fallback exists.
  *(2026-08-19, T12: this circularity is now disposed of rather than merely
  noted. ADR-020 rules on the fallback stage from the fallback-**addressable**
  surface — an input, measurable with no fallback in existence — not from
  metric 11. Metric 11 is demoted to a dependence monitor and carries a note in
  `evals/metrics.py` saying so.)*
- **Metric 5's denominator is padded.** Of its 63 checks, the 5
  `known_items_only` cannot fail, and `text_not_contains` is vacuous whenever
  the item has no span. It reads as 63 independent opportunities to fail; it is
  fewer. (`item_absent` is the strong form throughout — all 15 use
  `any_status` — that part is sound.)

### Confidence calibration — before and after (T10, ADR-018)

**Before (v1), for reference — the placeholder table above, bucketed and
structurally unable to fail:**

```
 8. confidence calibration
         [0.0,0.60)  n=2    pass=1.0
         [0.6,0.80)  n=5    pass=1.0
         [0.8,0.90)  n=37   pass=1.0
         [0.9,1.01)  n=92   pass=1.0
```

**After (v2, metric 8 v2), verbatim from `python3 -m evals.metrics` against
`evals/report/20260818-130421-all.json` (the post-audit-fixes run; the table is
numerically identical to the pre-remap measurement in `20260818-123114`):**

```
 8. confidence calibration
       conf=0.95  n_targeted=162  failed=0    n_debt_targeted=1    debt_failed=1
       conf=0.85  n_targeted=66   failed=0    n_debt_targeted=0    debt_failed=0
       conf=0.8   n_targeted=8    failed=0    n_debt_targeted=0    debt_failed=0
       conf=0.75  n_targeted=14   failed=0    n_debt_targeted=1    debt_failed=1
       conf=0.65  n_targeted=1    failed=0    n_debt_targeted=0    debt_failed=0
       conf=0.4   n_targeted=2    failed=0    n_debt_targeted=0    debt_failed=0
       note: the scored suite is gated green, so scored pass rates here are UPPER
       BOUNDS, not accuracy — nothing scored is currently failing by construction.
       debt rows (evals/run.py's unscored 'debt' suite) are the only current-code
       failure channel and are enumerated in full here, not sampled. scored
       unaudited confident items — not targeted by any check — are counted in
       metric 6's note, not here. metric 6 never reads debt rows, so debt rows'
       own unaudited confident items are counted here as debt_unaudited=12 and
       nowhere else
```

The measurement itself was audited (cold-reviewer + extraction-auditor, both
dispositions in ADR-018): among the fixes, debt cases now load on *every* suite
run including the pre-commit gate, a crashed case's checks can no longer count
as passing, a report run from a dirty tree stamps its sha `-dirty`, and metrics
run against a report older than its case files now announce the mismatch
instead of printing silent zeros.

The debt channel is what makes this table more than a re-bucketed v1: it
enumerates real failures instead of a gate-forced 1.0. `ba-2003-asterisk-ibr`
fails at two confidence values, not one — items 11 and 13, `extracted` at
0.95 over 34 chars and at 0.75 over 59 chars respectively, in a document that
otherwise reports plain `success`. Both are wrong for the same reason (the
IBR pointer for both lives in another item's span, ADR-005 rule 1), so this is
overconfident wrongness at the top of the scale and in the middle of it, not
a single outlier. Scored rates in the table above remain upper bounds, not
accuracy: the pre-commit gate forces every targeted scored item green, so a
1.0 row measures the gate, not correctness — the debt row is the only place a
real failure can currently show up at all. ADR-018's ruling from this table:
remap-to-empirical is rejected (mapping through gate-biased single-digit
samples, especially n=2 and n=14, would be fake precision of the kind ADR-008
already banned); no scored magnitude moves, because the demonstrated
overstatement is a status defect (an item that should never have been
`extracted`), not a scale defect; and the one thing the table did license is
collapsing `BASE_MISSING` from a phantom 0.55 — a value no item could ever
actually carry, since every missing item's own `expected_item_missing`
warning always pulled it to 0.40 — down to the 0.40 it always scored, net
zero behavioral change. The *rate* of this failure shape, sampled rather than
enumerated, is T11's charter.

### Provisional targets, reset

`docs/evals/evaluation-strategy.md` set aspirational targets before any data
existed: presence recall ≥ 0.95 and silent-failure rate < 5%. Presence recall
is met on the measured sample (1.0). Silent-failure rate was, at B-freeze,
read directly off metric 6 (0.0) — which the section above now states plainly
is gate-bounded, not a measurement. **The real number was measured at T11 by
sampling; see "Silent-failure rate — measured (T11)" below.** The A-level
priority that grew out of this — grow the audited denominator, not the pass
rate — was correct at B-freeze and remains the standing lesson: a target is
only as strong as the coverage behind it.

### Silent-failure rate — measured (T11, ADR-019)

Metric 6 cannot measure this rate: its denominator is items a declared check
targets, and the pre-commit gate forces every declared check green, so it
reads 0.0 by construction regardless of pipeline correctness. T11 measured
the rate directly by sampling the population metric 6 excludes — confident
items (≥0.8) in `success`/`success_with_warning` docs, targeted by **no**
check — 447 of 781 confident items at the time of sampling.

**Method.** `random.Random(11).sample(population, 30)` — seed recorded so the
draw is reproducible and cannot have been cherry-picked. Each of the 30
sampled `(fixture, item)` pairs was adjudicated blind by the
extraction-auditor, reading the span against the fixture text with no access
to implementation reasoning (`docs/evals/audits/2026-08-19-t11-silent-failure-sample.md`).

**Result.** 1 WRONG / 30 = **3.3%**, 95% Clopper-Pearson CI **[0.1%, 17.2%]**.
Applied to the population: ~15 items, CI [0, 77]. The < 5% target from
`docs/evals/evaluation-strategy.md`: **the point estimate meets it, the CI
upper bound does not — the target is not demonstrated, only not
contradicted.** n=30 is small; the interval is the honest statement, not the
point.

**Sensitivity.** 1/30 under the extraction-auditor's independent read; 2/30
(6.7%) under the implementer's. The one item of disagreement is `cvx-2015`
item 6, an internal pointer to a paginated section — the auditor called it
CORRECT (the pointer sentence is honestly the whole labeled answer); the
implementer reads it as the same silent-failure shape as the same filing's
items 7/8 (never independently adjudicated). Recorded as a standing
disagreement in ADR-019 §e, not resolved by fiat.

**Three-instrument table:**

| instrument | what it found | coverage |
|---|---|---|
| extraction-auditor sample (blind, n=30) | 1 confirmed WRONG (`textron-2001` item 4, Executive-Officers bleed — fixed); 1 standing disagreement (`cvx-2015` item 6) | 30 of 447 unaudited confident items, 6.7% |
| stdlib screen (`evals/oracle.py`, 4 signals) | 107/521 flagged (pre-fix); net **zero** new confirmed defects, 1 known defect re-confirmed (`ba-2003`) | all 36 fixtures, every confident item |
| OSS cross-check (`evals/oracle_oss.py`, edgartools 5.50.0, dev-only) | 25/574 disagreements (4.4%); 2 are the `jpm-2024` items 7/8 internal-pointer finding this ADR adopts as debt, rest traced to edgartools' own defects or expected-by-design | 28 of 30 HTML/iXBRL fixtures; **zero plain-text coverage** (6 fixtures) |

**Correction (2026-08-19, post-commit review):** the stdlib-screen row's
107/521 was measured before this same milestone's `EXEC_OFFICERS_RE` fix
landed. At head, post-fix, the committed `evals/report/20260819-014559-
oracle.json` and a fresh run both read **224/521 = 0.4299** (the artifact's
own `screened_rate` field). Every one of the 117 new flags traces to the
fix itself — the now self-induced `large_interior_gap` check firing on its
own deliberate clip (7 fixtures, by design not defect), plus a small
`short_span` ripple from the shortened spans (3 items, all legitimate
"Reserved"-shaped Item 4 bodies). Net **zero** new confirmed defects still
holds. Full method, and the reconciliation between this confident-population
count and the CLI's own differently-scoped per-check tallies: ADR-019 §b
correction.

The screen with the widest coverage found nothing new; the judge with the
narrowest scope found the one real defect and the one open disagreement. Read
together: audit depth mattered more than audit breadth on this evidence, and
the plain-text stratum — this project's hardest era — still has no
independent second read at all. Full ruling, including the Executive-Officers
fix and the new internal-pointer debt class: `specs/decisions/ADR-019-silent-failure-rate.md`.

---

## 2. Generalization — the held-out result

The number that matters most, because it is the only one measured on filings
the implementation was never built against.

| Run | Date | Score | Reading |
|---|---|---|---|
| **H1** | 2026-08-16 | **1/5** | first execution, at git `70d10f1` |
| **H1b** | 2026-08-16 | **4/5** | after the ADR-013 fixes, at git `453cbc4` |
| **H2** | 2026-08-17 | **5/5** | T8 milestone run, at git `61619e6`, after `gs-2002` was burned to enumerated debt and replaced by `pgr-2023` |

**Neither 1/5 → 4/5 nor H2's 5/5 may be quoted as a generalization number.**
Across all three runs the set has only ever contained a handful of genuinely
unobserved filings at a time. H2's five passes decompose as: two filings with
generalization content (`csco-2016`, `pgr-2023`), two that pass because their
*labels* were corrected after H1, and one clean twice. **The generalization
evidence at B-freeze is two filings, and both of those carry no anchors and no
length bands** — so they establish that the right items were found with the
right statuses, not that their boundaries are right. A TOC-collapsed extraction
would clear either.

`gs-2002`, the one real failure H1 and H1b both found, was burned to enumerated
debt rather than fixed: the era-model rework it demands conflicts with INV-S3
and is A-level scope. It still runs every suite and still reports `STILL RED`.

What H1 actually bought, in order of value:

1. **A severe defect no dev fixture could have found.** JNJ FY2016 returned 3
   of 21 items. The segmenter's load-bearing rule — a real heading carries its
   title on the same line — inverts on a filer that puts code and title in
   separate markup blocks. The cold review had named this exact assumption as
   the one it would attack next and could not construct a fixture for it.
2. **A second, independent defect**: 18 of 21 items missing still reported
   `success_with_warning`, because no *volume* of a non-escalating warning
   could move `doc_status`.
3. **Four authoring errors of my own** — a higher error rate than the
   extractor's on the same filings. Recorded in
   `docs/evals/audits/2026-08-16-h1-heldout-triage.md` in full, including the
   methodological lesson: I asserted an *absence* using a verification scan
   weaker than the pipeline under test, which is unsound in a way asserting
   presence is not.
4. **Evidence the validator battery works on unseen input** — it caught Exxon's
   tail bleed unprompted and made JNJ's collapse loud rather than silent.

---

## 3. Runtime performance

**Input:** `evals/report/20260820-020815-bench.json`, written by
`python3 -m evals.bench --json …` (a dev instrument added in T13; design and
its seven measurement choices in
[ADR-021](../specs/decisions/ADR-021-benchmark-instrument.md)). All 37
committed fixtures, median of 3 repeats each, single process, no caching,
Python 3.14.6 on macOS arm64, pipeline at git `20f8be0`. Re-run it and the
artifact regenerates; every number in this section is a field of that file.
(The artifact's `git_sha` is this branch's *parent* commit, and correctly so:
`evals/bench.py` was still untracked when the run of record was taken, and
`src/` is byte-identical in this milestone — the sha names the pipeline that
was measured. Timings are wall-clock on one machine and will not reproduce to
the last decimal on another; the artifact records `platform` and `python` so a
divergent re-run can be told from a regression.)

| | |
|---|---|
| Latency p50 | **0.044 s** |
| Latency p95 | **0.533 s** (`bac-2006`) |
| Slowest filing | **`jpm-2024`**, 12.8 MB → **0.578 s** |
| Aggregate throughput, batch | **14.3 MB/s** (58.4 MB in 4.072 s) |
| Per-fixture throughput | **6.3 – 42.8 MB/s**, median 13.9 |
| Peak RSS | **122.1 MB** driving all 37 filings in one process (25.8 MB baseline) |

Metric 9 in §1 quotes p50/p95 over eval **cases** rather than fixtures — today
`[0.07, 0.52]` over 45 cases in `evals/report/20260820-020944-all.json`. Cases
re-run some fixtures and skip others, so the two populations differ by
construction and both are reproducible; ADR-021 §b choice 1 explains why the
fixture is the right unit here.

Selected points, showing that the size relationship is not the whole story:

| fixture | raw bytes | normalized chars | median s | MB/s |
|---|---|---|---|---|
| `textron-2001` | 69,521 | 69,398 | 0.0049 | 13.6 |
| `caps-cover-2016` | 642,332 | 67,592 | 0.0440 | 13.9 |
| `msft-2013` | 1,776,947 | 312,483 | 0.2355 | 7.2 |
| `bac-2006` | 4,517,513 | 705,899 | 0.5331 | 8.1 |
| `cvx-2015` | 5,606,365 | 417,523 | 0.3851 | 13.9 |
| `jpm-2024` | 12,849,180 | 1,213,298 | 0.5781 | 21.2 |

**Bytes are the first-order term and nothing else is close — but throughput is
not flat.** A least-squares fit of elapsed time on raw bytes explains
**R² = 0.78** of the variance, and the residual is real work, not noise:
`bac-2006` (4.5 MB) takes 0.533 s while `xom-2021` (6.2 MB) takes 0.248 s —
**2.1× longer on 27% less input**. The low-throughput end is
normalization-heavy markup (`tgt-2002` 6.3, `intc-2002` 6.5, `gs-2002` 7.0,
`ba-2003` 7.2, `msft-2013` 7.2 MB/s); the high end is text-like input
(`ksb-2007` 42.8, `ibm-1997` 32.8 MB/s). The shape is still a single-pass
parse — cost tracks input size, not item count — with a markup-density
coefficient on top of it.

**No warm-up effect beyond module import.** Across 37 fixtures the
first-repeat / fastest-repeat ratio has median **1.007** and worst case
**1.04**, and 11 fixtures were fastest on their *first* run. The per-fixture
`first_s`, `min_s`, `mean_s` and `max_s` are all in the artifact; repeat spread
`(max−min)/median` has median 1.4% and worst case 8% — stable enough that the
artifact's four-decimal latencies are quoted to three here and no further.

**Memory plateaus; it is not set by the largest document.** Fixtures are timed
in descending size order precisely so this is readable off the artifact. The
largest filing (`jpm-2024`, 12.8 MB) alone takes the process high-water from a
25.8 MB baseline to **96.4 MB**. A further 26 MB accrues over the next several
fixtures, reaching **122.1 MB** by roughly the tenth, and then stays flat for
the remaining 27 — a plateau, not a leak.

**Corrections to v3 (2026-08-20, T13).** v3's §3 was measured over 21 fixtures
with an ad-hoc script that committed nothing, and four of its claims are wrong
at 37 fixtures rather than merely stale. Recorded here rather than silently
replaced, per ADR-021 §c:

| v3 said | measured now |
|---|---|
| aggregate throughput 18.9 MB/s (37.8 MB in 2.00 s) | **14.34 MB/s** (58.4 MB in 4.072 s) |
| latency p95 0.249 s | **0.533 s** |
| "throughput is roughly flat … 8–37 MB/s", one outlier (`msft-2013`) | **6.3–42.8 MB/s**, R²=0.78, five low-throughput fixtures sharing a cause |
| "peak RSS scales with the single largest document … 110 MB" | largest filing alone **96.4 MB**, corpus peak **122.1 MB** |

The operational conclusions are unchanged — everything here is fast and small —
but v3's *explanations* of why were partly wrong, and a 21-fixture throughput
figure was propagating into every §5 projection.

**The one figure in this section with no committed artifact:** the deployed
instance (Zeabur, 2026-08-16) measured AAPL 285 ms and JPM 1,683 ms end-to-end
over HTTPS including JSON serialization, the ~3× gap versus local being
transport and serialization rather than extraction. That was a manual
observation, it is not reproducible from `evals/report/`, and re-measuring it
requires a network call this milestone is not making. It is flagged rather than
restated as though it were measured like the rest.

## 4. Cost

**Reported: $0.00 per filing** — metric 10, n=45, from
`evals/report/20260820-020944-all.json`. This is a *measurement*, not an
estimate or a target: the pipeline has no paid dependency to incur a cost. No
LLM call, no paid API, no managed service beyond the container. The extractor's
own envelope carries `cost: {llm_calls: 0, tokens: 0, usd: 0.0}` on every run.

The cost of the *project* is engineering time and the SEC's free bandwidth. The
only per-request external dependency is the optional EDGAR URL mode: one fetch
of a public document with a declared User-Agent, far under SEC's 10 req/s
fair-access ceiling.

T12's ledger row said a shipped fallback's cost model would land here. Nothing
shipped — [ADR-020](../specs/decisions/ADR-020-fallback-not-justified.md) ruled
the LLM fallback stage **not justified** — so per its §f this section carries
four things in that model's place.

### 4.1 The counterfactual: what the road not taken would have cost

Recomputed for v4 from `evals/report/20260820-020815-bench.json`
(`cost.counterfactual`), not inherited from ADR-020: the three character counts
underneath it were re-measured independently here and match §d **to the
character** (corpus 8,450,478; median fixture 108,938, `wmt-2010`; `jpm-2024`
1,213,298).

| one input pass over | est. tokens | `claude-opus-5` | `claude-haiku-4-5` |
|---|---|---|---|
| median filing | ~27,200 | **$0.14** | $0.03 |
| largest filing (`jpm-2024`) | ~303,300 | **$1.52** | $0.30 — **does not fit** |
| whole 37-fixture corpus, uncached | ~2,112,600 | **$10.56** | $2.11 — does not fit |

**Every dollar figure above is an estimate and is labelled one.** Tokens are
`chars / 4`, not a tokenizer count. ADR-020 §d asked T13 to firm them with
`count_tokens`; that is a network call, and neither `anthropic` nor `tiktoken`
is importable here or listed in `requirements.txt` — checked, not assumed.
ADR-020 §f forbids adding a dependency for it and forbids a live extraction
against a paid endpoint, so the approximation is carried forward with its
caveat intact. **How far off it is, is itself unmeasured** — that is what
"estimate" means here, and no margin is quoted because quoting one would be the
same guess wearing a confidence interval. What the table supports is an
order-of-magnitude comparison, which is all the ruling ever needed.

**The price basis is carried, not re-verified.** Anthropic first-party API list
price **as of 2026-06-24** — `claude-opus-5` $5.00/MTok input at 1M context,
`claude-haiku-4-5` $1.00/MTok input at 200K context. ADR-020 §d asked T13 to
re-check the published list before quoting it; re-checking is a network call.
The artifact stamps `cost.price_basis_date` next to every figure. **Treat the
date as the fact, not the number.**

Two properties of that table are structural rather than incidental, and they
are why the number is a decision instead of an absence:

1. **The unit of spend is the filing, not the item.** A locate-an-item fallback
   must see the whole document, because if we already knew which region to send
   we would not need it.
2. **The cheap tier does not divide the problem.** `claude-haiku-4-5`'s 200K
   context does not hold `jpm-2024`'s ~303K estimated tokens at all — the
   artifact computes that flag rather than asserting it in prose. So the
   largest filings, which have the hardest boundaries and carry the set's only
   doc-level `ambiguous`, force either a 1M-context model or a
   chunking/retrieval subsystem far larger than "a fallback stage".

And one property of caching, which is the trap this project would have walked
into: **caching bounds the eval bill and not the product bill.** Content-hash +
prompt-version caching makes the second `full`-suite run ~$0 (`cost-discipline`
rule 2). But this ships as a deployed service accepting arbitrary EDGAR URLs,
and cache hit rate on an unseen filing is zero by definition. The fallback's
cost would be bounded exactly where it does not matter.

### 4.2 The addressable surface: what that money would have bought

**4 of 768 distinct items.** Re-derived for v4 from today's committed reports —
`evals/report/20260820-020944-all.json` (dev) unioned with
`evals/report/20260820-013515-fast.json` (held-out), keyed on (fixture, item):
**768** distinct items, of which **15** come back `missing`. Of those 15, nine
sit in synthetic fixtures built by deleting the headings — eight in
`items-stripped`, one in `heading-unnumbered` — where `missing` is the correct
answer by construction of the fixture; two are genuinely absent from their real
documents (`xom-2021` item 6, `malformed-html` item 1A); and the remaining
**four are `axp-2008` items 10–13**, one filing, one root cause, a single
heading naming four item codes. ADR-020's arithmetic, which was corrected four
times under review, reproduces exactly.

One refinement to §b's wording while re-deriving it: ADR-020 describes those
nine as items "whose own committed expectations assert `missing` is the CORRECT
answer". The **counts** are right, but only two of the nine are asserted
item-by-item (`items-stripped` item 8, `heading-unnumbered` item 8); for the
other seven the case asserts the aggregate consequence instead —
`doc_status: ambiguous` plus the `expected_items_mostly_missing` warning. The
distinction does not move the surface, and it is written down rather than
smoothed over.

All four are reachable by a deterministic combined-heading fan-out, at $0, for
the whole class rather than the instances a model happens to be invoked on and
get right. That is rung 1 of the escalation ladder answering a rung-4 proposal,
and it is the whole of the ruling.

### 4.3 Metric 11 is a dependence monitor, not an argument

v1 of this report said deterministic coverage being 100% "is the number that
would justify or kill a fallback stage; today it kills it." **That was
circular and is withdrawn** (first noted in the 2026-08-19 T12 correction, now
folded into the section body). Metric 11 reads 1.0 — n=647 in
`20260820-020944-all.json` — because no code path emits `llm_fallback`, so it
reads 1.0 whatever the pipeline does. It monitors the day a fallback exists.
It never measured one. The non-circular substitute is §4.2's *input*-side
count, measurable with no fallback in existence.

### 4.4 What would reopen the question

Stated so this section reads as a decision with falsifiers rather than a
permanent answer. Any one of these reopens T12 with its own ADR; full text in
ADR-020 §e.

1. **One** addressable item appears that a deterministic change cannot reach
   *and* a fallback can — both halves required. Instrument: count
   `status: "missing"` in any committed report's `items_summary`, then check
   each against the filing **and** the contract by running the checks.
2. A residual *precision* failure acquires an honest doc-level trigger (the
   escalation-policy successor named in ADR-019 §d).
3. The plain-text stratum — six fixtures with **zero** independent
   cross-check — gets a second read and it disagrees.
4. ADR-019's sampled silent-failure CI moves, specifically its *lower* bound,
   and the new defects turn out to be absences rather than precision failures.

Explicitly **not** sufficient: metric 11 reading 100% (§4.3); the deployed
service being asked for an LLM; a filing merely being large or old.

## 5. Scalability

**Input:** `evals/report/20260820-020815-bench.json`, `perf.projection`.
Projections divide into the measured **batch** throughput of 14.34 MB/s — one
sequential pass over the whole corpus timed as a unit — rather than into the
sum of per-fixture medians, so per-file open and allocator churn are paid for.
(The two agree closely: batch 4.072 s vs sum-of-medians 4.13 s, which is the
evidence that no batch overhead is hiding.) Mean filing in this corpus is
**1.58 MB** (median 0.61 MB — 10-K sizes are heavily right-skewed, so the mean
is the right multiplier for a sweep and the median is not).

| Workload | Single process | Notes |
|---|---|---|
| 1 filing | ~0.11 s | mean-sized; p50 0.044 s, p95 0.533 s |
| 1,000 filings | **~1.8 min** (110 s) | 1.54 GB read |
| Full EDGAR year (~7,000 10-Ks) | **~13 min** (770 s) | embarrassingly parallel |

These replace v3's ~3 min / ~20 min, which divided into the 18.9 MB/s figure
§3 now corrects to 14.34 MB/s and assumed a 1.8 MB average filing. The
projections got *faster* despite the slower throughput, because the corpus mean
filing size fell as the fixture set grew.

`extract_items` is a pure function of the file bytes — no shared state, no
cross-call caching, no database — so horizontal scaling is linear and needs no
coordination. Memory is the practical per-worker constraint, and §3's
measurement changes the reasoning without changing the answer: peak RSS is not
set by the single largest document (that alone reaches 96.4 MB) but by a
122.1 MB plateau the process reaches after ~10 filings and holds for the next
27. A 256 MB worker is sufficient and 512 MB comfortable.

**The honest limit is not throughput, it is correctness coverage.** At 14 MB/s
a full-year sweep is 13 minutes; what a full-year sweep would actually surface
is format variance far beyond 37 fixtures, and the held-out result in §2 is the
evidence for that — one unseen filer's markup choice cost 18 of 21 items. Every
projection above is a *capacity* number and none of them is a *correctness*
number.


## 6. Where this system is weak

Consolidated; each entry is demonstrated by a case, a run, or an ADR, and the
README carries the same list for a general reader.

1. **The era table is a single point of silent failure.** An item mis-dated by
   one season vanishes and cannot even reach the TOC manifest to raise a
   mismatch. Three independent confirmations: Item 9C (ADR-010), GS FY2002's
   Item 15 (H1, unfixed), and the mechanism recorded as debt in ADR-013.
2. **Boundary correctness after the last item.** JPM's Item 15 swallows 83% of
   the document; Exxon's Item 16 swallows the Financial Section. Both are
   caught and flagged, neither is correctly bounded.
3. **Eval coverage is thinner than the pass rate suggests** — four vacuous
   checks, four validators with no firing proof, 284 unaudited confident items.
4. **Confidence is measured, not accuracy-calibrated.** Magnitudes stand per
   ADR-018 — the T10 measurement found no scored value overstating, only a
   status defect wrongly reaching a real confidence value. Demonstrated
   overconfident wrongness lives in the enumerated debt channel (metric 8 v2,
   §1). *(Corrected 2026-08-20, T13: this bullet used to end "the sampled rate
   of that shape across unseen filings is T11's work." **T11 shipped** —
   ADR-019 measured it at 1/30 = 3.3%, 95% CI [0.1%, 17.2%], and §1 reports it.
   What is still open is the CI, not the measurement: n=30 leaves an upper
   bound the < 5% target does not clear.)*
5. **`missing` vs `omitted`** is decided by a hardcoded two-code list, so
   permitted omissions outside it are reported as failures to find.

## 7. What would move the needle next, in order

Ranked by evaluation value per unit of effort, consistent with
`docs/product/milestones.md`:

1. **Grow the audited denominator**, not the pass rate — metric 6 is the
   headline number and 73% of confident items are outside it.
2. **Make the four vacuous checks able to fail**, starting with `verbatim`,
   which today asserts bounds and calls it verbatimness.
3. **Era-model rework** so a physically present heading can surface regardless
   of the era table — the single highest-value correctness change, and a spec
   change (INV-S3) rather than a bug fix.
4. **Held-out expansion and a second refresh cycle**; five filings found two
   real defects, and the marginal return is clearly still high.
5. ~~**Sampled confident-wrong rate (T11)**~~ — **done, 2026-08-19, ADR-019.**
   Sampled at 1/30 = 3.3%, 95% CI [0.1%, 17.2%]. *(Corrected 2026-08-20, T13:
   this item still read as future work after T11 shipped.)* Its successor on
   this list is **tighten the interval, not repeat the point estimate** —
   n=30's upper bound is what stops the < 5% target being demonstrated, and
   only a larger blind sample moves it.
