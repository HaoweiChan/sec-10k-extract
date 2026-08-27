"""Layer 10 — the tiered slow path (ADR-036, D11; supersedes ADR-020).

The deterministic pipeline stays the default and the ONLY path on a clean
filing. When the D8 document-level signal fires the document escalates, one
rung at a time, and every rung is recorded in the envelope:

    rung 0  deterministic     always, $0
    rung 1  llm_localize      cheap model, bounded input: WHERE is the content
    rung 2  llm_extract       big model, the document up to EXTRACT_WINDOW:
                              same question, wider view, more $

Both paid rungs answer the same question and differ only in cost class and
input scope — rung 1 sees only the text no item claimed, rung 2 sees the whole
document up to a cap — which is what makes the ladder cost-proportionate rather than
decorative. Neither rung's answer is trusted: `verify()` re-derives every
offset against the deterministic output and the contract's own invariants, and
a proposal that does not verify is DISCARDED, with the rejection published.
A model can therefore move this pipeline's spans only to somewhere the
deterministic layers already agree is unattributed, contiguous and in order.

Three things this module deliberately does NOT do, each a ruling in ADR-036:

* it does not render anything (no vision rung — §e, two independent reasons);
* it does not send an unbounded prompt: BOTH rungs' inputs are capped, so one
  call's price is bounded even on an attacker-chosen upload (§h2, PR #58 R12);
* it does not touch a document the trigger left quiet, so default-flag output
  is byte-identical (§f, and `evals/snapshot.py` is the harness that proves it);
* it does not import `llm` at module scope. The import is inside `route()`, so
  `python3 -m evals.run` never loads a network module at all (§h).

Self-check: python3 -m src.sec10k.escalate
"""
from src.sec10k.segment import SIM_FLOOR, title_similarity
from src.sec10k.validate import SPAN_FLOOR

# WHICH D8 code escalates the DOCUMENT — the single most consequential constant
# in this file, and the one the whole cost argument rests on (ADR-036 §c).
# RE-DERIVED 2026-08-28 (PR #61 R14) over all 44 dev filing fixtures
# (`tasks/reviews/d11_trigger_scan.py --rates`, artifact
# `tasks/reviews/d11-trigger-scan.txt`):
#
#   low_item_coverage      2/44 = 0.0455 overall, 1/29 on real EDGAR filings
#   item_span_near_empty  13/44 = 0.2955 overall, 10/29 on real EDGAR filings
#
# The figures this comment carried until then — 1/43 and 0/28 — were measured
# 2026-08-26 and went stale the moment the live exam burned `intc-2025` to the
# dev side. The real-filing rate is no longer zero: it is one, and it is that
# filing. Nothing about the ruling below changes, and saying so is the point —
# `item_span_near_empty` is still an order of magnitude more frequent.
#
# Only the first is here. ADR-035 §c already ruled that a single pointer-bodied
# item is a fact about that ITEM and not a verdict on the document — it warns,
# sets `review_required`, and deliberately does not escalate `doc_status`. The
# router inherits that ruling rather than re-deciding it: escalating on
# `item_span_near_empty` would send 9 real dev filings to a paid tier and put
# the dev escalation rate at 32% against a ledger row that requires it near
# zero. Of those 9, exactly FOUR — cvx-2015, jpm-2024, ge-1994, spatz-2014 —
# are members of the A2 set ADR-034 §d1 enumerates and §e2 DECLINED (the
# fifth A2 filing, bac-2006, does not fire). The other five (xom-2021,
# ko-1997, nvda-2024, reac-2015, sandston-2021) were never in D9's scope and
# are an UNRULED population, not a declined one — PR #58 R5. And the reason
# for the decline is that items 7/8 are UNADJUDICATED: ADR-034 §e2 records
# the auditor's blind sample adjudicating cvx-2015 item **6** CORRECT and
# says in terms that "items 7 and 8 were never independently adjudicated".
TRIGGER_CODES = ("low_item_coverage",)

# The statuses that carry offsets (`specs/001-sec10k-contract.md`: "For status:
# missing / omitted: start/end are null — there is no span", and ADR-011 for
# why IBR is in). A tier may not resolve an item outside this set: doing so
# publishes a non-null span on an item the contract says has none, and — the
# part that bites — `meta.coverage` sums every item with a non-null start, so a
# resolved `missing` item inflates the exact number the D8 trigger thresholds
# on. Measured on the repro in `tasks/reviews/pr58-r1-red.txt`: 0.0030 -> 0.6142
# on one item. PR #58 R1. Pinned against `eval_adapter.SPAN_STATUSES` in _demo.
SPAN_STATUSES = ("extracted", "incorporated_by_reference")

