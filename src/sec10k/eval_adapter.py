"""Eval adapter for sec10k — owns the check vocabulary and item registry.

Case shape:
    "input":  {"path": "evals/fixtures/<name>/<file>"}
    "expect": {"checks": [{"type": ..., ...}, ...]}
"""
from pathlib import Path

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
# statuses that carry offsets, per ADR-011. `incorporated_by_reference` points
# at the pointer paragraph — real, inspectable text — so every span-level check
# must reach it. `missing`/`omitted` have no span by definition.
SPAN_STATUSES = {"extracted", "incorporated_by_reference"}
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
    by_code = {i["item"]: i for i in result["items"]}
    entry = by_code.get(chk.get("item"))
    extracted = [i for i in result["items"] if i["status"] == "extracted"]
    spanned = [i for i in result["items"] if i["status"] in SPAN_STATUSES]
    has_span = entry is not None and entry["status"] in SPAN_STATUSES

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
        # FIRES when it should — the counterpart to warning_absent
        if not [w for w in result.get("warnings", []) if w.get("code") == chk["code"]]:
            got = sorted({w.get("code") for w in result.get("warnings", [])})
            return f"expected warning {chk['code']!r}, got {got}"
    elif t == "warning_absent":
        # warnings are not free: they downgrade doc_status to
        # success_with_warning and move confidence, so a validator that cries
        # wolf on a normal filing is a defect the doc_status checks can't see
        hits = [w for w in result.get("warnings", []) if w.get("code") == chk["code"]]
        if hits:
            return f"unexpected warning {chk['code']!r}: {hits[0].get('message')}"
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
    elif t == "confidence":
        # the contract promises confidence is honest and that the eval set
        # punishes overconfident wrongness. Until this check type existed no
        # case read the field at all, so every constant in ADR-008's
        # confidence table was free to change with the suite still green.
        if entry is None:
            return f"item {chk['item']} not in output"
        c = entry.get("confidence")
        if c is None:
            return f"item {chk['item']} has no confidence"
        if "value" in chk and c != chk["value"]:
            return f"item {chk['item']} confidence {c} != {chk['value']}"
        if "max" in chk and c > chk["max"]:
            return f"item {chk['item']} confidence {c} > {chk['max']}"
        if "min" in chk and c < chk["min"]:
            return f"item {chk['item']} confidence {c} < {chk['min']}"
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
    elif t == "deterministic":
        from src.sec10k.extract import extract_items
        r2 = extract_items(path)
        if {k: result.get(k) for k in DETERMINISM_FIELDS} \
                != {k: r2.get(k) for k in DETERMINISM_FIELDS}:
            return "non-deterministic output"
    else:
        return f"unknown check type {t!r}"
    return None


def run_case(case):
    from src.sec10k.extract import extract_items
    path = str(ROOT / case["input"]["path"])
    result = extract_items(path)
    extracted = [i for i in result["items"] if i["status"] == "extracted"]

    failures = []
    for chk in case["expect"]["checks"]:
        reason = eval_check(result, chk, path=path)
        if reason:
            failures.append({"check": chk, "why": reason})

    items_summary = [{
        "item": i["item"], "status": i["status"],
        "confidence": i.get("confidence"), "method": i.get("method"),
        "chars": (i["end"] - i["start"]) if i["status"] == "extracted" else None,
    } for i in result["items"]]

    return {"passed": not failures, "failures": failures,
            "n_items": len(result["items"]), "n_extracted": len(extracted),
            "doc_status": result.get("doc_status"), "items_summary": items_summary}
