"""Layer 8: the label-free validator battery, and layer 9 confidence.

These validators need no annotations, so they run on EVERY filing — including
held-out ones the eval set has never seen. That is where robustness beyond the
labeled fixtures comes from.

Policy (failure-taxonomy F7): every validator is itself a false-positive
source, so validators emit warnings and move confidence; none hard-fails a run
alone, and only the three named in `AMBIGUOUS_CODES` may push `doc_status` to
`ambiguous`. Thresholds are measured, never assumed — ADR-008 carries the
distributions and the priors this battery REJECTED after measuring them.

Self-check: python3 -m src.sec10k.validate
"""
import re

# ADR-008, measured over 13 fixtures. Clean modern filings leave 0.7-7.6% of
# the document outside every item; IBR-heavy and appendix-carrying filings
# leave 26.5-76.9%. The floor sits in that empty band.
UNATTRIBUTED_MAX = 0.17
# JPM 2024 puts its whole financial appendix after the Item 15 exhibit index,
# so the last item swallows 83.3% of the document. Next highest in the set is
# 18.9% (Textron's exhibit list). Band midpoint.
LAST_ITEM_MAX = 0.50
# content-shape validators cannot judge a pointer paragraph: GE's Item 8 is
# "See index under item 14." (86 chars) and NVDA's is a 209-char internal
# pointer, both legitimately `extracted` per ADR-004 shape 2
SUBSTANTIVE_MIN = 5000

# Only these may push doc_status to `ambiguous`. `unattributed_content` is
# deliberately NOT among them: for IBR-heavy filings (IBM 1997 leaves 43% of
# the document outside every item, Textron 28%) that shape is normal and the
# honest report is a warning, not "we could not resolve this".
AMBIGUOUS_CODES = {"toc_manifest_mismatch", "last_item_dominates",
                   "expected_items_mostly_missing"}

# H1: JNJ 2016 lost 18 of 21 items and still reported success_with_warning,
# because `expected_item_missing` is per-item and is not an escalating code —
# so no VOLUME of it could ever move doc_status. Measured over all 17
# non-refused dev fixtures: fifteen lose ZERO items, and the only two that lose
# any (heading-unnumbered 0.043, malformed-html 0.048) already escalate by
# another route. Held-out JNJ sat at 0.857. Empty band 0.048–0.857.
#
# The floor is 0.25, not the band midpoint this repo usually takes: the cost
# asymmetry differs from a content-shape validator. A false `ambiguous` is a
# conservative report a consumer can inspect; a false `success_with_warning` on
# a collapsed document is the silent failure the whole battery exists to
# prevent. 0.25 still sits 5x above the worst real filing in the set.
MISSING_MAX = 0.25

# per-item vocabulary priors: does this span READ like its label?
FINGERPRINTS = {
    "1A": ["risk", "adversely", "could"],
    "3": ["legal", "proceedings"],
    "8": ["total", "net"],
    "9A": ["internal control", "disclosure controls"],
}


def _density(s):
    """digit/$/% ratio — Item 8 runs high, Item 1A near zero."""
    return sum(c.isdigit() or c in "$%" for c in s) / max(len(s), 1)


