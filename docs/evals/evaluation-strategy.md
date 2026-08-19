# Evaluation strategy — sec10k

How we know the extractor is correct without any public ground truth. Suite
mechanics live in the `eval-protocol` skill; annotation mechanics in the
`case-authoring` skill; this doc fixes the dataset design, the ground-truth
process, and the metrics. **Every numeric target here is PROVISIONAL until the
first full baseline run**; revisions are recorded in the analysis report.

## Dataset design

Stratify deliberately, not randomly, across: **format era** (pre-2001 txt /
2001–2019 HTML / 2019+ iXBRL) × **size** (<1 MB vs >5 MB) × **industry**
(tech / industrial / financial — financials stress the Item 8 / F-pages
boundary hardest) × **difficulty** (standard / known-trap / designed-to-fail).

Two **annotation tiers** buy diversity without linear annotation cost:

- **Deep tier** (~5 golden filings, ~30–60 min each): full anchor work —
  boundary anchors, length bands, cross-item exclusions. Candidates: AAPL 2025
  (done), a mid-era HTML filing (~2005–2015), a large financial iXBRL, one more
  pre-2003/early-HTML, one boring mid-cap.
- **Shallow tier** (+5–8 filings, minutes each): presence/status/era assertions
  only — the structural invariants run free on every filing, so even a
  shallow case buys real correctness signal.

Plus **4–5 adversarial cases**: GE 1994 (done), 10-Q input → `unsupported`,
hand-degraded malformed HTML (self-created), a 10-K405, and whatever
cold-reviewer finds during implementation.

**B-level total ≈ 12–15 filings.** A-level: 25–35 — shell-company tiny 10-Ks,
more financials, a 2001–2004 transitional filing, smaller-reporting-company
variants (omitted 7A), every burned held-out filing promoted in; shallow
filings upgraded to deep where audits warrant.

## Splits and anti-overfitting

- **Dev** = `evals/golden/` + `evals/adversarial/` — iterate freely; the fast
  suite gates every commit.
- **Local held-out** = `evals/heldout/`, deliberately **not** in the runner's
  `CASE_DIRS` so `--suite all` cannot leak it; run only via an explicit
  `--dir evals/heldout` invocation (small runner addition, T2). 3–5 filings at
  B, fixtures + cases committed (public EDGAR data; keeps milestone results
  reproducible), frozen at authoring time.
- **Workflow**: held-out runs happen only at milestones; results are committed
  to `evals/report/` **before** any fix is attempted.
- **Audit trail** (the burn rule is otherwise honor-system — these make
  violations detectable): held-out runs never use `--no-report`; run reports
  embed the git SHA at run time (runner addition, T2); each milestone held-out
  report is committed in its own commit, so run-before-fix ordering is
  provable from history rather than asserted.
- **Burn semantics**: a held-out case is burned the moment its labeled outcome
  influences implementation in any way — a fix, a threshold choice, a new case
  authored because of it. Re-running alone does not burn a case; influence
  does. Burned cases go through failure-triage, are promoted to
  dev-adversarial, and are replaced with fresh filings at the next expansion.

## Ground truth without public data

Key constraint, stated plainly: `normalized_text` is extractor-owned, so
**offset-level ground truth cannot be pre-labeled** — any pre-labeled offset
would freeze the normalizer. Ground truth is therefore built from
normalization-independent evidence:

1. **Boundary anchors** — a unique phrase from an item's first and last
   paragraphs, verified against the raw fixture by grep, occurrence counts
   recorded in the case's `provenance` (pattern established by
   `aapl-2025-content`).
2. **Presence / status / era assertions** — cheap and high-value on every
   filing.
3. **Length bands** — `min_chars` (exists) + `max_chars` (T2) from measured
   raw lengths.
4. **Cross-item exclusions** — `text_not_contains` guarding known bleed
   directions.
5. **Structural invariants + the label-free validator battery** (architecture
   layer 8: TOC manifest cross-check, gap analysis, fingerprints, dual-method
   agreement) — free correctness signal on every filing, annotated or not,
   including held-out filings no label ever touched.
6. **Dual-pass review** — the extraction-auditor independently re-verifies a
   sample of anchors against the source before a golden case is trusted;
   recorded in `provenance`.
7. **Sampling audit** — post-run, the auditor reads sampled extracted items
   against the source filing (see `.claude/agents/extraction-auditor.md`).