# rung -> (model, the `method` an item carries when that rung produced its span)
# Model choice is the cost-discipline ladder, small before big. These are
# OpenRouter SLUGS (owner instruction 2026-08-27), both present verbatim in
# `tasks/reviews/2026-08-27-openrouter-models.json`, which is also where
# `llm.usd()` reads their per-token price — there is no hand-maintained price
# table. Per-document estimates: ADR-036 §d.
# The answer is a small JSON map of offsets — a few hundred tokens at most.
# `MAX_TOKENS` is what the ANSWER may use; a reasoning rung additionally gets
# `REASONING_TOKENS` of thinking, and the request's `max_tokens` is the sum, so
# the two never compete for one allowance.
#
# Sized by the intc-2025 exam, 2026-08-27, which billed $0.895360 for exactly
# this mistake: `max_tokens: 2048` and no reasoning budget sent to
# `anthropic/claude-opus-5` came back with `completion_tokens: 2048` and EMPTY
# content — the whole allowance spent thinking, nothing left to answer with.
# OpenRouter documents the requirement: for Anthropic models `max_tokens` must
# be strictly higher than the reasoning budget.
#
# On cost: of that $0.895360, only $0.0512 was output — the other $0.844160 was
# the input, paid whatever comes back. So a bigger answer allowance is nearly
# free (6,144 output tokens at $25/MTok caps one rung-2 call's output at
# $0.1536) while too small an allowance means paying the input for a guaranteed
# empty answer. The cost-discipline move here is UP, not down.
MAX_TOKENS = 2048        # the answer
REASONING_TOKENS = 4096  # the thinking, for a rung whose model does that

# (rung, model, reasoning_tokens). The third element is 0 for a rung that must
# NOT be sent a reasoning budget: `openai/gpt-5-mini` answered the exam
# correctly at 842 output tokens with none, and changing a rung that demonstrably
# works — on a provider behaviour this repo cannot test without spending — is the
# unverified change this PR has been burned by four times. Only the rung the
# exam proved broken gets the new parameter.
RUNGS = (
    ("llm_localize", "openai/gpt-5-mini", 0),
    ("llm_extract", "anthropic/claude-opus-5", REASONING_TOKENS),
)
LOCALIZE_WINDOW = 60_000  # chars of unattributed text rung 1 is allowed to see

# Chars of the document rung 2 is allowed to see. PR #58 R12: rung 2 used to
# send the WHOLE document, and on the deployed inspector the document is
# attacker-supplied and bounded only by `MAX_BYTES` (25 MB) — so a ~4M-char
# upload was a single ~$5.00 call, which `Budget` can take at spent=$4.99
# because it checks what has already been spent (§d3). One uncapped call
# therefore roughly doubled the configured deployment ceiling.
#
# 1,250,000 is not a round number pulled from nowhere: it is the largest
# committed dev filing (jpm-2024, 1,213,284 chars) rounded up. So no document
# in the corpus is truncated, and one call's price on ARBITRARY input is
# bounded. That bound is a DERIVED figure, not one restated here:
# `tasks/reviews/d11_sweep_cost.py` prints it under "§h2 — the effective
# deployment ceiling", and ADR-036 §h2 quotes the script. This comment used to
# carry its own hand-typed number, which was the fifth such figure in this
# branch and was wrong (PR #58 R22).
#
# KEPT, on a premise that has since changed (2026-08-27). The value was chosen
# when the bound it produced was believed to be $1.5675; the corrected
# per-model token proxy puts it at $2.4697, so the window bounds one call to
# roughly 1.6x what was published. The window is NOT re-tuned to chase the old
# dollar figure, because that figure was never the requirement — "bounded on
# arbitrary input" was, and it still is — and shrinking it to ~844,000 chars
# would truncate `jpm-2024`, giving up the property that justified the number
# in order to preserve a number that was wrong. The levers for a smaller
# ceiling are the documented ones: lower `SEC10K_ESCALATION_MAX_USD`, or build
# §d3's projected-cost pre-check. Both are the operator's call, not a silent
# re-tune here. ADR-036 §h2 states the corrected ceiling.
#
# Truncation is never silent: the tier record publishes `input_chars` and
# `truncated`, so a resolution over a clipped document says so.
# ponytail: a char cap, not a token estimate. Ceiling: a document whose real
# content sits past 1.25M chars cannot be resolved by rung 2 at all. Upgrade
# path once the first live run has real token counts — cap on projected COST
# instead, which also fixes §d3's overshoot in the same move.
EXTRACT_WINDOW = 1_250_000

