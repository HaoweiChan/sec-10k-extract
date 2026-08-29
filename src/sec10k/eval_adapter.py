"""Eval adapter for sec10k — owns the check vocabulary and item registry.

Case shape:
    "input":  {"path": "evals/fixtures/<name>/<file>",
               "exclude_boilerplate": false,   # optional, ADR-026
               "tables": false,                # optional, ADR-029
               "blocks": false,                # optional, ADR-032 (implies tables)
               "images": false}                # optional, ADR-033
    "expect": {"checks": [{"type": ..., ...}, ...]}
"""
from pathlib import Path

from src.sec10k.markdown import blocks_in, to_markdown as md_to_markdown
from src.sec10k.tables import grid, to_markdown

ROOT = Path(__file__).resolve().parents[2]

# item -> part. Union of modern + legacy codes; era validity is a case concern
# (an adversarial case asserts item_absent for era-invalid codes).
CANONICAL = {
    "1": "I", "1A": "I", "1B": "I", "1C": "I", "2": "I", "3": "I", "4": "I",
    "5": "II", "6": "II", "7": "II", "7A": "II", "8": "II", "9": "II",
    "9A": "II", "9B": "II", "9C": "II",
    "10": "III", "11": "III", "12": "III", "13": "III",
    "14": "III",  # modern: Accountant Fees; pre-2003: Exhibits (Part IV)
    "15": "IV", "16": "IV",
}
STATUSES = {"extracted", "missing", "incorporated_by_reference", "omitted"}
# contract v2 normative enums read by `envelope_shape`. `heading_lenient` and
# `llm_fallback` are in the contract by decision (ADR-027 / ADR-020): the
# first is emitted for a weak-title heading match, the second never.
DOC_STATUSES = {"success", "success_with_warning", "ambiguous", "unsupported", "failed"}
# ADR-036 (D11) adds `llm_localize` and `llm_extract` — the two escalation
# rungs. An item carries one of them ONLY when that rung's proposed offsets
# survived `escalate.verify`, so the value is a claim about how the PUBLISHED
# span was produced, not about which tiers were attempted (that is `routing`).
# `llm_fallback` stays in the enum and stays unemitted: it was ADR-020's name
# for the unconditional fallback that never shipped, and ADR-036 §j keeps it
# rather than reusing it for a triggered tier that means something else.
METHODS = {"heading_strict", "heading_lenient", "status_keyword", "llm_fallback",
           "llm_localize", "llm_extract", "cross_reference_index", "agent_loop"}
ESCALATION_METHODS = {"llm_localize", "llm_extract", "agent_loop"}
# statuses that carry offsets, per ADR-011. `incorporated_by_reference` points
# at the pointer paragraph — real, inspectable text — so every span-level check
# must reach it. `missing`/`omitted` have no span by definition.
SPAN_STATUSES = {"extracted", "incorporated_by_reference"}
# check types that read an item's offsets, and so may be pointed at an offsets
# pair the item publishes under evidence[<key>] instead (ADR-031: `footnote`).
# Any other check type REFUSES an "evidence" key — a silently ignored key is a
# check that cannot fail (PR #42 R1).
EVIDENCE_CHECKS = {"text_contains", "text_not_contains", "min_chars", "max_chars"}
NO_EMPTY_SUCCESS_FLOOR = 1000  # provisional floor — narrows (not closes) the one-good-item hole
# fields that determinism actually governs — timings/cost/trace/meta legitimately vary
# run to run (wall-clock, run-local trace ids) on an honest, correct pipeline
DETERMINISM_FIELDS = ("normalized_text", "items", "doc_status", "warnings")


def item_text(result, entry):
    return result["normalized_text"][entry["start"]:entry["end"]]


