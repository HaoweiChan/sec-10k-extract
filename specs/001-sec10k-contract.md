# 001 — sec10k output contract (v2)

What `src/sec10k/extract.py::extract_items(path)` must return for any input
filing (iXBRL .htm, legacy HTML, or pre-2001 full-text .txt submission).
v2 (ADR-002) is strictly additive over v1 — every v1 field and rule is
unchanged; field rationale lives in `docs/product/task2-problem-definition.md`.

## Shape

```json
{
  "normalized_text": "<the full filing as extractor-normalized plain text>",
  "doc_status": "success_with_warning",
  "warnings": [{"code": "lenient_match", "message": "...", "item": "7A"}],
  "meta": {
    "format_era": "ixbrl",
    "taxonomy_era": "modern",
    "document_selected": "...",
    "input_sha256": "...",
    "extractor_version": "..."
  },
  "trace": [],
  "timings": {"total_ms": 0},
  "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0},
  "items": [
    {
      "item": "1A",
      "part": "I",
      "title": "Risk Factors",
      "heading_text": "Item 1A. Risk Factors",
      "start": 123,
      "end": 45678,
      "status": "extracted",
      "confidence": 0.95,
      "method": "heading_strict",
      "evidence": {}
    }
  ]
}
```

## Rules

- `item` codes come from the canonical registry in
  `src/sec10k/eval_adapter.py` (modern + legacy taxonomies). Nothing else.
- `status` ∈ `extracted` | `missing` | `incorporated_by_reference` | `omitted`.
  Every item in the filing-era's expected set MUST appear in `items` with some
  status — silence is not an allowed way to report absence (INV-S4).
- For `status: extracted`: `normalized_text[start:end]` must equal the item's
  text verbatim (INV-S2); `[start, end)` ranges must not overlap and must
  appear in document order (INV-S1). Item text is read via the offsets — there
  is deliberately no separate `text` field to drift from them.
- For any other status: `start`/`end` are null; `confidence` still required
  (how sure are we it's actually absent/incorporated, not missed).
- `confidence` ∈ [0,1] and must be honest: downstream consumers will threshold
  on it, and the eval set contains cases that punish overconfident wrongness.
- Offsets are into `normalized_text`, NOT the raw file. Normalization is owned
  by the extractor but must be deterministic for a given input.

## Envelope rules (v2, normative)

- `doc_status` ∈ `success` | `success_with_warning` | `ambiguous` |
  `unsupported` | `failed`. Derivation order is fixed (first match wins):
  unusable input / normalization collapse → `failed`; input is not a detectable
  10-K → `unsupported`; unresolvable competing candidates or implausibly low
  extraction coverage → `ambiguous`; any warning emitted →
  `success_with_warning`; else `success`. Thresholds inside these rules are
  implementation-owned and provisional; the ordering is not.
- `unsupported`/`failed` mean the pipeline **refused** — it must never emit a
  best-effort `items` parse of a document it could not identify as a 10-K.
- `warnings` is present (possibly empty); `doc_status: success` requires it to
  be empty.
- `method` ∈ `heading_strict` | `heading_lenient` | `status_keyword` |
  `llm_fallback` (extensible via ADR) — feeds the deterministic-coverage
  metric.

## Envelope fields (v2, informative)

`meta`, `trace`, `timings`, `cost`, `heading_text`, `evidence` must be present,
but their internal shape is implementation-owned and may evolve without an ADR
as long as `docs/architecture/overview.md` stays accurate. They exist for
inspectability (frontend, extraction-auditor) and for the analysis report —
`trace` records structured decisions and evidence only, never model
chain-of-thought.
