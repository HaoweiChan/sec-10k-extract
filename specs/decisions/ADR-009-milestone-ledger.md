# ADR-009 — A milestone ledger, and why hard rule 3 had to bend

Date: 2026-08-16. Status: accepted. Amends CLAUDE.md hard rule 3.

## Context

Hard rule 3 said: *"No tasks.md, no plans — task lists live in the session, not
in files."* The rule was right about its actual target — `specs/` must not
decay into a plan dump, and a checked-in plan file rots the moment reality
diverges from it. It was wrong about one thing, and that error cost three
milestones before anyone noticed.

`docs/product/milestones.md` already carried a per-milestone decomposition,
including each milestone's exit conditions. T5's read, in full:

> → `doc_status` cases green; then cold-reviewer run → findings become
> adversarial cases → fix loop.

That is a gate. It lived as a clause in the middle of a prose paragraph, and
nothing in the repo could tell whether it had run. In the T5 session subagents
were unavailable, so the cold-reviewer half was silently skipped; the same
clause in T3 and T4 had been skipped before it. The omission surfaced at the
T6/T7 boundary, by accident, while planning something else.

Two properties made it invisible rather than merely undone:

1. **Judgment gates had no status field.** The eval suites report themselves —
   a red case is loud. A review that never happened produces no artifact, so
   its absence looks exactly like its success.
2. **Session capability is not constant.** A gate that assumes a subagent is
   available becomes a no-op in a session where it is not, and the next
   session inherits no record of the gap.

A related finding from the same review, recorded here because it has the same
shape: `.eval-baseline.json` has been `{}` since T1. `evals/run.py:130` only
compares when the suite key is present, so the pre-commit gate has been
passing vacuously — it could catch a crashing runner and nothing else. The
automated gate and the judgment gates were both weaker than the documentation
implied, for the same reason: **a gate nobody can observe is indistinguishable
from a gate that passed.** Arming the baseline is its own decision and gets
its own ADR; this one is about making gates observable.

## Decision

Exactly one milestone-level ledger file is allowed: **`tasks/TODO.md`**.

Hard rule 3 is amended to:

- `specs/` purity is unchanged — invariants, contracts, ADRs, nothing else.
- **Micro-tasks still live in the session.** The ledger holds milestones, not
  steps. If a row could be finished in one sitting it does not belong there.
- Every row carries a **Validation** column naming its own exit gate, and a
  **Status** column that must record **unrun gates explicitly** (`UNRUN`), not
  silently omit them.

`tasks/TODO.md` becomes the single home for milestone rows and their status.
The decomposition section moves out of `milestones.md`, which keeps what it is
actually good at: durable B-exit criteria, the ranked A-hardening list, commit
strategy, and the pre-implementation self-review.

## Alternatives rejected

- **Leave the gates in prose and try harder.** This is what already failed,
  and it failed in a way that hid itself for three milestones.
- **Enforce via a hook** — grep the commit message, or require a gate log
  file. Fake enforcement: a session that skips a review can also write the log
  line, and the hook cannot tell a real cold-reviewer run from an assertion
  that one happened. Judgment gates are enforced by being *visible to the next
  reader*, not by being blocked on. Hooks stay for what is machine-decidable.
- **A status table inside `milestones.md`.** One file mixing durable exit
  criteria (stable, decided once) with mutable status (churns every session),
  and the decomposition would then exist twice.

## Consequences

- `tasks/TODO.md` is the first thing a session reads to learn what is done,
  what is next, and which gates are outstanding. Three `UNRUN` markers ship
  with it — T3–T5 cold-reviewer, T5 spec-drift — and they block T7 rather than
  being quietly absorbed.
- The ledger admits three milestone rows the original decomposition never had:
  the gate-catch-up, CI + baseline arming + branch protection, and held-out
  authoring. Each had been an implicit sub-step of a larger milestone, which
  is precisely the shape that goes missing.
- Held-out moves from one run at T8 to authoring before T7 and two runs
  (T7 exit, T8). One generalization measurement taken on the last day leaves
  no room to react to it, and the burn/refresh cycle in
  `docs/evals/evaluation-strategy.md` needs at least one turn of the crank to
  be more than a described policy.
- This ADR is itself the record that a gate was skipped. That is deliberate —
  the alternative was to add the ledger quietly and let the history imply the
  reviews happened on time.
