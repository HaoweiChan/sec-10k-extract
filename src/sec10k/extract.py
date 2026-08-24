"""10-K item-level extraction. Contract: specs/001-sec10k-contract.md.

Layers 1-9 and 11 are real: selection, normalization, candidates, TOC filter,
boundaries, status, label-free validation, confidence, assembly. Layer 10
(LLM fallback) stays deferred until residual-failure data justifies one.
`success` is deliberately hard to earn — it requires the validator battery to
find nothing at all.
"""
import hashlib
import time
from pathlib import Path

from src.sec10k.boilerplate import find_chrome
from src.sec10k.cover import resolve as resolve_cover
from src.sec10k.normalize import ACCEPTED_FORMS, COLLAPSE_FLOOR, select_and_normalize
from src.sec10k.segment import (
    assign_boundaries, classify, expected_items, filter_candidates, footnote_pointer,
    item_label, find_candidates,
)
from src.sec10k.validate import AMBIGUOUS_CODES, STRICT_SIM, score, validate

VERSION = "0.8.0-d4"  # meta.extractor_version — audits compare across runs


def _item(code, cand, status, period_end=None, footnote=None):
    part, title = item_label(code, period_end)
    if cand is None:
        # no heading anywhere: the entry exists because INV-S4 says every
        # expected item must appear with some status (contract, `method`)
        return {"item": code, "part": part, "title": title,
                "heading_text": None, "start": None, "end": None,
                "status": status,
                "method": "status_keyword", "evidence": {}}
    return {
        "item": code, "part": part, "title": title,
        "heading_text": cand["heading_text"], "start": cand["start"],
        "end": cand["end"], "status": status,
        # ADR-027 §b: `method` names the heading-match tier by the SAME cut
        # that pays BASE_STRICT vs BASE_WEAK, so the envelope can no longer
        # publish "strict" on a heading the score calls weak (SD-1)
        "method": "heading_strict" if cand["similarity"] >= STRICT_SIM else "heading_lenient",
        "evidence": {"title_similarity": cand["similarity"],
                     "chars": cand["end"] - cand["start"],
                     # ADR-031: the footnote that resolved a marked, empty
                     # heading to IBR — offsets into normalized_text, the
                     # pointer sentence a human reads; the item's own span stays
                     # the heading line (INV-S1 forbids pointing it into the
                     # item that holds the footnote). Key absent otherwise.
                     **({"footnote": {"start": footnote[0], "end": footnote[1]}}
                        if footnote else {})},
    }


def _promote_item_headings(blocks, tables, items):
    """ADR-032 §b3: the block a span-carrying item opens with IS the heading
    the segmenter identified (`verbatim` asserts the span opens with
    `heading_text`), so it becomes a level-2 `heading` carrying the item
    code — a paragraph block, or a table block with exactly one visible row
    (jnj-2016 / spatz-2014 / wmt-2010 typeset `Item N.` | `TITLE` as a
    two-cell table). A longer table the heading merely opens (bac-2006 item
    7's MD&A index, 36 visible rows) stays a table: promoting it would swallow
    the index into an `##`. Measured 2026-08-23 over the 624 span items of
    the 34 HTML/iXBRL fixtures: 488 paragraph blocks equal to heading_text,
    135 one-row tables, 1 multi-row table."""
    at = {b["start"]: b for b in blocks}
    for it in items:
        b = at.get(it["start"])
        if b is None:
            continue
        if b["kind"] == "table":
            rows = [r for r in tables[b["table"]]["rows"] if any(c[0] < c[1] for c in r)]
            if len(rows) != 1:
                continue
            del b["table"]
        elif b["kind"] != "paragraph":
            continue
        b.pop("strong", None)
        b.update(kind="heading", level=2, item=it["item"])


