# Milestones — B-level exit criteria, A-level hardening

Durable exit criteria, ranked hardening priorities, and the milestone
decomposition (what must go red/green, in what dependency order). Fine-grained
scheduling and task status live in the session; judgment calls become ADRs.

## B-level exit checklist

A legitimate B is a complete, honest system — not a happy-path prototype.

- [ ] All three format eras handled (pre-2001 txt subject to its stop-loss ADR —
  if demoted, `ge-1994-oldformat` is enumerated as honest adversarial debt,
  never deleted).
- [ ] All golden cases green; adversarial cases green or enumerated as debt
  with triage notes.
- [ ] Eval set ≈ 12–15 filings across deep + shallow annotation tiers,
  era-stratified (see `docs/evals/evaluation-strategy.md`).
- [ ] Every invariant in `specs/000-invariants.md` backed by a case tagged
  `"suites": ["invariant"]` — includes retagging `ge-1994-oldformat` to close
  the known INV-S3/S4 gap.
- [ ] Held-out set (3–5 filings) authored frozen, run once at the milestone,
  results committed **before** any fix.
- [ ] Contract v2 envelope implemented; ADR-001..003 recorded.
- [ ] Zeabur-deployed inspector: fixture select + upload + EDGAR URL;
  item/status/confidence/method badges; warnings + `doc_status` banner; trace
  debug panel (frontend spec in `task2-problem-definition.md`).
- [ ] README: run instructions, key design decisions, where AI helped, and the
  assignment-mandatory **works-well** and **difficult/unreliable/unsupported**
  lists with concrete failure cases.
- [ ] `docs/analysis-report.md` v1 with **measured** numbers: latency p50/p95,
  cost (structurally $0 + reasoning), scalability notes, metrics table,
  correctness-verification summary.
- [ ] ≥ 3 curated prompt records; pre-B extraction-auditor audit committed to
  `docs/evals/audits/`.
- [ ] Baseline armed via `--update-baseline` with its ADR.

## A-level hardening — ranked by marginal evaluation value

Evidence-deepening, not feature-adding:

1. **Eval expansion** to 25–35 filings + the held-out refresh cycle (deepest
   lever on the "eval depth" grade).
2. **Confidence calibration** measured per bucket, published, and scores
   remapped through the empirical table.
3. **Silent-failure rate** measured and driven down via the auditor loop + the
   OSS second-extractor cross-check oracle.
4. **Fallback stage** designed in a dedicated ADR only once residual-failure data
   exists and justifies one (if it ships: cached, budget-capped, `full`-suite
   only, runtime prompt preserved in `prompts/`).
5. **Perf/cost/scalability with real numbers**: large-filing and batch
   benchmarks, projection to N filings, fallback cost model.
6. **Taxonomy completeness** + 10-K/A stretch scope.

## Milestone decomposition (eval-first: every implementation task names cases that go red first)

- **T1** — planning artifacts: docs/, contract v2, ADR-001..003,
  extraction-auditor agent, case-authoring skill, curated prompt record.
- **T2** — eval expansion round 1 (case-commit, all red): retag `ge-1994`;
  new deep-tier goldens + shallow-tier filings + 10-Q→unsupported +
  malformed-HTML adversarial cases. Hardening scope fixed by the 2026-08-15
  methodology audit (`docs/evals/audits/2026-08-15-methodology.md`):
  - adapter: `doc_status` + `max_chars` + expected-set-completeness check
    (INV-S4 currently has no enforcing check); era-validity strengthening
    (`item_absent`/`known_items_only` pass era-invalid non-extracted codes);
    `no_empty_success` reconciled with `doc_status` and its one-good-item
    gaming hole closed; `min_chars` on null offsets → judgment, not TypeError;
    result echo is per-item (confidence, status, method) + `doc_status`, not
    per-check only.
  - runner: `--dir` flag for held-out; reports embed the git SHA; case
    discovery hardened against stray nested JSONs.
  - cases: end-of-item anchors + `max_chars` on existing goldens; replace
    non-discriminating anchors (GE "General Electric": 101 hits) and record
    every anchor's occurrence count; status assertions for AAPL items 6 and
    10–14 ([Reserved] / incorporated-by-reference) and 7A checks; a
    determinism check backing INV-S2 (the current `verbatim` check is a
    bounds check only). While authoring, record each item's measured
    length/shape/density stats in `provenance` — they seed the layer-8
    validator priors set at T5.
  **Plus the early end-to-end deploy spike**: hello-world FastAPI wrapping the
  stub, live on Zeabur, one EDGAR fetch from it — de-risks deployment and
  EDGAR egress now, not at T7.
