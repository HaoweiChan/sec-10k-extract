# ADR-001 — Adapting the Task 2 planning prompt to groundwork conventions

Date: 2026-08-15. Status: accepted.

## Context

The planning prompt (`prompts/001-task2-planning-and-evaluation-design.md`)
proposes a repo shape this repo deliberately does not have: a `docs/plans/`
tree, a `tasks/TODO.md` scheduler, ~9 per-feature spec files, several
additional subagents (Researcher, Evaluator) and skills (create-spec,
plan-feature, execute-task, run-eval, debug-eval-failure, review-change,
finish-task). The prompt itself instructs: challenge weak assumptions,
document disagreements, and let the assignment win over the prompt. ADR-000
already fixed the opposite conventions here.

## Decision

1. **Durable design docs go in `docs/`** (product, evals, architecture) —
   descriptive references, written once and maintained. `specs/` stays
   restricted to invariants, output contracts, and ADRs.
2. **Precise spec framing**: the durable *normative* spec is the contract +
   invariants in `specs/`. Eval cases are their **executable enforcement** —
   the mechanism that makes the norms bite, not themselves the norm. The
   architecture overview is **descriptive**. ("The eval set is the spec" in
   CLAUDE.md/README is shorthand for this arrangement.)
3. **No plan files, no task tracker.** Fine-grained scheduling and task status
   live in the session; what is durable — exit criteria and the milestone
   decomposition (which cases must go red/green, in what dependency order) —
   lives in `docs/product/milestones.md`. The prompt's 9 feature-spec files
   are rejected: feature decomposition is expressed as contract clauses +
   invariants + the cases that enforce them, staged in milestones.md.
4. **Subagents**: keep cold-reviewer / eval-adversary / spec-drift; add exactly
   one — `extraction-auditor` (outputs + eval methodology, the two things no
   existing agent examines). Researcher and Evaluator are rejected: WebSearch
   in the main session and the eval runner already do those jobs.
5. **Skills**: add exactly one — `case-authoring` (the golden-annotation SOP).
   The prompt's other candidates map to existing machinery: debug-eval-failure
   → `failure-triage`; run-eval → `eval-protocol`; audit-extraction → the
   auditor agent; create-spec/plan-feature/execute-task/finish-task → the
   CLAUDE.md per-feature loop; persona skills rejected on principle.

## Consequences

- Every §17 planning-prompt output exists, but some live in adapted locations;
  `docs/product/assignment-requirements.md` is the coverage map proving
  nothing was dropped.
- Divergence from the prompt is now recorded (this ADR), as the prompt itself
  requests.
- Cost: no per-feature spec files means feature history is reconstructed from
  eval cases + ADRs + commit history rather than dedicated documents.