SYSTEM = (
    "You locate SEC 10-K item content by character offset. You are given the "
    "normalized text of one filing (or a window of it) and a list of item "
    "codes whose extracted span the deterministic parser believes is a stub, "
    "a cross-reference index row, or an internal pointer rather than the "
    "item's own content.\n"
    "Answer with a JSON object and nothing else: a map from item code to "
    "[start, end] character offsets INTO THE TEXT AS GIVEN TO YOU, or null "
    "when you cannot locate that item's content. Do not quote, summarize, "
    "rewrite or extract any text. Offsets only.\n"
    "Every offset you return is re-checked against the parser's own output "
    "before it is used; a span that overlaps another item, sits inside text "
    "another item already claims, is shorter than "
    f"{SPAN_FLOOR} characters, or does not open with something recognisable "
    "as that item's heading will be discarded. Return null rather than a "
    "guess."
)


def trigger(warnings):
    """The router's sensor. Reads the warnings the layer-8 battery already
    produced — it re-derives nothing and owns no threshold of its own, so the
    trigger cannot drift away from the validator that defines it."""
    hits = [w for w in warnings if w.get("code") in TRIGGER_CODES]
    return {
        "fired": bool(hits),
        "codes": sorted({w["code"] for w in hits}),
        # the per-item hint the rungs are pointed at: every item D8 flagged as
        # a stub or a pointer. Non-escalating on its own (ADR-035 §c) — it says
        # WHICH items to ask about once something else has escalated.
        "items": sorted({w["item"] for w in warnings
                         if w.get("code") == "item_span_near_empty" and w.get("item")}),
        "message": "; ".join(w["message"] for w in hits),
    }


def _windows(text, items):
    """The regions of `text` no item span claims, longest first.

    This is what rung 1 is shown, and it is also the premise of the whole
    escalation: on a collapsed document the filing's real content is exactly
    the text the fast path failed to attribute.
    """
    spans = sorted((i["start"], i["end"]) for i in items
                   if i.get("start") is not None)
    free, at = [], 0
    for s, e in spans:
        if s > at:
            free.append((at, s))
        at = max(at, e)
    if at < len(text):
        free.append((at, len(text)))
    return sorted(free, key=lambda w: w[1] - w[0], reverse=True)


