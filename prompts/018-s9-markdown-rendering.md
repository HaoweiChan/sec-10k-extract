# 018 — S9: whole-document Markdown as a derived view over block annotations (2026-08-23)

The S9 row asked for the filing "parsed into Markdown — headings, paragraphs,
lists, emphasis where the HTML carries it, and the S7 tables" so the inspector
and any consumer can re-render it, with an explicit ruling on the alternative
the direction literally names: making `normalized_text` itself Markdown.
Post-freeze, ADR first. Ruling:
[ADR-031](../specs/decisions/ADR-031-block-structure-markdown-view.md).
(Numbered 018: 016 and 017 were taken by the D2 and D3 records.)

## The prompt decisions that mattered

- **"Parse the filing into Markdown" and "never edit `normalized_text`" are
  reconciled the way S7 reconciled tables: the Markdown is a function of
  the envelope, not a field of it.** The one-pass HTML walk already emits a
  newline at every block-tag boundary; recording the KIND of the text between
  two boundaries — heading level, list item, table record, strong, pre —
  against the text it is already emitting is the whole capability. The
  Markdown is then `to_markdown(text, blocks, tables, start, end)`, per
  document or per item by the same offsets the item is read through.
- **The alternative was measured, not argued away.** Rendering the whole
  document with the same renderer and diffing it against `normalized_text`
  IS the string the alternative would have stored: first differing offset
  0–74 on 46/46 parseable fixtures, 812/812 item spans moved, every
  normalized length changed (+8 to +140,040), 74 band checks and 6 table grids
  re-derived — and only 1 of 71 text anchors broken, which is stated too,
  because Markdown leaves most prose alone and the refusal must not lean on a
  number it does not have. The annotation route moves zero offsets; that is
  the ruling's evidence (ADR-031 §f2).
