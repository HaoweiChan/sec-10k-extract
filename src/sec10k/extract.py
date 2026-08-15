"""10-K item-level extraction. Contract: specs/001-sec10k-contract.md.

T3 state: layers 2-3 (document selection + normalization) and layer 11
(assembly) are real; layers 4-9 (candidates, boundaries, status, validation,
confidence) land at T4-T5, so `items` is always empty here and any filing we
DID identify as a 10-K reports `ambiguous` — zero extraction coverage is
exactly what rule 3 of the doc_status ladder describes. It is never `success`.
"""
import hashlib
import time
from pathlib import Path

from src.sec10k.normalize import ACCEPTED_FORMS, COLLAPSE_FLOOR, select_and_normalize

VERSION = "0.3.0-t3"


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
    # ponytail: format era proxies taxonomy era until T4 needs the real thing —
    # T4 derives it from the period-of-report date, which is what actually
    # decides the expected item set (a 2002 HTML filing has no Item 1A either).
    meta["taxonomy_era"] = "legacy" if meta.get("format_era") == "txt" else "modern"
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

    # layers 4-9 are T4/T5. Zero items = zero coverage = `ambiguous` by the
    # ladder's rule 3; INV-0 holds because this is never reported as success.
    warnings.append({"code": "segmentation_not_implemented", "item": None,
                     "message": "T3: normalization only, no items extracted yet"})
    return _envelope("ambiguous", text, meta=meta, warnings=warnings,
                     trace=trace, t0=t0)
