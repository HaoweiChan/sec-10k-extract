"""D17 deliverable (b): the intc-2025 measurement the D11 burn left unrun.

Runs the REAL post-§h4 ladder — `extract_items(..., escalate=True)` — against
`evals/fixtures/intc-2025/filing.htm`, the one real collapsed filing this repo
owns, with a HARD $5.00 cumulative cap enforced BEFORE each paid call.

The cap is not `Budget` alone: `Budget.take` checks what has ALREADY been
spent, so one call can overshoot its ceiling by its own price (ADR-036 §d3).
This script wraps `llm.call` with a pre-call gate that PROJECTS the call's
worst-case cost from the committed price record
(tasks/reviews/2026-08-27-openrouter-models.json, read via `llm.price`) and
the committed per-model chars/token minima
(tasks/reviews/2026-08-27-token-ratio.json: the MINIMUM observed ratio per
model, i.e. the conservative end — fewer chars per token means MORE tokens),
plus the full output allowance, and raises HardCapAbort BEFORE the socket if
cumulative_actual + projected would exceed $5.00. An explicit
Budget(max_calls=4, max_usd=5.00) rides along as belt-and-braces.

Honesty rules (repo rule 4, ADR-036):
* a cache hit (evals/cache/llm/ holds the exam's responses) is $0 and is
  REPORTED as cached — it is a replay, not a fresh call;
* no OPENROUTER_API_KEY, or a failed call, is a LOUD failure recorded as the
  measurement's outcome — never a fabricated answer;
* at most ONE bounded retry per rung, and only on a transient transport
  failure ("API unreachable"), never on a refusal or a missing credential.

Run:  python3 tasks/reviews/d17_intc_measurement.py
Artifact: tasks/reviews/d17-intc-measurement.txt (hand-written from this
script's output, pr58-exam-red.txt style).
"""
import copy
import json
import math
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import src.sec10k.llm as llm
from src.sec10k.llm import Budget, EscalationUnavailable

HARD_CAP_USD = 5.00
FIXTURE = "evals/fixtures/intc-2025/filing.htm"
RATIO_FILE = ROOT / "tasks" / "reviews" / "2026-08-27-token-ratio.json"
PROXY = json.loads(RATIO_FILE.read_text())["published_chars_per_token"]


class HardCapAbort(RuntimeError):
    """Deliberately NOT EscalationUnavailable: route() swallows that class
    into a tier record, and the cap must abort the whole run instead."""


calls = []            # one entry per llm.call the ladder makes
spent_actual = [0.0]  # cumulative dollars actually charged (usage-field usd)
retried = {}          # model -> retry count (bounded at 1)

real_call = llm.call


def gated_call(model, system, user, max_tokens, budget, timeout=120,
               reasoning_tokens=None):
    entry = {"model": model, "prompt_chars": len(system) + len(user),
             "max_tokens": max_tokens, "reasoning_tokens": reasoning_tokens}
    key = llm._cache_key(model, system, user, max_tokens)
    cached = (llm.CACHE_DIR / f"{key}.json").exists()
    entry["cache_hit_expected"] = cached
    if not cached:
        # THE PRE-CALL GATE (ADR-036 §d3's missing pre-check, built here):
        # worst-case projected cost from the committed records, checked
        # against the cumulative ACTUAL spend before any socket opens.
        in_est = math.ceil(entry["prompt_chars"] / PROXY[model])
        projected = llm.usd(model, in_est, max_tokens)
        entry["projected_usd"] = projected
        entry["projected_input_tokens"] = in_est
        if spent_actual[0] + projected > HARD_CAP_USD:
            entry["outcome"] = "HARD_CAP_ABORT"
            calls.append(entry)
            raise HardCapAbort(
                f"pre-call gate: ${spent_actual[0]:.6f} spent + "
                f"${projected:.6f} projected for {model} exceeds the "
                f"${HARD_CAP_USD:.2f} cap — refusing before the socket")
    for attempt in (1, 2):
        try:
            got = real_call(model, system, user, max_tokens, budget,
                            timeout=timeout, reasoning_tokens=reasoning_tokens)
            break
        except EscalationUnavailable as e:
            transient = str(e).startswith("API unreachable")
            if transient and attempt == 1 and not retried.get(model):
                retried[model] = 1
                entry["retried_once"] = f"transient: {e}"
                continue
            entry["outcome"] = "unavailable"
            entry["error"] = str(e)
            calls.append(entry)
            raise
    entry.update(cached=got["cached"], usage=got["usage"],
                 usd=0.0 if got["cached"] else got["usd"],
                 finish_reason=got.get("finish_reason"),
                 outcome="returned")
    if not got["cached"]:
        spent_actual[0] = round(spent_actual[0] + got["usd"], 6)
    calls.append(entry)
    return got


