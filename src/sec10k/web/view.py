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
import hashlib
from collections import Counter

from src.sec10k.boilerplate import strip_chrome
from src.sec10k.markdown import to_markdown

# JPM 2024's Item 15 span is 1,010,422 chars. Sending that to a browser per
# item is not inspection, it is a download. Truncate for display and say so —
# the full length always travels as `chars`, so a truncated pane can never be
# mistaken for a short item.
DISPLAY_MAX = 40_000
TRACE_MAX = 400  # rejected-candidate lists on a bad filing can run to thousands


def build_view(result, display_max=DISPLAY_MAX):
    """Envelope -> UI payload. Never raises on a well-formed envelope.

    S8: the envelope carries a `boilerplate` key exactly when the caller
    passed `exclude_boilerplate=True` (ADR-026), so its presence — not a
    second parameter — is what switches the pane to the stripped view. The
    stripped view is ADR-026 s.d's definition and nothing more:
    `strip_chrome(normalized_text, boilerplate, start, end)` per item,
    derived here, never stored. `start`, `end` and `chars` keep reporting the
    SPAN, identical with the flag on and off — INV-S2 offsets do not move
    because a reader chose to hide the furniture between them.

    The stripped string is a SECOND field, `display_text`, and `text` stays
    the verbatim slice in both modes. PR #27 R1: `text` has two consumers,
    not one. Besides the pane it is the body-agreement oracle `findAnchor`
    uses to tell an item's real heading from its table-of-contents entry —
    against the ORIGINAL filing, which still contains the chrome. Handing
    that consumer the stripped string cost six items their source anchor.
    Only the render point may see a string that is not `normalized_text
    [start:end]`, so only the render point gets one; `display_text` is
    absent whenever it would be identical to `text`.

    S9 (ADR-032): the envelope carries a `blocks` key exactly when the caller
    passed `blocks=True`, and then `display_text` is the item's derived
    Markdown — `markdown.to_markdown` over the blocks clipped to the item's
    span, rendered from the first `display_max` characters of the span so
    `truncated` keeps meaning what it meant — with any ADR-026 chrome runs
    omitted when exclusion was asked for too. `text` stays the verbatim
    slice for the same reason as above; `markdown` on the payload tells the
    pane to render rather than to print.
    """
    text = result.get("normalized_text") or ""
    spans = result.get("boilerplate")     # present iff exclusion was asked for
    blocks = result.get("blocks")         # present iff the Markdown view was asked for
    tables = result.get("tables") or []
    items = []
    bp_applied = False
    for i in result.get("items", []):
        s, e = i.get("start"), i.get("end")
        has_span = s is not None and e is not None
        raw = text[s:e] if has_span else ""
        # ADR-026 s.d's own definition of "exclusion removed something from
        # this item", computed whichever view is rendered. In the plain path it
        # IS the body, so it costs nothing; in `blocks` mode it is the one extra
        # pass that keeps `boilerplate_applied` meaning the same thing in both.
        stripped = (strip_chrome(text, spans, s, e)
                    if has_span and spans is not None else raw)
        if stripped != raw:
            bp_applied = True
        if has_span and blocks is not None:
            shown_end = min(e, s + display_max)
            body = to_markdown(text, blocks, tables, s, shown_end, omit=spans or ())
            truncated = shown_end < e
        else:
            body = stripped
            truncated = len(body) > display_max
            body = body[:display_max]
        # ADR-042 §f: the two evidence shapes whose CONTENT is not in the
        # item's own span. `text` stays the verbatim slice — the anchor oracle
        # above depends on that and PR #27 R1 is the record of what happens
        # when it doesn't — so the resolved regions are appended to the RENDER
        # string only, which is exactly what `display_text` is for. Without
        # this the inspector shows Intel FY2025's item 7 as a 226-char index
        # entry and the 119,881 chars it points at are reachable only by
        # reading the evidence offsets by hand.
        ev = i.get("evidence") or {}
        elsewhere = [(f"pages {r['pages']}", r["start"], r["end"])
                     for r in ev.get("cross_reference") or []]
        xref_composite = bool(ev.get("cross_reference_entry") and ev.get("cross_reference"))
        pointer = ev.get("cross_reference_pointer") or {}
        if pointer:
            elsewhere.append(("verified incorporation pointer", pointer["start"], pointer["end"]))
        elsewhere += [("verified alternative evidence", r["start"], r["end"])
                      for r in ev.get("alternative_regions") or []]
        if ev.get("collective_reference"):
            cr = ev["collective_reference"]
            elsewhere.append(("the pointer this Part states once, for every "
                              "item it names", cr["start"], cr["end"]))
        source_anchor = None
        if xref_composite:
            label, a, b = elsewhere[0]
            lines = [line.strip() for line in text[a:b].splitlines() if line.strip()]
            heading = next((line for line in lines
                            if line.casefold() != "table of contents"), "")
            anchor_start = text.find(heading, a, b) if heading else -1
            if anchor_start >= 0:
                source_anchor = {"label": label, "heading": heading[:240],
                                 "text": text[anchor_start:min(b, anchor_start + 512)]}
        if elsewhere:
            # The index row is still published as `text` and its exact offsets
            # remain primary provenance. It is not the answer, though: these
            # verified page ranges are separate regions, never one invented
            # contiguous span.
            out = [] if xref_composite else ([body] if body else [])
            for label, a, b in elsewhere:
                lead = "\n\n" if out else ""
                kind = f"verified cross-reference evidence · {label}" if xref_composite else label
                if blocks is not None:
                    region = to_markdown(text, blocks, tables, a, b, omit=spans or ())
                else:
                    region = strip_chrome(text, spans, a, b) if spans is not None else text[a:b]
                if spans is not None and strip_chrome(text, spans, a, b) != text[a:b]:
                    bp_applied = True
                out.append(f"{lead}———— {kind} · chars {a:,}–{b:,} ————\n\n" + region)
            joined = "".join(out)
            truncated = len(joined) > display_max
            body = joined[:display_max]
        external = ev.get("external_regions") or []
        if external:
            notes = []
            for region in external:
                doc = region["document"]
                identity = doc.get("url") or doc.get("sgml_block")
                notes.append(f"{doc.get('type')} {doc.get('filename') or 'embedded document'}"
                             f" · document chars {region['start']:,}–{region['end']:,}"
                             f" · {identity}")
            body = (body + "\n\n———— verified evidence in another same-accession "
                    "document (offsets are not /normalized_text) ————\n\n"
                    + "\n".join(notes))[:display_max]

        item = {
            "item": i.get("item"), "part": i.get("part"), "title": i.get("title"),
            "status": i.get("status"), "confidence": i.get("confidence"),
            "method": i.get("method"), "heading_text": i.get("heading_text"),
            "review_required": i.get("review_required", False),
            "start": s, "end": e,
            "chars": len(raw) if has_span else None,
            # Primary offsets always describe this short row/span. Cross-reference
            # evidence is a separate annotation and must never be presented as
            # primary character coverage.
            "primary_chars": len(raw) if has_span else None,
            "index_entry_chars": ((ev.get("cross_reference_entry") or {}).get("end", 0)
                                  - (ev.get("cross_reference_entry") or {}).get("start", 0)) or None,
            "cross_reference_chars": sum(r["end"] - r["start"]
                                         for r in ev.get("cross_reference") or []),
            "cross_reference_pointer_chars": (pointer.get("end", 0) - pointer.get("start", 0)) or None,
            "text": raw[:display_max],
            "truncated": truncated,
            "evidence": i.get("evidence") or {},
        }
        if body != raw[:display_max]:
            item["display_text"] = body
        if xref_composite:
            item["display_kind"] = "verified_cross_reference"
            item["composite_regions"] = len(elsewhere)
        if source_anchor:
            item["source_anchor"] = source_anchor
        if elsewhere:
            # so the pane can say WHY the text it shows is longer than `chars`
            item["elsewhere"] = [{"label": l, "start": a, "end": b}
                                 for l, a, b in elsewhere]
        items.append(item)
    starts = [i.get("start") for i in result.get("items", [])
              if i.get("start") is not None]
    front_end = min(starts, default=len(text))
    front = text[:front_end]
    return {
        "doc_status": result.get("doc_status"),
        "warnings": result.get("warnings", []),
        "meta": _jsonable(result.get("meta", {})),
        "timings": result.get("timings", {}),
        "cost": result.get("cost", {}),
        "trace": _scrub(_jsonable(result.get("trace", []))[:TRACE_MAX]),
        "items": items,
        "front_matter": {
            "text": front[:display_max],
            "chars": len(front),
            "truncated": len(front) > display_max,
        },
        "norm_chars": len(text),
        # D12: the sha a consumer verifies the /api/normalized/{token}
        # download against before trusting the offsets against it. Of the
        # NORMALIZED text — `meta.input_sha256` already pins the raw file,
        # and those two shas are exactly the distinction the recipe exists
        # to teach. Derived here, like every other field: no second copy.
        "norm_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "counts": _counts(result.get("items", [])),
        # so the pane can SAY it is hiding text. `chars` still reports the
        # full span, so without this the two numbers silently disagree.
        "boilerplate_excluded": spans is not None,
        # PR #46 R1: ASKED FOR is not APPLIED. `boilerplate_excluded` is True
        # whenever the caller passed the flag — including aapl-2025, where the
        # detector returns [] and all 23 items come back byte-identical to the
        # un-flagged run, and aapl-2026-10q, where there are no items at all.
        # Anything that ASSERTS the pane on screen differs (the D5 compare-pane
        # note) must key on this instead. `boilerplate_excluded` keeps its own
        # meaning for the consumers it already has (the S8 pane header, its pins).
        #
        # D5/S9 MERGE: this used to read `any("display_text" in i)`, which was
        # equivalent to "exclusion removed something" only while exclusion was
        # that field's only producer. S9 gave it a second one — in `blocks` mode
        # `display_text` is the derived Markdown — so the old expression is True
        # whenever Markdown is on, boilerplate or not, which is R1 again wearing
        # S9's clothes. It is now measured from the EXCLUSION itself (see
        # `bp_applied` in the loop), so it means the same thing in both modes.
        "boilerplate_applied": bp_applied,
        "markdown": blocks is not None,
        # D11 (ADR-036 §i): the doc-level routing record, passed through
        # verbatim and ONLY when the envelope carries it — same rule as
        # `boilerplate`/`blocks`. Absent means "escalation was not asked for",
        # which is a different answer from "asked for, trigger stayed quiet",
        # and the banner strip says which. Nothing here is derived: the record
        # is small, already JSON-shaped, and a second computation of it in the
        # view is a second place for it to disagree with the envelope.
        "routing": _jsonable(result["routing"]) if "routing" in result else None,
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
    assert v["front_matter"] == {"text": "", "chars": 0, "truncated": False}
    assert v["counts"] == {"extracted": 2, "omitted": 1}
    # D12: the sha binds a normalized-text download to THIS run, so it has
    # to be of the normalized text and of nothing else — not the raw file.
    assert v["norm_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert v["norm_chars"] == len(text)
    # the trace must not hand a stranger the server's directory layout
    assert v["trace"][0]["path"] == "filing.htm"
    assert v["trace"][1] == {"layer": "candidates", "found": 40}
    # the whole payload must survive stdlib json — date included
    json.dumps(v)
    assert v["meta"]["period_end"] == "2024-12-31"
    # an empty/refused envelope must not blow up
    empty = build_view({"doc_status": "failed", "normalized_text": "", "items": []})
    assert empty["items"] == [] and empty["counts"] == {}
    assert empty["front_matter"] == {"text": "", "chars": 0, "truncated": False}
    assert empty["norm_sha256"] == hashlib.sha256(b"").hexdigest()
    json.dumps(empty)

    # S8: the same envelope plus ADR-026's `boilerplate` key renders the
    # stripped view — and ONLY the shown text moves.
    head = "ACME 10-K\n"
    doc = head + "Item 1. Business\nreal prose\n" + head + "Item 7. MD&A\nmore prose\n"
    h2 = doc.index(head, 1)                               # second head starts item 7
    plain = {"normalized_text": doc, "items": [
        {"item": "1", "status": "extracted", "start": 0, "end": h2},
        {"item": "7", "status": "extracted", "start": h2, "end": len(doc)}]}
    # one head per item, so a strip that ignores the window takes the wrong one
    spans = [{"start": 0, "end": len(head), "kind": "running_head"},
             {"start": h2, "end": h2 + len(head), "kind": "running_head"}]
    off, on = build_view(plain), build_view(dict(plain, boilerplate=spans))
    assert off["boilerplate_excluded"] is False and on["boilerplate_excluded"] is True
    # PR #46 R1: applied, not merely asked for. The same envelope with an EMPTY
    # span list is the aapl-2025 shape — the flag was honoured, nothing was
    # found, so nothing on screen differs and nothing may claim it does.
    none_found = build_view(dict(plain, boilerplate=[]))
    assert none_found["boilerplate_excluded"] is True
    assert none_found["boilerplate_applied"] is False
    assert on["boilerplate_applied"] is True and off["boilerplate_applied"] is False
    # zero items: no pane, nothing to differ from (aapl-2026-10q, truncated-download)
    assert build_view({"normalized_text": "", "items": [],
                       "boilerplate": []})["boilerplate_applied"] is False
    # `text` is VERBATIM in both modes (PR #27 R1). It is not only what the
    # pane shows: findAnchor matches it against the ORIGINAL filing, which
    # still has the chrome in it, so handing that consumer a stripped string
    # cost six fixtures their source anchor.
    assert off["items"][0]["text"] == doc[:h2] == on["items"][0]["text"]
    assert "display_text" not in off["items"][0]         # flag off hides nothing
    assert on["items"][0]["display_text"] == "Item 1. Business\nreal prose\n"
    # windowed: item 7 loses its OWN head, not item 1's, and keeps its prose
    assert on["items"][1]["display_text"] == "Item 7. MD&A\nmore prose\n"
    for a, b in zip(off["items"], on["items"]):           # offsets never move
        assert (a["start"], a["end"], a["chars"]) == (b["start"], b["end"], b["chars"])
    assert on["items"][0]["chars"] == h2                  # the SPAN, not the shown text
    # flag on, nothing detected: exclusion was still asked for, and asked-for
    # with an empty answer must not fall back to the un-flagged path — but it
    # must not pay for a display_text identical to `text` either
    none = build_view(dict(plain, boilerplate=[]))
    assert none["boilerplate_excluded"] is True
    assert none["items"][0]["text"] == doc[:h2]
    assert "display_text" not in none["items"][0]
    # an item with no chrome inside its own span, on a run that HAS chrome
    # elsewhere, is the same case and must also stay lean
    one = build_view(dict(plain, boilerplate=spans[:1]))
    assert "display_text" in one["items"][0] and "display_text" not in one["items"][1]

    # S9: the same envelope plus ADR-032's `blocks` (+ `tables`) key renders
    # the item as Markdown — derived from the blocks clipped to the span,
    # `text` still the verbatim slice, offsets and chars untouched.
    from src.sec10k.normalize import normalize
    html = ("<html><body><p>ACME 10-K</p><p>Item 1. Business</p><p>real <b>prose</b></p>"
            "<table><tr><td>a</td><td>b</td></tr></table>"
            "<p>ACME 10-K</p><p>Item 7. MD&amp;A</p><p>more prose</p></body></html>")
    ntext, tabs, blks, _ = normalize(html, "html", blocks=True)
    i7 = ntext.index("Item 7.")
    env2 = {"normalized_text": ntext, "tables": tabs, "blocks": blks, "items": [
        {"item": "1", "status": "extracted", "start": ntext.index("Item 1."), "end": i7 - len("ACME 10-K\n\n")},
        {"item": "7", "status": "extracted", "start": i7, "end": len(ntext)}]}
    md = build_view(env2)
    assert md["markdown"] is True and off["markdown"] is False
    assert md["items"][0]["text"] == ntext[env2["items"][0]["start"]:env2["items"][0]["end"]]   # verbatim
    assert md["items"][0]["display_text"] == "Item 1. Business\n\nreal prose\n\n| a | b |\n|---|---|"
    # ...and absent when the Markdown IS the slice (nothing to escape, no structure)
    assert "display_text" not in md["items"][1] and md["items"][1]["text"] == "Item 7. MD&A\n\nmore prose"
    assert md["items"][0]["truncated"] is False
    # truncation renders the first display_max chars of the SPAN, not display_max chars of Markdown
    cut = build_view(env2, display_max=20)
    assert cut["items"][0]["truncated"] is True
    assert cut["items"][0].get("display_text", cut["items"][0]["text"]) == "Item 1. Business\n\nre"
    # with exclusion asked for as well, a chrome block is omitted from the view
    head2 = ntext.index("ACME 10-K", 1)
    both = build_view(dict(env2, boilerplate=[{"start": head2, "end": head2 + 9, "kind": "running_head"}]))
    assert "display_text" not in both["items"][1]     # the head sits before item 7's span
    assert both["items"][0]["display_text"].startswith("Item 1. Business") and both["boilerplate_excluded"] is True
    # a chrome block INSIDE the span is left out of the view; the span itself does not move
    item1_from0 = build_view(dict(env2, items=[dict(env2["items"][0], start=0)],
                                  boilerplate=[{"start": 0, "end": 9, "kind": "running_head"}]))
    assert item1_from0["items"][0]["start"] == 0
    assert item1_from0["items"][0]["display_text"] == "Item 1. Business\n\nreal prose\n\n| a | b |\n|---|---|"
    # D5/S9 MERGE: `boilerplate_applied` must survive S9 giving `display_text`
    # a second producer. `md` has display_text on item 1 (the derived Markdown)
    # and no exclusion at all, so the OLD `any("display_text" in i)` expression
    # would report True here — the PR #46 R1 defect in S9's clothes.
    assert md["boilerplate_applied"] is False
    # and it is still True when exclusion actually removes something, in EITHER
    # view: plain (`on`, above) and Markdown (`item1_from0`, head inside the span)
    assert item1_from0["boilerplate_applied"] is True
    # asked for, found nothing, Markdown on: still False
    assert both["boilerplate_excluded"] is True and both["boilerplate_applied"] is False
    json.dumps(md)

    # D11: the routing record rides through only when the envelope has one,
    # and the per-item tier provenance is already carried by `method` and
    # `evidence` — which the item whitelist above must not drop.
    assert off["routing"] is None and md["routing"] is None
    rec = {"trigger": {"fired": True, "codes": ["low_item_coverage"],
                       "items": ["1"], "message": "3%"},
           "tiers": [{"tier": "llm_localize", "model": "openai/gpt-5-mini",
                      "outcome": "unavailable", "error": "no key",
                      "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0}}],
           "resolved": [], "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0}}
    routed = build_view({**plain, "routing": rec,
                         "items": [dict(plain["items"][0], method="llm_localize",
                                        confidence=0.8, evidence={
                                            "deterministic": {"method": "heading_strict"}}),
                                   plain["items"][1]]})
    assert routed["routing"] == rec
    assert routed["items"][0]["method"] == "llm_localize"
    assert routed["items"][0]["evidence"]["deterministic"]["method"] == "heading_strict"
    json.dumps(routed)
    print("[view self-check] ok")


if __name__ == "__main__":
    _demo()