def validate(text, items, accepted, manifest):
    """Returns a list of warning dicts. Never raises, never mutates."""
    warns = []
    n = max(len(text), 1)
    spans = {i["item"]: (i["start"], i["end"]) for i in items
             if i["status"] == "extracted"}
    body = {c: text[s:e] for c, (s, e) in spans.items()}
    # ADR-011: IBR items carry pointer-text offsets. They stay OUT of the
    # content-shape validators below — coverage, domination and density were
    # all measured over extracted spans, and a pointer paragraph has no
    # vocabulary or numeric profile to judge — but their boundaries are checked
    # like any other span. Before this, an IBR span was invisible to all six.
    hygiene_spans = dict(spans)
    hygiene_spans.update({i["item"]: (i["start"], i["end"]) for i in items
                          if i["status"] == "incorporated_by_reference"
                          and i["start"] is not None})

    def warn(code, msg, item=None):
        warns.append({"code": code, "item": item, "message": msg})

    # 1. TOC manifest cross-check — the filing's own declared item list. The
    # trap doubles as a checklist: it is the only free, label-free statement of
    # what SHOULD be here that the document itself provides.
    if manifest:
        found = {c for c in accepted}
        missing = [c for c in manifest if c not in found]
        if missing:
            warn("toc_manifest_mismatch",
                 f"filing's own table of contents lists {missing} but no heading was resolved")

    # 1b. Missing PROPORTION, not missing count. The per-item
    # `expected_item_missing` warnings are emitted upstream and are informative
    # but non-escalating; on their own they let a document that lost most of
    # its items present as a qualified success. The contract calls doc_status
    # "the frontend's headline banner" and invites consumers to threshold on
    # it, so losing a quarter of the expected items is a refusal to resolve,
    # not a footnote.
    if items:
        missing = [i for i in items if i["status"] == "missing"]
        frac = len(missing) / len(items)
        if frac > MISSING_MAX:
            warn("expected_items_mostly_missing",
                 f"{len(missing)} of {len(items)} expected items ({frac:.0%}) have no "
                 f"heading: {[i['item'] for i in missing][:8]}"
                 f"{'…' if len(missing) > 8 else ''}")

    # 2. Unattributed content — everything outside every item. Localises the
    # complement of coverage: preamble is the cover page, tail is signatures,
    # and a large one means a whole region went unlabelled.
    if spans:
        first = min(s for s, _ in spans.values())
        last = max(e for _, e in spans.values())
        outside = (first + (n - last)) / n
        if outside > UNATTRIBUTED_MAX:
            warn("unattributed_content",
                 f"{outside:.0%} of the document lies outside every item "
                 f"({first:,} chars before the first, {n - last:,} after the last)")

    # 3. Last-item domination — the tail-bleed detector. An exhibit index is
    # never the largest thing in a 10-K; if it is, the span swallowed an
    # appendix (ADR-004 shape 2 content that carries no heading of its own).
    if spans:
        last_code = max(spans, key=lambda c: spans[c][0])
        frac = (spans[last_code][1] - spans[last_code][0]) / n
        if frac > LAST_ITEM_MAX:
            warn("last_item_dominates",
                 f"item {last_code} is {frac:.0%} of the document — its span most "
                 "likely swallowed unlabelled content that follows it",
                 item=last_code)

    # 4. Boundary hygiene — every span must open with its own heading. Cheap,
    # and it is the one thing that must never be wrong.
    for code, (s, e) in hygiene_spans.items():
        head = text[s:s + 60].split("\n")[0]
        if not re.match(r"(?i)^\s*(part\s+[ivx]+\s*[-–—.:]?\s*)?item\s*" +
                        re.escape(code) + r"\b", head):
            warn("boundary_hygiene", f"item {code} span does not start with its heading",
                 item=code)

    # 5. Numeric density, RELATIVE within the filing — absolute bands overlap
    # across filers (measured), the ordering does not: financials are denser
    # than risk factors in 9 of 9 filings where both are substantive.
    if len(body.get("8", "")) >= SUBSTANTIVE_MIN and len(body.get("1A", "")) >= SUBSTANTIVE_MIN:
        d8, d1a = _density(body["8"]), _density(body["1A"])
        if d8 <= d1a:
            warn("numeric_density_inversion",
                 f"item 8 is no denser in figures than item 1A ({d8:.3f} vs {d1a:.3f}) "
                 "— the two spans may be mislabelled", item="8")

    # 6. Keyword fingerprints — does a substantive span read like its label?
    for code, words in FINGERPRINTS.items():
        span = body.get(code, "")
        if len(span) < SUBSTANTIVE_MIN:
            continue  # a pointer paragraph has no vocabulary to judge
        low = span.lower()
        if not any(w in low for w in words):
            warn("keyword_fingerprint",
                 f"item {code} contains none of {words} — span may not be its item",
                 item=code)

    return warns


# --------------------------------------------------------------- confidence

