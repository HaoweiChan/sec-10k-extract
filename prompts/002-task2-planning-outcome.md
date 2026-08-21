# 002 — Task 2 planning: outcome record

## Purpose

Outcome of running the planning prompt preserved in
`001-task2-planning-and-evaluation-design.md`. That file is the input; this
file records what the planning session decided, what the human constrained,
and what got corrected.

## Human decisions that constrained the AI

Before/at plan review, the human fixed:

1. Planning artifacts adapt to this repo's conventions — `docs/` for durable
   design docs, no plan files, no task tracker (ADR-001).
2. Frontend = single FastAPI service + vanilla JS inspector on Zeabur.
3. B-level fully deterministic; any LLM stage deferred to A-level and gated on
   residual-failure data.
4. Eight plan-review revision directives (see correction chain below).

## Outcome

Planning artifacts written: `docs/product/` (assignment-requirements,
task2-problem-definition, milestones), `docs/evals/` (evaluation-strategy,
failure-taxonomy), `docs/architecture/overview.md`, contract v2
(`specs/001` + ADR-002), ADR-001 (planning adaptations), ADR-003 (stdlib
normalization), `.claude/agents/extraction-auditor.md`,
`.claude/skills/case-authoring/SKILL.md`. Pipeline implementation deliberately
not started; T2+ awaits go-ahead.

## Assumption → Eval contradiction → Correction

(Contradictions here came from human plan review — no pipeline exists yet, so
no eval runs could contradict anything. Recorded in the same format.)

- Assumed: concrete confidence values and thresholds (0.95/0.85/0.60, cluster
  sizes, stub lengths) could be committed at planning time.
- Review said: no data exists yet — pre-data numbers are fiction that anchors
  implementation.
- Corrected: all numerics marked PROVISIONAL across docs; structure and
  ordering committed, values set empirically at T4/T5 and recorded in an ADR.

- Assumed: held-out hygiene means limiting how often held-out cases run
  ("run >2× = burned").
- Review said: runs don't leak — influence does.
- Corrected: burn-on-influence semantics in evaluation-strategy.md (a case is
  burned the moment its labeled outcome shapes a fix, threshold, or new case).

- Assumed: ~10 filings (5 deep-annotated) is enough diversity at B.
- Review said: diversity too thin for the annotation budget spent.
- Corrected: deep/shallow annotation tiers — shallow presence/status/era cases
  cost minutes each, lifting B to 12–15 filings without linear cost.

- Assumed: the LLM fallback design (verbatim-quote relocation) could be fixed
  in the architecture now.
- Review said: designing the fallback before residual-failure data exists is
  speculation.
- Corrected: architecture layer 10 is explicitly deferred to ADR-004; the
  quote-relocation idea survives only as a labeled candidate.

- Assumed: deployment risk could wait for the frontend task (T7).
- Review said: Zeabur→EDGAR reachability is a top-3 unknown; prove the
  end-to-end path early.
- Corrected: minimal stub-wrapping FastAPI deploy spike moved into T2.

- Assumed: "the eval set is the spec" was adequate framing for the planning
  docs.
- Review said: it conflates the norm with its enforcement.
- Corrected: ADR-001 fixes the precise framing — contract + invariants are
  normative, eval cases are their executable enforcement, the architecture
  overview is descriptive.

- Assumed: the freshly written contract v2 was internally consistent.
- Audit said: spec-drift found the Shape example violating v2's own
  warnings rule, and the expected-set rule citing INV-0 instead of INV-S4.
- Corrected: both fixed in `specs/001` before the batch was committed.

- Assumed: the committed invariants were enforced as written.
- Audit said (methodology audit, `docs/evals/audits/2026-08-15-methodology.md`):
  INV-S4 has no enforcing check anywhere, `verbatim` is a bounds check that
  cannot detect an INV-S2 violation, and `no_empty_success` is passed by one
  100-char item.
- Corrected: all became named T2 scope in milestones.md — the eval expansion
  now starts from audited gaps, not assumptions.

- Assumed: layer-8 validation limited to coverage ratio, length priors, and
  sequence checks was sufficient self-verification.
- Review said (Willy, post-planning): verify the way a human does — multiple
  independent naive signals (word counts, paragraph shape, beginning/ending
  words), so results are cross-checked several ways, not one.
- Corrected: layer 8 became a label-free validator battery (TOC manifest
  cross-check, gap analysis, boundary hygiene, part-region consistency,
  rank-order length sanity, numeric density, keyword fingerprints,
  dual-method boundary agreement) chosen for signal independence, running on
  every filing including held-out ones; priors measured at T5, seeded from
  stats recorded during T2 case authoring.
