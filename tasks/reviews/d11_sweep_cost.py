#!/usr/bin/env python3
"""ADR-036 §d's dollar figures, DERIVED — the way §c1 is derived by
`d11_trigger_scan.py`, and for the same reason.

§d4's sweep total was published wrong twice running (PR #58 R4, then R8). The
root cause was not the cost model — the reviewer confirmed the model reproduces
every §d1 figure to the published digit — it was that the per-document
character counts were HAND-TYPED into the ADR, and five of the twelve were
wrong (ko-1997, nvda-2024, reac-2015, sandston-2021, spatz-2014; reac-2015 by
3.3x). A number a human retypes is a number that will be wrong again, so this
script reads the char counts from the same census the trigger figures come
from, reads the prices from the committed OpenRouter record, and prints the
tables that go into the ADR verbatim.

    python3 tasks/reviews/d11_sweep_cost.py

Deterministic, offline, $0. Held-out is NOT read: the census it reuses covers
`evals/fixtures` only.
"""
import importlib.util
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from src.sec10k.escalate import (EXTRACT_WINDOW, LOCALIZE_WINDOW,  # noqa: E402
                                 MAX_TOKENS, RUNGS)
from src.sec10k.llm import price                                        # noqa: E402

# §d's stated model, in one place. `chars/4` is the token proxy (no tokenizer
# call is available offline); SYS is the system prompt; OUT is the answer, a
# small JSON map of offsets.
SYS_TOKENS = 250
TOKEN_RATIO = os.path.join(ROOT, "tasks", "reviews", "2026-08-27-token-ratio.json")


def chars_per_token(model):
    """Chars per input token for `model`, DERIVED from billed responses.

    Not a constant, and not one value for every model. The proxy was `4` for
    both rungs, retyped and never measured, until the two held-out exam runs
    billed four real responses. Measured, it is wrong in BOTH directions and
    the split is per model, not one multiplier:

        anthropic/claude-opus-5   3.0740, 2.7395  -> `4` UNDERSTATED tokens 1.46x
        openai/gpt-5-mini         5.4195, 4.2663  -> `4` overstated them

    The understatement is the one that cost money: ADR-036 §h2 published a
    worst-case single call of $1.5675 while a real call on a LARGER input had
    already been billed $2.12163, and the per-document $1.00 `Budget` was
    overshot to $2.13.

    The published value is the MINIMUM observed per model, floored to 1 dp —
    minimum because fewer chars per token means MORE tokens for the same text,
    so it is the end that cannot understate a price. Samples, provenance and an
    honest note about their thinness (two per model, one corpus) live in
    `tasks/reviews/2026-08-27-token-ratio.json`; `token_proxy_bound` pins this
    function against that record. OpenRouter documents no tokenizer endpoint,
    so a proxy is unavoidable — it can only be measured and bounded.
    """
    rec = json.load(open(TOKEN_RATIO))
    seen = [s["chars_per_token"] for s in rec["samples"] if s["model"] == model]
    if seen:
        return math.floor(min(seen) * 10) / 10
    conservative = rec.get("conservative_unmeasured", {})
    if model in conservative:
        return conservative[model]
    raise KeyError(f"no measured or conservative chars-per-token bound for "
                   f"{model!r} in {os.path.basename(TOKEN_RATIO)}")
# OUTPUT is the rung's own `max_tokens` CEILING, not a guessed 150 (changed
# 2026-08-27, after the intc-2025 exam). Reasoning tokens are billed as output
# and a reasoning rung can spend its whole allowance thinking —
# `anthropic/claude-opus-5` returned exactly 2,048 output tokens of nothing —
# so 150 understated output cost by more than an order of magnitude. A ceiling
# cannot understate, which is the property a published cost figure needs, so
# every output figure below is an UPPER BOUND rather than an expectation.