# ADR-008: coarse and clamped — no fake precision. Every input is recorded in
# the item's evidence{} so an auditor can recompute or dispute the number.
BASE_STRICT, BASE_WEAK = 0.95, 0.75
BASE_IBR, BASE_OMITTED, BASE_MISSING = 0.85, 0.80, 0.55
WARN_PENALTY = 0.15
FLOOR, CEIL = 0.20, 0.95


def score(item, warns):
    """Confidence for one item, from recorded evidence only."""
    ev = dict(item.get("evidence") or {})
    if item["status"] == "extracted":
        base = BASE_STRICT if ev.get("title_similarity", 0) >= 0.8 else BASE_WEAK
    elif item["status"] == "incorporated_by_reference":
        base = BASE_IBR
    elif item["status"] == "omitted":
        base = BASE_OMITTED
    else:
        base = BASE_MISSING  # missing: we expected it and found nothing
    hits = [w["code"] for w in warns if w.get("item") == item["item"]]
    conf = max(FLOOR, min(CEIL, base - WARN_PENALTY * len(hits)))
    ev["warnings"] = hits
    ev["confidence_base"] = base
    return round(conf, 2), ev


def _demo():
    text = ("Item 1. Business\n" + "We sell things. " * 400 +
            "\nItem 15. Exhibits\n" + "x" * 40)
    cut = text.index("Item 15.")  # computed, never hand-typed — the demo's own
    items = [{"item": "1", "part": "I", "status": "extracted", "start": 0,
              "end": cut, "evidence": {"title_similarity": 1.0}},
             {"item": "15", "part": "IV", "status": "extracted", "start": cut,
              "end": len(text), "evidence": {"title_similarity": 1.0}}]
    w = validate(text, items, {"1": {}, "15": {}}, [])
    assert not [x for x in w if x["code"] == "boundary_hygiene"], w

    # ...and the positive case, which ONLY exists here. No fixture can fire
    # boundary_hygiene: spans are built from heading matches, so a span always
    # opens with its heading by construction, and the check re-applies a copy
    # of the regex that produced the offset. It is a consistency assertion
    # between two layers, not a statement about any document — so it is proved
    # against the layer boundary, on offsets a caller could only produce by
    # being wrong. ADR-016 records why that is the honest place for it.
    off = [{**items[0], "start": items[0]["start"] + 40}, items[1]]
    codes = [x["code"] for x in validate(text, off, {"1": {}, "15": {}}, [])]
    assert "boundary_hygiene" in codes, codes
    # an IBR span is checked the same way (ADR-011): before that extension an
    # IBR item's offsets were invisible to every validator here
    ibr = [{**items[0], "status": "incorporated_by_reference",
            "start": items[0]["start"] + 40}]
    codes = [x["code"] for x in validate(text, ibr, {"1": {}}, [])]
    assert "boundary_hygiene" in codes, codes

    # a manifest naming an item we never resolved is a strong, free signal
    w = validate(text, items, {"1": {}}, ["1", "7", "8"])
    assert [x["code"] for x in w if x["code"] == "toc_manifest_mismatch"], w

    # last-item domination: one span swallowing the document
    big = "Item 1. Business\nshort\n" + "Item 15. Exhibits\n" + "y" * 5000
    cut2 = big.index("Item 15.")
    items2 = [{"item": "1", "part": "I", "status": "extracted", "start": 0, "end": cut2,
               "evidence": {}},
              {"item": "15", "part": "IV", "status": "extracted", "start": cut2,
               "end": len(big), "evidence": {}}]
    codes = [x["code"] for x in validate(big, items2, {"1": {}, "15": {}}, [])]
    assert "last_item_dominates" in codes, codes

    # confidence: warnings on an item pull it down, others leave it alone
    it = {"item": "8", "status": "extracted", "evidence": {"title_similarity": 1.0}}
    assert score(it, [])[0] == BASE_STRICT
    assert score(it, [{"code": "keyword_fingerprint", "item": "8"}])[0] < BASE_STRICT
    assert score(it, [{"code": "keyword_fingerprint", "item": "1"}])[0] == BASE_STRICT
    assert score({"item": "9", "status": "missing", "evidence": {}}, [])[0] == BASE_MISSING
    print("[validate self-check] ok")


if __name__ == "__main__":
    _demo()
