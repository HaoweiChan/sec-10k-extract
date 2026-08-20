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