def _census():
    spec = importlib.util.spec_from_file_location(
        "d11_trigger_scan", os.path.join(ROOT, "tasks", "reviews", "d11_trigger_scan.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.scan()


def rung_cost(chars, model, cap, out_tokens):
    """(usd, input_tokens) for one call of one rung over a document."""
    cin, cout = price(model)
    itok = min(chars, cap) / chars_per_token(model) + SYS_TOKENS
    return itok * cin / 1e6 + out_tokens * cout / 1e6, int(itok)


def _rung(i):
    """(model, input cap, output ceiling) for rung i, read from escalate."""
    _, model, think = RUNGS[i]
    return model, (LOCALIZE_WINDOW if i == 0 else EXTRACT_WINDOW), MAX_TOKENS + think


def ladder(chars):
    return sum(rung_cost(chars, *_rung(i))[0] for i in (0, 1))


def main():
    rows = _census()
    by = {r["fixture"]: r for r in rows}
    spanned = sorted(r["chars"] for r in rows if r["coverage"] is not None)
    median = spanned[len(spanned) // 2]

    print("# ADR-036 §d, derived. Prices from tasks/reviews/2026-08-27-openrouter-models.json;")
    print(f"# char counts from the §c1 census; model = chars/proxy + "
          f"{SYS_TOKENS} in, output at each rung's own ceiling (an UPPER BOUND).")
    for i, (rung, model, think) in enumerate(RUNGS):
        cin, cout = price(model)
        _, cap, out = _rung(i)
        print(f"#   {rung:13} {model:26} ${cin}/${cout} per MTok, input capped at "
              f"{cap:,} chars, output ceiling {out:,} tok"
              + (f" (incl. {think:,} reasoning)" if think else ""))

    print("\n## §d1 — per document")
    print(f"{'document':34} {'chars':>9} {'rung 1':>9} {'rung 2':>9} {'ladder':>9}")
    named = [("xref-index-collapse", by["xref-index-collapse"]["chars"]),
             ("median span-bearing dev filing", median),
             ("bac-2006 (2nd largest)", by["bac-2006"]["chars"]),
             ("jpm-2024 (largest)", by["jpm-2024"]["chars"])]
    for label, c in named:
        a, ai = rung_cost(c, *_rung(0))
        b, bi = rung_cost(c, *_rung(1))
        print(f"{label:34} {c:>9} {a:>9.4f} {b:>9.4f} {a + b:>9.4f}")
    print(f"  (rung 1 input tokens on the median filing: "
          f"{rung_cost(median, *_rung(0))[1]:,}; "
          f"rung 2: {rung_cost(median, *_rung(1))[1]:,})")

    # the chosen trigger: exactly the documents low_item_coverage fires on
    chosen = [r for r in rows if r["low_item_coverage"]]
    wide = [r for r in rows if r["low_item_coverage"] or r["near_empty_items"]]
    chosen_total = sum(ladder(r["chars"]) for r in chosen)
    wide_total = sum(ladder(r["chars"]) for r in wide)

    print(f"\n## §d2 — the CHOSEN trigger (low_item_coverage), whole dev sweep")
    for r in chosen:
        print(f"  {r['fixture']:26} {r['chars']:>9} chars  ${ladder(r['chars']):.4f}")
    print(f"  {len(chosen)} of {len(rows)} documents escalate   TOTAL ${chosen_total:.4f}")

    print(f"\n## §d4 — the WIDE trigger (+ item_span_near_empty), whole dev sweep")
    for r in sorted(wide, key=lambda r: -ladder(r["chars"])):
        print(f"  {r['fixture']:26} {r['chars']:>9} chars  ${ladder(r['chars']):.4f}")
    print(f"  {len(wide)} of {len(rows)} documents escalate   TOTAL ${wide_total:.4f}"
          f"   ratio {wide_total / chosen_total:.1f}x")
    assert "bac-2006" not in {r["fixture"] for r in wide}, \
        "bac-2006 is silent (§c3) and must not appear in the wide set"

    print(f"\n## §h2 — the effective deployment ceiling")
    worst, _ = rung_cost(10 ** 9, *_rung(1))
    print(f"  one rung-2 call is capped at {EXTRACT_WINDOW:,} chars = ${worst:.4f}")
    print(f"  Budget refuses only once spent >= max_usd, so the effective ceiling")
    print(f"  is MAX_USD + ${worst:.4f} (default $5.00 -> ${5.00 + worst:.4f}).")


if __name__ == "__main__":
    main()
