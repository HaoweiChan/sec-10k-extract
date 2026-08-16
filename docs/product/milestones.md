# Milestones — B-level exit criteria, A-level hardening

Durable exit criteria and ranked hardening priorities — what "done" means, not
where we are. Milestone status and per-milestone exit gates live in
`tasks/TODO.md` (ADR-009); fine-grained scheduling lives in the session;
judgment calls become ADRs.

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
- [ ] Held-out set (3–5 filings) authored frozen **before** the frontend, run
  twice (T7 exit, T8), results committed **before** any fix — one measurement
  taken on the last day cannot be reacted to, and the burn/refresh cycle needs
  a turn of the crank to be more than a described policy.
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

## Milestone decomposition — moved

The per-milestone decomposition, its status, and each milestone's exit gate now
live in **`tasks/TODO.md`** (ADR-009). It moved rather than being copied: two
files listing the same milestones drift, and the T5 exit gate went unnoticed
precisely because it was a clause inside prose here. This file keeps the
durable half — exit criteria, hardening rank, commit strategy, self-review.

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
