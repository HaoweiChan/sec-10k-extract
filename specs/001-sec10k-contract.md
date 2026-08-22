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

- `item` codes come from the emitting registry, `TITLES`/`ORDER` in
  `src/sec10k/segment.py` (modern + legacy taxonomies). Nothing else.
  `eval_adapter.CANONICAL` is a hand-kept mirror used for judging, which is
  why `known_items_only` can only ever pass — see ADR-010's open list.
- `status` ∈ `extracted` | `missing` | `incorporated_by_reference` | `omitted`.
  Every item in the filing-era's expected set MUST appear in `items` with some
  status — silence is not an allowed way to report absence (INV-S4).
- For `status: extracted`: `normalized_text[start:end]` must equal the item's
  text verbatim (INV-S2); `[start, end)` ranges must not overlap and must
  appear in document order (INV-S1). Item text is read via the offsets — there
  is deliberately no separate `text` field to drift from them.
- For `status: incorporated_by_reference`: `start`/`end` point at the item's
  own pointer text — the sentence naming the other document. That text is real
  and is the evidence a human uses to confirm the claim, so it is addressable
  like any other span, and INV-S1 + boundary hygiene cover it (ADR-011).
- For `status: missing` / `omitted`: `start`/`end` are null — there is no span.
- All statuses require `confidence` (how sure are we it's actually
  absent/incorporated, not missed).
- `confidence` ∈ [0,1] and must be honest: downstream consumers will threshold
  on it. Cases pin the scale's constants via the `confidence` check type
  (ADR-010). The scale is now *measured*, not merely asserted: metric 8 v2
  publishes a per-value table (docs/analysis-report.md), scored rates there are
  upper bounds because the suite is gated green, and the enumerated debt
  channel demonstrates real overconfident wrongness at both a high and a mid
  scale value. ADR-018 rules on the remap question this measurement raised:
  magnitudes stand (no constant moves), and the phantom `BASE_MISSING = 0.55`
  — a value no item could ever actually carry — collapsed to the 0.40 every
  missing item already scored. The scale itself is an ordinal evidence
  encoding — status tier, title-match quality, warning count — not a
  probability.
- Offsets are into `normalized_text`, NOT the raw file. Normalization is owned
  by the extractor but must be deterministic for a given input.
- **`boilerplate` (optional, ADR-026)**: present *only* when the caller passes
  `extract_items(path, exclude_boilerplate=True)`. A list of
  `{"start", "end", "kind"}` line runs into `normalized_text`, `kind` ∈
  `edgar_chrome` | `running_head` | `page_number`, non-overlapping and in
  document order. It is an annotation, never an edit: `normalized_text` and
  every item offset are byte-identical with the flag on and off, so the rules
  above hold unchanged in both modes. `[]` means "asked, found none" and is a
  different answer from the key being absent. The stripped view is derived by
  `src/sec10k/boilerplate.strip_chrome()` and is deliberately not a field —
  same reason item text is not one.

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