def eval_check(result, chk, path=None):
    """Judge a single check against a result dict.

    Returns None on pass, else a failure reason string. Pure and synthetic-
    testable (no I/O) except `deterministic`, the only check allowed to call
    extract_items — it needs `path` to re-run the pipeline.
    """
    t = chk["type"]
    by_code = {i["item"]: i for i in result.get("items", [])}
    entry = by_code.get(chk.get("item"))
    extracted = [i for i in result.get("items", []) if i["status"] == "extracted"]
    # ADR-042 §c: a span-carrying status with NULL offsets is the collective
    # Part-level pointer, whose sentence names three or more items at once —
    # INV-S1 forbids them sharing it, so none of them carries it. Filtered
    # here rather than special-cased in five checks below.
    spanned = [i for i in result.get("items", []) if i["status"] in SPAN_STATUSES
               and i["start"] is not None]
    has_span = (entry is not None and entry["status"] in SPAN_STATUSES
                and entry["start"] is not None)
    if "evidence" in chk:
        # ADR-031 / PR #42 R1: resolve (item, evidence key) -> offsets ONCE, and
        # let the span-reading checks below run on that slice unchanged. The
        # key must exist; a check type that does not read spans refuses it.
        if t not in EVIDENCE_CHECKS:
            return f"check type {t!r} does not read 'evidence' — key refused"
        if entry is None:
            return f"item {chk['item']} not in output"
        ev = (entry.get("evidence") or {}).get(chk["evidence"])
        if not ev:
            return f"item {chk['item']} has no evidence span {chk['evidence']!r}"
        entry = {**entry, "start": ev["start"], "end": ev["end"], "status": "extracted"}
        has_span = True

    if t == "item_present":
        if entry is None or entry["status"] != chk.get("status", "extracted"):
            return (f"item {chk['item']} not {chk.get('status', 'extracted')}: "
                     f"{entry and entry['status']}")
    elif t == "item_absent":
        if chk.get("any_status"):
            if entry is not None:
                return f"item {chk['item']} present ({entry['status']}) but must not exist here"
        elif entry is not None and entry["status"] == "extracted":
            return f"item {chk['item']} was extracted but must not exist here"
    elif t == "text_contains":
        if entry is None:
            return f"item {chk['item']} missing text {chk['value']!r}"
        if not has_span:
            return "item has no span"
        if chk["value"] not in item_text(result, entry):
            return f"item {chk['item']} missing text {chk['value']!r}"
    elif t == "text_not_contains":
        # a null-offset status has no text at all -> vacuously can't contain it
        if has_span and chk["value"] in item_text(result, entry):
            return f"item {chk['item']} contains forbidden {chk['value']!r}"
    elif t == "min_chars":
        if entry is not None and not has_span:
            return "item has no span"
        n = (entry["end"] - entry["start"]) if entry else 0
        if n < chk["value"]:
            return f"item {chk['item']} has {n} chars < {chk['value']}"
    elif t == "max_chars":
        if entry is None:
            return "item not in output"
        if not has_span:
            return "item has no span"
        n = entry["end"] - entry["start"]
        if n > chk["value"]:
            return f"item {chk['item']} has {n} chars > {chk['value']}"
    elif t == "norm_contains":
        # normalized_text-level, item-independent: lets a normalization defect be
        # caught before segmentation exists to carry it into an item span
        if chk["value"] not in result["normalized_text"]:
            return f"normalized_text missing {chk['value']!r}"
    elif t == "norm_not_contains":
        n = result["normalized_text"].count(chk["value"])
        if n:
            return f"normalized_text contains {chk['value']!r} ({n}x)"
    elif t == "warning_present":
        # layer-8 validators are only worth having if a case can prove one
        # FIRES when it should — the counterpart to warning_absent. An "item"
        # key narrows the match to that item — without it, any item (or none)
        # satisfies the code, which is how a heading-line false-pass on 1A/3
        # hid behind a fingerprint firing on some other item.
        hits = [w for w in result.get("warnings", []) if w.get("code") == chk["code"]]
        if "item" in chk:
            hits = [w for w in hits if w.get("item") == chk["item"]]
        if not hits:
            got = sorted({w.get("code") for w in result.get("warnings", [])})
            return f"expected warning {chk['code']!r}, got {got}"
    elif t == "warning_absent":
        # warnings are not free: they downgrade doc_status to
        # success_with_warning and move confidence, so a validator that cries
        # wolf on a normal filing is a defect the doc_status checks can't see
        hits = [w for w in result.get("warnings", []) if w.get("code") == chk["code"]]
        if "item" in chk:
            hits = [w for w in hits if w.get("item") == chk["item"]]
        if hits:
            return f"unexpected warning {chk['code']!r}: {hits[0].get('message')}"
    elif t == "cross_reference":
        # ADR-042 §d. The trailing cross-reference index's page references,
        # resolved to character regions. Read like `text_contains` but against
        # what the item POINTS AT rather than what its span holds — which is
        # the whole distinction the ADR rests on, so a case must be able to
        # state it. `min_chars` guards against a resolution that technically
        # succeeded on an empty region.
        if entry is None:
            return f"item {chk['item']} not in output"
        regs = (entry.get("evidence") or {}).get("cross_reference")
        if not regs:
            return f"item {chk['item']} has no evidence.cross_reference"
        n = len(result["normalized_text"])
        for r in regs:
            if not (0 <= r["start"] < r["end"] <= n):
                return f"item {chk['item']} cross_reference region {r} out of bounds"
        total = sum(r["end"] - r["start"] for r in regs)
        if "min_chars" in chk and total < chk["min_chars"]:
            return f"item {chk['item']} cross_reference {total} chars < {chk['min_chars']}"
        body = "".join(result["normalized_text"][r["start"]:r["end"]] for r in regs)
        if "contains" in chk and chk["contains"] not in body:
            return f"item {chk['item']} cross_reference text lacks {chk['contains']!r}"
        if "not_contains" in chk and chk["not_contains"] in body:
            return f"item {chk['item']} cross_reference text contains {chk['not_contains']!r}"
    elif t == "item_field":
        # `title` and `part` ship on every item and the inspector renders them,
        # but until the pre-B audit nothing in the eval vocabulary could read
        # either — so an era-wrong label over correct text was structurally
        # invisible. Asserts any scalar item field by name.
        if entry is None:
            return f"item {chk['item']} not in output"
        got = entry.get(chk["field"])
        if got != chk["value"]:
            return f"item {chk['item']} {chk['field']} {got!r} != {chk['value']!r}"
    elif t == "meta_field":
        # PR #57 R1. `item_field`'s counterpart for `meta`. The contract makes
        # three `meta` keys normative on the non-refusal path (`taxonomy_era`,
        # `toc_manifest`, ADR-035's `coverage`) and `envelope_shape` could only
        # test them for PRESENCE — so a build publishing a hard-coded
        # `coverage: 1.0` on every document passed the whole gate. Asserts any
        # scalar `meta` field by name.
        got = result.get("meta", {}).get(chk["field"])
        if got != chk["value"]:
            return f"meta.{chk['field']} {got!r} != {chk['value']!r}"
    elif t == "confidence":
        # the contract promises confidence is honest and that the eval set
        # punishes overconfident wrongness. Until this check type existed no
        # case read the field at all, so every constant in ADR-008's
        # confidence table was free to change with the suite still green.
        # Without an "item" key the bound applies to EVERY item — that is how
        # a case states ADR-027's document-level rule (an `ambiguous` document
        # caps every item) without enumerating the item set.
        if "item" not in chk:
            targets = result["items"]
        elif entry is None:
            return f"item {chk['item']} not in output"
        else:
            targets = [entry]
        for it in targets:
            c = it.get("confidence")
            if c is None:
                return f"item {it['item']} has no confidence"
            if "value" in chk and c != chk["value"]:
                return f"item {it['item']} confidence {c} != {chk['value']}"
            if "max" in chk and c > chk["max"]:
                return f"item {it['item']} confidence {c} > {chk['max']}"
            if "min" in chk and c < chk["min"]:
                return f"item {it['item']} confidence {c} < {chk['min']}"
    elif t == "envelope_shape":
        # specs/001-sec10k-contract.md, Shape + Envelope fields: `meta`, `trace`,
        # `timings`, `cost`, `heading_text`, `evidence` "must be present" and
        # `method` is a normative enum — and until this check existed nothing in
        # the vocabulary read any of them (gates-2026-08-22 SD-1/SD-2/SD-6). The
        # internal shapes are implementation-owned, so only presence and the
        # normative enums are asserted here; no value is fabricated or compared.
        top = {"normalized_text", "doc_status", "warnings", "meta", "trace",
               "timings", "cost", "items"}
        # the optional keys: ADR-026's `boilerplate`, ADR-029's `tables`,
        # ADR-032's `blocks`, ADR-033's `images`, ADR-036's `routing`
        extra = set(result) - top - {"boilerplate", "tables", "blocks", "images",
                                     "routing"}
        if not top <= set(result) or extra:
            return f"envelope keys: missing {sorted(top - set(result))}, undeclared {sorted(extra)}"
        if "images" in result:
            # ADR-033 contract shape: [{offset, src, alt, width, height}],
            # offsets into normalized_text, document order. Same rule as
            # `tables`: a wrong SHAPE is red on any case that asks for
            # images, not only on one that labels an image.
            why = _images_shape(result)
            if why:
                return f"images not in contract shape: {why}"
        if "tables" in result:
            # ADR-029 contract shape: [{start, end, header, rows: [[[s, e] |
            # [s, e, colspan>1], ...], ...]}], offsets into normalized_text,
            # document order. Checked here so a wrong SHAPE is red on any
            # case that asks for tables, not only on one that labels a table.
            why = _tables_shape(result)
            if why:
                return f"tables not in contract shape: {why}"
        if "blocks" in result:
            # ADR-032 contract shape, same reasoning; `blocks` implies `tables`
            why = _blocks_shape(result)
            if why:
                return f"blocks not in contract shape: {why}"
        ds = result["doc_status"]
        if ds not in DOC_STATUSES:
            return f"doc_status {ds!r} not in contract enum"
        refusal = ds in ("unsupported", "failed")
        meta_keys = {"extractor_version", "input_sha256", "format_era", "document_selected"}
        if not refusal:
            # set only once the filing is accepted (SD-6): a refused document
            # has no era and no manifest to report
            # ADR-035 §d adds `coverage` on the same terms: a document the
            # pipeline refused has no items, so no coverage to report
            meta_keys |= {"taxonomy_era", "toc_manifest", "coverage"}
        if not meta_keys <= set(result["meta"]):
            return f"meta missing {sorted(meta_keys - set(result['meta']))}"
        if not refusal:
            # PR #57 R1, the root-cause half. `meta.coverage` is PUBLISHED by
            # extract.py and THRESHOLDED by validate.py from two separate calls
            # to the same function, so nothing made the published number agree
            # with the judged one — the band pins stayed green with the field
            # hard-coded. This restates the contract's own definition (ADR-035
            # §d: span-carrying chars over normalized chars, 4 dp) against the
            # items the SAME envelope publishes, so it binds every case that
            # runs `envelope_shape`, not just the two that pin a literal.
            cov = round(sum(i["end"] - i["start"] for i in result["items"]
                            if i.get("start") is not None)
                        / max(len(result["normalized_text"]), 1), 4)
            if result["meta"]["coverage"] != cov:
                return (f"meta.coverage {result['meta']['coverage']!r} != {cov!r} "
                        "recomputed from the items this envelope publishes")
        if not isinstance(result["trace"], list) or "total_ms" not in result["timings"] \
                or not {"llm_calls", "tokens", "usd"} <= set(result["cost"]):
            return "trace/timings/cost not in contract shape"
        if refusal and result["items"]:
            return f"{ds} envelope carries {len(result['items'])} items — refusal must not best-effort"
        if ds == "success" and result["warnings"]:
            return "doc_status success with non-empty warnings"
        for w in result["warnings"]:
            if not {"code", "item", "message"} <= set(w):
                return f"warning not in contract shape: {w}"
        item_keys = {"item", "part", "title", "heading_text", "start", "end",
                     "status", "confidence", "method", "evidence",
                     "review_required"}  # ADR-035 §e
        for i in result["items"]:
            if not item_keys <= set(i):
                return f"item {i.get('item')} missing {sorted(item_keys - set(i))}"
            if i["method"] not in METHODS:
                return f"item {i['item']} method {i['method']!r} not in contract enum"
            if i["status"] not in STATUSES:
                return f"item {i['item']} status {i['status']!r} not in contract enum"
            # PR #58 R1. `specs/001-sec10k-contract.md`: "For status: missing /
            # omitted: start/end are null — there is no span." Nothing in the
            # vocabulary asserted it, so an envelope publishing offsets on a
            # `missing` item was green — and because `meta.coverage` (checked
            # above) sums every item with a non-null start, that malformed
            # envelope also inflated the number the D8 trigger thresholds on.
            # Asserted here rather than only in `escalate.verify` so it binds
            # every producer, not just the one that broke it.
            spanned = i["status"] in SPAN_STATUSES
            if not spanned and (i["start"] is not None or i["end"] is not None):
                return (f"item {i['item']} is {i['status']!r} but carries "
                        f"offsets [{i['start']}, {i['end']}) — the contract says "
                        "missing/omitted spans are null")
            if spanned and i["start"] is None and i["end"] is None \
                    and "collective_reference" in (i.get("evidence") or {}):
                spanned = False   # ADR-042 §c, the one sanctioned null pair
            if spanned and (i["start"] is None or i["end"] is None):
                return (f"item {i['item']} is {i['status']!r} but has null "
                        "offsets — a span-carrying status must carry a span")
        # ADR-036 contract shape. LAST in this branch, and deliberately so
        # (CI failure on 9f43429): both this block and `_routing_shape` read
        # `i["method"]` and `result["cost"][...]`, and running them before the
        # loop above subscripted fields whose presence had not been validated
        # yet — so an envelope MISSING `method` raised KeyError instead of
        # being reported as the contract violation it is. `eval_check`'s whole
        # job is judging malformed envelopes; crashing on one is not judging
        # it. Order is the fix: validate shape, then cross-check honesty.
        if "routing" in result:
            why = _routing_shape(result)
            if why:
                return f"routing not in contract shape: {why}"
        elif any(i["method"] in ESCALATION_METHODS for i in result["items"]):
            # the honesty clause, and the one an implementation is most likely
            # to break: an item may not claim a tier produced it on an envelope
            # that carries no record of a tier having run.
            return ("an item claims an escalation method but the envelope has "
                    "no `routing` record")
    elif t == "known_items_only":
        bad = [i["item"] for i in result["items"] if i["item"] not in CANONICAL]
        bad += [i["item"] for i in result["items"] if i["status"] not in STATUSES]
        if bad:
            return f"non-canonical items or statuses: {bad}"
    elif t == "only_items":
        # era-validity: stronger than known_items_only, whitelist is case-declared
        bad = [i["item"] for i in result["items"] if i["item"] not in chk["items"]]
        if bad:
            return f"items outside allowed set {chk['items']}: {bad}"
    elif t == "expected_set_complete":
        missing = [c for c in chk["items"]
                   if c not in by_code or by_code[c]["status"] not in STATUSES]
        if missing:
            return f"expected items missing or unstatused: {missing}"
    elif t == "no_overlap_ordered":
        # INV-S1 covers every span-carrying status (ADR-011), not just
        # `extracted`: an IBR span excluded from this check is how a
        # misclassified item disowned 4,805 chars with nothing registering it
        spans = [(i["start"], i["end"], i["item"]) for i in spanned]
        for (s1, e1, a), (s2, e2, b) in zip(spans, spans[1:]):
            if s2 < e1:
                return f"items {a} and {b} overlap or are out of order"
    elif t == "verbatim":
        # INV-S2. Bounds first — offsets outside the text are the loud failure.
        n = len(result["normalized_text"])
        for i in spanned:
            if not (0 <= i["start"] < i["end"] <= n):
                return f"item {i['item']} offsets outside normalized_text"
        # ...then the quiet one. The G1 audit's complaint about this check was
        # that it "asserts bounds and never compares text", so an offset pair
        # that was in range but pointed at the wrong region satisfied INV-S2's
        # enforcement. There IS something to compare: the envelope publishes
        # `heading_text`, and a span must open with the heading the item claims.
        # Verified across all 31 dev fixtures before landing — zero mismatches,
        # so this pins current behaviour rather than describing an aspiration.
        for i in spanned:
            head = i.get("heading_text")
            if head and not result["normalized_text"][i["start"]:i["end"]] \
                    .lstrip().startswith(head):
                return (f"item {i['item']} span does not open with its own "
                        f"heading_text {head[:40]!r}")
    elif t == "doc_status":
        if "doc_status" not in result:
            return "doc_status missing (contract v2)"
        ds = result["doc_status"]
        if "value" in chk and ds != chk["value"]:
            return f"doc_status {ds!r} != {chk['value']!r}"
        if "in" in chk and ds not in chk["in"]:
            return f"doc_status {ds!r} not in {chk['in']}"
    elif t == "no_empty_success":
        if "doc_status" not in result:
            return "doc_status missing (contract v2)"
        if result["doc_status"] in ("success", "success_with_warning"):
            total = sum(i["end"] - i["start"] for i in extracted)
            if not extracted or total < NO_EMPTY_SUCCESS_FLOOR:
                return "pipeline returned success with (near-)empty output"
    elif t == "routing":
        # ADR-036. Reads the doc-level record by name: whether the trigger
        # fired, which tiers were attempted and with what outcome, what the run
        # cost, and which items a tier resolved. `envelope_shape` already
        # proves the record is internally consistent; this asserts the VALUES a
        # particular filing must produce, which is the part a refactor can
        # silently change.
        if "routing" not in result:
            return "no routing in result (was escalate set?)"
        r = result["routing"]
        if "fired" in chk and r["trigger"]["fired"] != chk["fired"]:
            return (f"routing.trigger.fired {r['trigger']['fired']} != {chk['fired']}"
                    f" (codes {r['trigger']['codes']})")
        if "trigger_codes" in chk and sorted(r["trigger"]["codes"]) != sorted(chk["trigger_codes"]):
            return f"trigger codes {r['trigger']['codes']} != {chk['trigger_codes']}"
        if "trigger_items" in chk and sorted(r["trigger"]["items"]) != sorted(chk["trigger_items"]):
            return f"trigger items {r['trigger']['items']} != {chk['trigger_items']}"
        if "tiers" in chk and [x["tier"] for x in r["tiers"]] != chk["tiers"]:
            return f"tiers attempted {[x['tier'] for x in r['tiers']]} != {chk['tiers']}"
        if "outcomes" in chk and [x["outcome"] for x in r["tiers"]] != chk["outcomes"]:
            return f"tier outcomes {[x['outcome'] for x in r['tiers']]} != {chk['outcomes']}"
        if "resolved" in chk and sorted(r["resolved"]) != sorted(chk["resolved"]):
            return f"routing.resolved {r['resolved']} != {chk['resolved']}"
        if "usd" in chk and r["cost"]["usd"] != chk["usd"]:
            return f"routing.cost.usd {r['cost']['usd']} != {chk['usd']}"
        if "llm_calls" in chk and r["cost"]["llm_calls"] != chk["llm_calls"]:
            return f"routing.cost.llm_calls {r['cost']['llm_calls']} != {chk['llm_calls']}"
        if "error_contains" in chk:
            blob = " ".join(x.get("error", "") for x in r["tiers"])
            if chk["error_contains"] not in blob:
                return f"no tier error contains {chk['error_contains']!r}; got {blob!r}"
    elif t == "verify_guards":
        # PR #58 R1/R2/R7. Until this existed NO eval case reached
        # `escalate.verify` at all — `escalation-trigger-quiet` returns at the
        # quiet branch and `escalation-no-credential` breaks at the refusal —
        # so every trust-boundary guard in the module could be deleted with
        # both suites 100% green (repro: tasks/reviews/pr58-r1-red.txt).
        #
        # It feeds constructed proposals to `verify` against THIS fixture's own
        # real items and real normalized_text. Nothing is mocked: the offsets
        # come from the envelope the pipeline just produced (`like_item` names
        # the item whose span to borrow), and the only thing the case supplies
        # is which item the proposal claims — which is exactly the thing a
        # model gets to choose, and therefore the thing that must be guarded.
        import json as _json

        from src.sec10k.escalate import verify
        # D17: verify is a pure checker — after EVERY sub-case, accepted or
        # rejected, the deterministic item list must be byte-untouched. Only
        # `apply` may move a span, and only on an accepted proposal.
        items_before = _json.dumps(result["items"], sort_keys=True)
        for sub in chk["cases"]:
            proposal = {}
            for code, spec in sub["proposal"].items():
                if isinstance(spec, dict) and "like_item" in spec:
                    src = by_code.get(spec["like_item"])
                    if src is None or src.get("start") is None:
                        return (f"{sub['name']}: like_item {spec['like_item']} "
                                "has no span in this fixture")
                    s, e = src["start"], src["end"]
                    # D17 modifiers, applied to the borrowed REAL span so a
                    # case can aim at mid-paragraph prose (`shift`), a
                    # sub-floor stub (`trunc`), an overlap with a sibling's
                    # real span (`grow`), or past the document (`overrun`)
                    # without hand-typing fixture offsets that would go stale.
                    s, e = s + spec.get("shift", 0), e + spec.get("shift", 0)
                    if "trunc" in spec:
                        e = s + spec["trunc"]
                    e += spec.get("grow", 0)
                    if "overrun" in spec:
                        e = len(result["normalized_text"]) + spec["overrun"]
                    proposal[code] = [s, e]
                else:
                    proposal[code] = spec
            asked = set(sub["asked"]) if "asked" in sub else None
            got, why = verify(result["normalized_text"], result["items"],
                              proposal, asked=asked)
            if _json.dumps(result["items"], sort_keys=True) != items_before:
                return (f"{sub['name']}: verify MUTATED the deterministic "
                        "item list — it must be a pure checker")
            if sub["expect"] == "reject":
                if got:
                    return (f"{sub['name']}: verify ACCEPTED {sorted(got)} — "
                            f"it must reject the whole proposal (why={why})")
                if not any(sub["why_contains"] in w for w in why):
                    return (f"{sub['name']}: rejected, but for the wrong reason "
                            f"— no rejection contains {sub['why_contains']!r}: {why}")
            else:
                if sorted(got) != sorted(sub["accepts"]):
                    return (f"{sub['name']}: verify accepted {sorted(got)} != "
                            f"{sorted(sub['accepts'])} (why={why})")
    elif t == "external_wrong_section_guard":
        # PR83 R1: real PGR attachment, wrong item and unproved end boundary.
        from src.sec10k.escalate import verify_external
        from src.sec10k.package import document

        raw = Path("evals/package-fixtures/pgr-2023/pgr-20231231_d2.htm").read_bytes()
        url = ("https://www.sec.gov/Archives/edgar/data/80661/"
               "000008066124000007/pgr-20231231_d2.htm")
        doc = document(raw, "EX-13", "6", "pgr-20231231_d2.htm", url=url)
        text = doc["text"]
        statements = "Consolidated Statements of Comprehensive Income"
        mda = "Management’s Discussion and Analysis of Financial Condition and Results of Operations"
        statement_at, mda_at = text.find(statements), text.find(mda)
        item = next((i for i in result["items"] if i["item"] == "7"), None)
        if item is None or min(statement_at, mda_at) < 0:
            return "PGR review guard fixture lacks Item 7 or a real attachment title"
        identity = doc["document"]
        def proposal(start, end, title):
            return {"action": "propose_external_regions", "item": "7",
                    "document": identity["id"],
                    "raw_sha256": identity["raw_sha256"],
                    "normalized_sha256": identity["normalized_sha256"],
                    "regions": [{"start": start, "end": end, "title": title}]}
        wrong, wrong_why = verify_external(result["normalized_text"], [item],
            proposal(statement_at, mda_at, statements), [doc], {"7"})
        arbitrary, arbitrary_why = verify_external(result["normalized_text"], [item],
            proposal(mda_at, mda_at + 1000, mda), [doc], {"7"})
        if wrong or not any("requested item" in x for x in wrong_why):
            return f"Item 7 accepted the real wrong section: {wrong}, {wrong_why}"
        if arbitrary or not any("end" in x for x in arbitrary_why):
            return f"Item 7 accepted an arbitrary unrelated end: {arbitrary}, {arbitrary_why}"
        return None
    elif t == "external_cp1252_raw_hash":
        # PR83 R2: exact bytes differ from UTF-8 after decoding 0xE9.
        import hashlib as _hashlib
        from src.sec10k.normalize import format_era, normalize
        from src.sec10k.package import embedded_documents

        body = b"\nFINANCIAL STATEMENTS caf\xe9\n"
        raw = (b"<DOCUMENT>\n<TYPE>EX-13\n<SEQUENCE>2\n"
               b"<FILENAME>annual.txt\n<TEXT>" + body
               + b"</TEXT>\n</DOCUMENT>")
        docs = embedded_documents(raw)
        if len(docs) != 1:
            return f"CP1252 SGML produced {len(docs)} attachments"
        identity = docs[0]["document"]
        exact = _hashlib.sha256(body).hexdigest()
        decoded = body.decode("cp1252")
        normalized = normalize(decoded, format_era(decoded))[0]
        normalized_hash = _hashlib.sha256(normalized.encode()).hexdigest()
        if identity["raw_sha256"] != exact:
            return "raw_sha256 is not the exact CP1252 source attachment bytes"
        if identity["normalized_sha256"] != normalized_hash:
            return "normalized hash changed while preserving exact raw bytes"
        return None
    elif t == "external_numbered_exhibit":
        # PR83 R3: real KO EX-13.1 and Item 8 cached/offline route.
        import copy
        import json as _json
        from src.sec10k.escalate import route
        from src.sec10k.package import embedded_documents
        import src.sec10k.llm as _llm

        documents = embedded_documents(Path(path).read_bytes())
        doc = next((d for d in documents if d["document"]["type"] == "EX-13.1"), None)
        if doc is None:
            return "KO full submission did not admit its EX-13.1 attachment"
        unrelated = (b"<DOCUMENT>\n<TYPE>EX-130\n<SEQUENCE>1\n"
                     b"<FILENAME>wrong.txt\n<TEXT>unrelated\n</TEXT>\n</DOCUMENT>"
                     b"<DOCUMENT>\n<TYPE>EX-13.A\n<SEQUENCE>2\n"
                     b"<FILENAME>wrong2.txt\n<TEXT>unrelated\n</TEXT>\n</DOCUMENT>")
        if embedded_documents(unrelated):
            return "unrelated exhibit types passed the bounded EX-13 allowlist"
        title = "CONSOLIDATED STATEMENTS OF INCOME"
        start = doc["text"].find(title)
        if start < 0:
            return "KO EX-13.1 lacks its financial-statement title"
        identity = doc["document"]
        actions = [
            {"action": "list_documents"},
            {"action": "search_document", "document": identity["id"],
             "query": title},
            {"action": "propose_external_regions", "item": chk["item"],
             "document": identity["id"], "raw_sha256": identity["raw_sha256"],
             "normalized_sha256": identity["normalized_sha256"],
             "regions": [{"start": start, "end": len(doc["text"]), "title": title}]},
        ]
        queued = copy.deepcopy(actions)
        def _stub(model, system, user, max_tokens, budget, **kw):
            return {"cached": True, "text": _json.dumps(queued.pop(0)),
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                    "usd": 0.0, "model": model}
        warnings = [{"code": "item_span_near_empty", "item": chk["item"],
                     "message": "PR83 R3 cached numbered-exhibit replay"}]
        items = copy.deepcopy(result["items"])
        before = [(i["item"], i.get("start"), i.get("end")) for i in items]
        real, _llm.call = _llm.call, _stub
        try:
            routing, extra = route(result["normalized_text"], items, warnings,
                                   documents=documents,
                                   acquisition={"status": "available", "source": "sgml",
                                                "calls": 0, "bytes": len(Path(path).read_bytes()),
                                                "latency_ms": 0.0})
        finally:
            _llm.call = real
        after = [(i["item"], i.get("start"), i.get("end")) for i in items]
        if extra or routing["external"] != [chk["item"]] or before != after:
            return f"KO numbered-exhibit route did not resolve externally: {routing}, {extra}"
        return None
    elif t == "external_agent_loop":
        # D24: cached actions over real same-accession attachments. Attachment
        # text is local fixture/SGML input; only the model transport is replayed.
        import copy
        import json as _json
        from src.sec10k.escalate import (_document_allowed, _page_marker, route,
                                         verify_external)
        from src.sec10k.package import document, embedded_documents
        import src.sec10k.llm as _llm

        source = result
        items = copy.deepcopy(source["items"])
        targets = chk["items"]
        warnings = [{"code": "item_span_near_empty", "item": code,
                     "message": "D24 cached external replay"} for code in targets]
        source_url = None
        if chk["scenario"] == "mrk_1995":
            documents = embedded_documents(Path(path).read_bytes())
            doc = next((d for d in documents if d["document"]["type"] == "EX-13"), None)
            if doc is None:
                return "MRK full submission has no EX-13 document"
            s7, e7 = _page_marker(doc["text"], 28), _page_marker(doc["text"], 38)
            s8 = e7
            proposals = [
                {"item": "7", "document": doc["document"]["id"],
                 "raw_sha256": doc["document"]["raw_sha256"],
                 "normalized_sha256": doc["document"]["normalized_sha256"],
                 "regions": [{"start": s7, "end": e7, "pages": [28, 37]}]},
                {"item": "8", "document": doc["document"]["id"],
                 "raw_sha256": doc["document"]["raw_sha256"],
                 "normalized_sha256": doc["document"]["normalized_sha256"],
                 "regions": [{"start": s8, "end": len(doc["text"]), "pages": [38, 50]}]},
            ]
            actions = [
                {"action": "search_document", "document": doc["document"]["id"],
                 "query": "FINANCIAL REVIEW"},
                {"action": "read_document_window", "document": doc["document"]["id"],
                 "start": s7, "end": s7 + 4000},
                {"action": "propose_external_regions", "proposals": proposals},
            ]
        elif chk["scenario"] == "pgr_2023":
            source_url = ("https://www.sec.gov/Archives/edgar/data/80661/"
                          "000008066124000007/pgr-20231231.htm")
            attachment = Path("evals/package-fixtures/pgr-2023/pgr-20231231_d2.htm").read_bytes()
            doc = document(attachment, "EX-13", "6", "pgr-20231231_d2.htm",
                           url=source_url.rsplit("/", 1)[0] + "/pgr-20231231_d2.htm")
            documents = [doc]
            md = doc["text"].find("Management’s Discussion and Analysis of Financial Condition and Results of Operations")
            if md < 0:
                return "PGR EX-13 has no MD&A title"
            proposals = [
                {"item": "7", "document": doc["document"]["id"],
                 "raw_sha256": doc["document"]["raw_sha256"],
                 "normalized_sha256": doc["document"]["normalized_sha256"],
                 "regions": [{"start": md, "end": len(doc["text"]),
                              "title": "Management’s Discussion and Analysis of Financial Condition and Results of Operations"}]},
                {"item": "8", "document": doc["document"]["id"],
                 "raw_sha256": doc["document"]["raw_sha256"],
                 "normalized_sha256": doc["document"]["normalized_sha256"],
                 "regions": [{"start": 0, "end": md,
                              "title": "Consolidated Statements of Comprehensive Income"}]},
            ]
            actions = [
                {"action": "list_documents"},
                {"action": "search_document", "document": doc["document"]["id"],
                 "query": "Management’s Discussion and Analysis"},
                {"action": "propose_external_regions", "proposals": proposals},
            ]
        else:
            return f"unknown external_agent_loop scenario {chk['scenario']!r}"

        calls, queued = [], copy.deepcopy(actions)
        def _stub(model, system, user, max_tokens, budget, **kw):
            calls.append(_json.loads(user))
            return {"cached": True, "text": _json.dumps(queued.pop(0)),
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                    "usd": 0.0, "model": model}
        before = {i["item"]: (i.get("start"), i.get("end"), i.get("method"),
                               i.get("heading_text")) for i in items}
        real, _llm.call = _llm.call, _stub
        try:
            routing, extra = route(source["normalized_text"], items, warnings,
                                   source_url=source_url, documents=documents,
                                   acquisition={"status": "available", "source": "fixture",
                                                "calls": 0, "bytes": 0, "latency_ms": 0.0})
        finally:
            _llm.call = real
        after = {i["item"]: (i.get("start"), i.get("end"), i.get("method"),
                              i.get("heading_text")) for i in items}
        if extra or routing["external"] != targets or routing["resolved"]:
            return f"4/4 external replay did not resolve honestly: {routing}, {extra}"
        envelope = {**source, "items": items, "routing": routing,
                    "cost": routing["cost"]}
        shaped = eval_check(envelope, {"type": "envelope_shape"})
        if shaped:
            return f"external replay failed public envelope shape: {shaped}"
        from src.sec10k.web.view import build_view
        view = build_view(envelope)
        for code in targets:
            shown = next(i for i in view["items"] if i["item"] == code)
            if (not shown["evidence"].get("external_regions")
                    or "offsets are not /normalized_text" not in shown["display_text"]):
                return f"inspector/API hid or conflated item {code} external evidence"
        if before != after or source["meta"]["coverage"] != result["meta"]["coverage"]:
            return "external evidence moved a primary pointer span or coverage"
        for code in targets:
            got = next(i for i in items if i["item"] == code)["evidence"].get("external_regions")
            if not got or any(r["end"] <= r["start"] or not r.get("document")
                              or not all(r["verifier"].get(k) for k in ("identity", "hashes", "bounds"))
                              for r in got):
                return f"item {code} lacks reproducible document-scoped evidence"
        if len(calls) != 3 or any(set(c) < {"target_items", "documents", "outline", "observation"}
                                  for c in calls):
            return "external replay lost persistent target/document/outline context"
        for turn in range(1, 3):
            previous = routing["tiers"][turn - 1]["observations"][0]
            if calls[turn]["observation"] != previous:
                return f"turn {turn + 1} lost exact prior external observation"

        # Trust-boundary mutation matrix: schema, identity, accession, hash,
        # bounds and proof each have a red-producing rejection.
        base_action = actions[-1]
        mutations = [
            ({"action": "propose_external_regions", "proposals": "bad"}, "no proposals"),
            ({**base_action, "proposals": [{**proposals[0], "document": "missing"}]}, "not in"),
            ({**base_action, "proposals": [{**proposals[0], "raw_sha256": "0" * 64}]}, "hash"),
            ({**base_action, "proposals": [{**proposals[0], "regions": [{"start": -1, "end": 2, "title": "invalid"}]}]}, "bounds"),
            ({**base_action, "proposals": [{**proposals[0], "regions": [{"start": 0, "end": 2, "title": "absent title"}]}]}, "title-or-page"),
        ]
        for bad, needle in mutations:
            got, why = verify_external(source["normalized_text"], items, bad,
                                       documents, set(targets))
            if got or not any(needle in reason for reason in why):
                return f"external verifier failed {needle} rejection: {got}, {why}"
        evil = copy.deepcopy(documents[0]); evil["document"]["url"] = "https://evil.example/x.htm"; evil["document"]["sgml_block"] = None
        wrong = copy.deepcopy(documents[0]); wrong["document"]["url"] = "https://www.sec.gov/Archives/edgar/data/1/000000000000000001/x.htm"; wrong["document"]["sgml_block"] = None
        if _document_allowed(evil, source_url) or _document_allowed(wrong, source_url):
            return "off-origin or wrong-accession attachment passed the allowlist"

        # Attachment absent: no model call, no clean claim. Three bad cached
        # proposals: exact three-turn exhaustion and honest abstention.
        no_doc, no_extra = route(source["normalized_text"], copy.deepcopy(source["items"]),
                                 warnings, source_url=source_url, documents=[])
        if no_doc["tiers"] or no_doc["external"] or no_doc["trigger"]["fired"]:
            return f"absent attachment did not abstain before a model call: {no_doc}"
        bad_actions = [{**base_action, "proposals": [{**proposals[0], "raw_sha256": "bad"}]}] * 3
        def _bad_stub(model, system, user, max_tokens, budget, **kw):
            return {"cached": True, "text": _json.dumps(bad_actions.pop(0)),
                    "usage": {"input_tokens": 0, "output_tokens": 0}, "usd": 0.0,
                    "model": model}
        real, _llm.call = _llm.call, _bad_stub
        exhausted_items = copy.deepcopy(source["items"])
        try:
            exhausted, exhausted_extra = route(source["normalized_text"], exhausted_items,
                                               warnings, source_url=source_url,
                                               documents=documents)
        finally:
            _llm.call = real
        if len(exhausted["tiers"]) != 3 or exhausted["external"] or not exhausted_extra:
            return "external rejection did not exhaust exactly three turns and abstain"
        return None
    elif t == "agent_loop":
        # D22's transport is recorded/cached: it exercises the real router,
        # normalised offsets, and deterministic verifier without a paid call.
        import copy
        import json as _json

        import src.sec10k.llm as _llm
        from src.sec10k.extract import extract_items
        from src.sec10k.escalate import route
        positive = chk["scenario"] == "replan_positive"
        source = (extract_items("evals/fixtures/xom-2021/filing.htm") if positive else result)
        target_code = "7" if positive else "2"
        target = next((i for i in source["items"] if i["item"] == target_code), None)
        if target is None or target["start"] is None:
            return "fixture has no primary Item 2 span for the cached agent replay"
        warnings = [{"code": "internal_pointer_unreached", "item": target_code,
                     "message": "cached D22 replay target"}]
        text, calls, items_in = source["normalized_text"], [], copy.deepcopy(source["items"])
        if chk["scenario"] == "replan_positive":
            destination = text.find("Item 7", target["end"])
            if destination < 0:
                return "XOM has no distinct Item 7 destination after its pointer span"
            actions = [
                {"action": "search", "query": "Item 7"},
                {"action": "read_window", "start": destination, "end": destination + 4000},
                {"action": "propose_alternative_regions", "item": "7", "regions": [{
                    "start": destination, "end": min(len(text), destination + 4000), "reference": "Item 7"}]},
            ]
        elif chk["scenario"] in ("exhaustion_negative", "empty_and_malformed"):
            items_in.append({"item": "16", "status": "missing", "start": None, "end": None,
                             "method": "status_keyword", "heading_text": None, "confidence": 0.0,
                             "part": "IV", "title": "Form 10-K Summary", "evidence": {}, "review_required": False})
            warnings.append({"code": "internal_pointer_unreached", "item": "16", "message": "mixed missing target"})
            actions = [{"action": "propose_primary_span", "item": "2", "start": 0, "end": 1}] * 3
        elif chk["scenario"] == "quiet_and_xref":
            def _quiet(*args, **kwargs):
                raise AssertionError("quiet/xref route made a model call")
            real, _llm.call = _llm.call, _quiet
            try:
                quiet, _ = route(result["normalized_text"], copy.deepcopy(result["items"]), [])
                xref, _ = route(result["normalized_text"], copy.deepcopy(result["items"]), [
                    {"code": "low_item_coverage", "item": "2", "message": "replay"},
                    {"code": "cross_reference_index", "item": "2", "message": "replay"}])
            finally:
                _llm.call = real
            if quiet["tiers"] or xref["tiers"] or quiet["cost"]["llm_calls"] or xref["cost"]["llm_calls"]:
                return "quiet or cross-reference-resolved route recorded model work"
            return None
        elif chk["scenario"] == "persistent_context":
            warnings = [{"code": "internal_pointer_unreached", "item": code,
                         "message": "cached D22 CVX target"}
                        for code in ("2", "6", "7A")]
            expected = {
                "target_items": [w["item"] for w in warnings],
                "outline": {
                    "items": [{"item": i["item"], "status": i["status"],
                               "start": i.get("start"), "end": i.get("end")}
                              for i in source["items"]],
                    "warnings": [{"code": w["code"], "item": w["item"]}
                                 for w in warnings],
                },
            }
            destination = text.find("Item 7", target["end"])
            if destination < 0:
                return "CVX has no bounded read destination for context replay"
            plans = [
                [{"action": "search", "query": "Item 7"},
                 {"action": "read_window", "start": destination, "end": destination + 40},
                 {"action": "propose_primary_span", "item": "1", "start": 0, "end": 1}],
                [{"action": "propose_primary_span", "item": "1", "start": 0, "end": 1},
                 {"action": "finish"}, {"action": "finish"}],
            ]
            for actions in plans:
                calls = []
                def _context_stub(model, system, user, max_tokens, budget, **kw):
                    calls.append(user)
                    return {"cached": True, "text": _json.dumps(actions.pop(0)),
                            "usage": {"input_tokens": 0, "output_tokens": 0}, "usd": 0.0,
                            "model": model}
                real, _llm.call = _llm.call, _context_stub
                try:
                    routing, _ = route(text, copy.deepcopy(source["items"]), warnings)
                finally:
                    _llm.call = real
                if len(calls) != 3:
                    return "persistent-context replay did not use all three turns"
                try:
                    prompts = [_json.loads(call) for call in calls]
                except _json.JSONDecodeError:
                    return "persistent-context replay did not send JSON context"
                for turn, prompt in enumerate(prompts):
                    if {k: prompt.get(k) for k in expected} != expected:
                        return f"turn {turn + 1} lost target_items or compact outline"
                    observation = {"initial": True}
                    if turn:
                        previous = routing["tiers"][turn - 1]["observations"][0]
                        observation = ({"verifier_rejections": previous["verifier"]}
                                       if "verifier" in previous else previous)
                    if prompt.get("observation") != observation:
                        return f"turn {turn + 1} lost exact preceding feedback"
                mutated = copy.deepcopy(prompts)
                mutated[2].pop("outline")
                if all({k: prompt.get(k) for k in expected} == expected for prompt in mutated):
                    return "persistent-context mutation dropped turn 3 outline unnoticed"
            return None
        else:
            return f"unknown agent_loop scenario {chk['scenario']!r}"

        if chk["scenario"] == "empty_and_malformed":
            actions = ["", "[]", "{"]
        def _stub(model, system, user, max_tokens, budget, **kw):
            calls.append(user)
            action = actions.pop(0)
            return {"cached": True, "text": action if isinstance(action, str) else _json.dumps(action),
                    "usage": {"input_tokens": 0, "output_tokens": 0}, "usd": 0.0,
                    "model": model}

        real, _llm.call = _llm.call, _stub
        try:
            routing, extra = route(text, items_in, warnings)
        finally:
            _llm.call = real
        tiers = routing["tiers"]
        envelope = {**source, "items": items_in, "routing": routing,
                    "cost": routing["cost"]}
        why_shape = eval_check(envelope, {"type": "envelope_shape"})
        if why_shape:
            return f"produced routing did not pass public envelope_shape: {why_shape}"
        bad = copy.deepcopy(envelope)
        bad["routing"]["tiers"][0].pop("actions", None)
        if eval_check(bad, {"type": "envelope_shape"}) is None:
            return "envelope_shape accepted an agent tier without actions"
        bad = copy.deepcopy(envelope)
        if len(bad["routing"]["tiers"]) > 2 and any("text" in x for x in bad["routing"]["tiers"][1].get("observations", [])):
            bad["routing"]["tiers"][2]["offset"] += 1
            if eval_check(bad, {"type": "envelope_shape"}) is None:
                return "envelope_shape accepted a mismatched read-window range"
        if chk["scenario"] == "replan_positive":
            if [x["outcome"] for x in tiers] != ["rejected", "rejected", "resolved"]:
                return f"expected rejected -> resolved re-plan, got {[x['outcome'] for x in tiers]}"
            if not tiers[0]["observations"] or not routing["alternative"]:
                return "rejection was not observed by the next cached turn or alternative was not recorded"
            if extra or "alternative_regions" not in items_in[[i["item"] for i in items_in].index(target_code)]["evidence"]:
                return f"verified cached repair did not apply honestly: extra={extra}"
            if _json.dumps(tiers[0]["observations"][0]) not in calls[1] or _json.dumps(tiers[1]["observations"][0]) not in calls[2]:
                return "exact search/read observation did not reach the next model prompt"
        else:
            if len(tiers) != 3 or any(x["outcome"] != "rejected" for x in tiers):
                if chk["scenario"] != "empty_and_malformed" or len(tiers) != 3 or any(x["outcome"] != "unparseable" for x in tiers):
                    return f"agent exhaustion did not use three bounded turns: {tiers}"
            if set(routing["trigger"]["target_items"]) != {"2", "16"}:
                return "mixed missing and bad-primary targets did not both reach route planning"
            if not extra or not items_in[[i["item"] for i in items_in].index("2")]["review_required"]:
                return "exhaustion did not leave the target review_required"
            if not items_in[[i["item"] for i in items_in].index("16")]["review_required"]:
                return "mixed missing target lost review_required"
            from src.sec10k.web.view import build_view
            view_item = next(i for i in build_view({"normalized_text": result["normalized_text"], "items": items_in})["items"]
                             if i["item"] == "2")
            if not view_item["review_required"]:
                return "view payload dropped item review_required"
        if routing["cost"] != {"llm_calls": 0, "tokens": 0, "usd": 0.0} or any(len(x) >= len(text) for x in calls):
            return "cached loop cost or bounded observation accounting is dishonest"
        if chk["scenario"] == "empty_and_malformed":
            expected = {"target_items": ["16", "2"], "outline": {
                "items": [{"item": i["item"], "status": i["status"],
                           "start": i.get("start"), "end": i.get("end")}
                          for i in items_in],
                "warnings": [{"code": w["code"], "item": w["item"]}
                             for w in warnings],
            }}
            prompts = [_json.loads(call) for call in calls]
            if len(prompts) != 3 or any({k: prompt.get(k) for k in expected} != expected
                                        for prompt in prompts):
                return "malformed-response continuation lost target_items or compact outline"
            for turn in (1, 2):
                if prompts[turn].get("observation") != {"rejection": tiers[turn - 1]["error"]}:
                    return "malformed-response continuation lost exact parse rejection"
    elif t == "route_payload":
        # PR #58 / the intc-2025 exam. Replays a RECORDED transport response
        # through `escalate.route` and asserts the router reports something
        # honest about it. The payload in the case is the one the live run
        # actually produced — 2,048 output tokens and empty content — so this
        # is the exam's evidence kept as a $0 regression test rather than as a
        # paragraph. Same shape as `verify_guards`: the case supplies only what
        # the TRANSPORT returned, and everything else is the real pipeline over
        # this fixture's real text and real items.
        import copy

        import src.sec10k.llm as _llm
        from src.sec10k.escalate import route
        sent = []

        def _stub(model, system, user, max_tokens, budget, **kw):
            sent.append({"model": model, "max_tokens": max_tokens,
                         "reasoning_tokens": kw.get("reasoning_tokens")})
            # `cached: False` by default — the exam's calls were live and
            # BILLED, and the point of replaying the payload is that the cost
            # of a call that returned nothing is still reported.
            return {"cached": False, **chk["response"], "model": model}

        real, _llm.call = _llm.call, _stub
        items_in = copy.deepcopy(result["items"])
        try:
            rec, extra = route(result["normalized_text"], items_in,
                               result["warnings"])
        except Exception as e:                     # the pre-fix behaviour
            return (f"route CRASHED on the recorded payload "
                    f"({type(e).__name__}: {e}) — a transport that returns "
                    "empty content must be reported, not raised through")
        finally:
            _llm.call = real
        got = [x["outcome"] for x in rec["tiers"]]
        if "outcomes" in chk and got != chk["outcomes"]:
            return f"tier outcomes {got} != {chk['outcomes']}"
        # D17: a transport answer the router did not accept must leave the
        # deterministic item list byte-untouched — all-or-nothing, and
        # nothing applied means NOTHING moved.
        if chk.get("untouched") and items_in != result["items"]:
            return ("route mutated the item list on an answer it did not "
                    "accept — the deterministic output must stand untouched")
        if "error_contains" in chk:
            blob = " ".join(x.get("error", "") for x in rec["tiers"])
            for want in chk["error_contains"]:
                if want not in blob:
                    return (f"no tier error mentions {want!r} — the record must "
                            f"say WHAT happened; got {blob!r}")
        if "usd" in chk and round(rec["cost"]["usd"], 6) != chk["usd"]:
            return (f"routing.cost.usd {rec['cost']['usd']} != {chk['usd']} — a "
                    "call that was billed and produced nothing must still be "
                    "reported as billed")
        if "resolved" in chk and sorted(rec["resolved"]) != sorted(chk["resolved"]):
            return f"routing.resolved {rec['resolved']} != {chk['resolved']}"
        # per-MODEL, because the rungs differ on measured evidence: the exam
        # showed `openai/gpt-5-mini` answering correctly inside 2,048 tokens
        # with no reasoning budget, and `anthropic/claude-opus-5` spending all
        # 2,048 on thinking and emitting nothing. Asserting one floor across
        # both would demand a change to the rung that works.
        by_model = {x["model"]: x for x in sent}
        for model, want in (chk.get("min_max_tokens") or {}).items():
            got_call = by_model.get(model)
            if got_call is None:
                return f"no call was made to {model} — nothing to bound"
            if got_call["max_tokens"] < want:
                return (f"{model} was called with max_tokens "
                        f"{got_call['max_tokens']} < {want} — the exam paid "
                        "$0.895360 for 2,048 output tokens of nothing because "
                        "the allowance was consumed before any content emerged")
        for model, want in (chk.get("reasoning_tokens") or {}).items():
            got_call = by_model.get(model)
            if got_call is None or got_call["reasoning_tokens"] != want:
                return (f"{model} was sent reasoning_tokens="
                        f"{got_call and got_call['reasoning_tokens']!r}, want "
                        f"{want!r} — OpenRouter documents that for Anthropic "
                        "models max_tokens must be strictly higher than the "
                        "reasoning budget, so the split must be explicit")
    elif t == "escalation_invariant":
        # ADR-036 §f, asserted as the equality the ADR claims it is rather than
        # left to `evals/snapshot.py` alone: run the same file with the flag on
        # and off and compare the fields determinism governs, plus the envelope
        # key list minus the one key the flag is allowed to add. Self-contained,
        # like `offsets_invariant_under_exclusion` — it does not care which way
        # the case itself ran. Only meaningful on a filing whose trigger stays
        # quiet, which is why the case that runs it also asserts `fired: false`.
        from src.sec10k.extract import extract_items
        on = extract_items(path, escalate=True)
        off = extract_items(path)
        for k in DETERMINISM_FIELDS:
            if on.get(k) != off.get(k):
                return f"escalate=True changed {k} on a document that did not escalate"
        if sorted(set(on) - {"routing"}) != sorted(off):
            return (f"escalate=True changed the envelope key list: "
                    f"{sorted(set(on) - {'routing'})} vs {sorted(off)}")
        if on["cost"] != {"llm_calls": 0, "tokens": 0, "usd": 0.0}:
            return f"a quiet trigger reported a cost: {on['cost']}"
        if "routing" not in on or "routing" in off:
            return "the routing key must appear with the flag and only with it"
    elif t == "d21_verify":
        # D21's direct, synthetic verifier battery: no model transport and no
        # live call can make these contract decisions pass by accident.
        from src.sec10k.escalate import (classify, verify, verify_alternatives,
                                         vision_verify, VISION_CAP,
                                         VISION_TEXT_CAP, _vision_prompt,
                                         _vision_verdict)
        from src.sec10k.segment import item_label
        title = item_label("1", None)[1]
        body = f"Item 1. {title}\n" + "evidence " * 400
        alt_body = "Item 7. Alternative evidence\n" + "evidence " * 400
        text = "stub\n" + body + alt_body + "tail " * 400
        start = text.index(body)
        alt_start = text.index(alt_body)
        items = [{"item": "1", "start": 0, "end": 5, "status": "extracted",
                  "method": "heading_strict", "heading_text": "stub"},
                 {"item": "7", "start": None, "end": None, "status": "missing",
                  "method": "status_keyword", "heading_text": None}]
        scenario = chk["scenario"]
        if scenario == "contiguous":
            got, why = verify(text, items, {"1": [start, start + len(body)]})
            if set(got) != {"1"} or why:
                return f"contiguous repair rejected: {why}"
        elif scenario == "missing_alternative":
            got, why = verify_alternatives(text, items, {"7": {"regions": [
                {"start": alt_start, "end": alt_start + len(alt_body), "reference": "Item 7"}]}})
            if set(got) != {"7"} or items[1]["start"] is not None or why:
                return f"missing alternative rejected or rewrote primary: {why}"
        elif scenario == "overlap":
            got, why = verify_alternatives(text, items, {"7": {"regions": [
                {"start": alt_start, "end": alt_start + 1800, "reference": "Item 7"},
                {"start": alt_start, "end": alt_start + 1900, "reference": "Item 7"}]}})
            if len(got.get("7", ())) != 2 or why:
                return f"overlapping regions rejected: {why}"
        elif scenario == "partial":
            got, why = verify(text, items, {"1": [start, start + len(body)], "99": [start, start + len(body)]})
            if set(got) != {"1"} or not why:
                return f"valid delta was erased by sibling: {got}, {why}"
        elif scenario == "invalid":
            got, why = verify_alternatives(text, items, {"7": {"regions": [
                {"start": start, "end": start + 1800}]}})
            if got or not why:
                return "invalid in-bounds region was accepted"
        elif scenario == "suppressed":
            c = classify([{"code": "low_item_coverage"}, {"code": "cross_reference_index"}], items)
            if c["route"] != "suppressed" or c["calls_paid"]:
                return f"xref route not suppressed: {c}"
        elif scenario == "vision":
            alternatives = {"7": [{"start": alt_start, "end": alt_start + 1800, "reference": "Item 7"}]}
            images = [{"src": f"chart-{n}.png", "offset": alt_start + n} for n in range(VISION_CAP + 1)]
            base = "https://www.sec.gov/Archives/edgar/data/1/a/filing.htm"
            yes = vision_verify(images, alternatives, "confirm", base)
            no = vision_verify(images, alternatives, "reject", base)
            null = vision_verify(images, alternatives, None, base)
            skip = vision_verify([], alternatives, "confirm")
            unsafe = vision_verify([{"src": "https://evil.example/x.png", "offset": alt_start}], alternatives, "confirm", base)
            bad_src = [vision_verify([{"src": src, "offset": alt_start}], alternatives, "confirm", base)
                       for src in ("", "?page=2", "filing.htm")]
            sibling = {"7": alternatives["7"], "8": [{"start": alt_start + 1900,
                                                           "end": alt_start + 2000}]}
            scoped = vision_verify(images[:1], sibling, "reject", base)
            kept = {code: regions for code, regions in sibling.items() if code not in scoped["items"]}
            from src.sec10k.llm import _body, _cache_key, PROMPT_VERSION
            body = _body("openai/gpt-5-mini", "s", "u", 9, image_urls=yes["images"])
            content = body["messages"][1]["content"]
            prompt = _vision_prompt(text, alternatives)
            malformed = []
            for raw in ('[]', '"confirm"', '{"verdict":"confirm","extra":1}'):
                try: _vision_verdict(raw)
                except (ValueError, TypeError): malformed.append(raw)
            if (yes["status"] != "verified" or yes.get("source") != "cached_test"
                    or no.get("verdict") != "reject" or null["status"] != "skipped"
                    or skip["reason"] != "no validated SEC Archives base"
                    or unsafe["status"] != "skipped" or len(yes["images"]) != VISION_CAP
                    or any(x["status"] != "skipped" for x in bad_src)
                    or scoped["items"] != ["7"] or set(kept) != {"8"}
                    or not all(u.startswith("https://www.sec.gov/Archives/") for u in yes["images"])
                    or content[0] != {"type": "text", "text": "u"}
                    or not all(x["type"] == "image_url" for x in content[1:])
                    or '"item": "7"' not in prompt or "Alternative evidence" not in prompt
                    or len(malformed) != 3
                    or _cache_key("m", "s", "u", 1) != __import__("hashlib").sha256(__import__("json").dumps([PROMPT_VERSION, "m", "s", "u", 1], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                    or _cache_key("m", "s", "u", 1) == _cache_key("m", "s", "u", 1, yes["images"])
                    or len(_vision_prompt("x" * 20000, {"7": [
                        {"start": n, "end": n + 2000}
                        for n in range(0, 12000, 2000)]})) > VISION_TEXT_CAP + 1000):
                return f"vision bounded cached decisions wrong: {yes}, {no}, {null}, {skip}"
        elif scenario == "flow":
            from src.sec10k.escalate import _stages
            tr = {"fired": False, "reason": "no trigger", "route": "none", "target_items": []}
            stages = _stages(tr, {"resolved": [], "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0}})
            if [s["stage"] for s in stages] != ["classify", "plan", "route", "verify", "decide"] or not any(s["status"] == "skipped" for s in stages):
                return f"flow stages not fixed/visible: {stages}"
        else:
            return f"unknown d21 scenario {scenario!r}"
    elif t == "deterministic":
        from src.sec10k.extract import extract_items
        r2 = extract_items(path)
        if {k: result.get(k) for k in DETERMINISM_FIELDS} \
                != {k: r2.get(k) for k in DETERMINISM_FIELDS}:
            return "non-deterministic output"
    elif t == "boilerplate":
        # ADR-026. `enabled` asserts only whether the envelope carries the key
        # at all; `value` (exact stripped line text) and/or `kind` select runs,
        # and `min`/`max` bound how many were selected. A bare `max: 0` is how
        # a case says "this line must never be treated as chrome".
        if "enabled" in chk:
            if chk["enabled"] != ("boilerplate" in result):
                return (f"boilerplate key {'absent' if chk['enabled'] else 'present'}, "
                        f"expected {'present' if chk['enabled'] else 'absent'}")
            if len(chk) == 2:  # type + enabled: nothing else to select on
                return None
        if "boilerplate" not in result:
            return "no boilerplate in result (was exclude_boilerplate set?)"
        runs = result["boilerplate"]
        if "kind" in chk:
            runs = [b for b in runs if b["kind"] == chk["kind"]]
        if "value" in chk:
            runs = [b for b in runs
                    if result["normalized_text"][b["start"]:b["end"]].strip() == chk["value"]]
        n = len(runs)
        sel = f"{chk.get('value', '<any>')!r}/{chk.get('kind', '<any kind>')}"
        # a selector with NO bound at all asserts presence — otherwise a typo in
        # `value` would pass silently. `max` alone means the case is asserting
        # absence, so it must not also demand one.
        lo = chk.get("min", 0 if "max" in chk else 1)
        if n < lo:
            return f"boilerplate {sel}: {n} runs < min {lo}"
        if "max" in chk and n > chk["max"]:
            return f"boilerplate {sel}: {n} runs > max {chk['max']}"
    elif t == "boilerplate_spans_sane":
        # the off-by-one guard: a chrome run must be whole lines and nothing
        # else, or "exclusion" silently eats a character of filing prose.
        if "boilerplate" not in result:
            return "no boilerplate in result (was exclude_boilerplate set?)"
        text = result["normalized_text"]
        prev = 0
        for b in result["boilerplate"]:
            if not (0 <= b["start"] < b["end"] <= len(text)):
                return f"boilerplate run {b} outside normalized_text"
            if b["start"] < prev:
                return f"boilerplate run {b} overlaps or is out of order"
            prev = b["end"]
            if b["start"] and text[b["start"] - 1] != "\n":
                return f"boilerplate run {b} does not start at a line start"
            if b["end"] < len(text) and text[b["end"] - 1] != "\n":
                return f"boilerplate run {b} does not end at a line end"
            if "\n" in text[b["start"]:b["end"] - 1]:
                return f"boilerplate run {b} spans more than one line"
    elif t == "boilerplate_stripped":
        # PR #25 R2: the three checks above all read the SPANS, so replacing
        # strip_chrome's body with `return text[start:end]` — a total no-op —
        # left every suite green. This one derives the stripped view, which is
        # the "a stripped run is reconstructible" half of S6's acceptance.
        if "boilerplate" not in result:
            return "no boilerplate in result (was exclude_boilerplate set?)"
        from src.sec10k.boilerplate import strip_chrome
        text, spans = result["normalized_text"], result["boilerplate"]
        stripped = strip_chrome(text, spans)
        removed = len(text) - len(stripped)
        # the spans and the removal are the same set of characters: nothing
        # extra came out, and nothing the envelope named stayed in
        want = sum(b["end"] - b["start"] for b in spans)
        if removed != want:
            return f"stripped view removed {removed} chars, spans total {want}"
        if "removed_chars" in chk and removed != chk["removed_chars"]:
            return f"stripped view removed {removed} chars != {chk['removed_chars']}"
        for v in chk.get("not_contains", []):
            if v in stripped:
                return f"stripped view still contains {v!r}"
        if spans:
            b = spans[0]
            # the window form — how a caller strips ONE item's body — and the
            # reconstruction identity: the original run is still addressable
            if strip_chrome(text, spans, start=b["start"], end=b["end"]) != "":
                return "a chrome run is not fully removed from its own window"
            if not text[b["start"]:b["end"]].strip():
                return "chrome run does not reconstruct to its original text"
    elif t == "offsets_invariant_under_exclusion":
        # S6's acceptance criterion, asserted as the equality ADR-026 §d claims
        # it is: run the same file both ways and compare. Self-contained — it
        # does not care which way the case itself ran.
        from src.sec10k.extract import extract_items
        on = extract_items(path, exclude_boilerplate=True)
        off = extract_items(path, exclude_boilerplate=False)
        for k in DETERMINISM_FIELDS:
            if on.get(k) != off.get(k):
                return f"{k} differs with exclusion on vs off — INV-S2 offsets moved"
        if "boilerplate" in off:
            return "exclusion OFF emitted a boilerplate key; default must change nothing"
        if "boilerplate" not in on:
            return "exclusion ON emitted no boilerplate key"
    elif t == "table":
        # ADR-029 §c. A hand-labeled grid: `rows` is what `tables.grid` must
        # derive for the table located by `anchor` (first record whose slice
        # contains it; `index` picks a later one). Exact match, every cell,
        # in order; `header` pins the <th> row count when given. The same
        # comparison feeds the per-run table-fidelity metric (`table_fidelity`).
        f = table_fidelity(result, chk)
        if f["why"]:
            return f["why"]
    elif t == "table_markdown":
        # the derived view itself (PR #25 R2's lesson: a check that reads only
        # the record cannot see a no-op renderer). `value` is the exact
        # Markdown `tables.to_markdown` must produce for the anchored table.
        tab, why = _locate_table(result, chk)
        if why:
            return why
        md = to_markdown(result["normalized_text"], tab)
        if md != chk["value"]:
            return f"markdown differs; got:\n{md}"
    elif t == "tables_sane":
        # ADR-029 §d: offsets in bounds, records in document order, every
        # cell inside its own table, every cell slice tight (no separator
        # whitespace leaked in). The shape itself is `envelope_shape`'s job.
        if not isinstance(result.get("tables"), list):
            return (f"tables is {type(result['tables']).__name__}, not a list" if "tables" in result
                    else "no tables in result (was tables set?)")
        text, prev = result["normalized_text"], 0
        for n, tab in enumerate(result["tables"]):
            if not (0 <= tab["start"] <= tab["end"] <= len(text)):
                return f"table {n} outside normalized_text"
            if tab["start"] < prev:
                return f"table {n} out of document order"
            prev = tab["start"]
            for row in tab["rows"]:
                for c in row:
                    if not (tab["start"] <= c[0] <= c[1] <= tab["end"]):
                        return f"table {n} cell {c} outside its table"
                    if text[c[0]:c[1]] != text[c[0]:c[1]].strip():
                        return f"table {n} cell {c} slice is not tight: {text[c[0]:c[1]]!r}"
        if "min" in chk and len(result["tables"]) < chk["min"]:
            return f"{len(result['tables'])} tables < min {chk['min']}"
        if "max" in chk and len(result["tables"]) > chk["max"]:
            return f"{len(result['tables'])} tables > max {chk['max']}"
    elif t == "offsets_invariant_under_tables":
        # ADR-029's equality, stated as ADR-026's was: the same file both
        # ways, DETERMINISM_FIELDS identical, the key on exactly one side.
        from src.sec10k.extract import extract_items
        on = extract_items(path, tables=True)
        off = extract_items(path, tables=False)
        for k in DETERMINISM_FIELDS:
            if on.get(k) != off.get(k):
                return f"{k} differs with tables on vs off — INV-S2 offsets moved"
        if "tables" in off:
            return "tables OFF emitted a tables key; default must change nothing"
        if not isinstance(on.get("tables"), list):
            return "tables ON emitted no tables list"
    elif t == "image":
        # ADR-033 §c. A hand-labeled image reference, located by `src`
        # (`index` picks a later one when a filing reuses a src). Every other
        # key is optional and asserted exactly when present: `alt`, `width`,
        # `height`, `offset`; `before`/`after` pin what the offset SITS
        # BETWEEN, which is the half a bare integer cannot show is right;
        # `item` is the code of the item whose span holds the offset, derived
        # the way ADR-029 derives an item's tables — from offsets, not from a
        # stored field — with null meaning "inside no item's span".
        if "images" not in result:
            return "no images in result (was images set?)"
        hits = [im for im in result["images"] if im["src"] == chk["src"]]
        k = chk.get("index", 0)
        if len(hits) <= k:
            return f"src {chk['src']!r}: {len(hits)} image(s) carry it, wanted #{k}"
        im, text = hits[k], result["normalized_text"]
        for f in ("alt", "width", "height", "offset"):
            if f in chk and im[f] != chk[f]:
                return f"image {chk['src']} {f} {im[f]!r} != {chk[f]!r}"
        if "before" in chk and not text[:im["offset"]].endswith(chk["before"]):
            return (f"image {chk['src']} at {im['offset']} is not preceded by "
                    f"{chk['before']!r}: {text[max(0, im['offset'] - 60):im['offset']]!r}")
        if "after" in chk and not text[im["offset"]:].startswith(chk["after"]):
            return (f"image {chk['src']} at {im['offset']} is not followed by "
                    f"{chk['after']!r}: {text[im['offset']:im['offset'] + 60]!r}")
        if "item" in chk:
            got = next((i["item"] for i in result["items"]
                        if i["status"] in SPAN_STATUSES and i["start"] is not None
                        and i["start"] <= im["offset"] < i["end"]), None)
            if got != chk["item"]:
                return f"image {chk['src']} falls in item {got!r}, labeled {chk['item']!r}"
        if "in_table" in chk:
            # PR #44 R1: whether the offset lies inside a recorded ADR-029
            # table span. It usually does NOT even for an image the raw HTML
            # puts inside a <td>, because a table span is tightened to the
            # table's visible TEXT and an image contributes none — so this
            # relationship has to be asserted, not assumed (ADR-033 §b2a).
            # HALF-OPEN, the same convention as the `item` derivation above
            # (PR #44 R7): an offset equal to `end` is the first character
            # AFTER the table, so an image there — e.g. one that follows
            # </table> — is outside it.
            if "tables" not in result:
                return "in_table needs the tables annotation too (set \"tables\": true)"
            got = any(t["start"] <= im["offset"] < t["end"] for t in result["tables"])
            if got != chk["in_table"]:
                return (f"image {chk['src']} at {im['offset']} is "
                        f"{'inside a' if got else 'outside every'} recorded table span, "
                        f"labeled in_table={chk['in_table']}")
    elif t == "images_sane":
        # ADR-033 §d, the counterpart to `tables_sane`: the contract shape
        # (offsets in bounds, document order, field types) plus a count band.
        if "images" not in result:
            return "no images in result (was images set?)"
        why = _images_shape(result)
        if why:
            return why
        n = len(result["images"])
        if "min" in chk and n < chk["min"]:
            return f"{n} images < min {chk['min']}"
        if "max" in chk and n > chk["max"]:
            return f"{n} images > max {chk['max']}"
    elif t == "offsets_invariant_under_images":
        # ADR-033's equality, stated as ADR-026's and ADR-029's are.
        from src.sec10k.extract import extract_items
        on = extract_items(path, images=True)
        off = extract_items(path, images=False)
        for k in DETERMINISM_FIELDS:
            if on.get(k) != off.get(k):
                return f"{k} differs with images on vs off — INV-S2 offsets moved"
        if "images" in off:
            return "images OFF emitted an images key; default must change nothing"
        if not isinstance(on.get("images"), list):
            return "images ON emitted no images list"
    elif t == "blocks":
        # ADR-032 §c. A hand-labeled block sequence over the window the labels
        # span: `blocks` is what the envelope's annotation must hold there —
        # kind, start, end, and level/ordered/strong/item exactly as labeled
        # (a table block's record index is not labeled; its record is checked
        # to sit on the block). `head`/`tail` on a label are the label's own
        # anchors into normalized_text, so a reviewer can re-derive the
        # offsets and a mistyped label is reported as such, not as a miss.
        # The same comparison feeds the per-run structure-fidelity metric.
        f = structure_fidelity(result, chk)
        if f["why"]:
            return f["why"]
    elif t == "markdown":
        # the derived view itself (ADR-029's lesson restated: a check that
        # reads only the record cannot see a no-op renderer). `value` is the
        # exact Markdown `markdown.to_markdown` must produce for the window —
        # an item's span (`item`), explicit `start`/`end` offsets (the same
        # offsets a `blocks` label in the case anchors with head/tail),
        # `anchor`..`end_anchor` (first occurrences) in normalized_text, or
        # the whole document when none is given. `omit_chrome: true` renders
        # with the envelope's ADR-026 runs omitted (PR #45 R1: the S8
        # checkbox must keep its meaning in Markdown mode, on real chrome);
        # `contains` / `not_contains` pin substrings of the rendering.
        if "blocks" not in result:
            return "no blocks in result (was blocks set?)"
        text = result["normalized_text"]
        if "item" in chk:
            if entry is None or not has_span:
                return f"item {chk['item']} has no span to render"
            s, e = entry["start"], entry["end"]
        elif "start" in chk:
            s, e = chk["start"], chk["end"]
        elif "anchor" in chk:
            s = text.find(chk["anchor"])
            if s < 0:
                return f"anchor {chk['anchor']!r} not in normalized_text"
            e = text.find(chk["end_anchor"], s)
            if e < 0:
                return f"end_anchor {chk['end_anchor']!r} not after the anchor"
            e += len(chk["end_anchor"])
        else:
            s, e = 0, len(text)
        omit = ()
        if chk.get("omit_chrome"):
            if "boilerplate" not in result:
                return "omit_chrome asks for chrome, but no boilerplate in result (was exclude_boilerplate set?)"
            omit = result["boilerplate"]
            if len(omit) < chk.get("min_chrome_runs", 0):
                return f"{len(omit)} chrome runs < min_chrome_runs {chk['min_chrome_runs']}"
        got = md_to_markdown(text, result["blocks"], result.get("tables") or [], s, e, omit=omit)
        if "value" in chk and got != chk["value"]:
            return f"markdown differs; got:\n{got}"
        for v in chk.get("contains", []):
            if v not in got:
                return f"{'stripped ' if omit else ''}markdown missing {v!r}"
        for v in chk.get("not_contains", []):
            if v in got:
                return (f"{'stripped ' if omit else ''}markdown still contains {v!r} "
                        f"({got.count(v)}x)")
    elif t == "blocks_sane":
        # ADR-032 §d: in bounds, document order, non-overlapping, every slice
        # tight, every kind in the enum, a table block sitting exactly on its
        # record, a heading carrying a level, and — the view loses nothing —
        # every non-space character of normalized_text inside some block.
        if not isinstance(result.get("blocks"), list):
            return (f"blocks is {type(result['blocks']).__name__}, not a list" if "blocks" in result
                    else "no blocks in result (was blocks set?)")
        text, prev, tabs = result["normalized_text"], 0, result.get("tables") or []
        covered = bytearray(len(text))
        for n, b in enumerate(result["blocks"]):
            if not (0 <= b["start"] < b["end"] <= len(text)):
                return f"block {n} {b} outside normalized_text or empty"
            if b["start"] < prev:
                return f"block {n} {b} overlaps or is out of document order"
            prev = b["end"]
            if text[b["start"]:b["end"]] != text[b["start"]:b["end"]].strip():
                return f"block {n} slice is not tight: {text[b['start']:b['end']][:40]!r}"
            if b["kind"] not in BLOCK_KINDS:
                return f"block {n} kind {b['kind']!r} not in {sorted(BLOCK_KINDS)}"
            if b["kind"] == "table" and (b.get("table") is None or not 0 <= b["table"] < len(tabs)
                                         or (tabs[b["table"]]["start"], tabs[b["table"]]["end"])
                                         != (b["start"], b["end"])):
                return f"block {n} table block does not sit on its record: {b}"
            if b["kind"] == "heading" and not isinstance(b.get("level"), int):
                return f"block {n} heading without a level: {b}"
            covered[b["start"]:b["end"]] = b"\x01" * (b["end"] - b["start"])
        lost = next((i for i, ch in enumerate(text) if not covered[i] and not ch.isspace()), None)
        if lost is not None:
            return f"visible text outside every block at {lost}: {text[lost:lost + 40]!r}"
        if "min" in chk and len(result["blocks"]) < chk["min"]:
            return f"{len(result['blocks'])} blocks < min {chk['min']}"
        if "max" in chk and len(result["blocks"]) > chk["max"]:
            return f"{len(result['blocks'])} blocks > max {chk['max']}"
    elif t == "offsets_invariant_under_blocks":
        # ADR-032's equality, as ADR-026/029 state theirs: the same file both
        # ways, DETERMINISM_FIELDS identical, the key on exactly one side —
        # and `blocks` implies `tables`, so that key rides along.
        from src.sec10k.extract import extract_items
        on = extract_items(path, blocks=True)
        off = extract_items(path, blocks=False)
        for k in DETERMINISM_FIELDS:
            if on.get(k) != off.get(k):
                return f"{k} differs with blocks on vs off — INV-S2 offsets moved"
        if "blocks" in off or "tables" in off:
            return "blocks OFF emitted a blocks/tables key; default must change nothing"
        if not isinstance(on.get("blocks"), list) or not isinstance(on.get("tables"), list):
            return "blocks ON emitted no blocks + tables lists"
    else:
        return f"unknown check type {t!r}"
    return None


BLOCK_KINDS = {"heading", "paragraph", "list_item", "table", "pre"}
BLOCK_LABEL_KEYS = {"kind", "start", "end", "level", "ordered", "strong", "item"}


# ADR-036 §g. The routing record's contract shape, asserted structurally so a
# case that merely asks for escalation still catches a malformed one.
ROUTING_OUTCOMES = {"resolved", "rejected", "unparseable", "unavailable",
                    # the intc-2025 exam: billed, and nothing came back
                    "empty_completion"}
COST_KEYS = {"llm_calls", "tokens", "usd"}


def _routing_shape(result):
    """None if `routing` is contract-shaped, else why not.

    The two clauses that are about HONESTY rather than shape, and are the
    reason this is a check and not a docstring:

    * the record's `cost` must equal the sum of its tiers' costs, and the
      envelope's own `cost` must equal the record's. A published price a
      consumer cannot re-derive from the tiers that produced it is exactly the
      undisclosed-cost shape D11 exists to close.
    * `resolved` must name only items that actually carry an escalation
      `method`. A record claiming a resolution the item list does not show is
      the fabricated-output failure repo rule 4 forbids.
    """
    r = result["routing"]
    if not isinstance(r, dict) or not {"trigger", "tiers", "resolved", "cost", "stages"} <= set(r):
        return f"keys {sorted(r) if isinstance(r, dict) else type(r).__name__}"
    t = r["trigger"]
    if not isinstance(t, dict) or not {"fired", "codes", "items", "route", "reason",
                                       "target_items", "calls_paid"} <= set(t):
        return "trigger missing fired/codes/items/route/reason/target_items/calls_paid"
    if not isinstance(t["fired"], bool):
        return f"trigger.fired {t['fired']!r} is not a bool"
    if not t["fired"] and r["tiers"]:
        return "a trigger that did not fire may not report attempted tiers"
    stages = r["stages"]
    if not isinstance(stages, list) or [s.get("stage") for s in stages if isinstance(s, dict)] != ["classify", "plan", "route", "verify", "decide"]:
        return "routing.stages is not the fixed classify/plan/route/verify/decide flow"
    for stage in stages:
        if not isinstance(stage, dict) or not {"stage", "status", "reason", "targets", "cost", "skipped"} <= set(stage):
            return f"flow stage malformed: {stage!r}"
        if stage["status"] not in {"done", "skipped", "failed"} or not isinstance(stage["targets"], list):
            return f"flow stage invalid status/targets: {stage!r}"
        if not COST_KEYS <= set(stage["cost"]):
            return f"flow stage cost missing keys: {stage!r}"
    total = {k: 0 for k in COST_KEYS}
    prior_window = None
    for tier in r["tiers"]:
        # PR #58 R17/R19: `offset` joins the required set, and the three are
        # required TOGETHER because they are one fact — what this rung was
        # shown. `input_chars` alone let the inspector print "the first N
        # chars" about a window starting at offset 178,087, and deleting all
        # three left the whole gate green. Required here so it binds every
        # producer and every case that runs `envelope_shape`, not just the one
        # that noticed.
        need = {"tier", "outcome", "cost", "offset", "input_chars", "truncated"}
        if not need <= set(tier):
            return (f"tier record missing {sorted(need - set(tier))}: "
                    f"{sorted(tier)}")
        lo, n = tier["offset"], tier["input_chars"]
        if not (isinstance(lo, int) and isinstance(n, int) and lo >= 0 and n >= 0
                and lo + n <= len(result["normalized_text"])):
            return (f"tier {tier['tier']} reports window [{lo}, {lo + n}) "
                    f"outside normalized_text (0, {len(result['normalized_text'])})")
        if tier["truncated"] != (n < len(result["normalized_text"])):
            return (f"tier {tier['tier']} says truncated={tier['truncated']} "
                    f"over {n} of {len(result['normalized_text'])} chars")
        if tier["outcome"] not in ROUTING_OUTCOMES:
            return f"tier outcome {tier['outcome']!r} not in {sorted(ROUTING_OUTCOMES)}"
        if tier["tier"] == "agent_loop":
            if not isinstance(tier.get("actions"), list) or not isinstance(tier.get("observations"), list):
                return "agent_loop tier missing action/observation lists"
            if prior_window is not None and (tier["offset"], tier["input_chars"]) != prior_window:
                return "agent_loop tier range does not match the prior read_window observation"
            prior_window = None
            for obs in tier["observations"]:
                if (isinstance(obs, dict) and isinstance(obs.get("text"), str)
                        and "document" not in obs):
                    prior_window = (obs["start"], obs["end"] - obs["start"])
        if not COST_KEYS <= set(tier["cost"]):
            return f"tier {tier['tier']} cost missing {sorted(COST_KEYS - set(tier['cost']))}"
        for k in COST_KEYS:
            total[k] = round(total[k] + tier["cost"][k], 6)
    vision = r.get("vision")
    if vision is not None:
        if not isinstance(vision, dict) or not COST_KEYS <= set(vision.get("cost") or {}):
            return f"routing.vision missing measured cost: {vision!r}"
        for k in COST_KEYS:
            total[k] = round(total[k] + vision["cost"][k], 6)
    if {k: round(r["cost"][k], 6) for k in COST_KEYS} != total:
        return (f"routing.cost {r['cost']} != {total} summed over its own tiers")
    if {k: round(result["cost"][k], 6) for k in COST_KEYS} != total:
        return (f"envelope cost {result['cost']} != routing total {total}")
    by_tier = {i["item"] for i in result["items"]
               if i["method"] in ESCALATION_METHODS}
    if set(r["resolved"]) != by_tier:
        return (f"routing.resolved {sorted(r['resolved'])} != the items whose "
                f"method names a tier {sorted(by_tier)}")
    external = r.get("external", [])
    if not isinstance(external, list):
        return "routing.external is not a list"
    by_code = {i["item"]: i for i in result["items"]}
    for code in external:
        regions = (by_code.get(code, {}).get("evidence") or {}).get("external_regions")
        if not regions:
            return f"routing.external names item {code} without external_regions"
        for region in regions:
            if not isinstance(region, dict) or not {"start", "end", "document", "verifier"} <= set(region):
                return f"item {code} external region malformed: {region!r}"
            doc = region["document"]
            required = {"id", "type", "sequence", "filename", "url", "sgml_block",
                        "raw_sha256", "normalized_sha256"}
            if not required <= set(doc) or bool(doc["url"]) == bool(doc["sgml_block"]):
                return f"item {code} external document identity malformed: {doc!r}"
            if not all(isinstance(doc[k], str) and len(doc[k]) == 64
                       for k in ("raw_sha256", "normalized_sha256")):
                return f"item {code} external document hashes malformed"
            if not (isinstance(region["start"], int) and isinstance(region["end"], int)
                    and 0 <= region["start"] < region["end"]):
                return f"item {code} external document offsets malformed"
            if not all(region["verifier"].get(k) is True
                       for k in ("identity", "hashes", "bounds")):
                return f"item {code} external verifier decisions incomplete"
    acquisition = r.get("acquisition")
    if external and (not isinstance(acquisition, dict)
                     or not {"status", "calls", "bytes", "latency_ms"} <= set(acquisition)):
        return "externally resolved routing lacks measured acquisition provenance"
    return None


def _blocks_shape(result):
    """None if `result['blocks']` is in ADR-032's contract shape, else why."""
    blocks = result["blocks"]
    if not isinstance(blocks, list):
        return f"blocks is {type(blocks).__name__}, not a list"
    if not isinstance(result.get("tables"), list):
        return "blocks without a tables list (blocks imply tables)"
    n, prev = len(result["normalized_text"]), 0
    for i, b in enumerate(blocks):
        if not isinstance(b, dict) or b.get("kind") not in BLOCK_KINDS:
            return f"record {i} {b!r}: kind not in {sorted(BLOCK_KINDS)}"
        if not (isinstance(b.get("start"), int) and isinstance(b.get("end"), int)
                and 0 <= b["start"] < b["end"] <= n):
            return f"record {i} start/end {b.get('start')},{b.get('end')} not offsets into normalized_text"
        if b["start"] < prev:
            return f"record {i} overlaps or is out of document order ({b['start']} < {prev})"
        prev = b["end"]
        extra = set(b) - BLOCK_LABEL_KEYS - {"table"}
        if extra:
            return f"record {i} undeclared keys {sorted(extra)}"
        if b["kind"] == "heading" and not isinstance(b.get("level"), int):
            return f"record {i} heading without an int level"
        if b["kind"] == "table" and not (isinstance(b.get("table"), int)
                                         and 0 <= b["table"] < len(result["tables"])):
            return f"record {i} table block without a valid record index"
        if b["kind"] != "table" and "table" in b:
            return f"record {i} {b['kind']} carries a table index"
    return None


def structure_fidelity(result, chk):
    """Compare the labeled block sequence with the derived one over the
    window the labels span ([first start, last end)).

    Returns {"blocks": (ok, total), "bounds": (ok, total), "why": reason|None}.
    bounds: labeled (start, end) pairs that some derived block in the window
    has, over the LARGER of the two counts — the boundary agreement. blocks:
    labeled blocks reproduced exactly (kind, start, end, level, ordered,
    strong, item — everything a label states, nothing it omits), over the
    larger count — kind agreement on top of boundaries. An envelope without
    blocks scores 0 over the labeled counts. Exact match of the whole
    sequence is the pass condition; the fractions are the per-run metric
    (ADR-032 §c), so a partial miss is measured, not only declared.
    """
    want = [{k: v for k, v in b.items() if k in BLOCK_LABEL_KEYS} for b in chk["blocks"]]
    zero = {"blocks": (0, len(want)), "bounds": (0, len(want)), "why": None}
    if "blocks" not in result:
        return dict(zero, why="no blocks in result (was blocks set?)")
    text = result["normalized_text"]
    for lab in chk["blocks"]:
        slice_ = text[lab["start"]:lab["end"]]
        if not slice_.startswith(lab.get("head", "")) or not slice_.endswith(lab.get("tail", "")):
            return dict(zero, why=f"LABEL does not match normalized_text at [{lab['start']}, "
                                  f"{lab['end']}): {slice_[:60]!r}")
    s, e = want[0]["start"], want[-1]["end"]
    got = [{k: v for k, v in b.items() if k in BLOCK_LABEL_KEYS}
           for b in blocks_in(result["blocks"], s, e)]
    total = max(len(want), len(got))
    got_bounds = {(b["start"], b["end"]) for b in got}
    bounds_ok = sum(1 for b in want if (b["start"], b["end"]) in got_bounds)
    blocks_ok = sum(1 for b in want if b in got)
    out = {"blocks": (blocks_ok, total), "bounds": (bounds_ok, total), "why": None}
    if got != want:
        bad = next((i for i, (a, b) in enumerate(zip(want, got)) if a != b), min(len(want), len(got)))
        out["why"] = (f"blocks differ: {len(got)} derived vs {len(want)} labeled in "
                      f"[{s}, {e}); blocks {blocks_ok}/{total}, bounds {bounds_ok}/{total}; "
                      f"first mismatch at #{bad}: got {got[bad] if bad < len(got) else None} "
                      f"!= labeled {want[bad] if bad < len(want) else None}")
    return out


def _tables_shape(result):
    """None if `result['tables']` is in ADR-029's contract shape, else why."""
    tabs = result["tables"]
    if not isinstance(tabs, list):
        return f"tables is {type(tabs).__name__}, not a list"
    n, prev = len(result["normalized_text"]), 0
    for i, tab in enumerate(tabs):
        if not isinstance(tab, dict) or set(tab) != {"start", "end", "header", "rows"}:
            return f"record {i} keys {sorted(tab) if isinstance(tab, dict) else tab!r}"
        if not (isinstance(tab["start"], int) and isinstance(tab["end"], int)
                and 0 <= tab["start"] <= tab["end"] <= n):
            return f"record {i} start/end {tab['start']},{tab['end']} not offsets into normalized_text"
        # PR #34 R2: the contract names document order and cell-in-span as
        # part of the shape, so they are refused here too, not only by
        # `tables_sane` (which every table case also runs)
        if tab["start"] < prev:
            return f"record {i} out of document order ({tab['start']} < {prev})"
        prev = tab["start"]
        if not (isinstance(tab["header"], int) and 0 <= tab["header"] <= len(tab["rows"])):
            return f"record {i} header {tab['header']!r}"
        if not tab["rows"] or not all(isinstance(r, list) and r for r in tab["rows"]):
            return f"record {i} has an empty row or no rows"
        for r in tab["rows"]:
            for c in r:
                if not (isinstance(c, list) and len(c) in (2, 3)
                        and all(isinstance(x, int) for x in c)
                        and tab["start"] <= c[0] <= c[1] <= tab["end"]
                        and (len(c) == 2 or c[2] > 1)):
                    return f"record {i} cell {c!r} (not inside [{tab['start']}, {tab['end']}] or malformed)"
    return None


def _images_shape(result):
    """None if `result['images']` is in ADR-033's contract shape, else why."""
    imgs = result["images"]
    if not isinstance(imgs, list):
        return f"images is {type(imgs).__name__}, not a list"
    n, prev = len(result["normalized_text"]), 0
    for i, im in enumerate(imgs):
        if not isinstance(im, dict) or set(im) != {"offset", "src", "alt", "width", "height"}:
            return f"record {i} keys {sorted(im) if isinstance(im, dict) else im!r}"
        if not (isinstance(im["offset"], int) and 0 <= im["offset"] <= n):
            return f"record {i} offset {im['offset']!r} is not an offset into normalized_text"
        if im["offset"] < prev:
            return f"record {i} out of document order ({im['offset']} < {prev})"
        prev = im["offset"]
        for k in ("src", "alt"):
            if not (im[k] is None or isinstance(im[k], str)):
                return f"record {i} {k} {im[k]!r} is not a string or null"
        for k in ("width", "height"):
            if not (im[k] is None or (isinstance(im[k], int) and im[k] > 0)):
                return f"record {i} {k} {im[k]!r} is not a positive int or null"
    return None


def _locate_table(result, chk):
    """(record, None) for the `index`-th record (default first) whose slice
    holds `anchor`, else (None, reason)."""
    if "tables" not in result:
        return None, "no tables in result (was tables set?)"
    text = result["normalized_text"]
    hits = [t for t in result["tables"] if chk["anchor"] in text[t["start"]:t["end"]]]
    k = chk.get("index", 0)
    if len(hits) <= k:
        return None, f"anchor {chk['anchor']!r}: {len(hits)} table(s) contain it, wanted #{k}"
    return hits[k], None


def table_fidelity(result, chk):
    """Compare the derived grid of the anchored table with the labeled rows.

    Returns {"cells": (ok, total), "rows": (ok, total), "why": reason|None}.
    cells: positions (i, j) whose text matches exactly, over the LARGER of
    the labeled and derived cell counts — extra or missing cells count
    against, not for. rows: rows reproduced exactly, over the larger row
    count. A table that cannot be located scores 0 over the labeled counts.
    Exact match is the pass condition; the fractions are the per-run metric
    (ADR-029 §c), so a partial miss is measured, not only declared.
    """
    want = chk["rows"]
    n_want_cells = sum(len(r) for r in want)
    tab, why = _locate_table(result, chk)
    if why:
        return {"cells": (0, n_want_cells), "rows": (0, len(want)), "why": why}
    got = grid(result["normalized_text"], tab)
    n_got_cells = sum(len(r) for r in got)
    cells_ok = sum(1 for i in range(min(len(want), len(got)))
                   for j in range(min(len(want[i]), len(got[i])))
                   if want[i][j] == got[i][j])
    rows_ok = sum(1 for i in range(min(len(want), len(got))) if want[i] == got[i])
    out = {"cells": (cells_ok, max(n_want_cells, n_got_cells)),
           "rows": (rows_ok, max(len(want), len(got))), "why": None}
    if "header" in chk and tab["header"] != chk["header"]:
        out["why"] = f"header rows {tab['header']} != {chk['header']}"
    elif got != want:
        bad = next(((i, j) for i in range(min(len(want), len(got)))
                    for j in range(min(len(want[i]), len(got[i]))) if want[i][j] != got[i][j]),
                   None)
        out["why"] = (f"grid differs: {len(got)} rows x {len(got[0]) if got else 0} got vs "
                      f"{len(want)} x {len(want[0]) if want else 0} labeled; "
                      f"cells {cells_ok}/{out['cells'][1]}, rows {rows_ok}/{out['rows'][1]}"
                      + (f"; first mismatch at {bad}: {got[bad[0]][bad[1]]!r} != "
                         f"{want[bad[0]][bad[1]]!r}" if bad else ""))
    return out


def _no_credential():
    """Remove `OPENROUTER_API_KEY` from this process's environment, restoring
    it on exit. Every sec10k case runs inside this.

    Cost-discipline rule 4 — "the `fast` suite makes zero paid calls" — is
    enforced HERE, structurally, rather than trusted: a case declaring
    `escalate: true` would otherwise behave differently on a developer's
    machine depending on whether they happened to have a key exported, and on
    a machine that had one it would spend real money inside the pre-commit
    gate. Clearing it makes every suite run take the refusal path, which is
    also the path D11 most needs a case to pin while no credential exists.

    A future paid case does not weaken this: it gets its own suite tag and its
    own opt-in, and this stays the default for everything in `fast`/`invariant`.
    """
    import contextlib
    import os

    @contextlib.contextmanager
    def _ctx():
        saved = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            yield
        finally:
            if saved is not None:
                os.environ["OPENROUTER_API_KEY"] = saved
    return _ctx()


def run_case(case):
    from src.sec10k.extract import extract_items
    path = str(ROOT / case["input"]["path"])
    # the WHOLE case runs keyless, not just the first extraction: `deterministic`,
    # `offsets_invariant_under_exclusion` and `escalation_invariant` each re-run
    # the pipeline from inside the check loop, and a suite that spends money on
    # the second run of a file has not made zero paid calls.
    with _no_credential():
        result = extract_items(
            path, exclude_boilerplate=case["input"].get("exclude_boilerplate", False),
            tables=case["input"].get("tables", False),
            blocks=case["input"].get("blocks", False),
            images=case["input"].get("images", False),
            escalate=case["input"].get("escalate", False))
        extracted = [i for i in result["items"] if i["status"] == "extracted"]

        failures = []
        # ADR-029 §c: every `table` check's cell/row counts, summed for the run;
        # ADR-032 §c: every `blocks` check's block/bounds counts, the same way
        cells, rows, blks, bnds = [0, 0], [0, 0], [0, 0], [0, 0]
        for chk in case["expect"]["checks"]:
            if chk["type"] == "table":
                f = table_fidelity(result, chk)   # one comparison: the verdict AND the metric
                reason = f["why"]
                cells = [cells[0] + f["cells"][0], cells[1] + f["cells"][1]]
                rows = [rows[0] + f["rows"][0], rows[1] + f["rows"][1]]
            elif chk["type"] == "blocks":
                f = structure_fidelity(result, chk)
                reason = f["why"]
                blks = [blks[0] + f["blocks"][0], blks[1] + f["blocks"][1]]
                bnds = [bnds[0] + f["bounds"][0], bnds[1] + f["bounds"][1]]
            else:
                reason = eval_check(result, chk, path=path)
            if reason:
                failures.append({"check": chk, "why": reason})

    items_summary = [{
        "item": i["item"], "status": i["status"],
        "confidence": i.get("confidence"), "method": i.get("method"),
        "chars": (i["end"] - i["start"]) if i["status"] == "extracted" else None,
    } for i in result["items"]]

    out = {"passed": not failures, "failures": failures,
           "n_items": len(result["items"]), "n_extracted": len(extracted),
           "doc_status": result.get("doc_status"), "items_summary": items_summary}
    if cells[1] or rows[1]:
        # only a case that labels a table contributes to the run's fidelity
        out["table_fidelity"] = {"cells": cells, "rows": rows}
    if blks[1] or bnds[1]:
        out["structure_fidelity"] = {"blocks": blks, "bounds": bnds}
    return out
