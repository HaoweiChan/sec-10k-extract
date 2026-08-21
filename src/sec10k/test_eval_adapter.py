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



TESTS = [
    test_item_field,
    test_ibr_spans_are_checked,
    test_checks_that_had_never_gone_red,
    test_confidence,
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
]


def main():
    for t in TESTS:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"[eval_adapter self-check] {len(TESTS)}/{len(TESTS)} passed")


if __name__ == "__main__":
    main()
