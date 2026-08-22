"""Eval adapter for sec10k — owns the check vocabulary and item registry.

Case shape:
    "input":  {"path": "evals/fixtures/<name>/<file>",
               "exclude_boilerplate": false}   # optional, ADR-026
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
# contract v2 normative enums read by `envelope_shape`. `heading_lenient` and
# `llm_fallback` are in the contract by decision (ADR-027 / ADR-020): the
# first is emitted for a weak-title heading match, the second never.
DOC_STATUSES = {"success", "success_with_warning", "ambiguous", "unsupported", "failed"}
METHODS = {"heading_strict", "heading_lenient", "status_keyword", "llm_fallback"}
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
    by_code = {i["item"]: i for i in result.get("items", [])}
    entry = by_code.get(chk.get("item"))
    extracted = [i for i in result.get("items", []) if i["status"] == "extracted"]
    spanned = [i for i in result.get("items", []) if i["status"] in SPAN_STATUSES]
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
        extra = set(result) - top - {"boilerplate"}  # ADR-026's one optional key
        if not top <= set(result) or extra:
            return f"envelope keys: missing {sorted(top - set(result))}, undeclared {sorted(extra)}"
        ds = result["doc_status"]
        if ds not in DOC_STATUSES:
            return f"doc_status {ds!r} not in contract enum"
        refusal = ds in ("unsupported", "failed")
        meta_keys = {"extractor_version", "input_sha256", "format_era", "document_selected"}
        if not refusal:
            # set only once the filing is accepted (SD-6): a refused document
            # has no era and no manifest to report
            meta_keys |= {"taxonomy_era", "toc_manifest"}
        if not meta_keys <= set(result["meta"]):
            return f"meta missing {sorted(meta_keys - set(result['meta']))}"
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
                     "status", "confidence", "method", "evidence"}
        for i in result["items"]:
            if not item_keys <= set(i):
                return f"item {i.get('item')} missing {sorted(item_keys - set(i))}"
            if i["method"] not in METHODS:
                return f"item {i['item']} method {i['method']!r} not in contract enum"
            if i["status"] not in STATUSES:
                return f"item {i['item']} status {i['status']!r} not in contract enum"
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
    else:
        return f"unknown check type {t!r}"
    return None


def run_case(case):
    from src.sec10k.extract import extract_items
    path = str(ROOT / case["input"]["path"])
    result = extract_items(
        path, exclude_boilerplate=case["input"].get("exclude_boilerplate", False))
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