def _envelope(doc_status, text="", items=None, warnings=None, meta=None,
              trace=None, t0=None, boilerplate=None, tables=None, blocks=None,
              cover=None, images=None):
    env = {
        "normalized_text": text,
        "doc_status": doc_status,
        "warnings": warnings or [],
        "meta": {"extractor_version": VERSION, **(meta or {})},
        "trace": trace or [],
        "timings": {"total_ms": round((time.monotonic() - t0) * 1000, 1) if t0 else 0},
        "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0},  # deterministic-only at B
        "items": items or [],
    }
    if boilerplate is not None:
        # ADR-026: the key exists only when the caller asked. `[]` means "asked,
        # found none" and is not the same answer as the key being absent.
        env["boilerplate"] = boilerplate
    if tables is not None:
        env["tables"] = tables   # ADR-029: same rule — present only when asked
    if blocks is not None:
        env["blocks"] = blocks   # ADR-032: same rule again
    if images is not None:
        env["images"] = images   # ADR-033: same rule again
    if cover is not None:
        env["cover"] = cover     # ADR-034: and again
    return env


# ADR-034 (cold review): the cover region is capped, not just bounded by the
# first item span. Without a cap, a document where NO item carries a span —
# `ambiguous`, an envelope that still ships — hands the whole filing to the
# resolver, and EIN_RE/COVER_DATE_RE/SYMBOL_HDR_RE then match a subsidiaries
# exhibit's EIN or an Item 5 sentence about a trading symbol. 12,000 is 1.16x
# the largest cover region in the committed corpus (nvda-2024, 10,384 chars).
COVER_MAX = 12000


def _cover(text, items):
    """ADR-034's cover region: text[0:first item span], capped at COVER_MAX and
    never sub-divided — ge-1994 opens with a section index and does not reach
    its cover until ~offset 1000, which a TOC-aware split would have to know
    about and this does not."""
    spans = [i["start"] for i in items if i.get("start") is not None]
    return resolve_cover(text, min(min(spans) if spans else len(text), COVER_MAX))


