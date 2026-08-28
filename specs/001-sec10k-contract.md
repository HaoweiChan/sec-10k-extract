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
    "coverage": 0.9484,
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
      "review_required": false,
      "evidence": {}
    }
  ]
}
```

The example is the non-refusal shape. `meta.taxonomy_era`,
`meta.toc_manifest` and `meta.coverage` (ADR-035) are present **on the
non-refusal path only**
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
  A SECOND shape puts the pointer outside the item and shares it with several
  items at once (ADR-042 §c): a Part addressed by ONE sentence naming three or
  more items — Berkshire Hathaway FY2024's whole of Part III is "information
  required by this Part (Items 10, 11, 12, 13 and 14) is incorporated by
  reference to the definitive proxy statement". There the item's own
  `start`/`end` are **null** and the sentence's offsets are published at
  `evidence.collective_reference = {"start", "end"}`. This is the ONLY
  sanctioned null pair on a span-carrying status, and it exists because
  INV-S1 forbids five items sharing one range while slicing the sentence five
  ways would publish spans whose text is "10, " and "11, ".
- A third `evidence` key, `cross_reference`, is a pure ANNOTATION and moves
  nothing (ADR-042 §a): a list of `{"pages", "start", "end"}` regions naming
  where a *cross-reference index* says an item is answered, present only on a
  filing that carries one. The regions may OVERLAP and NEST — Intel FY2024's
  item 3 is pages 102-105, inside item 8's 56-108 — which is exactly why they
  are not the item's span. An item whose span the index's own row supplied
  (a filing that writes no `Item N` heading at all) carries
  `method: "cross_reference_index"`; those rows partition the index region, so
  they satisfy INV-S1 like any other span.
- For `status: missing` / `omitted`: `start`/`end` are null — there is no span.
  Conversely a span-carrying status (`extracted`, `incorporated_by_reference`)
  must have both, the one exception being the collective pointer above —
  enforced as a conjunction (null pair AND `evidence.collective_reference`),
  never as a status exemption. **Enforced by `envelope_shape` since 2026-08-27** (PR #58 R1);
  before that this rule was documented and unchecked, and ADR-036's escalation
  tier could write offsets onto a `missing` item — which also inflated
  `meta.coverage`, since that figure sums every item with a non-null `start`.
- All statuses require `confidence` (how sure are we it's actually
  absent/incorporated, not missed).
- All statuses require **`review_required`** (bool, ADR-035 §e): true exactly
  when some warning in `warnings` carries this item's code, excluding
  `expected_item_missing` (which only restates `status: missing`). It is the
  same set of hits that moves `confidence` by `WARN_PENALTY`, so the two can
  never disagree, and it exists because `status` alone cannot say it: a
  validator-flagged item stays `extracted` — the filing really did answer it
  that way — and a consumer reading `status` and the text must not be told
  the span is clean when a layer-8 check fired on it. It is **item-level**:
  a document-level warning (`item: null`) does not set it, because
  `doc_status` already carries that, and an `ambiguous` document separately
  caps every item at 0.75 (ADR-027 §a).
- **`meta.coverage`** (float in [0,1], ADR-035 §d): the fraction of
  `normalized_text` that lies inside SOME item's span — every span-carrying
  status, `extracted` and `incorporated_by_reference` alike, summed (INV-S1
  makes the spans disjoint, so the sum is exact) and rounded to 4 dp. It is
  **not** `1 - unattributed_content`: that figure counts only the preamble
  and the tail and understates true non-coverage by up to 9.7 points on the
  7 `EXEC_OFFICERS_RE` fixtures (ADR-019 §d). Below `COVERAGE_MIN` it
  escalates (`low_item_coverage`, in `AMBIGUOUS_CODES`); above it, it is
  still published, because a document that places 37% of its text in items
  must be able to say so at the API level without a consumer parsing a
  warning message for the number.
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
- **`images` (optional, ADR-033)**: present *only* when the caller passes
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
  fall inside any table or cell span; ADR-033 §b2a carries the measured
  instances and the corpus split. The image BYTES are
  never fetched (ADR-033 §c); `<object>`, `<embed>`, inline `<svg>` and CSS
  background images are not recorded (ADR-033 §e). `envelope_shape` refuses
  any other shape.

- **`routing` (optional, ADR-036)**: present *only* when the caller passes
  `extract_items(path, escalate=True)`. The tiered slow path's record —
  `{trigger: {fired, codes, items, message}, tiers: [...], resolved: [...],
  cost: {llm_calls, tokens, usd}}`. `trigger.fired` is true exactly when a
  warning in `warnings` carries a code in `escalate.TRIGGER_CODES`
  (`low_item_coverage` today); `trigger.items` names the items D8 flagged as
  stubs or pointers and is a hint to the tiers, not an escalation on its own
  (ADR-035 §c). Each `tiers` entry is `{tier, model, items, offset,
  input_chars, truncated, outcome, cost, ...}` with `outcome` ∈ `resolved` |
  `rejected` | `unparseable` | `unavailable`; `offset`/`input_chars`/
  `truncated` report what that rung was actually shown, as a RANGE
  (`[offset, offset + input_chars)` into `normalized_text`) and not merely a
  length — both rungs' inputs are capped (ADR-036 §h2) and rung 1's window
  starts at the largest unattributed region, so a length alone cannot say what
  was read; a tier that answered from the response cache carries
  `cached: true` and a zero cost. `resolved` names exactly the items whose
  `method` is an escalation method, and `routing.cost` is exactly the sum of
  its own tiers' costs, which is exactly the envelope's top-level `cost` —
  three statements `envelope_shape` re-derives rather than trusts, because a
  published price a consumer cannot check is the failure D11 exists to close.
  A trigger that did not fire may not report attempted tiers. This is the one
  optional key that is **not** a pure annotation: a resolved tier moves the
  affected items' `start`, `end`, `method` and `heading_text`, preserving the
  deterministic answer under `evidence.deterministic`. With the trigger quiet
  nothing moves — see ADR-036 §f for the measured blast radius.
  ADR-046 adds deterministic `trigger.class`, `route`, `reason`,
  `target_items`, and `calls_paid`; a resolved cross-reference class is
  `deterministic_resolved` / `suppressed` / false. Alternative results are
  published at `evidence.alternative_regions`: a list of bounded
  `{start,end,title}` or `{start,end,reference}` records whose evidence string
  is verbatim inside that region. They may overlap, nest, or be discontiguous,
  and are annotations only: primary `start`/`end` and INV-S1 never move.
  `routing.stages` is always the ordered list `classify`, `plan`, `route`,
  `verify`, `decide`; each record has backend-authored `status`, `reason`,
  `targets`, zero-or-measured `cost`, and `skipped`. The view passes it through
  verbatim. Its verify record may contain the bounded cached vision seam;
  vision can only confirm/reject/null already verified alternative evidence.

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
  listed code is one a path produces) and `low_item_coverage` (ADR-035 —
  `meta.coverage` below `COVERAGE_MIN`; produced end to end on
  `evals/adversarial/xref-index-collapse.json`). A resolved
  `cross_reference_index` qualifies only `low_item_coverage`: the warning and
  `meta.coverage` remain published, but that code alone yields
  `success_with_warning` because the filing's alternative content is resolved
  (ADR-045). Every other warning code is
  non-escalating — including `item_span_near_empty` (ADR-035 §c) and
  `internal_pointer_unreached` (ADR-039 §b), which carry an item code, move
  that item's `confidence` and set its `review_required`, and say nothing
  about the document.
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
  never emitted (ADR-020, and ADR-036 §j keeps it that way rather than reusing
  the name for a triggered tier that means something else).
  ADR-036 adds `llm_localize` and `llm_extract`: the item's span was produced
  by escalation rung 1 or rung 2 and survived `escalate.verify`. Both are
  emitted only on an `escalate=True` run, and only on an envelope that also
  carries a `routing` record naming the same items in `resolved` —
  `envelope_shape` refuses an item that claims a tier the envelope has no
  record of. An item carrying either value has `heading_text: null` (its span
  no longer opens with the heading the segmenter matched) and an
  `evidence.deterministic` block holding the offsets, method, heading and
  title similarity the $0 path had published. `envelope_shape` refuses any
  value outside the enum; `item_field` pins the value per item.

## Envelope fields (v2, informative)

`meta`, `trace`, `timings`, `cost`, `heading_text`, `evidence` must be present,
but their internal shape is implementation-owned and may evolve without an ADR
as long as `docs/architecture/overview.md` stays accurate. They exist for
inspectability (frontend, extraction-auditor) and for the analysis report —
`trace` records structured decisions and evidence only, never model
chain-of-thought.
