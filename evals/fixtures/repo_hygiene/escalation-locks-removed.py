"""D11 regression fixture (ADR-036 §h2, PR #58 R9). Four ways the two money
locks on the PUBLIC deployment come off while everything else stays wired.

  1. `ESCALATION_ENABLED = True` — a constant, so a credential landing on the
     host arms paid work by itself. This is the reviewer's own mutation, and
     it left invariant 76/76, fast 139/139 and both module self-checks green
     before this check existed.
  2. `SERVER_MAX_USD` is a literal instead of an env read, so the operator
     cannot lower the ceiling on a running deployment.
  3. the process `Budget(...)` is built from literals rather than from the two
     constants — the reviewer's second mutation, which made the ceiling
     effectively infinite while `SERVER_MAX_CALLS` still sat in the file
     looking authoritative.
  4. nothing calls `server_budget()`, so the budget is constructed and never
     passed: every request would get `llm.Budget`'s per-DOCUMENT default and
     the deployment would have no aggregate bound at all.

`SERVER_MAX_CALLS` is left correctly wired on purpose, so a check that
blanket-failed would exceed the pinned count rather than reach it.

Caught by evals/adversarial/ui-escalation-locks-regression.json
(expect.min_failures/max_failures). Not imported — read as text.
"""
import os

ESCALATION_ENABLED = True
SERVER_MAX_CALLS = int(os.environ.get("SEC10K_ESCALATION_MAX_CALLS") or 20)
SERVER_MAX_USD = 5.00
_SERVER_BUDGET = None


def server_budget():
    global _SERVER_BUDGET
    if _SERVER_BUDGET is None:
        from src.sec10k.llm import Budget
        _SERVER_BUDGET = Budget(max_calls=10**9, max_usd=10.0**9)
    return _SERVER_BUDGET


def _run(path, source, raw=None, exclude_boilerplate=False, markdown=False,
         escalate=False):
    armed = escalate and ESCALATION_ENABLED
    return extract_items(path, exclude_boilerplate=exclude_boilerplate,
                         blocks=markdown, escalate=armed, budget=None)