def extract_items(path, exclude_boilerplate=False, tables=False, blocks=False,
                  images=False, cover=False):

    """Extract items from a 10-K filing.

    Returns {"normalized_text": str, "doc_status": str, "items": [...], ...}
    per specs/001-sec10k-contract.md.

    `exclude_boilerplate=True` adds ONE key, `boilerplate` — the chrome runs
    found in `normalized_text` (ADR-026). It is a pure annotation: nothing else
    in the envelope moves, so INV-S2 offsets mean the same thing either way.

    `tables=True` adds ONE key, `tables` — every HTML <table> as offsets into
    `normalized_text` (ADR-029), the same annotation-not-edit rule. The
    Markdown view is derived by `src/sec10k/tables.to_markdown`, never stored.

    `blocks=True` adds `blocks` (and implies `tables`) — the document's block
    structure as offsets into `normalized_text` (ADR-032): headings,
    paragraphs, list items, tables (pointing at the `tables` record), or one
    `pre` block for a txt-era filing. The whole-document / per-item Markdown
    view is derived by `src/sec10k/markdown.to_markdown`, never stored.

    `images=True` adds ONE key, `images` — every HTML <img> as
    `{offset, src, alt, width, height}`, the offset into `normalized_text`
    (ADR-033). Same annotation-not-edit rule; the image BYTES are not
    fetched, by ruling (ADR-033 §c).
    """
    t0 = time.monotonic()
    raw_bytes = Path(path).read_bytes()
    sha = hashlib.sha256(raw_bytes).hexdigest()
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # 1990s filings carry Word's cp1252 smart quotes as raw bytes, not
        # entities; errors="replace" would silently mangle them to U+FFFD.
        # All 13 committed fixtures are pure ASCII — this is for held-out input.
        raw = raw_bytes.decode("cp1252", errors="replace")

    trace = [{"layer": "acquisition", "path": str(path), "bytes": len(raw_bytes)}]
    text, meta, warnings, tabs, blks, imgs = select_and_normalize(
        raw, tables=tables, blocks=blocks, images=images)
    meta["input_sha256"] = sha
    trace.append({"layer": "select+normalize", **meta})
    # ADR-026 layer 3b, opt-in. Computed here, off the normalized text, and
    # then carried untouched to whichever envelope this run returns — including
    # the `failed`/`unsupported` refusals, which still have readable text a
    # caller who asked for chrome is entitled to. Nothing downstream reads it.
    chrome = find_chrome(text) if exclude_boilerplate else None

    # ORDER IS THE CONTRACT'S, NOT A PREFERENCE (001-sec10k-contract, envelope
    # rules): collapse is tested BEFORE form identity. A truncated download
    # normalizes to nothing AND sniffs no form, and the two statuses are
    # different diagnoses to a user — "we could not read this" sends them to
    # re-download, "this is not a 10-K" sends them to check the wrong thing.
    if len(text) < COLLAPSE_FLOOR:
        warnings.append({
            "code": "normalization_collapse", "item": None,
            "message": f"{len(raw)} raw chars normalized to {len(text)}"})
        return _envelope("failed", text, meta=meta, warnings=warnings,
                         trace=trace, t0=t0, boilerplate=chrome, tables=tabs,
                         blocks=blks, images=imgs,
                         cover=_cover(text, []) if cover else None)

    if meta["form_type"] not in ACCEPTED_FORMS:
        # refusal, not a best-effort parse (contract v2 envelope rules)
        found = meta["form_type"] or "none"
        warnings.append({"code": "unsupported_form", "item": None,
                         "message": f"not an accepted 10-K form (detected: {found})"})
        return _envelope("unsupported", text, meta=meta, warnings=warnings,
                         trace=trace, t0=t0, boilerplate=chrome, tables=tabs,
                         blocks=blks, images=imgs,
                         cover=_cover(text, []) if cover else None)

    expected = expected_items(meta.get("period_end"))
    # taxonomy era is the item set the filing's date implies, not its file
    # format: a 2002 HTML filing is as legacy as a 1994 txt one
    meta["taxonomy_era"] = "modern" if "1A" in expected else "legacy"
    cands = find_candidates(text, expected)
    survivors, manifest, rejected = filter_candidates(cands)
    accepted = assign_boundaries(survivors, expected, text)
    meta["toc_manifest"] = manifest
    trace.append({"layer": "candidates", "found": len(cands),
                  "survived": len(survivors), "toc_manifest": manifest,
                  "rejected": [{"item": r["item"], "start": r["start"],
                                "why": r["why"]} for r in rejected]})

    items = []
    for code in expected:
        c = accepted.get(code)
        body = text[c["heading_end"]:c["end"]] if c else ""
        status = classify(code, body, c is not None)
        foot = None
        if c is not None and status == "extracted":
            # ADR-031 (D4): a marked heading over an empty body, resolved by a
            # footnote elsewhere that names this item and an external document
            foot = footnote_pointer(code, c["heading_text"], body, text)
            if foot:
                status = "incorporated_by_reference"
        items.append(_item(code, c, status, meta.get("period_end"), footnote=foot))
    trace.append({"layer": "status",
                  "counts": {s: sum(1 for i in items if i["status"] == s)
                             for s in {i["status"] for i in items}}})

    for i in items:
        if i["status"] == "missing":
            warnings.append({"code": "expected_item_missing", "item": i["item"],
                             "message": f"item {i['item']} expected in this era, no heading found"})
    if meta.get("period_end") is None:
        warnings.append({"code": "period_end_unknown", "item": None,
                         "message": "no period of report found; expected item set is a guess"})

    # layer 8: label-free validation, then layer 9 confidence from what it found
    findings = validate(text, items, accepted, manifest)
    warnings += findings
    trace.append({"layer": "validate",
                  "checks_fired": [w["code"] for w in findings]})

    if blks is not None:
        _promote_item_headings(blks, tabs, items)

    cov = _cover(text, items) if cover else None

    # doc_status ladder (contract v2, fixed order). Only the four validators
    # named in AMBIGUOUS_CODES may reach `ambiguous`; the rest warn and move
    # confidence, per the taxonomy's warn-don't-hard-fail policy. Decided
    # BEFORE scoring: an `ambiguous` verdict caps every item (ADR-027 §a) —
    # before that, no document-level warning ever reached an item's number.
    extracted = [i for i in items if i["status"] == "extracted"]
    ambiguous = not extracted or any(w["code"] in AMBIGUOUS_CODES for w in warnings)
    for i in items:
        i["confidence"], i["evidence"] = score(i, warnings, doc_ambiguous=ambiguous)
    if ambiguous:
        doc_status = "ambiguous"
    elif warnings:
        doc_status = "success_with_warning"
    else:
        doc_status = "success"
    return _envelope(doc_status, text, items=items, meta=meta,
                     warnings=warnings, trace=trace, t0=t0, boilerplate=chrome,
                     tables=tabs, blocks=blks, images=imgs, cover=cov)
