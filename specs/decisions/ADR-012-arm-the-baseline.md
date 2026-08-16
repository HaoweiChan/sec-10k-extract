# ADR-012 — Arming the eval baseline, and what it means that it was empty

Date: 2026-08-16. Status: accepted. Required by hard rule 1 (a baseline move is
a decision, recorded in an ADR — never a convenience to make a gate pass).

## Context

`.eval-baseline.json` has been `{}` since the harness was built at T1.
`evals/run.py:130` reads:

```python
if args.suite in baseline and score < baseline[args.suite]:
```

With an empty dict that condition is unreachable. Every commit from T1 through
G1 ran the pre-commit gate and every one of them passed it — but the gate could
only ever have caught a *crashing runner*, never a regression. Eight commits'
worth of "the eval gate is green" meant less than it read.

This is the same defect as the judgment gates in ADR-009 and the untested
`failed` branch in ADR-010, and by now the pattern is worth stating plainly:
**a check that cannot fail is indistinguishable from a check that passed, and
this repo has produced three of them by three different routes.** Recording the
empty baseline here rather than quietly filling it in is the point.

## Decision

`baseline["fast"] = 1.000`, recorded at 25/25 with the G1 corrections in.

Armed for `fast` only. The invariant suite is not baselined by design — the
runner demands 100% of it unconditionally (`evals/run.py:126-129`), so a
baseline entry would be redundant at best and a way to lower the bar at worst.

**Arming at 1.000 is deliberate and is the strict choice**: any future red case
blocks the commit until it is fixed or the baseline is moved with its own ADR.
The alternative — arming below the current score to leave headroom — would have
built the escape hatch into the gate on day one.

The consequence to accept: the red half of the repo's own red→green discipline
now needs `--no-verify` (hard rule 5, explained in the commit message) or a
branch whose CI failure is expected and visible. That is the correct trade. A
gate that permits red commits silently is the thing this ADR exists to end.

## Verification — the gate was proven to fire before it was trusted

Not asserted, run. Each CI job was broken deliberately, one at a time, and its
exit code observed:

| Job | Deliberate break | Exit |
|---|---|---|
| `fast-eval` | 9C boundary reverted to `date(2022, 1, 1)` | **1** — 0.920 < baseline 1.000, reported as REGRESSION |
| `unit-tests` | same break | **1** — `segment._demo`'s expected-set assertion |
| `invariant-eval` | `doc_status` ordering reverted (collapse tested after form identity) | **1** — `truncated-download`, 7/8, INVARIANT VIOLATION |

All three restored to green afterwards. Worth recording from the same
experiment: the 9C break does **not** trip `invariant-eval` (exit 0), because
`fy2021-item-9c` is tagged `fast` only. That is the intended split rather than
a gap — but it is the reason CI runs all three jobs and not just the invariant
one.

## Consequences

- The pre-commit hook and CI's `fast-eval` job now enforce something. They run
  the identical command, so a commit that passes locally cannot fail CI on the
  gate itself.
- Baseline moves from here are visible in `git log` as their own commits
  referencing an ADR, which is what makes "we never quietly lowered the bar"
  checkable by a reader rather than a claim.
- The score is 1.000 across 25 cases, and ADR-010's open list still applies: 4
  of 6 validators have no case proving they fire, and 4 adapter checks cannot
  go red. The baseline pins the number, not its meaning.