def main():
    tree = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()
    key_present = bool((os.environ.get("OPENROUTER_API_KEY") or "").strip())
    print(f"tree: {tree}")
    print(f"fixture: {FIXTURE}")
    print(f"OPENROUTER_API_KEY present: {key_present}")
    print(f"hard cap: ${HARD_CAP_USD:.2f} cumulative, checked BEFORE each "
          f"uncached call (proxy minima: {PROXY})")

    # gate self-check FIRST: a near-cap state plus an uncached prompt whose
    # projection exceeds the remainder must abort BEFORE any socket (and
    # before the budget or credential are even consulted). $0 by construction.
    spent_actual[0] = HARD_CAP_USD - 0.01
    try:
        gated_call("anthropic/claude-opus-5", "s", "x" * 100_000, 6144, Budget())
        raise AssertionError("the pre-call gate failed to trip")
    except HardCapAbort as e:
        print(f"gate self-check: tripped as designed ({e})")
    calls.clear()
    spent_actual[0] = 0.0

    from src.sec10k.extract import extract_items

    before = extract_items(FIXTURE)               # deterministic, $0
    b_items = copy.deepcopy(before["items"])

    llm.call = gated_call
    budget = Budget(max_calls=4, max_usd=HARD_CAP_USD)
    outcome = "ran"
    try:
        after = extract_items(FIXTURE, escalate=True, budget=budget)
    except HardCapAbort as e:
        outcome = f"ABORTED BY HARD CAP: {e}"
        after = None
    finally:
        llm.call = real_call

    print(f"\n=== per-call record (the gate's own log) ===")
    for c in calls:
        print(json.dumps(c, sort_keys=True))
    print(f"cumulative actual spend: ${spent_actual[0]:.6f}")
    print(f"budget: {budget.as_dict()}")

    if after is None:
        print(f"\nOUTCOME: {outcome}")
        return

    r = after["routing"]
    print(f"\n=== routing record ===")
    print(f"trigger: fired={r['trigger']['fired']} codes={r['trigger']['codes']} "
          f"items={r['trigger']['items']}")
    for t in r["tiers"]:
        print(f"tier {t['tier']}: model={t['model']} outcome={t['outcome']} "
              f"cached={t.get('cached')} cost={t['cost']} "
              f"offset={t.get('offset')} input_chars={t.get('input_chars')}")
        for rej in t.get("rejections", []):
            print(f"    rejection: {rej}")
        if t.get("error"):
            print(f"    error: {t['error']}")
    print(f"resolved: {r['resolved']}")
    print(f"cost: {r['cost']}")

    print(f"\n=== envelope delta (before vs after escalate=True) ===")
    print(f"meta.coverage: {before['meta']['coverage']} -> {after['meta']['coverage']}")
    moved = [(a["item"], (bb["start"], bb["end"], bb["method"]),
              (a["start"], a["end"], a["method"]))
             for bb, a in zip(b_items, after["items"])
             if (bb["start"], bb["end"], bb["method"])
             != (a["start"], a["end"], a["method"])]
    print(f"items whose span/method moved: {moved or 'NONE'}")
    ew = [w["code"] for w in after["warnings"]
          if w["code"].startswith("escalation")]
    print(f"escalation warnings: {ew}")


if __name__ == "__main__":
    main()
