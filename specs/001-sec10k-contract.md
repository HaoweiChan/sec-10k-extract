# 001 — sec10k output contract

What `src/sec10k/extract.py::extract_items(path)` must return for any input
filing (iXBRL .htm, legacy HTML, or pre-2001 full-text .txt submission).

## Shape

```json
{
  "normalized_text": "<the full filing as extractor-normalized plain text>",
  "items": [
    {
      "item": "1A",
      "part": "I",
      "title": "Risk Factors",
      "start": 123,
      "end": 45678,
      "status": "extracted",
      "confidence": 0.95
    }
  ]
}
```

## Rules

- `item` codes come from the canonical registry in
  `src/sec10k/eval_adapter.py` (modern + legacy taxonomies). Nothing else.
- `status` ∈ `extracted` | `missing` | `incorporated_by_reference` | `omitted`.
  Every item in the filing-era's expected set MUST appear in `items` with some
  status — silence is not an allowed way to report absence (INV-0).
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
