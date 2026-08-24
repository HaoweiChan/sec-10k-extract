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
  "warnings": [{"code": "keyword_fingerprint", "message": "...", "item": "1A"}],
  "meta": {
    "format_era": "ixbrl",
    "taxonomy_era": "modern",
    "toc_manifest": ["1", "1A", "..."],
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

The example is the non-refusal shape. `meta.taxonomy_era` and
`meta.toc_manifest` are present **on the non-refusal path only**
(`success` / `success_with_warning` / `ambiguous`): a document the pipeline
refused (`unsupported` / `failed`) has no era and no manifest to report
(ADR-027 §f; the `envelope_shape` check type encodes exactly this). The
warning code shown is one a path actually produces (ADR-016's table lists
them all); the example once showed `lenient_match`, which nothing emits.

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
  One shape puts the pointer OUTSIDE the item's body (ADR-031): a heading
  whose line ends in an asterisk run over an empty body, resolved by a
  footnote elsewhere that names the item and an external document. There the
  span is the item's own marked heading line and the footnote's offsets into
  `normalized_text` are published at `evidence.footnote = {"start", "end"}`
  (offsets only — no second copy of the text). The key is absent on every
  other item.
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
  encoding — status tier, title-match quality, warning count, and (ADR-027 §a)
  the document verdict: when `doc_status` is `ambiguous` every item is capped
  at the weak-title base (0.75), so an envelope can never say "we could not
  resolve this document" over a column of 0.95s — not a
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
- **`tables` (optional, ADR-029)**: present *only* when the caller passes
  `extract_items(path, tables=True)`. A list, in document order, of one
  record per HTML `<table>` that carries visible text:
  `{"start", "end", "header", "rows"}` — `start`/`end` are offsets into
  `normalized_text` bounding the table's text; `header` is the number of
  leading rows that are all-`<th>` (0 when none); `rows` is a list of rows,
  each a list of cells, each cell `[start, end]` or `[start, end, colspan]`
  (the third element only when `colspan > 1`), offsets into
  `normalized_text`, every cell inside its table's span, cell text tight
  (no leading/trailing whitespace). A cell's text **is**
  `normalized_text[start:end]` — there is no cell string to drift from it,
  exactly as there is no item `text` field. Same rule as `boilerplate`: an
  annotation, never an edit — `normalized_text`, every item offset and
  every published figure are byte-identical with the flag on and off.
  Carried on refusal envelopes too when asked for. The row-of-strings grid
  (`colspan` expanded to empty cells) and the Markdown rendering are derived
  by `src/sec10k/tables.grid()` / `to_markdown()` and are deliberately not
  fields. `rowspan`, nested tables and txt-era SGML `<TABLE>` layout are not
  interpreted (ADR-029 §e). `envelope_shape` refuses any other shape.
- **`blocks` (optional, ADR-032)**: present *only* when the caller passes
  `extract_items(path, blocks=True)`, which also implies `tables=True`
  (table blocks point into the `tables` records). A list, in document order
  and non-overlapping, of `{"kind", "start", "end", ...}` records —
  `start`/`end` offsets into `normalized_text` bounding one block's visible
  text (first to last non-space character); `kind` ∈ `heading` (with
  `level`, an int 1–6, and `item` when it is an item heading the segmenter
  identified) | `paragraph` (with `strong: true` when the whole block was
  bold in the HTML) | `list_item` (with `ordered`) | `table` (with `table`,
  the index of the `tables` record whose span the block is) | `pre` (the
  one block a txt-era filing is). A block's text **is**
  `normalized_text[start:end]`; together the blocks cover every non-space
  character of `normalized_text`. Same rule as `boilerplate` and `tables`:
  an annotation, never an edit — `normalized_text`, every item offset and
  every published figure are byte-identical with the flag on and off.
  Carried on refusal envelopes too when asked for (no items, so no item
  heading is promoted). The whole-document and per-item Markdown are
  derived by `src/sec10k/markdown.to_markdown()` and are deliberately not
  fields. Headings inferred from styling, inline emphasis, italic, nested
  lists, definition lists and txt-era structure are not interpreted
  (ADR-032 §e). `envelope_shape` refuses any other shape.
- **`images` (optional, ADR-034)**: present *only* when the caller passes
  `extract_items(path, images=True)`. A list, in document order, of one
  record per HTML `<img>`: `{"offset", "src", "alt", "width", "height"}` —
  `offset` is a **point** into `normalized_text` (an image emits no text, so
  it has no span), so document order is **non-decreasing**, not strictly
  increasing: two adjacent images share an offset. `src` and `alt` are the
  attributes verbatim, entity-decoded, `null` when absent. `width`/`height`
  are the declared pixel size as a positive int, from the `width=`/`height=`
  attribute or a `width:Npx` / `height:Npx` declaration in `style`, `null`
  when neither declares one in pixels. Same rule as `boilerplate` and
  `tables`: an annotation, never an edit — `normalized_text`, every item
  offset and every published figure are byte-identical with the flag on and
  off. Carried on refusal envelopes too when asked for. The item an image
  falls in is **derived** from offsets (the item whose span holds `offset`,
  `null` when none does) and is deliberately not a field. An image offset is
  **not** guaranteed to fall inside the `tables` span of a table the raw HTML
  puts it in. The rule is one comparison — `span.start <= offset <
  span.end`, half-open, cells and tables alike — and it has to be applied
  rather than predicted, because an `<img>` emits nothing while spans are
  tightened to visible characters and empty cells are clamped, so the two move
  independently. A table with no visible text anywhere in it is not recorded
  at all, so there is no span to compare against. 0 of the corpus's 53 offsets
  fall inside any table or cell span; ADR-034 §b2a carries the measured
  instances and the corpus split. The image BYTES are
  never fetched (ADR-034 §c); `<object>`, `<embed>`, inline `<svg>` and CSS
  background images are not recorded (ADR-034 §e). `envelope_shape` refuses
  any other shape.

- **`cover` (optional, ADR-034)**: present *only* when the caller passes
  `extract_items(path, cover=True)`. A dict keyed by field name —
  `registrant_name`, `state_of_incorporation`, `ein`,
  `commission_file_number`, `fiscal_year_end`, `trading_symbol` — each
  holding `{"value", "start", "end", "status", "confidence", "method"}`.
  `status` ∈ `resolved` | `not_in_era` | `missing`; `method` ∈
  `caption_anchored` | `ein_regex` | `ein_pivot` | `positional` |
  `cover_date_re` | `era_gate`. For `resolved`, `start`/`end` are offsets into
  `normalized_text` and `normalized_text[start:end]` **must equal** `value` —
  the same verbatim rule INV-S2 puts on an item span, so no cover fact is a
  bare assertion. For `not_in_era` (the filing's cover predates the field —
  `trading_symbol` on a 1994 filing) and `missing`, all three of
  `value`/`start`/`end` are null; `not_in_era` is a **positive claim** and
  carries a high confidence, `missing` carries `BASE_MISSING`. `confidence`
  reuses `src/sec10k/validate.py`'s scale unchanged — no second scale exists
  (ADR-034 §f). Same rule as `boilerplate`, `tables` and `blocks`: an
  annotation, never an edit. **No cover pseudo-item is emitted** — the item
  registry rule above ("Nothing else") is untouched, so every `only_items`,
  `known_items_only` and `expected_set_complete` check is unaffected by
  construction. Seven further cover fields were considered and cut with their
  measurements (ADR-034 §d). `envelope_shape` refuses any other shape.

## Envelope rules (v2, normative)

- `doc_status` ∈ `success` | `success_with_warning` | `ambiguous` |
  `unsupported` | `failed`. Derivation order is fixed (first match wins):
  unusable input / normalization collapse → `failed`; input is not a detectable
  10-K → `unsupported`; unresolvable competing candidates or implausibly low
  extraction coverage → `ambiguous`; any warning emitted →
  `success_with_warning`; else `success`. Thresholds inside these rules are
  implementation-owned and provisional; the ordering is not. The warning codes
  that may reach `ambiguous` are exactly `validate.AMBIGUOUS_CODES`:
  `toc_manifest_mismatch`, `last_item_dominates`,
  `expected_items_mostly_missing` (ADR-008, ADR-013) and `item_dominates`
  (ADR-030 — a non-last span above `ITEM_MAX`; produced end to end on
  `evals/adversarial/interior-span-dominates.json`, per ADR-016's rule that a
  listed code is one a path produces). Every other warning code is
  non-escalating.
- `unsupported`/`failed` mean the pipeline **refused** — it must never emit a
  best-effort `items` parse of a document it could not identify as a 10-K.
- `warnings` is present (possibly empty); `doc_status: success` requires it to
  be empty.
- `method` ∈ `heading_strict` | `heading_lenient` | `status_keyword` |
  `llm_fallback` (extensible via ADR) — feeds the deterministic-coverage
  metric. Defined (ADR-027 §b): `heading_strict` — a line-anchored heading
  whose title similarity to an era alias is ≥ `STRICT_SIM` (0.8);
  `heading_lenient` — a line-anchored heading whose similarity is in
  `[SIM_FLOOR, STRICT_SIM)`, the same condition that pays the weak confidence
  base, so `method` and `evidence.confidence_base` can never disagree;
  `status_keyword` — no heading was found and the entry exists because INV-S4
  requires every expected item to appear with a status (the name predates the
  implementation and is kept for v2 additivity); `llm_fallback` — declared,
  never emitted (ADR-020). `envelope_shape` refuses any value outside the
  enum; `item_field` pins the value per item.

## Envelope fields (v2, informative)

`meta`, `trace`, `timings`, `cost`, `heading_text`, `evidence` must be present,
but their internal shape is implementation-owned and may evolve without an ADR
as long as `docs/architecture/overview.md` stays accurate. They exist for
inspectability (frontend, extraction-auditor) and for the analysis report —
`trace` records structured decisions and evidence only, never model
chain-of-thought.
