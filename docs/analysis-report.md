# Analysis report v1 — sec-10k-extract at B-freeze

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

- **Metric 6 is the headline honesty number and its denominator is small.**
  0.0 silent failures is measured over **109 audited items out of 490 confident
  ones — 22% coverage**. 280 are targeted by no check at all, and a further
  **101 sit in non-success documents and fall outside the metric's definition**,
  among them the JPM item 15 that §6 of this report names as wrongly bounded.
  An earlier version of this section quoted 27% by counting only the first
  exclusion; the pre-B audit caught it, and `metrics.py` now publishes both.
- **Metric 8 is not calibration, it is a placeholder shaped like calibration.**
  Every bucket reads 1.0 because every targeted check passes. A calibration
  curve needs failures to have any shape at all. ADR-008 already states the
  confidence scale is uncalibrated; this table confirms we cannot yet measure
  it, which is different from confirming it is good.
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
- **Metric 5's denominator is padded.** Of its 63 checks, the 5
  `known_items_only` cannot fail, and `text_not_contains` is vacuous whenever
  the item has no span. It reads as 63 independent opportunities to fail; it is
  fewer. (`item_absent` is the strong form throughout — all 15 use
  `any_status` — that part is sound.)

### Provisional targets, reset

`docs/evals/evaluation-strategy.md` set aspirational targets before any data
existed: presence recall ≥ 0.95 and silent-failure rate < 5%. Both are met on
the measured sample (1.0 and 0.0). **They are hereby recorded as met but
uninformative**: a target is only as strong as the coverage behind it, and with
73% of confident items unaudited, the silent-failure target in particular is
not yet a meaningful bar. The A-level priority is to grow the denominator, not
to improve the numerator.

---

## 2. Generalization — the held-out result

The number that matters most, because it is the only one measured on filings
the implementation was never built against.

| Run | Date | Score | Reading |
|---|---|---|---|
| **H1** | 2026-08-16 | **1/5** | first execution, at git `70d10f1` |
| **H1b** | 2026-08-16 | **4/5** | after the ADR-013 fixes, at git `453cbc4` |

**1/5 → 4/5 must not be quoted as a generalization improvement.** Of H1b's four
passes, only two are generalization evidence: `cost-2022` (clean in H1) and
`csco-2016` (fresh, never observed). The other two pass because their *labels*
were corrected, which measures the correction. The remaining failure,
`gs-2002`, is a real limitation left unfixed on purpose.

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

Measured over all 21 committed fixtures, median of 3 runs each, single process,
no caching (verified: a 5.7 MB filing takes 0.260 s cold and 0.249 s on repeat
— there is no warm-up effect beyond module import).

| | |
|---|---|
| Latency p50 | **0.041 s** (metric 9 quotes `[0.08, 0.53]` over a different population — 27 cases including re-runs, single run each, versus 21 fixtures at median-of-3 here; both are reproducible and neither is wrong) |
| Latency p95 | **0.249 s** |
| Slowest filing | JPM FY2024, 12.8 MB → **0.526 s** |
| Aggregate throughput | **18.9 MB/s** (37.8 MB in 2.00 s) |
| Peak RSS | **110 MB** driving all 21 filings in one process |

Selected points showing the size relationship:

| raw bytes | normalized chars | median s | MB/s |
|---|---|---|---|
| 69,521 | 69,398 | 0.004 | 17.8 |
| 642,332 | 67,592 | 0.042 | 15.5 |
| 1,776,947 | 312,483 | 0.223 | 8.0 |
| 5,687,600 | 430,733 | 0.249 | 22.8 |
| 12,849,180 | 1,213,298 | 0.526 | 24.4 |

**Throughput is roughly flat across two orders of magnitude of input size**
(8–37 MB/s), which is the signature of a single-pass parse: cost tracks bytes,
not item count or document complexity. The outliers are low-throughput rather
than high — MSFT 2013 at 8.0 MB/s is a filing with 858 mid-sentence source
wraps, i.e. normalization work, not segmentation work.

Deployed instance (Zeabur, 2026-08-16): AAPL 285 ms, JPM 1,683 ms end-to-end
over HTTPS including JSON serialization of the response. The ~3× gap versus
local is transport and serialization, not extraction.

## 4. Cost

**$0.00 per filing, structurally.** Not "low" — there is no paid dependency in
the pipeline to incur one. No LLM call, no paid API, no managed service beyond
the container itself. Deterministic coverage is 100% (metric 11, n=413 items),
which is the number that would justify or kill a fallback stage; today it kills
it, which is why ADR-000's deferred-LLM decision has never been revisited.

The cost of the *project* is engineering time and the SEC's free bandwidth. The
only per-request external dependency is the optional EDGAR URL mode, which is
one fetch of a public document with a declared User-Agent, far under SEC's
10 req/s fair-access ceiling.

## 5. Scalability

Projections from the measured 18.9 MB/s single-process throughput. An average
10-K in this fixture set is ~1.8 MB.

| Workload | Single process | Notes |
|---|---|---|
| 1 filing | ~0.10 s | p50 0.041 s, p95 0.249 s |
| 1,000 filings | ~3 minutes | ~1.8 GB read |
| Full EDGAR year (~7,000 10-Ks) | ~20 minutes | embarrassingly parallel |

`extract_items` is a pure function of the file bytes — no shared state, no
cross-call caching, no database — so horizontal scaling is linear and requires
no coordination. Memory is the practical per-worker constraint: peak RSS scales
with the single largest document, and 12.8 MB of raw input produced a 110 MB
process peak, so a 256 MB worker is sufficient and 512 MB comfortable.

**The honest limit is not throughput, it is correctness coverage.** At 19 MB/s
a full-year sweep is trivial; what a full-year sweep would actually surface is
format variance far beyond 21 fixtures, and the held-out result is the evidence
for that — one unseen filer's markup choice cost 18 of 21 items.

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
4. **Confidence is uncalibrated** and cannot currently be measured (metric 8).
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
5. **Calibration**, once there are enough failures for a curve to have shape.