def verify(text, items, proposal, asked=None):
    """Deterministically re-check a rung's answer. Returns (accepted, why_not).

    `proposal` is {item_code: [start, end] | None}. `asked` is the set of codes
    the rung was actually given; when omitted, every item of the document is
    admissible (which is what `route` never does).

    **ALL-OR-NOTHING, and now actually so.** If ANY non-null proposed span
    fails ANY check, nothing is applied — `({}, why)`. Until PR #58 R2 the
    docstring and ADR-036 §b both claimed this while the loop `continue`d past
    failures and returned the survivors; the reviewer's mixed proposal is
    recorded in `tasks/reviews/pr58-r1-red.txt` and pinned by
    `evals/adversarial/escalation-verify-guards.json`. The claim was kept and
    the code was changed to match it, on the ADR's own stated rationale: the
    invariants at stake (INV-S1 ordering, INV-S2 offsets) are properties of the
    item list as a WHOLE, so partial application leaves ordering holding by
    accident. A null answer is NOT a failure — "I could not locate item 8" is
    the honest answer the prompt asks for, and it neither applies nor discards.
    # ponytail: all-or-nothing; go per-item only once a live run shows mixed
    # answers are common AND the ordering check is re-derived per item.

    The checks, in order, and why each one is here:

    1. the code is an item of this document, and — when `asked` is given — one
       the rung was actually given. A rung may not invent an item or resolve
       one nobody asked about;
    2. that item CARRIES A SPAN. `missing` and `omitted` items have null
       offsets by contract (`specs/001-sec10k-contract.md`), and resolving one
       both publishes a malformed envelope and inflates `meta.coverage`, the
       number the D8 trigger itself thresholds on. PR #58 R1 — this is the
       check whose absence would have been hit by the first live run, since
       one of the two exam filings is 21 `missing` + 2 `omitted`;
    3. bounds: 0 <= start < end <= len(text) (INV-S2);
    4. length >= SPAN_FLOOR — resolving a stub to another stub is not a
       resolution, and SPAN_FLOOR is the constant D8 already measured for
       exactly this question;
    5. the span opens with something that reads like this item's heading, by
       the SAME `title_similarity` / `SIM_FLOOR` cut the segmenter uses to
       accept a heading in the first place. This is the check that makes a
       hallucinated offset expensive to pass: a model must land on real
       heading text, not merely on a plausible-looking number;
    6. the whole item list, after substitution, is still disjoint and in
       ascending offset order (INV-S1, the same property `no_overlap_ordered`
       asserts).
    """
    by_code = {i["item"]: i for i in items}
    merged, why = {}, []
    for code, span in sorted(proposal.items()):
        if span is None:
            continue                       # "could not locate" is not a failure
        it = by_code.get(code)
        if it is None:
            why.append(f"item {code}: not an item of this document")
            continue
        if asked is not None and code not in asked:
            why.append(f"item {code}: not among the items this tier was asked "
                       f"about ({sorted(asked)})")
            continue
        if it["status"] not in SPAN_STATUSES:
            why.append(f"item {code}: status {it['status']!r} carries no span — "
                       f"only {list(SPAN_STATUSES)} may be resolved, and writing "
                       "offsets here would inflate meta.coverage")
            continue
        # D17: bool is EXCLUDED explicitly because it subclasses int —
        # isinstance(True, int) is True, so before 2026-08-28 a JSON
        # `[true, N]` passed this check and was accepted as [1, N] whenever
        # that span verified, publishing `"start": true` in the envelope.
        # Pinned red-first in evals/adversarial/escalation-verify-battery.json
        # and demonstrated in _demo below.
        if not (isinstance(span, (list, tuple)) and len(span) == 2
                and all(isinstance(v, int) and not isinstance(v, bool)
                        for v in span)):
            why.append(f"item {code}: {span!r} is not an [int, int] offset pair")
            continue
        s, e = span
        if not (0 <= s < e <= len(text)):
            why.append(f"item {code}: offsets [{s}, {e}) outside normalized_text "
                       f"(0, {len(text)})")
            continue
        if e - s < SPAN_FLOOR:
            why.append(f"item {code}: {e - s} chars < SPAN_FLOOR {SPAN_FLOOR} — "
                       "a stub resolved to another stub is not a resolution")
            continue
        head = text[s:s + 200].strip().splitlines()[0] if text[s:s + 200].strip() else ""
        sim = round(title_similarity(code, head), 3)
        if sim < SIM_FLOOR:
            why.append(f"item {code}: span opens {head[:60]!r}, title similarity "
                       f"{sim} < SIM_FLOOR {SIM_FLOOR}")
            continue
        merged[code] = {"start": s, "end": e, "title_similarity": sim}

    # ALL-OR-NOTHING (R2): one rejected sibling discards the whole proposal.
    if why:
        return {}, why
    if not merged:
        return {}, ["no rung returned a locatable span"]

    # 6. ordering and disjointness over the list AS IT WOULD BE
    after = [(merged[i["item"]]["start"], merged[i["item"]]["end"], i["item"])
             if i["item"] in merged
             else (i["start"], i["end"], i["item"])
             for i in items if i.get("start") is not None or i["item"] in merged]
    for (s1, e1, a), (s2, e2, b) in zip(after, after[1:]):
        if s2 < e1:
            why.append(f"items {a} and {b} would overlap or fall out of order "
                       f"([{s1}, {e1}) then [{s2}, {e2})) — INV-S1")
            return {}, why
    return merged, why


def apply(items, accepted, method):
    """Substitute verified spans into the item list, in place, honestly.

    The deterministic answer is never destroyed: it moves to
    `evidence.deterministic`, the same shape ADR-031 gave the footnote
    pointer. `heading_text` becomes None because the new span does not open
    with the heading the segmenter matched — the `verbatim` check reads that
    field and would (correctly) call the item a liar otherwise.
    """
    for it in items:
        got = accepted.get(it["item"])
        if not got:
            continue
        ev = dict(it.get("evidence") or {})
        it["evidence"] = {
            **ev,
            # the fast path's answer, kept whole. Nothing this module does
            # destroys the deterministic result — a reader can always see what
            # the $0 layers said and what the paid tier replaced it with.
            "deterministic": {"start": it.get("start"), "end": it.get("end"),
                              "method": it.get("method"),
                              "heading_text": it.get("heading_text"),
                              "title_similarity": ev.get("title_similarity")},
            # the PUBLISHED span's own numbers, not the old span's. `score()`
            # reads `title_similarity` to pick BASE_STRICT vs BASE_WEAK, so
            # leaving the index row's similarity here would let a resolved item
            # inherit a confidence earned by the heading it no longer opens with.
            "title_similarity": got["title_similarity"],
            "chars": got["end"] - got["start"],
        }
        it["start"], it["end"] = got["start"], got["end"]
        it["heading_text"] = None
        it["method"] = method


