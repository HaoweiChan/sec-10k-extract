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
METHODS = {"heading_strict", "heading_lenient", "status_keyword", "llm_fallback"}
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
    spanned = [i for i in result.get("items", []) if i["status"] in SPAN_STATUSES]
    has_span = entry is not None and entry["status"] in SPAN_STATUSES
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
        # the optional keys: ADR-026's `boilerplate`, ADR-029's `tables`,
        # ADR-032's `blocks`, ADR-033's `images`
        extra = set(result) - top - {"boilerplate", "tables", "blocks", "images"}
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
            # ADR-034 §d adds `coverage` on the same terms: a document the
            # pipeline refused has no items, so no coverage to report
            meta_keys |= {"taxonomy_era", "toc_manifest", "coverage"}
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
                     "status", "confidence", "method", "evidence",
                     "review_required"}  # ADR-034 §e
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
                        if i["status"] in SPAN_STATUSES
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


def run_case(case):
    from src.sec10k.extract import extract_items
    path = str(ROOT / case["input"]["path"])
    result = extract_items(
        path, exclude_boilerplate=case["input"].get("exclude_boilerplate", False),
        tables=case["input"].get("tables", False),
        blocks=case["input"].get("blocks", False),
        images=case["input"].get("images", False))
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
