"""Shapes an extractor envelope for the inspector UI. Pure — imports nothing
from fastapi, so CI's dependency-free unit job can test it.

Why a view layer exists at all: the contract says item text is readable ONLY
through offsets into `normalized_text`, deliberately, so no second copy can
drift from them (INV-S2). A browser cannot hold a 12 MB normalized_text for
every request, so the view slices each item's text from those same offsets at
response time. Derived per response, never stored, never sent alongside the
full text — the invariant survives and the payload stays sane.

Self-check: python3 -m src.sec10k.web.view
"""
from collections import Counter

# JPM 2024's Item 15 span is 1,010,422 chars. Sending that to a browser per
# item is not inspection, it is a download. Truncate for display and say so —
# the full length always travels as `chars`, so a truncated pane can never be
# mistaken for a short item.
DISPLAY_MAX = 40_000
TRACE_MAX = 400  # rejected-candidate lists on a bad filing can run to thousands


def build_view(result, display_max=DISPLAY_MAX):
    """Envelope -> UI payload. Never raises on a well-formed envelope."""
    text = result.get("normalized_text") or ""
    items = []
    for i in result.get("items", []):
        s, e = i.get("start"), i.get("end")
        has_span = s is not None and e is not None
        body = text[s:e] if has_span else ""
        items.append({
            "item": i.get("item"), "part": i.get("part"), "title": i.get("title"),
            "status": i.get("status"), "confidence": i.get("confidence"),
            "method": i.get("method"), "heading_text": i.get("heading_text"),
            "start": s, "end": e,
            "chars": len(body) if has_span else None,
            "text": body[:display_max],
            "truncated": len(body) > display_max,
            "evidence": i.get("evidence") or {},
        })
    return {
        "doc_status": result.get("doc_status"),
        "warnings": result.get("warnings", []),
        "meta": _jsonable(result.get("meta", {})),
        "timings": result.get("timings", {}),
        "cost": result.get("cost", {}),
        "trace": _scrub(_jsonable(result.get("trace", []))[:TRACE_MAX]),
        "items": items,
        "norm_chars": len(text),
        "counts": _counts(result.get("items", [])),
    }


def _counts(items):
    return dict(Counter(i.get("status") for i in items))


def _scrub(trace):
    """The acquisition layer records the absolute path it read. That is useful
    in a local run and an information leak on a deployed instance — it hands a
    stranger the server's directory layout, and for an upload it is a tempdir
    name that means nothing to them anyway. Keep the basename."""
    out = []
    for entry in trace:
        if isinstance(entry, dict) and "path" in entry:
            entry = dict(entry, path=str(entry["path"]).rsplit("/", 1)[-1])
        out.append(entry)
    return out


def _jsonable(o):
    """meta.period_end is a datetime.date and json.dumps refuses it. FastAPI's
    encoder would coerce it, but the eval/CLI paths have no encoder, so the
    view must not depend on one."""
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    return str(o)


def _demo():
    import json
    from datetime import date
    text = "Item 1. Business\n" + "x" * 100 + "Item 7. MD&A\nshort"
    cut = text.index("Item 7.")
    env = {
        "normalized_text": text,
        "doc_status": "success_with_warning",
        "warnings": [{"code": "unattributed_content", "item": None, "message": "m"}],
        "meta": {"period_end": date(2024, 12, 31), "format_era": "ixbrl"},
        "trace": [{"layer": "acquisition", "path": "/srv/app/evals/fixtures/x/filing.htm"},
                  {"layer": "candidates", "found": 40}],
        "items": [
            {"item": "1", "status": "extracted", "start": 0, "end": cut,
             "confidence": 0.95, "method": "heading_strict", "heading_text": "Item 1. Business"},
            {"item": "7", "status": "extracted", "start": cut, "end": len(text),
             "confidence": 0.95, "method": "heading_strict"},
            {"item": "9C", "status": "omitted", "start": None, "end": None,
             "confidence": 0.8, "method": "status_keyword"},
        ],
    }
    v = build_view(env, display_max=20)

    # text comes from the offsets, so it cannot disagree with them
    assert v["items"][0]["text"] == text[0:cut][:20]
    assert v["items"][0]["chars"] == cut and v["items"][0]["truncated"] is True
    # a null-offset status has no span: empty text, null chars, never truncated
    assert v["items"][2]["text"] == "" and v["items"][2]["chars"] is None
    assert v["items"][2]["truncated"] is False
    # short item is not marked truncated
    assert v["items"][1]["truncated"] is (len(text) - cut > 20)
    assert v["counts"] == {"extracted": 2, "omitted": 1}
    # the trace must not hand a stranger the server's directory layout
    assert v["trace"][0]["path"] == "filing.htm"
    assert v["trace"][1] == {"layer": "candidates", "found": 40}
    # the whole payload must survive stdlib json — date included
    json.dumps(v)
    assert v["meta"]["period_end"] == "2024-12-31"
    # an empty/refused envelope must not blow up
    empty = build_view({"doc_status": "failed", "normalized_text": "", "items": []})
    assert empty["items"] == [] and empty["counts"] == {}
    json.dumps(empty)
    print("[view self-check] ok")


if __name__ == "__main__":
    _demo()