def route(text, items, warnings, budget=None):
    """Run the ladder. Returns (routing_record, extra_warnings).

    `items` is mutated in place when — and only when — a rung's answer
    verifies. On every other path (trigger quiet, no credential, budget spent,
    API unreachable, answer rejected) the item list is untouched and the
    routing record says which of those happened.
    """
    from src.sec10k.llm import Budget, EscalationUnavailable, call  # noqa: E402
    import json

    tr = trigger(warnings)
    record = {"trigger": tr, "tiers": [], "resolved": [],
              "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0}}
    if not tr["fired"]:
        # THE COMMON CASE, and the one the cost budget lives on: 42 of 44 dev
        # documents land here, spend nothing, and are byte-identical to a run
        # with the flag off.
        return record, []

    budget = budget if budget is not None else Budget()
    codes = tr["items"] or [i["item"] for i in items
                            if i.get("start") is not None]
    extra = []
    for rung, model, think in RUNGS:
        free = _windows(text, items)
        if rung == "llm_localize":
            shown, offset = _window_text(text, free, LOCALIZE_WINDOW)
        else:
            # PR #58 R12: bounded like rung 1, so one call's price is bounded
            # on arbitrary input. offset stays 0 — the window starts at the
            # document's start, so every offset the rung returns still means
            # what it says without translation.
            shown, offset = text[:EXTRACT_WINDOW], 0
        prompt = (f"Item codes to locate: {', '.join(codes)}\n"
                  f"Text length: {len(shown)} characters.\n"
                  f"Offsets are relative to the start of the text below.\n\n"
                  f"<filing>\n{shown}\n</filing>")
        entry = {"tier": rung, "model": model, "items": list(codes),
                 # WHAT THE RUNG WAS ACTUALLY SHOWN, as a range and not as a
                 # length (PR #58 R17). rung 1's window starts at the largest
                 # unattributed region, which is almost never offset 0 — on 18
                 # of 43 dev documents it is not — so `input_chars` alone made
                 # the inspector say "the first N chars" about a model that had
                 # been shown chars 178,087-238,087 (axp-2008). The envelope
                 # publishes the offset so the screen can state the truth.
                 "offset": offset, "input_chars": len(shown),
                 "truncated": len(shown) < len(text),
                 "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0}}
        try:
            got = call(model, SYSTEM, prompt, MAX_TOKENS + think, budget,
                       reasoning_tokens=think or None)
        except EscalationUnavailable as e:
            # LOUD AND STRUCTURED. Repo rule 4: a live dependency that cannot
            # be reached fails visibly; it never degrades into a fabricated
            # answer, and it never silently leaves the envelope looking clean.
            entry.update(outcome="unavailable", error=str(e))
            record["tiers"].append(entry)
            extra.append({"code": "escalation_unavailable", "item": None,
                          "message": f"tier {rung} could not run: {e}"})
            break
        entry["cost"] = {"llm_calls": 0 if got["cached"] else 1,
                         "tokens": sum(got["usage"].values()),
                         "usd": 0.0 if got["cached"] else got["usd"]}
        entry["cached"] = got["cached"]
        # THE intc-2025 EXAM'S OWN FAILURE, given a name. An empty completion
        # used to fall through to `json.loads` and be recorded as `unparseable`
        # with a bare JSONDecodeError — true, but it explained nothing, so the
        # routing record could not say why $0.895360 bought nothing. It is its
        # own outcome now, carrying the numbers that identify it, and the cost
        # is recorded BEFORE the branch: a call that was billed and produced
        # nothing must still be reported as billed.
        if not (got.get("text") or "").strip():
            entry.update(
                outcome="empty_completion",
                error=(f"the model returned empty content: "
                       f"finish_reason={got.get('finish_reason')!r}, "
                       f"output_tokens={got['usage'].get('output_tokens')} of "
                       f"max_tokens={got.get('max_tokens', MAX_TOKENS + think)}"
                       " — the output allowance was consumed before any content "
                       "was emitted (OpenRouter normalizes finish_reason to "
                       "'length' when the token limit is reached). Nothing came "
                       "back to parse, and the call was billed."))
            record["tiers"].append(entry)
            continue
        try:
            proposal = json.loads(got["text"].strip().removeprefix("```json")
                                  .removesuffix("```").strip())
            # D17: refuse to coerce JSON booleans BEFORE int() can launder
            # them — int(True) is 1, so `{"1": [true, N]}` used to reach
            # verify as the plausible integer pair [1+offset, N+offset] and
            # compete on the same terms as a real answer, and even the
            # verify-side bool guard never sees the bool on this path. Floats
            # and digit strings stay coerced by ruling (benign: int() moves a
            # float by under one character and parses the number the model
            # evidently meant); a bool is an answer to a different question.
            # Red-first: evals/adversarial/escalation-route-parse.json.
            if any(isinstance(x, bool) for v in proposal.values()
                   if isinstance(v, (list, tuple)) for x in v):
                raise TypeError("JSON true/false is not a character offset")
            proposal = {k: (None if v is None else [int(v[0]) + offset,
                                                   int(v[1]) + offset])
                        for k, v in proposal.items()}
        except (ValueError, TypeError, IndexError, KeyError, AttributeError) as e:
            entry.update(outcome="unparseable", error=f"{type(e).__name__}: {e}")
            record["tiers"].append(entry)
            continue
        accepted, why = verify(text, items, proposal, asked=set(codes))
        entry["rejections"] = why
        if accepted:
            apply(items, accepted, rung)
            entry.update(outcome="resolved", resolved=sorted(accepted))
            record["resolved"] = sorted(accepted)
            record["tiers"].append(entry)
            break
        entry["outcome"] = "rejected"
        record["tiers"].append(entry)
    else:
        # every rung ran and none resolved anything. The document keeps its
        # deterministic answer and says so.
        extra.append({"code": "escalation_unresolved", "item": None,
                      "message": f"the escalation ladder ran {len(RUNGS)} tiers and "
                                 f"resolved no item; the deterministic spans stand"})

    for t in record["tiers"]:
        for k in record["cost"]:
            record["cost"][k] = round(record["cost"][k] + t["cost"][k], 6)
    return record, extra


def _window_text(text, free, budget_chars):
    """The largest unattributed region, capped. Rung 1's whole input.

    Returns (shown, offset) so offsets the model reports can be mapped back
    into `normalized_text` by addition — the model is told its text starts at
    0, and never sees an absolute offset it could echo back unchecked.
    """
    if not free:
        return text[:budget_chars], 0
    s, e = free[0]
    return text[s:s + budget_chars], s


def _demo():
    """Everything in this module that can be proven without spending money —
    which is everything except the two `call()` sites."""
    from src.sec10k.segment import item_label

    # --- the trigger reads the battery and owns no threshold
    assert trigger([])["fired"] is False
    quiet = trigger([{"code": "item_span_near_empty", "item": "8", "message": "m"}])
    assert quiet["fired"] is False, "an item-level flag must NOT escalate (ADR-035 §c)"
    assert quiet["items"] == ["8"], quiet
    loud = trigger([{"code": "low_item_coverage", "item": None, "message": "3%"},
                    {"code": "item_span_near_empty", "item": "1", "message": "m"},
                    {"code": "item_span_near_empty", "item": "7", "message": "m"}])
    assert loud["fired"] and loud["codes"] == ["low_item_coverage"]
    assert loud["items"] == ["1", "7"], loud

    # --- PR #58 R12/R17/R19: both rungs' inputs are bounded, and the tier
    #     record states WHAT WAS SEEN as a range. Bound by driving `route`
    #     itself over an over-long document — the previous version of this
    #     block asserted `len(big[:EXTRACT_WINDOW]) == EXTRACT_WINDOW` on a
    #     local string, which is a tautology for any value of the constant and
    #     never reached `route`; reverting the slice left the whole gate green
    #     (PR #58 R19, transcript in tasks/reviews/pr58-r3-red.txt).
    #
    #     The transport is stubbed, NOT the result: the stub records the prompt
    #     it was handed and returns unparseable text, so no fabricated model
    #     answer ever enters the pipeline (repo rule 4) and both rungs run to
    #     completion leaving one tier record each.
    # PR #61 R5: a floor alone let 25,000,000 through green while one call's
    # price rose ~20x. The ceiling is re-pinned in repo_hygiene
    # (`EXTRACT_WINDOW_BOUNDS`) too, so the eval gate sees it and not only CI.
    assert 1_213_284 <= EXTRACT_WINDOW <= 1_500_000, (
        "below the floor the cap truncates a dev filing; above the ceiling it "
        "multiplies one rung-2 call's price and voids ADR-036 §h2's figure")
    import src.sec10k.llm as _llm
    seen = []

    def _stub(model, system, user, max_tokens, budget, timeout=120, **kw):
        seen.append(user)
        return {"text": "not json", "usage": {"input_tokens": 0, "output_tokens": 0},
                "usd": 0.0, "model": model, "cached": True}

    long_items = [{"item": "1", "start": 0, "end": 40, "status": "extracted",
                   "method": "heading_strict", "heading_text": "Business . . 12"}]
    long_text = "Business . . 12\n" + "y" * (EXTRACT_WINDOW + 25_000)
    real_call, _llm.call = _llm.call, _stub
    try:
        rec, _ = route(long_text, long_items,
                       [{"code": "low_item_coverage", "item": None, "message": "3%"}])
    finally:
        _llm.call = real_call
    by_tier = {t["tier"]: t for t in rec["tiers"]}
    assert set(by_tier) == {"llm_localize", "llm_extract"}, rec["tiers"]

    ex = by_tier["llm_extract"]
    assert ex["input_chars"] == EXTRACT_WINDOW, (
        "rung 2's input must be CAPPED — this is the assertion whose absence "
        "let the cap be reverted with the gate 100% green", ex["input_chars"])
    assert ex["truncated"] is True and ex["offset"] == 0, ex
    assert len(seen[-1]) < len(long_text), "the prompt must not carry the whole document"

    lo = by_tier["llm_localize"]
    assert lo["input_chars"] == LOCALIZE_WINDOW and lo["truncated"] is True
    # R17: rung 1's window does NOT start at 0, which is exactly why a bare
    # `input_chars` made the inspector print a false sentence.
    assert lo["offset"] == 40, ("rung 1's window starts at the largest "
                                "unattributed region, not at 0", lo["offset"])
    assert lo["offset"] + lo["input_chars"] <= len(long_text)

    # --- unattributed windows
    assert _windows("x" * 100, [{"start": 10, "end": 20}, {"start": 60, "end": 70}]) \
        == [(20, 60), (70, 100), (0, 10)]
    assert _windows("x" * 10, [{"start": 0, "end": 10}]) == []
    shown, off = _window_text("abcdefghij", [(4, 9)], 3)
    assert (shown, off) == ("efg", 4)

    # --- verify(): a real heading over a real body verifies; everything else
    #     is rejected, one reason per rule.
    # the A1 shape in miniature: two index rows at the top, both items' real
    # content unattributed further down, a tail after it.
    t1, t7 = item_label("1", None)[1], item_label("7", None)[1]
    body = f"Item 1. {t1}\n" + "real business prose. " * 200
    body7 = f"Item 7. {t7}\n" + "real MD&A prose. " * 200
    # the collapsed spans are cross-reference INDEX rows — the xref-index shape
    # D8 measured — so they must not themselves read as the item's heading
    rows = ["Business . . . . 12\n", "MD&A . . . . 40\n"]
    text = "".join(rows) + body + "\n" + body7 + "\n" + "tail " * 500
    at, at7 = text.index(body), text.index(body7)
    items = [{"item": "1", "start": 0, "end": len(rows[0]), "status": "extracted",
              "method": "heading_strict", "heading_text": rows[0].strip()},
             {"item": "7", "start": len(rows[0]), "end": len(rows[0]) + len(rows[1]),
              "status": "extracted", "method": "heading_strict",
              "heading_text": rows[1].strip()}]
    ok, why = verify(text, items, {"1": [at, at + len(body)],
                                   "7": [at7, at7 + len(body7)]})
    assert ok and set(ok) == {"1", "7"}, (ok, why)
    assert ok["1"]["title_similarity"] >= SIM_FLOOR, ok

    # bounds
    assert verify(text, items, {"1": [0, len(text) + 5]})[0] == {}
    assert verify(text, items, {"1": [50, 10]})[0] == {}
    # too short to be a resolution
    assert verify(text, items, {"1": [at, at + SPAN_FLOOR - 1]})[0] == {}
    # an item this document does not have
    bad, why = verify(text, items, {"99": [at, at + len(body)]})
    assert bad == {} and "not an item of this document" in why[0], why
    # not an offset pair at all
    assert verify(text, items, {"1": "page 42"})[0] == {}
    # --- D17: JSON booleans. `isinstance(True, int)` is True, so the shape
    #     check must exclude bool EXPLICITLY. The sharp construction: a
    #     document whose real body starts at offset 1, so [True, N] coerced
    #     to [1, N] is exactly the span that verifies. Before 2026-08-28 this
    #     returned {'1': {'start': True, ...}} — an ACCEPTED proposal whose
    #     start `apply` would have published as `"start": true`.
    bt = "x" + body
    bit = [{"item": "1", "start": 1, "end": 21, "status": "extracted",
            "method": "heading_strict", "heading_text": None}]
    assert verify(bt, bit, {"1": [1, 1 + len(body)]})[0], \
        "the honest int twin of the bool span must verify, or this probes nothing"
    bad, why = verify(bt, bit, {"1": [True, 1 + len(body)]})
    assert bad == {} and "not an [int, int] offset pair" in why[0], (bad, why)
    assert verify(bt, bit, {"1": [False, 1 + len(body)]})[0] == {}
    # a long, in-bounds, correctly-ordered span that does NOT open with the
    # item's heading — the hallucination shape, and the one that matters
    tailat = text.index("tail ")
    bad, why = verify(text, items, {"1": [tailat, len(text)]})
    assert bad == {} and "title similarity" in why[0], why
    # ordering: the same two resolutions over a document whose item 7 content
    # physically precedes its item 1 content. Both spans are long enough and
    # both open with the right heading — only INV-S1 rejects them.
    trans = "".join(rows) + body7 + "\n" + body
    bad, why = verify(trans, items,
                      {"7": [trans.index(body7), trans.index(body7) + len(body7)],
                       "1": [trans.index(body), trans.index(body) + len(body)]})
    assert bad == {} and any("INV-S1" in w for w in why), why
    # null answers are not failures, they are "could not locate"
    assert verify(text, items, {"1": None})[0] == {}

    # --- PR #58 R1: an item whose status carries no span may NOT be resolved.
    #     This is the check the first live run would have hit: one of the two
    #     exam filings is 21 `missing` + 2 `omitted`.
    from src.sec10k.eval_adapter import SPAN_STATUSES as ADAPTER_SPANNED
    assert set(SPAN_STATUSES) == set(ADAPTER_SPANNED), (
        "escalate and the contract checker must agree on which statuses carry "
        "offsets", SPAN_STATUSES, ADAPTER_SPANNED)
    for bad_status in ("missing", "omitted"):
        gone = [dict(items[0], status=bad_status, start=None, end=None,
                     method="status_keyword", heading_text=None), items[1]]
        bad, why = verify(text, gone, {"1": [at, at + len(body)]})
        assert bad == {}, (bad_status, bad)
        assert "carries no span" in why[0], why
        # ...and the reason it matters, asserted rather than asserted-about:
        # apply() would otherwise write a start onto an item meta.coverage sums
        after = [dict(i) for i in gone]
        apply(after, bad, "llm_localize")
        assert after[0]["start"] is None and after[0]["status"] == bad_status

    # --- PR #58 R7: a code the tier was never asked about is refused
    bad, why = verify(text, items, {"7": [at7, at7 + len(body7)]}, asked={"1"})
    assert bad == {} and "not among the items this tier was asked about" in why[0], why
    assert verify(text, items, {"7": [at7, at7 + len(body7)]}, asked={"1", "7"})[0]

    # --- PR #58 R2: ALL-OR-NOTHING, on a mixed proposal that does NOT trip
    #     INV-S1 as a side effect (which is how _demo missed this before).
    #     Item 7's real body verifies on its own; item 1's 40-char stub does not.
    solo, _ = verify(text, items, {"7": [at7, at7 + len(body7)]})
    assert set(solo) == {"7"}, solo
    mixed, why = verify(text, items, {"7": [at7, at7 + len(body7)], "1": [0, 40]})
    assert mixed == {}, ("one rejected sibling must discard the whole "
                         "proposal — ADR-036 §b", mixed)
    assert any("SPAN_FLOOR" in w for w in why), why
    # a null sibling is NOT a rejection and must not discard the survivor
    with_null, why = verify(text, items, {"7": [at7, at7 + len(body7)], "1": None})
    assert set(with_null) == {"7"}, (with_null, why)

    # --- apply(): the deterministic answer survives, the invariants hold
    it = [dict(items[0]), dict(items[1])]
    apply(it, {"1": ok["1"]}, "llm_localize")
    assert it[0]["method"] == "llm_localize"
    assert it[0]["heading_text"] is None, "a moved span must not claim the old heading"
    assert it[0]["evidence"]["deterministic"] == {
        "start": 0, "end": len(rows[0]), "method": "heading_strict",
        "heading_text": rows[0].strip(), "title_similarity": None}
    # the published similarity describes the PUBLISHED span, not the index row
    assert it[0]["evidence"]["title_similarity"] == ok["1"]["title_similarity"]
    assert text[it[0]["start"]:it[0]["end"]] == body      # INV-S2 still exact
    assert it[1] == items[1], "an unresolved item must not move"

    # --- route(): the quiet path is free, and it touches nothing
    before = [dict(i) for i in items]
    rec, extra = route(text, items, [{"code": "unattributed_content",
                                      "item": None, "message": "m"}])
    assert rec["trigger"]["fired"] is False and rec["tiers"] == [] and extra == []
    assert rec["cost"] == {"llm_calls": 0, "tokens": 0, "usd": 0.0}
    assert items == before, "a quiet trigger must not touch the item list"

    # --- route(): fired, with no way to pay for it. The ONLY honest outcome is
    #     a loud refusal that leaves the deterministic answer exactly as it was.
    from src.sec10k.llm import Budget
    rec, extra = route(text, items, [{"code": "low_item_coverage", "item": None,
                                      "message": "3%"}],
                       budget=Budget(max_calls=0))
    assert rec["trigger"]["fired"] is True
    assert [t["outcome"] for t in rec["tiers"]] == ["unavailable"], rec["tiers"]
    assert rec["cost"]["usd"] == 0.0 and rec["resolved"] == []
    assert [w["code"] for w in extra] == ["escalation_unavailable"]
    assert items == before, "a refused escalation must not touch the item list"
    print("[escalate self-check] ok")


if __name__ == "__main__":
    _demo()
