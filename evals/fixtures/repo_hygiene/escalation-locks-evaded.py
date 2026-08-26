"""D11 regression fixture (ADR-036 §h2, PR #58 R18) — the EVASION, not the
removal. `escalation-locks-removed.py` deletes the locks; this file keeps every
name, every shape and every wire the round-2 check asserted, and defeats both
locks anyway with three one-token edits. All three passed that check.

  1. `!= "0"` instead of `== "1"`. Still an `ast.Compare` over the right env
     var, so the shape check was satisfied — and it evaluates to True with
     SEC10K_ESCALATION_ENABLED **unset**, which is exactly the state every host
     is in until someone sets it. That defeats Lock 1's stated property, "a
     credential alone never arms paid work", while reading as if it enforced it.
     Two failures: the operator, and the comparand the ADR names.
  2. `or 10 ** 9` as the call-ceiling default. `_env_get` steps over the `or`
     operand to find the variable name, so the name check passed while an unset
     variable meant a billion calls.
  3. `or 10.0 ** 9` as the dollar-ceiling default, the same way.

Everything else — the Budget built from the two constants, server_budget()
called from _run — is left correctly wired on purpose, so a check that
blanket-failed would exceed the pinned count rather than reach it.

Caught by evals/adversarial/ui-escalation-locks-evaded.json
(expect.min_failures/max_failures). Not imported — read as text.
"""
import os

ESCALATION_ENABLED = os.environ.get("SEC10K_ESCALATION_ENABLED") != "0"
SERVER_MAX_CALLS = int(os.environ.get("SEC10K_ESCALATION_MAX_CALLS") or 10 ** 9)
SERVER_MAX_USD = float(os.environ.get("SEC10K_ESCALATION_MAX_USD") or 10.0 ** 9)
_SERVER_BUDGET = None


def server_budget():
    global _SERVER_BUDGET
    if _SERVER_BUDGET is None:
        from src.sec10k.llm import Budget
        _SERVER_BUDGET = Budget(max_calls=SERVER_MAX_CALLS, max_usd=SERVER_MAX_USD)
    return _SERVER_BUDGET


def _run(path, source, raw=None, exclude_boilerplate=False, markdown=False,
         escalate=False):
    armed = escalate and ESCALATION_ENABLED
    return extract_items(path, exclude_boilerplate=exclude_boilerplate,
                         blocks=markdown, escalate=armed,
                         budget=server_budget() if armed else None)
