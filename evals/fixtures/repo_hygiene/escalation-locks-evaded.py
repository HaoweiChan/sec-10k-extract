"""D11 regression fixture (ADR-036 §h2, PR #58 R18; re-derived 2026-08-27 for
the owner's "make it default on, remove the button", and again in the PR #61
round-1 repair) — the EVASION, not the removal. `escalation-locks-removed.py`
deletes the brakes; this file keeps every name, every AST shape and every wire
the check asserts, and defeats them anyway with five one-token edits.

R18's original evasion was `!= "0"` where the ADR said `== "1"`. That became
the correct expression when the switch inverted, and then PR #61 R3 found that
`!= "0"` was itself the defect: `false`, `off`, `FALSE` and `"0 "` — what an
operator actually types into a Zeabur variable — all left it ARMED. The switch
now tests a named falsy SET, so the evasion moved again: keep the set, keep the
`not in`, and hollow it out.

  1. `DISARM_VALUES = ("0",)`. Still a module-level literal tuple of strings,
     still the name the comparison tests against, so every shape assertion is
     satisfied — and every spelling but the bare digit silently arms. A stop
     button whose accepted spellings nobody can read or document is worse than
     no stop button, because someone will believe it. One failure: the missing
     members.
  2. `or 10 ** 9` as the call-ceiling default. `_env_get` steps over the `or`
     operand to find the variable name, so the name check passes while an unset
     variable means a billion calls.
  3. `or 10.0 ** 9` as the dollar-ceiling default, the same way.
  4. `escalate=True` at the `extract_items` call site. With no request-level
     flag left to AND against, a literal here hard-wires paid work and orphans
     `ESCALATION_ENABLED` — which still sits above, still reads from the
     environment, still looks like the switch, and is now read by nothing.
  5. `server_budget()` drops its memo and returns a fresh `Budget` built from
     the same two constants (PR #61 R2). Every name survives: the ceilings are
     env-read, the `Budget` is built from the two NAMES, `_run` still calls
     `server_budget()`. Only the WORD "process-wide" stops being true — each
     request gets its own $5 / 20-call allowance, which is a ceiling on nothing
     when the caller is anonymous and unlimited. THREE failures, because the
     memo is three independent assertions and this defeats all of them: no
     `global`, a return that is not the module memo, and nothing assigning it.

Five mutations, seven failures. Everything else is left correctly wired on
purpose, so a check that blanket-failed would exceed the pinned count rather
than reach it.

Caught by evals/adversarial/ui-escalation-locks-evaded.json
(expect.min_failures/max_failures). Not imported — read as text.
"""
import os

DISARM_VALUES = ("0",)
ESCALATION_ENABLED = (os.environ.get("SEC10K_ESCALATION_ENABLED", "")
                      .strip().lower() not in DISARM_VALUES)
SERVER_MAX_CALLS = int(os.environ.get("SEC10K_ESCALATION_MAX_CALLS") or 10 ** 9)
SERVER_MAX_USD = float(os.environ.get("SEC10K_ESCALATION_MAX_USD") or 10.0 ** 9)
_SERVER_BUDGET = None


def server_budget():
    from src.sec10k.llm import Budget
    return Budget(max_calls=SERVER_MAX_CALLS, max_usd=SERVER_MAX_USD)


def _run(path, source, raw=None, exclude_boilerplate=False, markdown=False):
    return extract_items(path, exclude_boilerplate=exclude_boilerplate,
                         blocks=markdown, escalate=True,
                         budget=server_budget() if ESCALATION_ENABLED else None)