**Second-extractor cross-check oracle** (edgartools / sec-parser): **no at B,
yes at A.** Public OSS satisfies the materials rule; it runs only inside the
auditor loop as a dev-time instrument — never a runtime dependency, never
auto-accepted truth (correlated blind spots, and both tools are weak on
pre-2001 txt, exactly our hard cases). Disagreement is a lead for manual
source reading; agreement on modern filings raises audit confidence cheaply.

## Metrics

Computed by `evals/metrics.py` (stdlib, lands at T8 with the first milestone
run) over the latest committed
`evals/report/*.json` + case JSONs. Prerequisites (all T2): the adapter echoes
per-check results **and** per-item results (confidence, status, method) plus
the run's `doc_status` — metrics 6 and 8 join per-item confidence to check
outcomes, which per-check echo alone cannot support; audit findings are
recorded machine-joinable (case id + item code) so they can enter metric 6's
numerator. Metric 6's denominator counts only items that at least one check or
audit sample actually targets — items nothing targets are reported separately
as *unaudited high-confidence items*, never silently counted as fine.

| # | Metric | What it measures / computed from | Failure it reveals |
|---|---|---|---|
| 1 | Item presence recall | share of `item_present` checks passing | missed items |
| 2 | Status accuracy | share of status-asserting checks passing | absence misclassification (IBR vs missing vs omitted) |
| 3 | Anchor-containment accuracy | share of `text_contains` checks passing | boundary wrongness at containment level |
| 4 | Boundary tightness (IoU proxy) | items where first+last anchors pass AND length within band — honestly a proxy; true IoU is impossible without offset ground truth | loose or bleeding boundaries |
| 5 | False-positive extraction rate | failures among `item_absent` + `known_items_only` + `text_not_contains` | hallucinated items, cross-item bleed |
| 6 | **Silent-failure rate** | among items reported with confidence ≥ 0.8 (provisional threshold) inside `success`/`success_with_warning` docs: share failing any golden check or audit finding; measured at milestones over dev + held-out + audit samples | the headline honesty number |
| 7 | Doc-level success rate | share of eval filings with passing case and `doc_status` ∈ {success, success_with_warning} | overall usability |
| 8 | Confidence calibration | bucket items by confidence band (edges provisional); empirical accuracy of anchored checks per bucket | overconfidence — explicitly graded |
| 9 | Latency p50/p95 | per-case `seconds` + per-stage `timings` | perf analysis input |
| 10 | Cost per filing | envelope `cost` field | cost analysis input (B: structurally $0 — a reported result) |
| 11 | Deterministic coverage % | share of extracted items with `method != llm_fallback` | LLM dependence — a monitor, ~~the number that justifies or kills a fallback stage~~ (that claim was circular; see below) |

Aspirational initial targets (presence recall ≥ 0.95 on golden, silent-failure
rate < 5%) are **provisional** — reset after the first full baseline run, with
the change recorded in the analysis report. `metrics.py` output is pasted
verbatim into `docs/analysis-report.md` at each milestone; the report JSONs in
`evals/report/` remain the committed raw record.

**Silent-failure target, status (T11, ADR-019):** measured by sampling, not by
metric 6 (which reads 0.0 by construction — the gate forces every declared
check green, see `evals/metrics.py`'s metric-6 note). Sampled rate 1/30 =
3.3%, 95% CI [0.1%, 17.2%]. The point estimate meets the < 5% target; the CI
upper bound does not — **the target is not demonstrated, only not
contradicted**. n=30 is small; the honest statement is the interval.

**Metric 11, corrected (T12, ADR-020).** Metric 11 was written as "the number
that justifies or kills a fallback stage". It cannot be: it counts an *output*
of a stage that does not exist, so it reads 1.0 whatever the pipeline does, and
"100% deterministic coverage kills the fallback" is circular. It is retained as
a dependence monitor, meaningful only once a fallback exists. **The number that
actually ruled on the fallback stage is the fallback-*addressable* surface** —
the count of items on which any honest trigger policy would fire, which is an
*input* and therefore measurable with no fallback in existence: count
`status: "missing"` in a committed report's `items_summary`, then check each one
against the filing **and the contract**. It read **15 of 768** distinct items
across both eval sets. Eleven are either genuinely absent from their documents
or sit in fixtures whose own committed expectations assert `missing` is the
correct answer. The remaining four are one filing's combined
`ITEMS 10, 11, 12 and 13.` heading — real recall gaps — but only **1 can be
converted into a contract-valid improvement by any extraction method at all**:
INV-S1 forbids the other three from carrying a span, and ADR-011 leaves no
span-free status for them. A deterministic heading-shape change reaches that one
item identically, at $0. ADR-020 walks each one and names the conditions that
would reopen the decision.
