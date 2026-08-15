"""10-K item-level extraction. Contract: specs/001-sec10k-contract.md.

T4 state: layers 1-7 and 11 are real (selection, normalization, candidates,
TOC filter, boundaries, status, assembly). Layers 8-9 — the label-free
validator battery and calibrated confidence — land at T5, so a standing
`validation_not_implemented` warning caps every filing at
`success_with_warning`: nothing here may claim a clean `success` before it has
actually been validated, and a run that extracts nothing stays `ambiguous`.
"""
import hashlib
import time
from pathlib import Path

from src.sec10k.normalize import ACCEPTED_FORMS, COLLAPSE_FLOOR, select_and_normalize
from src.sec10k.segment import (
    TITLES, assign_boundaries, classify, expected_items, filter_candidates,
    find_candidates,
)

VERSION = "0.4.0-t4"

# Layer 9 in its provisional form: tiered by heading-match quality, coarse, and
# clamped away from 0 and 1. Calibration against measured per-bucket accuracy is
# T5 — these are placeholders that an auditor can recompute from `evidence`.
CONF_STRICT, CONF_WEAK_TITLE, CONF_NON_EXTRACTED = 0.9, 0.7, 0.8


def _item(code, cand, status):
    part, titles = TITLES[code]
    if cand is None:
        return {"item": code, "part": part, "title": titles[0],
                "heading_text": None, "start": None, "end": None,
                "status": status, "confidence": CONF_NON_EXTRACTED,
                "method": "status_keyword", "evidence": {}}
    strong = cand["similarity"] >= 0.8
    return {
        "item": code, "part": part, "title": titles[0],
        "heading_text": cand["heading_text"], "start": cand["start"],
        "end": cand["end"], "status": status,
        "confidence": CONF_STRICT if strong else CONF_WEAK_TITLE,
        "method": "heading_strict",
        "evidence": {"title_similarity": cand["similarity"],
                     "chars": cand["end"] - cand["start"]},
    }


def _envelope(doc_status, text="", items=None, warnings=None, meta=None,
              trace=None, t0=None):
    return {
        "normalized_text": text,
        "doc_status": doc_status,
        "warnings": warnings or [],
        "meta": {"extractor_version": VERSION, **(meta or {})},
        "trace": trace or [],
        "timings": {"total_ms": round((time.monotonic() - t0) * 1000, 1) if t0 else 0},
        "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0},  # deterministic-only at B
        "items": items or [],
    }


def extract_items(path):
    """Extract items from a 10-K filing.

    Returns {"normalized_text": str, "doc_status": str, "items": [...], ...}
    per specs/001-sec10k-contract.md.
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
    text, meta, warnings = select_and_normalize(raw)
    meta["input_sha256"] = sha
    trace.append({"layer": "select+normalize", **meta})

    if meta["form_type"] not in ACCEPTED_FORMS:
        # refusal, not a best-effort parse (contract v2 envelope rules)
        found = meta["form_type"] or "none"
        warnings.append({"code": "unsupported_form", "item": None,
                         "message": f"not an accepted 10-K form (detected: {found})"})
        return _envelope("unsupported", text, meta=meta, warnings=warnings,
                         trace=trace, t0=t0)

    if len(text) < COLLAPSE_FLOOR:
        warnings.append({
            "code": "normalization_collapse", "item": None,
            "message": f"{len(raw)} raw chars normalized to {len(text)}"})
        return _envelope("failed", text, meta=meta, warnings=warnings,
                         trace=trace, t0=t0)

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
        items.append(_item(code, c, status))
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

    # layers 8-9 (validation battery, calibrated confidence) are T5. Until they
    # exist nothing may claim a clean `success` — the honest ceiling is
    # success_with_warning, and a run with no extracted items stays ambiguous.
    extracted = [i for i in items if i["status"] == "extracted"]
    doc_status = "ambiguous" if not extracted else "success_with_warning"
    warnings.append({"code": "validation_not_implemented", "item": None,
                     "message": "T4: no structural validation yet (T5)"})
    return _envelope(doc_status, text, items=items, meta=meta,
                     warnings=warnings, trace=trace, t0=t0)
