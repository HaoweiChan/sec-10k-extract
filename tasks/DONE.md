# Milestone ledger — DONE (cold storage)

Append-only, one line per milestone, per [ADR-022](../specs/decisions/ADR-022-done-split.md)
(amends [ADR-009](../specs/decisions/ADR-009-milestone-ledger.md)). A row
lands here only once its Status carried no `UNRUN` gate — the full row text
(Contents, Reviewer evidence, complete Validation prose) stays in git history
at the pre-split commit, **cc6de9f6cbc5746ddf417dfa0649d9701afa9ce1**
(`git show cc6de9f:tasks/TODO.md`), except **T13**, added to `TODO.md` after
that split point by `c802e90` (`git show c802e90:tasks/TODO.md`) and archived
here in the same commit that reconciled the two branches. Live milestones
stay in [`tasks/TODO.md`](TODO.md).

- T1 — Planning package (2026-08-15) — validation: methodology audit ran, disposed in `docs/evals/audits/2026-08-15-methodology.md`
- T2 — Eval expansion r1 + deploy spike (2026-08-15) — validation: dual-pass audit ran, disposed in `docs/evals/audits/2026-08-15-t2-dualpass.md`
- T6 — Remaining goldens (2026-08-16) — validation: green with no new code, disposed in `evals/report/20260816-010527-all.json`
- G1 — Gate catch-up (2026-08-16) — validation: cold-reviewer + spec-drift audits ran, 4 findings watched red then fixed, disposed in `specs/decisions/ADR-010-g1-corrections.md` (residual validator-provability debt later closed in `specs/decisions/ADR-016-validator-provability.md`)
- G2 — CI + armed baseline + branch protection (2026-08-17) — validation: all three CI jobs proven to exit 1 on a deliberate break then green; protection observed via commit `cfcdc63`, disposed in `specs/decisions/ADR-012-arm-the-baseline.md`
- G3 — Held-out authoring (2026-08-16) — validation: isolation verified by an independent tag-strip scan, disposed in `evals/heldout/README.md` (burn rule)
- T7 — Frontend inspector (2026-08-16) — validation: all three input modes verified against the deployed instance, disposed at `https://whaleforce-sec10k.zeabur.app`
- H1 — Held-out run #1 (2026-08-16) — validation: report committed before triage, findings disposed in `specs/decisions/ADR-013-heading-shape-and-escalation.md`; `jnj-2016` burned to `evals/adversarial/jnj-bare-headings.json`
- T8 — B-freeze (2026-08-17) — validation: B-exit walk 11/11 green, disposed in `docs/evals/audits/2026-08-17-b-exit-walk.md`
- H2 — Held-out run #2 (2026-08-17) — validation: report committed before analysis, disposed in `evals/report/20260817-010004-fast.json`
- T9 — A1 — eval expansion r2 (2026-08-17) — validation: new goldens watched red first, code review disposed in PR #5, rulings in `specs/decisions/ADR-014-t9-tranche1-rulings.md` through `specs/decisions/ADR-017-pointer-window.md`
- T10 — A2 — confidence calibration (2026-08-18) — validation: measured table landed before any remap, both audits disposed, in `specs/decisions/ADR-018-confidence-calibration.md`
- T11 — A3 — silent-failure rate (2026-08-19) — validation: rate sampled and adjudicated by the extraction-auditor, OSS cross-check disposed in `specs/decisions/ADR-019-silent-failure-rate.md`
- S1 — Make the repo public (2026-08-17) — validation: `gh repo view` confirms PUBLIC, pre-flight secret scan disposed in `tasks/TODO.md` row history (see pre-split commit)
- T13 — A5 — perf/cost/scalability numbers (2026-08-20) — validation: `evals/bench.py` instrument watched red first (self-check + 30 mutations), disposed in `specs/decisions/ADR-021-benchmark-instrument.md`; four review rounds (PR #12) resolved 24/31 findings, R25–R31 carried as debt rows in `tasks/TODO.md`
- T12 — A4 — fallback stage: NOT JUSTIFIED, no fallback ships (2026-08-20) — validation: ruling in `specs/decisions/ADR-020-fallback-not-justified.md`; 4 review rounds on PR #11 (24 findings, 18 fixed, 0 rejected); round-4 residuals carried as debt rows in `tasks/TODO.md`; merged-as-is decision 2026-08-20
- T14 — A6 — taxonomy completeness + 10-K/A stretch (2026-08-20) — validation: 4 red cases / 11 assertions watched first, then fast 51/51 + invariant 13/13; rulings in `specs/decisions/ADR-023-era-label-corrections.md` (five era-label corrections, item set unchanged) and `specs/decisions/ADR-024-10ka-out-of-scope.md` (10-K/A ruled OUT); five review rounds on PR #17 (10 findings, 8 repaired, 0 rejected, R3/R4 carried as debt rows in `tasks/TODO.md`), two circuit breakers both cleared by human decision; full trace `tasks/reviews/pr17-r1..r5.json`
- S4 — Inspector UI round 2: centred layout, 11px type floor, source-HTML compare pane, README capability tables (2026-08-22) — validation: gate 22/22 invariant, 60/60 fast; three review rounds on PR #21 (13 findings, 10 repaired, 0 rejected, 5 carried as debt rows in `tasks/TODO.md`); V1 reopened at round 2 after anchoring proved wrong on `nike-2006`/`gs-2002`/`jpm-2024` and was rebuilt on body-agreement scoring, verified 0 wrong anchors over 641 items; full trace `tasks/reviews/pr21-r1..r3.json`
- S5 — Inspector UI round 3: wider split, aligned pane tops/bottoms, three equal-height scroll panes, legible item titles, parsed-pane metadata out of the way, capabilities panel promoted above trace/meta (2026-08-22) — validation: gate 32/32 invariant, 70/70 fast; 11 new `repo_hygiene` cases with paired red-first regression fixtures; browser-measured at 1920x1080 (panes 344/1143 x3, content [382,1142] vs [383,1142], titles rgb(224,230,235)/700, shell 1800px centred, S4 anchoring unregressed); closes debt row V4 from PR #21. Human reviewed the running build directly and amended the spec twice mid-flight; merged without a pr-loop review round at their instruction
- S6 — Document structure preservation: boilerplate header/footer chrome detected as opt-in, provenance-preserving spans, never as an edit to `normalized_text` (2026-08-22) — validation: ruling in `specs/decisions/ADR-026-boilerplate-chrome-exclusion.md`; four red-first cases re-falsified by mutation (`boilerplate-offsets-invariant`, `boilerplate-near-miss`, `boilerplate-chrome-detected`, `boilerplate-section-heads`), gate at merge invariant 33/33, fast 75/75 (baseline 1.000, not moved); detection fires on 16 of 28 fixtures, 0.607% of characters, zero false positives (ADR-026 §c6); recall and held-out evidence explicitly NOT claimed; two review rounds on PR #25 (6 MEDIUM repaired, 0 rejected, R7–R10 carried as debt rows in `tasks/TODO.md`), merged `d66711e`; full trace `tasks/reviews/pr25-r1..r2.json`