- **T3** — document selection + normalization (spike first: determinism +
  word-joining on both fixtures). Partial green: `verbatim`.
- **T4** — candidates + TOC filter + boundaries + status classification →
  `aapl-2025-*` and `ge-1994` green (the TOC trap dying is the single most
  important green in this repo). **Txt stop-loss decision point at T4 exit.**
- **T5** — validation + confidence + v2 envelope: the layer-8 **label-free
  validator battery** (TOC manifest cross-check, gap analysis, boundary
  hygiene, part-region consistency, rank-order length sanity, numeric
  density, keyword fingerprints, dual-method boundary agreement — architecture
  overview has the definitions and warn-don't-hard-fail policy), with priors
  and thresholds measured from eval-set distributions, ADR-recorded — no
  pre-data numbers. → `doc_status` cases green; then cold-reviewer run →
  findings become adversarial cases → fix loop.
- **T6** — remaining goldens green (mid-era HTML, large financial iXBRL).
- **T7** — full frontend UI on the already-proven Zeabur deploy.
- **T8** — held-out authoring (frozen) + `evals/metrics.py` + milestone run +
  analysis report v1 + README lists + pre-B audit + baseline = **B**.
- **T9+** — A-hardening in the ranked order above; each item starts with its
  eval cases (calibration starts by measuring; any fallback starts with the
  failures it must rescue, tagged `full`).

## Commit strategy

Commits map to the task list in eval-first pairs — `eval: add <cases> (red)`
then `feat: <stage>; <cases> green`. Docs/ADR commits stay separate but
consolidated: a coherent decision batch, never per-file dribbles. Consolidate
before every commit (CLAUDE.md hard rule 7): verify the batch first — diff
re-read, relevant audits — so the history reads as settled progress, not
fix-commits chasing mistakes. Milestone eval runs commit their
`evals/report/` JSON in the same commit. Baseline moves are their own commit
referencing an ADR (hard rule 1). Expect ~15–20 real commits to B with a
legible red→green narrative; the story is the deliverable — never squash it
away.

## Prompt curation for this task

Per `prompts/README.md` and hard rule 6, curate: the planning session
(with its correction chain); the contract-v2 decision; major failure-triage
correction chains during T3–T6; auditor invocations and finding dispositions;
and, if a fallback ships at A, its runtime prompt itself (versioned, tied to
cache keys — graders read `prompts/`, and a runtime prompt is a key prompt).

## Appendix — pre-implementation self-review

1. **All assignment requirements represented?** Yes — coverage map in
   `assignment-requirements.md`; audited by spec-drift + methodology-mode
   auditor runs.
2. **Could metrics pass while content is wrong?** Yes: anchors test
   containment, so a boundary can bleed while `text_contains` passes.
   Mitigations: length bands, cross-item exclusions, tightness proxy, auditor
   sampling. Named in taxonomy F7.
3. **Likeliest silent failures**: Item 8 tail bleed; IBR-vs-missing
   misclassification; lenient-tier false headings in old txt filings. Each has
   dedicated eval representation and audit focus.
4. **Eval-overfit risk?** Real — the implementer authors cases against known
   fixtures. Counters: frozen held-out with burn-on-influence semantics,
   auditor dual-pass on anchors, eval-adversary gap-hunting.
5. **Overengineering candidates**: any fallback before residual-failure data;
   accession lookup; HTML-parsing dependencies (stdlib until an eval case
   defeats it, ADR-003); trace schema beyond what UI/auditor consume.
6. **Under-specified areas**: page furniture inside old-txt items (kept in
   text — settle via eval case); signature-block tail of the last item;
   TOC-cluster thresholds (empirical, T4); GE Part III IBR granularity.
7. **Top-3 technical unknowns**: stdlib HTMLParser on 1.5 MB iXBRL (word
   boundaries + speed); TOC-cluster + greedy assignment on filings with loose
   TOCs; Zeabur→EDGAR reachability.
8. **Spikes before committing to architecture** (throwaway): normalization
   determinism + word-join check on both fixtures; candidate-count dump on
   AAPL (expect exactly 2 per code) and GE (expect prose-trap hits); minimal
   end-to-end deploy spike at T2.
9. **Shortest path to B**: T1→T8; only compressible items are deep-tier golden
   count (floor 4) and trace richness.
10. **Top-3 post-B investments**: eval expansion + held-out cycle; measured
    calibration; silent-failure rate via auditor + cross-check. Three evidence
    investments, zero feature investments.
