"""Self-check for the eval check vocabulary itself — NOT an eval run.

Feeds hand-built synthetic result dicts through eval_check() and asserts
pass/fail outcomes. Never imports or calls extract_items, never fabricates
an eval report (repo hard rule 4: no mocked results). `deterministic` is
skipped on purpose — it's the one check allowed to call extract_items, so it
needs a real pipeline and a real fixture, neither of which belongs here.

Run: python3 -m src.sec10k.test_eval_adapter
 or: python3 src/sec10k/test_eval_adapter.py   (from repo root)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sec10k.eval_adapter import eval_check  # noqa: E402


def item(code, status="extracted", start=0, end=0, confidence=0.9):
    if status == "extracted":
        return {"item": code, "status": status, "start": start, "end": end,
                "confidence": confidence}
    return {"item": code, "status": status, "start": None, "end": None,
            "confidence": confidence}


def test_doc_status():
    r = {"normalized_text": "", "doc_status": "unsupported", "items": []}
    assert eval_check(r, {"type": "doc_status", "value": "unsupported"}) is None
    assert eval_check(r, {"type": "doc_status", "value": "success"}) is not None
    assert eval_check(r, {"type": "doc_status", "in": ["success", "success_with_warning"]}) is not None

    r2 = {"normalized_text": "", "doc_status": "success", "items": []}
    assert eval_check(r2, {"type": "doc_status", "in": ["success", "success_with_warning"]}) is None

    r3 = {"normalized_text": "", "items": []}  # no doc_status key at all
    reason = eval_check(r3, {"type": "doc_status", "value": "success"})
    assert reason == "doc_status missing (contract v2)", reason


def test_max_chars():
    r = {"normalized_text": "x" * 100, "items": [item("1", "extracted", 0, 50)]}
    assert eval_check(r, {"type": "max_chars", "item": "1", "value": 60}) is None
    assert eval_check(r, {"type": "max_chars", "item": "1", "value": 10}) is not None
    assert eval_check(r, {"type": "max_chars", "item": "2", "value": 10}) == "item not in output"

    r2 = {"normalized_text": "", "items": [item("1", "missing")]}
    assert eval_check(r2, {"type": "max_chars", "item": "1", "value": 10}) == "item has no span"


def test_text_checks_non_extracted():
    # historical trap: normalized_text[None:None] == the whole document, which
    # could false-pass text_contains (doc happens to contain the value anywhere)
    # or false-fail text_not_contains (doc happens to contain the forbidden value
    # somewhere outside the missing item). Neither must happen.
    doc = "the forbidden phrase sits far away from item 1"
    r = {"normalized_text": doc, "items": [item("1", "missing")]}

    reason = eval_check(r, {"type": "text_contains", "item": "1", "value": "forbidden phrase"})
    assert reason == "item has no span", reason

    # value present elsewhere in the whole doc, but item 1 was never extracted —
    # must still fail, not false-pass via the whole-doc slice
    reason = eval_check(r, {"type": "text_contains", "item": "1", "value": "far away"})
    assert reason == "item has no span", reason

    # text_not_contains: nothing was extracted, so nothing can contain the
    # forbidden text — vacuous pass, even though the phrase IS in the full doc
    reason = eval_check(r, {"type": "text_not_contains", "item": "1", "value": "forbidden phrase"})
    assert reason is None, reason


def test_min_chars_null_offsets():
    # this is the historical TypeError trap: null start/end must not blow up
    r = {"normalized_text": "", "items": [item("1", "missing")]}
    assert eval_check(r, {"type": "min_chars", "item": "1", "value": 10}) == "item has no span"

    r2 = {"normalized_text": "x" * 20, "items": [item("1", "extracted", 0, 20)]}
    assert eval_check(r2, {"type": "min_chars", "item": "1", "value": 10}) is None
    assert eval_check(r2, {"type": "min_chars", "item": "1", "value": 30}) is not None

    # item absent entirely still defaults to 0 chars (pre-existing behavior, not TypeError)
    r3 = {"normalized_text": "", "items": []}
    assert eval_check(r3, {"type": "min_chars", "item": "1", "value": 10}) is not None


def test_expected_set_complete():
    r = {"normalized_text": "", "items": [item("1", "extracted", 0, 10), item("2", "missing")]}
    assert eval_check(r, {"type": "expected_set_complete", "items": ["1", "2"]}) is None
    reason = eval_check(r, {"type": "expected_set_complete", "items": ["1", "2", "3"]})
    assert reason is not None and "3" in reason, reason


def test_only_items():
    r = {"normalized_text": "", "items": [item("1", "extracted", 0, 10)]}
    assert eval_check(r, {"type": "only_items", "items": ["1", "2"]}) is None

    r2 = {"normalized_text": "", "items": [item("1", "extracted", 0, 10),
                                            item("99", "extracted", 10, 20)]}
    reason = eval_check(r2, {"type": "only_items", "items": ["1"]})
    assert reason is not None and "99" in reason, reason


def test_item_absent_any_status():
    r = {"normalized_text": "", "items": [item("1A", "missing")]}
    # default (any_status unset): only fails when extracted, so "missing" passes
    assert eval_check(r, {"type": "item_absent", "item": "1A"}) is None
    # any_status: fails on presence with ANY status, including "missing"
    assert eval_check(r, {"type": "item_absent", "item": "1A", "any_status": True}) is not None

    r2 = {"normalized_text": "", "items": []}
    assert eval_check(r2, {"type": "item_absent", "item": "1A", "any_status": True}) is None


def test_no_empty_success():
    for honest in ("failed", "unsupported", "ambiguous"):
        r = {"normalized_text": "", "doc_status": honest, "items": []}
        assert eval_check(r, {"type": "no_empty_success"}) is None, honest

    r = {"normalized_text": "", "doc_status": "success", "items": []}
    assert eval_check(r, {"type": "no_empty_success"}) is not None

    # the old hole: one 100-char extracted item among a sea of empties used to pass
    r = {"normalized_text": "x" * 100, "doc_status": "success",
         "items": [item("1", "extracted", 0, 100), item("2", "missing"), item("3", "missing")]}
    assert eval_check(r, {"type": "no_empty_success"}) is not None

    r = {"normalized_text": "x" * 2000, "doc_status": "success",
         "items": [item("1", "extracted", 0, 1200)]}
    assert eval_check(r, {"type": "no_empty_success"}) is None

    r = {"normalized_text": "", "items": []}  # doc_status missing entirely
    assert eval_check(r, {"type": "no_empty_success"}) is not None


def test_norm_checks():
    r = {"normalized_text": "UNITED STATES\n\nFORM 10-K\n\nMicrosoft was founded in 1975.",
         "items": []}
    assert eval_check(r, {"type": "norm_contains", "value": "FORM 10-K"}) is None
    assert eval_check(r, {"type": "norm_contains", "value": "us-gaap:"}) is not None
    assert eval_check(r, {"type": "norm_not_contains", "value": "us-gaap:"}) is None

    reason = eval_check(r, {"type": "norm_not_contains", "value": "FORM 10-K"})
    assert reason is not None and "1x" in reason, reason

    # these judge normalized_text alone — an empty items list must not make
    # them vacuous, which is exactly why they can go red before segmentation
    empty = {"normalized_text": "", "items": []}
    assert eval_check(empty, {"type": "norm_contains", "value": "anything"}) is not None
    # a newline where a space belongs is a failure, not a match
    wrapped = {"normalized_text": "Microsoft was\nfounded in 1975.", "items": []}
    assert eval_check(wrapped, {"type": "norm_contains",
                                "value": "Microsoft was founded in 1975"}) is not None


def test_warning_present():
    r = {"normalized_text": "", "items": [],
         "warnings": [{"code": "toc_manifest_mismatch", "message": "lists ['8']"}]}
    assert eval_check(r, {"type": "warning_present", "code": "toc_manifest_mismatch"}) is None
    reason = eval_check(r, {"type": "warning_present", "code": "last_item_dominates"})
    assert reason is not None and "toc_manifest_mismatch" in reason, reason
    # a validator that never fires must not pass silently
    assert eval_check({"normalized_text": "", "items": []},
                      {"type": "warning_present", "code": "x"}) is not None

    # "item" narrows the match: same code, wrong item, must still fail — this
    # is what let a fingerprint warning on item 8 satisfy a check meant for 1A
    r2 = {"normalized_text": "", "items": [],
          "warnings": [{"code": "keyword_fingerprint", "item": "8", "message": "m"}]}
    reason = eval_check(r2, {"type": "warning_present", "code": "keyword_fingerprint", "item": "1A"})
    assert reason is not None, reason
    assert eval_check(r2, {"type": "warning_present", "code": "keyword_fingerprint", "item": "8"}) is None
    # no "item" key on the check: today's behaviour, any item matches
    assert eval_check(r2, {"type": "warning_present", "code": "keyword_fingerprint"}) is None


def test_warning_absent():
    r = {"normalized_text": "", "items": [],
         "warnings": [{"code": "form_type_disagreement", "message": "10-K405 vs 10-K"}]}
    reason = eval_check(r, {"type": "warning_absent", "code": "form_type_disagreement"})
    assert reason is not None and "10-K405" in reason, reason
    assert eval_check(r, {"type": "warning_absent", "code": "lenient_match"}) is None

    # absent/empty warnings must not blow up — a clean run is the common case
    assert eval_check({"normalized_text": "", "items": [], "warnings": []},
                      {"type": "warning_absent", "code": "x"}) is None
    assert eval_check({"normalized_text": "", "items": []},
                      {"type": "warning_absent", "code": "x"}) is None

    # "item" narrows the match, mirroring warning_present
    r2 = {"normalized_text": "", "items": [],
          "warnings": [{"code": "keyword_fingerprint", "item": "8", "message": "m"}]}
    assert eval_check(r2, {"type": "warning_absent", "code": "keyword_fingerprint",
                           "item": "1A"}) is None
    reason = eval_check(r2, {"type": "warning_absent", "code": "keyword_fingerprint", "item": "8"})
    assert reason is not None, reason


def test_ibr_spans_are_checked():
    """ADR-011: incorporated_by_reference carries pointer-text offsets, so the
    structural checks must cover it. Before ADR-011 both checks iterated the
    extracted list only, which is what let a misclassified IBR item disown
    4,805 chars of GE 1994 with nothing anywhere registering it."""
    text = "x" * 100
    # an IBR span overlapping the extracted item that follows it
    r = {"normalized_text": text, "items": [
        {"item": "6", "status": "incorporated_by_reference", "start": 0,
         "end": 60, "confidence": 0.85},
        {"item": "7", "status": "extracted", "start": 40, "end": 90,
         "confidence": 0.95},
    ]}
    reason = eval_check(r, {"type": "no_overlap_ordered"})
    assert reason is not None and "6" in reason and "7" in reason, reason

    # and offsets outside the text must be caught on an IBR item too
    r2 = {"normalized_text": text, "items": [
        {"item": "6", "status": "incorporated_by_reference", "start": 0,
         "end": 400, "confidence": 0.85}]}
    assert eval_check(r2, {"type": "verbatim"}) is not None

    # null-offset statuses stay exempt — they have no span to check
    r3 = {"normalized_text": text, "items": [
        item("6", status="omitted"), item("7", status="missing")]}
    assert eval_check(r3, {"type": "no_overlap_ordered"}) is None
    assert eval_check(r3, {"type": "verbatim"}) is None

    # content checks reach IBR text: the pointer sentence is real, inspectable
    # evidence, and refusing to anchor it is what deleted coverage from
    # textron-2001-content in the first place
    r4 = {"normalized_text": "Item 6. See the proxy statement, page 61.",
          "items": [{"item": "6", "status": "incorporated_by_reference",
                     "start": 0, "end": 40, "confidence": 0.85}]}
    assert eval_check(r4, {"type": "text_contains", "item": "6",
                           "value": "proxy statement"}) is None
    assert eval_check(r4, {"type": "min_chars", "item": "6", "value": 10}) is None
    assert eval_check(r4, {"type": "text_not_contains", "item": "6",
                           "value": "proxy statement"}) is not None


def test_checks_that_had_never_gone_red():
    """The G1 audit (ADR-010 consequences) named four checks that were
    structurally incapable of failing: `no_overlap_ordered`, `verbatim`,
    `known_items_only` and the layer-8 `boundary_hygiene`. A check no case can
    turn red is decoration — it makes a suite look stronger than it is, which
    is the specific complaint. The first three are pure functions of a result
    dict, so they are provable HERE, on hand-built results, without waiting for
    a fixture whose segmentation happens to break. (`boundary_hygiene` is a
    validator, not a check; its positive case lives in validate._demo, and
    ADR-016 records why a real filing cannot fire it.)"""
    text = "Item 1. Business\n" + "x" * 200

    # known_items_only: a non-canonical code...
    r = {"normalized_text": text, "items": [item("1"), item("405")]}
    assert eval_check(r, {"type": "known_items_only"}) is not None
    # ...and a status outside the contract's four
    r2 = {"normalized_text": text, "items": [
        {"item": "1", "status": "partially_extracted", "start": 0, "end": 10}]}
    assert eval_check(r2, {"type": "known_items_only"}) is not None
    r3 = {"normalized_text": text, "items": [item("1"), item("9A"),
                                             item("16", status="omitted")]}
    assert eval_check(r3, {"type": "known_items_only"}) is None

    # no_overlap_ordered: overlap, and plain disorder
    over = {"normalized_text": text, "items": [
        item("1", start=0, end=100), item("2", start=50, end=150)]}
    assert eval_check(over, {"type": "no_overlap_ordered"}) is not None
    disorder = {"normalized_text": text, "items": [
        item("1", start=100, end=150), item("2", start=0, end=50)]}
    assert eval_check(disorder, {"type": "no_overlap_ordered"}) is not None

    # verbatim: out-of-range offsets...
    oob = {"normalized_text": text, "items": [item("1", start=0, end=99999)]}
    assert eval_check(oob, {"type": "verbatim"}) is not None
    assert eval_check({"normalized_text": text,
                       "items": [item("1", start=10, end=5)]},
                      {"type": "verbatim"}) is not None
    # ...and the half that did not exist before ADR-016: offsets in range but
    # pointing somewhere the item's own heading_text is not
    wrong = {"normalized_text": text, "items": [
        {"item": "1", "status": "extracted", "start": 30, "end": 120,
         "heading_text": "Item 1. Business", "confidence": 0.95}]}
    reason = eval_check(wrong, {"type": "verbatim"})
    assert reason is not None and "heading_text" in reason, reason
    right = {"normalized_text": text, "items": [
        {"item": "1", "status": "extracted", "start": 0, "end": 120,
         "heading_text": "Item 1. Business", "confidence": 0.95}]}
    assert eval_check(right, {"type": "verbatim"}) is None
    # an item without heading_text is exempt, not silently passed by accident
    assert eval_check({"normalized_text": text,
                       "items": [item("1", start=30, end=120)]},
                      {"type": "verbatim"}) is None


def test_item_field():
    """title/part ship on every item and the inspector renders them, but no
    check read either until the pre-B audit found every pre-2003 filing
    labelled with a post-2003 title and part."""
    r = {"normalized_text": "x" * 50, "items": [
        {"item": "14", "part": "IV", "title": "Exhibits", "status": "extracted",
         "start": 0, "end": 50, "confidence": 0.95}]}
    assert eval_check(r, {"type": "item_field", "item": "14",
                          "field": "part", "value": "IV"}) is None
    reason = eval_check(r, {"type": "item_field", "item": "14",
                            "field": "part", "value": "III"})
    assert reason is not None and "IV" in reason, reason
    # a field the item does not carry is a failure, not a crash
    assert eval_check(r, {"type": "item_field", "item": "14",
                          "field": "nope", "value": "x"}) is not None
    assert eval_check(r, {"type": "item_field", "item": "9",
                          "field": "part", "value": "II"}) is not None


def test_confidence():
    r = {"normalized_text": "x" * 100, "items": [
        item("1", start=0, end=100, confidence=0.95),
        item("7", status="incorporated_by_reference", confidence=0.85),
    ]}
    assert eval_check(r, {"type": "confidence", "item": "1", "value": 0.95}) is None
    assert eval_check(r, {"type": "confidence", "item": "1", "value": 0.75}) is not None
    # bands, so a case can pin "must not be confident" without pinning a constant
    assert eval_check(r, {"type": "confidence", "item": "1", "min": 0.9}) is None
    assert eval_check(r, {"type": "confidence", "item": "1", "max": 0.9}) is not None
    # non-extracted statuses carry confidence too (contract: how sure are we
    # it is really absent) — the check must not silently skip them
    assert eval_check(r, {"type": "confidence", "item": "7", "value": 0.85}) is None

    # missing item, and present-but-unscored item, are failures not crashes
    assert eval_check(r, {"type": "confidence", "item": "9", "value": 0.5}) is not None
    r2 = {"normalized_text": "", "items": [{"item": "1", "status": "missing",
                                            "start": None, "end": None}]}
    reason = eval_check(r2, {"type": "confidence", "item": "1", "value": 0.55})
    assert reason is not None and "no confidence" in reason, reason

    # no "item": the bound applies to every item (ADR-027's ambiguity cap is
    # stated this way). One item over the cap is enough to fail, and the
    # message names it.
    assert eval_check(r, {"type": "confidence", "max": 0.95}) is None
    reason = eval_check(r, {"type": "confidence", "max": 0.75})
    assert reason is not None and "item 1 confidence 0.95 > 0.75" in reason, reason
    assert eval_check(r, {"type": "confidence", "min": 0.85}) is None


def _envelope(**over):
    env = {"normalized_text": "Item 1. Business\nx", "doc_status": "success",
           "warnings": [],
           "meta": {"extractor_version": "t", "input_sha256": "s", "format_era": "html",
                    "document_selected": "d", "taxonomy_era": "modern", "toc_manifest": []},
           "trace": [], "timings": {"total_ms": 1}, "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0},
           "items": [{"item": "1", "part": "I", "title": "Business", "heading_text": "Item 1. Business",
                      "start": 0, "end": 18, "status": "extracted", "confidence": 0.95,
                      "method": "heading_strict", "evidence": {}}]}
    env.update(over)
    return env


def test_envelope_shape():
    chk = {"type": "envelope_shape"}
    assert eval_check(_envelope(), chk) is None
    # every contract-mandated top-level field, individually (SD-2: none of
    # these had any enforcement before)
    for k in ("meta", "trace", "timings", "cost", "warnings", "items"):
        e = _envelope(); del e[k]
        assert eval_check(e, chk) is not None, k
    assert eval_check(_envelope(extra_key=1), chk) is not None
    # item-level mandatory fields and the normative method enum (SD-1)
    for k in ("heading_text", "evidence", "method", "confidence", "part", "title"):
        e = _envelope(); del e["items"][0][k]
        assert eval_check(e, chk) is not None, k
    e = _envelope(); e["items"][0]["method"] = "llm_magic"
    assert "method" in eval_check(e, chk)
    e = _envelope(); e["items"][0]["method"] = "heading_lenient"   # in the enum
    assert eval_check(e, chk) is None
    # contract rules that are shape-checkable: success => no warnings;
    # refusal => no items; refusal envelopes need not carry taxonomy_era /
    # toc_manifest (SD-6), non-refusal envelopes must
    e = _envelope(warnings=[{"code": "x", "item": None, "message": "m"}])
    assert eval_check(e, chk) is not None
    e = _envelope(doc_status="success_with_warning",
                  warnings=[{"code": "x", "item": None, "message": "m"}])
    assert eval_check(e, chk) is None
    e = _envelope(doc_status="unsupported")
    assert eval_check(e, chk) is not None          # refusal carrying items
    e = _envelope(doc_status="unsupported", items=[])
    del e["meta"]["taxonomy_era"]; del e["meta"]["toc_manifest"]
    assert eval_check(e, chk) is None
    e = _envelope(); del e["meta"]["taxonomy_era"]
    assert "taxonomy_era" in eval_check(e, chk)
    e = _envelope(doc_status="bogus")
    assert eval_check(e, chk) is not None
    # the optional ADR-026 key is the ONE undeclared-by-default key allowed
    assert eval_check(_envelope(boilerplate=[]), chk) is None


def test_boilerplate_checks():
    """The two ADR-026 check types that are pure functions of a result dict.

    (`offsets_invariant_under_exclusion` calls extract_items, so it is out of
    scope here for the same reason `deterministic` is — see the module
    docstring.) The `min` default is the part worth pinning: a selector with no
    bound asserts PRESENCE, so a typo in `value` fails loudly, but a selector
    carrying only `max` is asserting absence and must not also demand one. The
    first draft got that backwards and turned every near-miss check red.
    """
    text = "Table of Contents\nbody prose here\n12\nmore prose"
    #       0..17            18..33          34..36  37..
    run = lambda s, e, k: {"start": s, "end": e, "kind": k}  # noqa: E731
    r = {"normalized_text": text, "items": [],
         "boilerplate": [run(0, 18, "running_head"), run(34, 37, "page_number")]}
    off = {"normalized_text": text, "items": []}

    # enabled, both directions
    assert eval_check(r, {"type": "boilerplate", "enabled": True}) is None
    assert eval_check(off, {"type": "boilerplate", "enabled": True}) is not None
    assert eval_check(off, {"type": "boilerplate", "enabled": False}) is None
    assert eval_check(r, {"type": "boilerplate", "enabled": False}) is not None
    # a check that selects but the envelope has no key at all
    assert eval_check(off, {"type": "boilerplate", "value": "x", "max": 0}) is not None

    # value / kind selection, and the min default
    assert eval_check(r, {"type": "boilerplate", "value": "Table of Contents"}) is None
    assert eval_check(r, {"type": "boilerplate", "value": "Table of Contnts"}) is not None
    assert eval_check(r, {"type": "boilerplate", "kind": "page_number"}) is None
    assert eval_check(r, {"type": "boilerplate", "kind": "edgar_chrome"}) is not None
    # ...but `max` alone asserts absence and must NOT imply min 1
    assert eval_check(r, {"type": "boilerplate", "kind": "edgar_chrome", "max": 0}) is None
    assert eval_check(r, {"type": "boilerplate", "value": "body prose here", "max": 0}) is None
    assert eval_check(r, {"type": "boilerplate", "value": "Table of Contents",
                          "max": 0}) is not None
    assert eval_check(r, {"type": "boilerplate", "min": 2, "max": 2}) is None
    assert eval_check(r, {"type": "boilerplate", "min": 3}) is not None

    # spans_sane: the off-by-one guard. Clean first...
    assert eval_check(r, {"type": "boilerplate_spans_sane"}) is None
    # ...then each way it can be wrong, one at a time
    for bad, why in [
        ([run(0, 99999, "running_head")], "outside"),
        ([run(1, 18, "running_head")], "line start"),
        ([run(0, 17, "running_head")], "line end"),
        ([run(0, 34, "running_head")], "more than one line"),
        ([run(34, 37, "page_number"), run(0, 18, "running_head")], "out of order"),
    ]:
        reason = eval_check({"normalized_text": text, "items": [], "boilerplate": bad},
                            {"type": "boilerplate_spans_sane"})
        assert reason is not None and why in reason, (why, reason)
    assert eval_check(off, {"type": "boilerplate_spans_sane"}) is not None

    # boilerplate_stripped (PR #25 R2). The span/removal equality is the branch
    # that catches a no-op strip_chrome, and it catches over-removal too.
    ok = {"type": "boilerplate_stripped", "removed_chars": 21,
          "not_contains": ["Table of Contents"]}
    assert eval_check(r, ok) is None, eval_check(r, ok)
    assert eval_check(r, {"type": "boilerplate_stripped", "removed_chars": 99}) is not None
    assert eval_check(r, {"type": "boilerplate_stripped",
                          "not_contains": ["body prose here"]}) is not None
    assert eval_check(off, {"type": "boilerplate_stripped"}) is not None
    # a span that claims more than strip_chrome removes -> the equality fires.
    # 0..18 and 34..37 are 18 + 3 = 21 chars; widening one span's END past a
    # line boundary is caught by spans_sane, so the honest way to break the
    # equality here is a duplicate span, which strip_chrome skips as already
    # consumed while the sum still counts it twice.
    dup = {"normalized_text": text, "items": [],
           "boilerplate": [run(0, 18, "running_head"), run(0, 18, "running_head"),
                           run(34, 37, "page_number")]}
    reason = eval_check(dup, {"type": "boilerplate_stripped"})
    assert reason is not None and "spans total" in reason, reason



def test_table_checks():
    # ADR-029 vocabulary on a synthetic envelope: text "a b\nc d" is one
    # 2x2 table; cells are slices, the second row's first cell carries colspan 2
    text = "a b\nc d"
    tab = {"start": 0, "end": 7, "header": 1,
           "rows": [[[0, 1], [2, 3]], [[4, 5, 2], [6, 7]]]}
    r = {"normalized_text": text, "doc_status": "success", "warnings": [], "items": [],
         "meta": {"extractor_version": "x", "input_sha256": "x", "format_era": "html",
                  "document_selected": "x", "taxonomy_era": "modern", "toc_manifest": []},
         "trace": [], "timings": {"total_ms": 0}, "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0},
         "tables": [tab]}
    good = {"type": "table", "anchor": "a b", "header": 1,
            "rows": [["a", "b", ""], ["c", "", "d"]]}   # rows pad to the table width
    assert eval_check(r, good) is None, eval_check(r, good)
    assert eval_check(r, {"type": "envelope_shape"}) is None, eval_check(r, {"type": "envelope_shape"})
    assert eval_check(r, {"type": "tables_sane", "min": 1, "max": 1}) is None
    # content: one wrong cell, wrong header count, a row too many, wrong anchor
    for bad, why in [
        ({**good, "rows": [["a", "b", ""], ["c", "", "X"]]}, "first mismatch at (1, 2)"),
        ({**good, "header": 0}, "header rows 1 != 0"),
        ({**good, "rows": [["a", "b", ""], ["c", "", "d"], ["e"]]}, "grid differs"),
        ({**good, "anchor": "zzz"}, "0 table(s) contain it"),
        ({**good, "index": 1}, "wanted #1"),
    ]:
        reason = eval_check(r, bad)
        assert reason is not None and why in reason, (why, reason)
    # and the fidelity fractions the metric reads: 6 of 6 cells / 2 of 2 rows
    # on the good label, 5 of 6 / 1 of 2 on the one-wrong-cell label, 0 on a
    # table that cannot be located
    from src.sec10k.eval_adapter import table_fidelity
    assert table_fidelity(r, good)["cells"] == (6, 6) and table_fidelity(r, good)["rows"] == (2, 2)
    f = table_fidelity(r, {**good, "rows": [["a", "b", ""], ["c", "", "X"]]})
    assert f["cells"] == (5, 6) and f["rows"] == (1, 2), f
    f = table_fidelity(r, {**good, "anchor": "zzz"})
    assert f["cells"] == (0, 6) and f["rows"] == (0, 2), f
    # markdown: the colspan pads, the header row is the first row
    md = {"type": "table_markdown", "anchor": "a b", "value": "| a | b |  |\n|---|---|---|\n| c |  | d |"}
    assert eval_check(r, md) is None, eval_check(r, md)
    assert eval_check(r, {**md, "value": "nope"}) is not None
    # shape: a string, a record with a cell outside the text, a colspan of 1
    # written out, a cell outside its table, a loose slice -- all red.
    # PR #34 R2: the contract says `envelope_shape` refuses any other shape,
    # and names document order and cell-in-span, so those two are red under
    # BOTH check types, not only under tables_sane
    t2 = {"start": 4, "end": 7, "header": 0, "rows": [[[4, 5], [6, 7]]]}
    for tables, via in [("10-Q", "envelope_shape"), ("10-Q", "tables_sane"),
                        ([{**tab, "rows": [[[0, 99]]]}], "envelope_shape"),
                        ([{**tab, "rows": [[[0, 1, 1]]]}], "envelope_shape"),
                        ([{**tab, "end": 3, "rows": [[[0, 1]], [[4, 5]]]}], "tables_sane"),
                        ([{**tab, "end": 3, "rows": [[[0, 1]], [[4, 5]]]}], "envelope_shape"),
                        ([t2, tab], "tables_sane"),
                        ([t2, tab], "envelope_shape"),
                        ([{**tab, "rows": [[[0, 2]]]}], "tables_sane")]:
        assert eval_check({**r, "tables": tables}, {"type": via}) is not None, (tables, via)
    # and the in-order pair is still in shape
    assert eval_check({**r, "tables": [tab, t2]}, {"type": "envelope_shape"}) is None
    # a missing key is the default (no flag): every table check says so
    no = {k: v for k, v in r.items() if k != "tables"}
    assert eval_check(no, {"type": "envelope_shape"}) is None
    for chk in (good, md, {"type": "tables_sane"}):
        assert eval_check(no, chk) is not None


TESTS = [
    test_item_field,
    test_ibr_spans_are_checked,
    test_checks_that_had_never_gone_red,
    test_confidence,
    test_envelope_shape,
    test_doc_status,
    test_norm_checks,
    test_warning_absent,
    test_warning_present,
    test_max_chars,
    test_text_checks_non_extracted,
    test_min_chars_null_offsets,
    test_expected_set_complete,
    test_only_items,
    test_item_absent_any_status,
    test_no_empty_success,
    test_boilerplate_checks,
    test_table_checks,
]


def main():
    for t in TESTS:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"[eval_adapter self-check] {len(TESTS)}/{len(TESTS)} passed")


if __name__ == "__main__":
    main()
