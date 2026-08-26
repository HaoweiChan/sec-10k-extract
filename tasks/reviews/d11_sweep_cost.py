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
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from src.sec10k.escalate import EXTRACT_WINDOW, LOCALIZE_WINDOW, RUNGS  # noqa: E402
from src.sec10k.llm import price                                        # noqa: E402

# §d's stated model, in one place. `chars/4` is the token proxy (no tokenizer
# call is available offline); SYS is the system prompt; OUT is the answer, a
# small JSON map of offsets.
CHARS_PER_TOKEN, SYS_TOKENS, OUT_TOKENS = 4, 250, 150


def _census():
    spec = importlib.util.spec_from_file_location(
        "d11_trigger_scan", os.path.join(ROOT, "tasks", "reviews", "d11_trigger_scan.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.scan()


def rung_cost(chars, model, cap):
    """(usd, input_tokens) for one call of one rung over a document."""
    cin, cout = price(model)
    itok = min(chars, cap) / CHARS_PER_TOKEN + SYS_TOKENS
    return itok * cin / 1e6 + OUT_TOKENS * cout / 1e6, int(itok)


def ladder(chars):
    (r1, _), (r2, _) = (rung_cost(chars, RUNGS[0][1], LOCALIZE_WINDOW),
                        rung_cost(chars, RUNGS[1][1], EXTRACT_WINDOW))
    return r1 + r2


def main():
    rows = _census()
    by = {r["fixture"]: r for r in rows}
    spanned = sorted(r["chars"] for r in rows if r["coverage"] is not None)
    median = spanned[len(spanned) // 2]

    print("# ADR-036 §d, derived. Prices from tasks/reviews/2026-08-27-openrouter-models.json;")
    print(f"# char counts from the §c1 census; model = chars/{CHARS_PER_TOKEN} + "
          f"{SYS_TOKENS} in, {OUT_TOKENS} out.")
    for rung, model in RUNGS:
        cin, cout = price(model)
        cap = LOCALIZE_WINDOW if rung == "llm_localize" else EXTRACT_WINDOW
        print(f"#   {rung:13} {model:26} ${cin}/${cout} per MTok, input capped at {cap:,} chars")

    print("\n## §d1 — per document")
    print(f"{'document':34} {'chars':>9} {'rung 1':>9} {'rung 2':>9} {'ladder':>9}")
    named = [("xref-index-collapse", by["xref-index-collapse"]["chars"]),
             ("median span-bearing dev filing", median),
             ("bac-2006 (2nd largest)", by["bac-2006"]["chars"]),
             ("jpm-2024 (largest)", by["jpm-2024"]["chars"])]
    for label, c in named:
        a, ai = rung_cost(c, RUNGS[0][1], LOCALIZE_WINDOW)
        b, bi = rung_cost(c, RUNGS[1][1], EXTRACT_WINDOW)
        print(f"{label:34} {c:>9} {a:>9.4f} {b:>9.4f} {a + b:>9.4f}")
    print(f"  (rung 1 input tokens on the median filing: "
          f"{rung_cost(median, RUNGS[0][1], LOCALIZE_WINDOW)[1]:,}; "
          f"rung 2: {rung_cost(median, RUNGS[1][1], EXTRACT_WINDOW)[1]:,})")

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
    worst, _ = rung_cost(10 ** 9, RUNGS[1][1], EXTRACT_WINDOW)
    print(f"  one rung-2 call is capped at {EXTRACT_WINDOW:,} chars = ${worst:.4f}")
    print(f"  Budget refuses only once spent >= max_usd, so the effective ceiling")
    print(f"  is MAX_USD + ${worst:.4f} (default $5.00 -> ${5.00 + worst:.4f}).")


if __name__ == "__main__":
    main()