- **Headings: what the HTML says, plus what the segmenter already knows —
  and nothing inferred.** The corpus census killed the obvious plan: the only
  `<hN>` tags in 34 HTML fixtures are 615 `<h5>Table of Contents</h5>`
  back-links. Modern filings have no heading tags at all; their headings are
  bold styled `<div>`s. Rather than infer levels from weight or size (a guess
  the S9 row's own adversarial shape forbids), the item headings the
  segmenter identified are promoted to level 2 — 488 paragraph blocks and 135
  one-row heading tables, and the one multi-row table (bac-2006 item 7's MD&A
  index) deliberately not — and every other styled heading stays a paragraph
  that carries `strong`, so the inspector shows it bold, not as `#`.
- **Emphasis ruled in at block level only.** `strong` means every visible
  character of the block was bold, by `<b>/<strong>` or by a
  `font-weight:700`-class style (Workiva never writes `<b>`; legacy filers
  never write the style — the census has both numbers). Partial and inline
  emphasis and italic are Debt: an inline span is a second annotation layer
  with no label to pin it, and the whole-block flag covers the sub-heading
  shape the human asked for.
- **`<br>` is a block boundary like `<p>` — one rule, no special case** — and
  the case that pins it exists because the mutation that drops the rule left
  every other case green (ADR-031 §g M9).
- **The inspector renders the Markdown it is given, not HTML it is handed.**
  A forty-line renderer for exactly the emitted subset (ATX headings,
  paragraphs, whole-paragraph `**strong**`, `- `/`1. `, GFM tables, fences),
  escaping after un-escaping, no dependency, no CDN. Server-side HTML was the
  other honest option and was not taken because it would have rendered the
  blocks, not the Markdown — and the Markdown is the deliverable.
- **A metric that is 1.0 by construction is still worth gating, if you say
  so out loud (ADR-029 §c2 restated).** Two numbers, blocks and bounds, so a
  kind error and a boundary error read differently in the time series: strong
  never recorded is 48/61 blocks at 61/61 bounds; table blocks dropped is
  48/61 on both (re-measured 2026-08-24 for PR #45 R2 — the first write-up
  carried 58-label numerators over 61; ADR-031 §g has the runner's lines).

## Assumption → Eval contradiction → Correction

- **Assumed:** naming the new `normalize()` / `select_and_normalize()`
  parameter `blocks` was a harmless choice.
- **Eval said:** the first all-fixture sweep: every iXBRL primary `.htm`
  (aapl-2025, nvda-2024, jpm-2024, xom-2021, cat-2023 …) came back with NO
  `blocks` key when asked, and on the default path axp-2008 came back WITH
  `blocks` and `tables` keys nobody asked for. `select_and_normalize` already
  had a local `blocks = split_documents(raw)` — the `<DOCUMENT>` list — which
  shadowed the flag: empty for an unwrapped filing (falsy → no annotation),
  non-empty for a wrapped one (truthy → annotation unasked). The S7 `found`
  collision, one name over.
- **Corrected:** renamed `docs`, and — hard rule 2 — pinned on BOTH shapes
  before the fix: `blocks-offsets-invariant` (aapl-2025, primary) and
  `blocks-wrapped-invariant` (msft-2013, wrapped), both invariant suite;
  re-introducing the collision (M8) turns six cases red in two directions.

- **Assumed:** `<h1>`–`<h6>` would carry the document's headings, and item
  headings would fall out of that.
- **Eval said:** the tag census — 0 `<h1>`–`<h4>`/`<h6>` anywhere, `<h5>`
  only in seven legacy filings, every one with text being `Table of
  Contents` (gs-2002's 51 are `&nbsp;`); aapl-2025 and jpm-2024 have 0
  heading tags and 0 `<b>`.
- **Corrected:** the item-heading promotion in `extract.py`, measured over
  all 624 span items (488 / 135 / 1), and the `<hN>` rule kept as what the
  HTML says — pinned on the one shape that exists (msft-2013's `<h5>` at
  level 5, bac-2006's too).

- **Assumed:** a heading typeset as a table could be promoted whenever the
  span opens on a table block.
- **Eval said:** bac-2006 item 7 — the span opens on the MD&A's own 72-row
  index table; promoting it writes a 1,187-character `##`.
- **Corrected:** promote a table block only when its record has exactly one
  row with visible text; `blocks-heading-index-table` pins both the promoted
  item 6 and the unpromoted item 7, and M7 (guard removed) is red on it
  alone.

- **Assumed:** the `<br>` rule needed no case of its own; the goldens would
  cover it.
- **Eval said:** M9 (`<br>` does not close a block) left all ten cases green.
- **Corrected:** `blocks-br-boundary` on intc-2002's cover (`UNITED
  STATES<BR>SECURITIES AND EXCHANGE COMMISSION<BR>` inside one `<P>`): three
  strong blocks, one newline apart.

- **Assumed:** the view could simply send the Markdown of the whole item and
  let the pane truncate it like the raw slice.
- **Eval said:** `view.py`'s own self-check — `truncated` and the "first N of
  M characters" line are promises about the SPAN; Markdown of a 68,000-char
  item truncated at 40,000 Markdown characters would cut mid-table and
  mis-count.
- **Corrected:** render the first `DISPLAY_MAX` characters of the span
  (blocks clipped to that window, a clipped table rendered as a paragraph),
  `truncated` from the span; pinned in `view.py::_demo`.

- **Assumed:** the inspector's Markdown table could inherit the pane's
  `overflow-wrap:anywhere`.
- **Eval said:** the first live screenshot — `Europe` wrapped as `Euro` /
  `pe` in an 11-column table.
- **Corrected:** cells wrap at word boundaries only and the table scrolls
  horizontally inside the pane; re-shot in the committed walk.

- **Assumed:** "leave out a block lying wholly inside a chrome run" was the
  S8 checkbox's meaning carried into Markdown mode.
- **Eval said:** PR #45 R1 — on jpm-2024 every one of the 572 ADR-026 runs
  sits inside a two-cell page-furniture table, so the rule omitted nothing:
  286 running heads in the "stripped" Markdown, 0 after `strip_chrome`, and
  the pane said "boilerplate hidden". The new case `blocks-omit-chrome`
  was red first: `stripped markdown still contains 'JPMorgan Chase &
  Co./2024 Form 10-K' (286x)`.
- **Corrected:** chrome is removed from every block's rendered text exactly
  as `strip_chrome` removes it — paragraph slices, heading slices and table
  cells (`tables.grid`/`to_markdown` take `omit`) — and an emptied row,
  table or block disappears; 0 running heads after, on the whole document
  and on item 15; csco-2016's 10 in-table page numbers likewise.

- **Assumed:** the mutation table could be re-denominated when three labels
  were added.
- **Eval said:** PR #45 R2 — the reviewer re-ran the mutations: 56/61 where
  53/61 was written, 31/61 where 28/61 was, 48/61 on both for M4.
- **Corrected:** every mutation re-run on the final tree and only the
  runner's lines written (ADR-031 §g); the PR #35 lesson in numeric form.
