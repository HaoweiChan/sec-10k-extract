# ADR-031 — S9: the filing's block structure is reported as offset records into an unchanged `normalized_text`; the whole-document and per-item Markdown are derived views; structure fidelity is a gated per-run metric

Date: 2026-08-23. Status: accepted. Amended in place 2026-08-23 (§h addendum: the baseline move as made). Implements S9. Sanctioned exception to
the T8 feature freeze (`tasks/TODO.md`, **Freeze guard**), on the pattern
[ADR-020](ADR-020-fallback-not-justified.md) established for T12 and
[ADR-026](ADR-026-boilerplate-chrome-exclusion.md) /
[ADR-029](ADR-029-structured-tables-annotation.md) applied for S6/S7 — this
ADR extends ADR-029's annotation-not-edit pattern from tables to the whole
document and is read with it.

**Ruling**: block structure ships as an **opt-in annotation, not an edit**. `extract_items(path, blocks=True)` adds one envelope key, `blocks` (and implies `tables=True`, because table blocks point into the ADR-029 records) — a list, in document order and non-overlapping, of `{kind, start, end, …}` records with offsets into `normalized_text`: `heading` (+`level`; +`item` when it is an item heading the segmenter identified), `paragraph` (+`strong` when the whole block was bold in the HTML), `list_item` (+`ordered`), `table` (+`table`, the index of the ADR-029 record it sits on), or `pre` (the one block a txt-era filing is). `normalized_text` is byte-identical with the flag on and off, as are every item offset, `doc_status` and `warnings`. The Markdown — of the whole document, or of an item by its offsets — is *derived* by `src/sec10k/markdown.to_markdown()` and never stored; the inspector renders that derived Markdown as the item body (the S8 `display_text` path) while the compare pane and `text` keep the raw slice. Structure quality is a per-run metric — block fidelity and boundary fidelity against hand-labeled goldens — reported next to table fidelity on every run and gated against the values the runner itself recorded with `--update-baseline`.
**Because**: the direction literally names the alternative — "parse the filing into Markdown" — and §f2 measures it: rewriting `normalized_text` as Markdown moves the first character on 46 of 46 parseable fixtures (first differing offset 0–74, median 0), every one of the 812 committed item spans, every normalized-length figure ever published (+8 to +140,040 characters per filing), the 74 `min_chars`/`max_chars` band checks and the 6 `table` grids' cell offsets; the annotation route moves **zero** offsets, and that equality is asserted on every run (§d). The one-pass HTML walk already emits a newline at every block-tag boundary, so recording the kind of the text between two boundaries costs nothing the text run does not already have (§b1); the S7 table records and the segmenter's item headings are reused rather than re-derived (§b3); and the Markdown is a function of the envelope exactly as the table grid is.
**Enforced by**: `evals/golden/aapl-2025-blocks.json`, `evals/golden/msft-2013-blocks.json`, `evals/golden/ge-1994-blocks.json`, `evals/golden/xom-2021-blocks.json`, `evals/adversarial/blocks-heading-two-cell-table.json`, `evals/adversarial/blocks-heading-index-table.json`, `evals/adversarial/blocks-bullet-paragraphs.json`, `evals/adversarial/blocks-br-boundary.json`, `evals/adversarial/blocks-refusal-path.json` (fast), `evals/adversarial/blocks-offsets-invariant.json` and `evals/adversarial/blocks-wrapped-invariant.json` (invariant + fast); `src/sec10k/eval_adapter.py` (`blocks`, `markdown`, `blocks_sane`, `offsets_invariant_under_blocks`, and `envelope_shape`'s `_blocks_shape`); `evals/run.py` (the `structure_blocks_fidelity` / `structure_bounds_fidelity` gate); `src/sec10k/markdown.py::_demo`, `src/sec10k/web/view.py::_demo`; `tasks/reviews/s9_markdown_walk.py` + `s9-markdown-walk.json` (the inspector, in a browser) — see §g.

---

## a. Why this is a sanctioned exception and not scope creep

The freeze guard says a post-T8 capability is scope creep "no matter how good
it looks". S9 is in scope for the three reasons ADR-026 §a and ADR-029 §a
gave, re-checked rather than inherited:

1. **The human asked for it in writing, on the record** — the S9 row of
   `tasks/TODO.md`, 2026-08-23, which also demanded "its own ADR before any
   code, on the ADR-029 pattern". This document is that ADR; the code in this
   PR was written to it.
2. **ADR-020/026/029 set the shape: a post-freeze capability gets a written
   ruling with its cost named**, whichever way it goes. This one is ruled IN,
   its cost measured on the largest fixture (§f), and the alternative the
   direction names is ruled OUT with its blast radius measured (§f2), as the
   row required.
3. **It changes no existing behaviour.** With the flag off — every existing
   caller, every existing eval case, the inspector with the box unticked — not
   one byte of any envelope moves. §d proves it two ways: a 47-fixture
   main-vs-HEAD snapshot (42 dev + 5 held-out; normalized-text sha, every
   item's status/offsets/confidence/method/heading, `doc_status`, `warnings`,
   envelope key set) is byte-identical, and the equality is asserted on every
   run by `blocks-offsets-invariant` and `blocks-wrapped-invariant`
   (invariant suite).

What would have made it scope creep — rendering the filing into
`normalized_text` as Markdown — is refused in §f2 with the measurement the S9
row asked for. The row's own words, "parse the filing into Markdown", are
honoured as a *derived view* and not as an edit.

## b. What is recorded, and what is derived

### b1. The record (`src/sec10k/normalize.py::_Plain`, `normalize(..., blocks=True)`)

The existing one-pass HTML walk emits `\n` at every open and close of a
`BLOCK_TAGS` member (`p`, `div`, `h1`–`h6`, `li`, `ol`, `ul`, `table`, `tr`,
`br`, `hr`, …) and nothing for inline tags. With `blocks=True` the same walk
also notes, against the running length of the text it is emitting, where a
run of visible text between two such boundaries begins and ends. **A block
is the text between two block-tag boundaries, outside any `<table>`**; it
opens at the first non-whitespace data after a boundary and closes at the
next boundary. There is no special case: `<br>` is a boundary like `<p>`
(`blocks-br-boundary` pins it — the alternative, letting `<br>` continue a
block, merges a `UNITED STATES<BR>SECURITIES AND EXCHANGE COMMISSION` cover
line into one three-line paragraph whose Markdown a renderer folds onto one
line; the uniform rule keeps what the text run already has). Text inside a
`<table>` belongs to the ADR-029 record, not to a block. The recorder reads
`self.pos`; it never emits, so the text cannot differ with the flag on or
off — by construction, not by care (ADR-029 §b1's argument, unchanged).

Offsets are pre-`_tidy`. They ride through `_tidy` on the same `_sub_map`
path the table offsets use (one sorted mark list, one pass), then every block
is pulled in to its first/last non-space character and a block empty after
that is dropped. One `table` block is added per ADR-029 record (the record's
own tightened span, the record's index); the list is sorted by start and a
block starting inside the previous block's span is dropped — the only such
case is a table nested inside another's cell, which ADR-029 §e records but
does not claim (zero in the corpus, §e).

A txt-era filing has no markup to recover structure from (ADR-006: the
newlines ARE the document), so it is exactly one block, `{kind: "pre", start:
0, end: len(text)}` (`ge-1994-blocks`); `[]` when the text is empty.

| field | meaning |
|---|---|
| `kind` | `heading`, `paragraph`, `list_item`, `table`, `pre` — nothing else |
| `start`, `end` | offsets into `normalized_text`, first to last visible character |
| `level` | headings only: 1–6 from `<h1>`–`<h6>`, or 2 for a promoted item heading (§b3) |
| `item` | headings only, promoted ones: the item code whose span opens with this block |
| `strong` | `true` when every visible character of the block was emitted inside a bold context (§b2); absent otherwise |
| `ordered` | list items only: whether the innermost open list is `<ol>` |
| `table` | table blocks only: the index into `tables` of the record the block sits on |

### b2. The kinds — what counts, and what does NOT

- **heading** — the text inside `<h1>`–`<h6>` is a heading of that level,
  because the HTML says so. Measured over the corpus this rule pins almost
  nothing a reader would call a heading: the only `<hN>` tags in the 34
  HTML/iXBRL fixtures are `<h5>` in seven legacy filings, and every one that
  carries text is the page-top back-link `Table of Contents` (axp-2008 98,
  ba-2003 129, bac-2006 182, msft-2013 96, nike-2006 80, wfc-2008 30; gs-2002's
  51 are `&nbsp;` only and so no block). No fixture has `<h1>`–`<h4>` or
  `<h6>`. Real headings in these filings are styled paragraphs (§b3 handles
  the item headings; the rest stay paragraphs, below).
- **paragraph** — everything else outside a table: `<p>`, `<div>`, `<td>`-less
  text, text after a `<br>`, a page number, a running head. A *styled*
  heading — `<P align=center><U>GENERAL</U></P>` (msft-2013), `<B>PART I</B>`,
  a Workiva `<span style="font-weight:700">Macroeconomic and Industry
  Risks</span>` — is a paragraph, **never a heading**: underline, centering,
  size and bold are styling, and a heading level inferred from them would be
  a guess no label set pins (the S9 row's adversarial shape; `msft-2013-
  blocks` window 1, `aapl-2025-blocks` window 1). What the annotation does
  carry for such a paragraph is **`strong`**: the HTML carries bold two ways —
  `<b>`/`<strong>`, or a `style` with `font-weight: bold|bolder|600–900` on
  any tag (Workiva iXBRL writes `<span style="font-weight:700">` and never
  `<b>`: aapl-2025 has 415 such styles and 0 `<b>`; msft-2013 has 3,392 `<b>`
  and 0 bold styles) — and a block is `strong` iff every character of visible
  data in it was emitted while at least one such context was open. Partial
  emphasis (`<B><I>Principal Products and Services</I></B>: Windows…`, xom's
  `Price<span bold> </span>– Higher realizations…` where the only bold run
  is a space) is **not** recorded: `strong` is whole-block or nothing, and
  inline runs are a Debt row (§e). A bold context closes at the matching end
  tag (innermost of that name); an unclosed carrier therefore leaks until the
  next same-name end tag — browsers do the same for `<b>`/`<font>` (the
  active-formatting-element rule) and differently for `<span>`. Measured: the
  `malformed-html` fixture (15 `</font>` removed from premier-pacific-2016)
  has 177 strong blocks where its source has 79, the leak named in §e.
  Italic is not recorded (§e).
- **list_item** — the text inside `<li>` (cleared by `</li>`, `</ol>`,
  `</ul>`), `ordered` when the innermost open list is `<ol>`. **Zero `<li>`
  in the committed corpus** (the two fixtures with `<ul>`, intc-2002 and
  tgt-2002, use it as an indent wrapper around `<p>`), so the kind is pinned by
  `markdown.py::_demo` only and claimed no further. A list typeset as bullet
  characters in `<div>`s (cat-2023: 103 `•`, 0 `<li>`) is paragraphs
  (`blocks-bullet-paragraphs`); a list typeset as four-cell tables (msft-2013,
  57 of 178 tables) is table blocks, as ADR-029 §e already ruled.
- **table** — one block per ADR-029 record, on the record's span. Nothing is
  re-derived: the block points at the record and the renderer calls
  `tables.to_markdown` on it.
- **pre** — txt era only. HTML `<pre>` does not occur in the corpus, and
  `_Plain` collapses its whitespace like any other element's, so an HTML
  `<pre>` would be a paragraph; not claimed (§e).

By construction — every visible character lies between two boundaries or
inside a table — **the blocks cover every non-space character of
`normalized_text`**: measured 0 uncovered characters on all 47 fixtures, and
asserted on every run by `blocks_sane`, so the view can lose no text.

### b3. Item headings — the one promotion, and its limit

The segmenter already knows where every item heading is: `verbatim` asserts
each span opens with its `heading_text`. So after segmentation,
`extract.py::_promote_item_headings` turns the block at every span-carrying
item's `start` into `{kind: "heading", level: 2, item: <code>}` — when it is
a paragraph block, or a table block whose record has **exactly one row with
visible text** (jnj-2016, spatz-2014, wmt-2010, axp-2008, gs-2002, wfc-2008
and bac-2006 typeset `Item N.` | `TITLE` as a two-cell table). Measured
2026-08-23 over the 624 span items of the 34 HTML/iXBRL fixtures: 488 are
paragraph blocks whose text equals `heading_text`, 135 are one-row tables,
and **one** — bac-2006 item 7, whose heading is the first cell of the MD&A's
own 72-row index table (36 visible rows) — is neither and stays a table
(`blocks-heading-index-table`): promoting it would swallow the index into an
`##`. Level 2 for every item; Part headings (`PART I`) are not promoted
(§e). A promoted heading drops `strong` (a heading is strong by kind). On a
refusal envelope (`unsupported`/`failed`) there are no items and nothing is
promoted (`blocks-refusal-path`). Item boundaries and block boundaries
coincide on every HTML fixture: 0 of 624 span items start or end inside a
block; in the txt era every item is a window onto the one `pre` block, which
is what §b4's clipping rule is for.

### b4. The derived views (`src/sec10k/markdown.py`) — and what "the item body" is

- `to_markdown(text, blocks, tables, start=0, end=None, omit=())` →
  GitHub-flavoured Markdown of `text[start:end]` — the whole document by
  default, an item by its offsets. A block straddling the window is
  **clipped** to it and its clipped slice renders as its kind, except a
  clipped table, which has no grid and renders as a paragraph. A block lying
  wholly inside any `omit` span (the ADR-026 chrome runs, when the caller also
  asked for exclusion) is left out — the S8 checkbox keeps its meaning in
  Markdown mode. Rendering: a heading is `#`×level + its text with internal
  whitespace collapsed (`## Item 1. BUSINESS` for the two-cell shape); a
  strong paragraph is `**…**`; a list item `- ` / `1. `; a table is
  `tables.to_markdown` (ADR-029 §b2, unchanged); `pre` is the slice in a
  backtick fence longer than any backtick run inside it. Paragraph and heading
  text is escaped so no filing prose can open a Markdown construct:
  backslash, asterisk, underscore, backtick, square brackets, angle brackets,
  tilde and hash everywhere; greater-than, plus, equals, pipe, hyphen, or a
  number followed by a period or parenthesis at line start. Blocks are joined
  by one blank line.
- `blocks_in(blocks, start, end)` → the blocks overlapping `[start, end)`.

**What "the item body" means for a consumer**: unchanged from ADR-029 §b2 —
`normalized_text[start:end]`, verbatim. The item's Markdown is
`to_markdown(text, blocks, tables, start, end)`, a view a consumer asks for
by offsets, deliberately not a field.

### b5. Opt-in, not always-on; the inspector asks

`extract_items(path, blocks=False)` is the default and the pre-S9 code path.
Ruled opt-in on the cost in §f (1.37× time, +119% envelope bytes on jpm-2024,
most of it the implied `tables`). The inspector asks per request through a
second checkbox, `render as Markdown`, that rides the same three wires the
S8 checkbox rides (`markdown` in the JSON body / `?markdown=1` on upload →
`_run(markdown=…)` → `extract_items(blocks=markdown)`); `build_view` then
sets `display_text` to the item's Markdown — rendered from the first
`DISPLAY_MAX` characters of the span, so `truncated` and `chars` keep their
meaning — and `markdown: true` on the payload, and `index.html` renders that
string with a forty-line Markdown-to-HTML function for exactly the subset
§b4 emits (ATX headings, paragraphs, whole-paragraph `**strong**`, `- `/`1. `
items, GFM tables, fenced pre), HTML-escaping every cell and paragraph after
undoing the backslash escapes it wrote — no dependency, no CDN (S3-FONT), no
other syntax parsed. `text` stays the verbatim slice (PR #27 R1: it is also
`findAnchor`'s oracle) and the compare pane still shows the original filing;
with the box unticked the pane is the same `<pre>` it was. The box is
default-off, and the `repo_hygiene` wire pins that S8 put on
`exclude_boilerplate` now also read the Markdown flag on all three wires
(`boilerplate_plumbing`'s `WIRE_UI`/`WIRE_API`, moved deliberately with the
literals they pin; the two regression fixtures re-spelled to match, counts
unchanged at 8 and 9).

## c. The structure-fidelity metric

### c1. Definition

A hand-labeled golden pins a **window** with a `blocks` check: `{"blocks":
[{kind, start, end, level?, ordered?, strong?, item?, head?, tail?}, …]}` —
the complete block sequence the annotation must hold between the first
label's `start` and the last label's `end`, transcribed from the raw HTML by
the §b rules, offsets into `normalized_text`. `head`/`tail` are the label's
own anchors: the check first verifies `normalized_text[start:end]` opens
with `head` and closes with `tail`, and reports a mismatch as a **label**
defect, not as a miss, so a reviewer can re-derive every offset from the
text and a mistyped label cannot pass as a finding against the code.

Per check, `src/sec10k/eval_adapter.structure_fidelity` takes the derived
blocks overlapping the window (`markdown.blocks_in`) and computes, with
`total = max(labeled, derived)`:

- **bounds fidelity** = labeled `(start, end)` pairs that some derived block
  in the window has, over `total` — the boundary agreement;
- **block fidelity** = labeled blocks reproduced exactly (kind, start, end,
  level, ordered, strong, item — everything a label states and nothing it
  omits; a table block's record index is not labeled, its record is checked
  to sit on the block by `blocks_sane`), over `total` — kind agreement on top
  of the boundaries.

An envelope without blocks scores 0 over the labeled counts. The check
**passes only when the derived sequence equals the labeled one** (a golden
is the truth, not a tolerance); the fractions are what the run reports. The
`markdown` check pins the derived view itself (an item's span, explicit
offsets, or `anchor`..`end_anchor`) against an exact string, ADR-029's
`table_markdown` lesson restated: a check that reads only the record cannot
see a no-op renderer (§g M1).

Per run, `evals/run.py` micro-averages over every `blocks` check the *scored*
cases ran (debt excluded, exactly as the score and the table metric are):
`structure_blocks_fidelity` and `structure_bounds_fidelity`, printed on the
line after table fidelity, written into the report JSON and into the
`history.jsonl` line (ADR-025 schema extended again, shared keys unchanged),
`null` on a suite that labeled no block — absent, never a number.

### c2. Gate and baseline — and what the gate is honestly worth

`--update-baseline` records the two values next to the suite score and the
two table keys in `.eval-baseline.json` (only when the run measured them);
every later run compares, and a drop is a `REGRESSION` with exit 1, like the
score (§h). Hard rule 1 holds: the runner is the only writer, and this ADR
records the move.

What the gate is worth *today*, stated as ADR-029 §c2 stated it: every
committed `blocks` golden asserts an exact sequence, so on a green suite the
metric is 1.0 by construction and a drop always coincides with a case going
red. Its value now is the **magnitude** (§g: strong never recorded is a 17%
block loss with 100% boundary agreement; table blocks dropped is a 22% loss
on both; the name collision is a 52% loss) and the time series. It becomes an
independent gate the day a `blocks` case is labeled with a tolerance or a
held-out structure set is scored — a Debt row, not claimed.

## d. Offset invariance — the equality, asserted

As ADR-026 §d and ADR-029 §d: `normalized_text`, `items`, `warnings`,
`doc_status` are identical with `blocks` on and off, the `blocks` and `tables`
keys are present on exactly one side, and this is **asserted on every run**
by `offsets_invariant_under_blocks` in `blocks-offsets-invariant` (aapl-2025,
a primary `.htm`) and `blocks-wrapped-invariant` (msft-2013, an SGML-wrapped
`.htm`) — both invariant suite — and `blocks-refusal-path` (aapl-2026-10q,
the refusal path). Two fixtures, not one, because the first build of this
annotation failed each in a different direction (§g, the name collision).
Measured 2026-08-23 over all 42 committed dev fixtures and the 5 held-out
fixtures: a snapshot of (normalized-text sha256, `norm_chars`, `doc_status`,
`warnings`, envelope key set, every item's
`item`/`status`/`start`/`end`/`confidence`/`method`/`heading_text`) at
`origin/main` (145fe4a) and at HEAD, default flags, is **byte-identical** —
dev snapshot sha256 `fa26ff98…bef05` both sides, held-out `da21a260…2714`
both sides — and with the flag ON, `DETERMINISM_FIELDS` are identical to the
flag-off envelope on 47 of 47. Every published normalized-length figure, every
ADR-021 bench number and every case anchor therefore stands unchanged.

Also asserted, by `blocks_sane` on every blocks case: offsets in bounds,
document order, non-overlapping, every slice tight, every kind in the enum, a
table block sitting exactly on its record, a heading carrying a level, and
every non-space character of `normalized_text` inside some block; and by
`envelope_shape`'s `_blocks_shape` on the contract shape (a `blocks` value
that is not a list of well-formed records, or a `blocks` without `tables`,
is red on any case that asks for blocks).

## e. What is NOT claimed

Each out-of-scope item that someone might want is a Debt row in
`tasks/TODO.md` with `Origin: S9`.

| shape | ruling |
|---|---|
| headings from styling | **out**: bold, underline, centering, font size never make a heading (§b2). A bold whole block is `strong`; the inspector renders it bold, not as `#` |
| Part headings | **out**: `PART I` stays a (strong) paragraph; only item headings are promoted (§b3) |
| inline emphasis | **out**: `strong` is whole-block; a bold lead-in or a bold phrase inside a paragraph is not recorded. Italic (`<i>/<em>/font-style:italic`) is not recorded at all. Debt |
| bold leaking from an unclosed carrier | **known**: an unclosed `<b>`/`<font style=bold>` marks every following block strong until the next same-name end tag (malformed-html: 177 vs 79). The text is untouched and the view loses nothing; the flag is wrong on those blocks. Debt |
| `<li>` lists | **recorded, pinned only synthetically**: no committed fixture has one (§b2). Nested lists render flat; numbering is `1.` for every ordered item (Markdown renumbers) |
| bullet glyphs / bullet tables | **not lists**: paragraphs and table blocks respectively (§b2); the inspector shows a bullet table as a one-row table |
| definition lists, blockquotes, HTML `<pre>`, `<caption>` | paragraphs (`<dl>/<dt>/<dd>` in intc-2002 and tgt-2002 only; 0 `<pre>`, 0 `<caption>` in the corpus). Debt |
| paragraphs split by a page break | two blocks, not rejoined (msft-2013 window 2) |
| images | emit no text and no block; render as the S10 placeholder once S10 lands (xom-2021's `<img>` at raw 1704772 is the pinned instance: no block) |
| txt-era structure | one `pre` block; item headings inside it are not promoted, fixed-width tables stay text (ADR-029 §e). Debt |
| nested tables | the inner record gets no block (§b1); ADR-029 §e's "recorded, not claimed" stands |
| held-out structure labels, a bench column for `blocks=True`, tolerance-labeled goldens | out of S9: Debt rows |
| Markdown round-trip | **not a property**: the Markdown is escaped so prose cannot open a construct, but no check re-parses it; the inspector's renderer parses only the subset §b4 emits |

## f. Cost, measured

`blocks=True` on jpm-2024 (12,849,180 raw bytes, 1,213,284 normalized chars):
4,700 blocks (4,020 paragraphs + 680 tables), extraction 0.594 s → 0.814 s
(**1.37×**; `tables=True` alone 0.733 s, 1.23×), envelope 1,267,198 →
2,780,859 bytes (**+119%**, of which the `blocks` key is 275,819 bytes, +22%,
and the implied `tables` key 1,237,818). Across all 47 dev + held-out
fixtures: 32,228 blocks, 1,894,734 bytes of block annotation (medians of 5
runs, 2026-08-23, this working tree). The flag-off path pays nothing: the
marks-free `_tidy` branch is the original three `re.sub` calls. This is why
§b5 rules opt-in and why the inspector asks per request.

### f2. The alternative the direction names — `normalized_text` itself as Markdown — measured and refused

The S9 row required an explicit ruling on "making `normalized_text` itself
Markdown", with the blast radius measured on every fixture if it were taken.
It is **refused**; the measurement is why, and not a preference.

Method (2026-08-23, this working tree): for every fixture, render the whole
document with `to_markdown` and compare it to `normalized_text` character by
character — that is exactly the string the alternative would have stored.

| measured over the 46 parseable fixtures (42 dev + 5 held-out, less `truncated-download`, which normalizes to nothing) | value |
|---|---|
| first differing offset | **0 – 74, median 0** (44 of 46 below 25: the cover page's first bold line is the first strong paragraph) |
| item spans whose offsets move | **812 of 812** — every span-carrying item on every fixture |
| normalized-length change | **+8 (every txt-era filing, the fence) to +140,040 (jpm-2024), median +4,734** — so every `norm_chars` figure, every ADR-021 bench figure derived from lengths, and every normalized-character figure in the README and the ADRs moves |
| offset-band checks that would need re-deriving | **74** (`min_chars` 41 + `max_chars` 33) — they bound span lengths in normalized characters |
| `table` grids whose cell offsets move | **6 of 6** (the S7 records index the text) |
| text anchors that stop occurring verbatim | **1 of 71** `text_contains`/`norm_contains` values — `tables-cell-div`'s flattened two-line shape, which a table grid rewrites; the other 70 survive because Markdown leaves most prose alone |

Against that, the annotation route moves **zero** offsets (§d), and the
Markdown a consumer gets is the same string either way — it is a function of
`normalized_text` and `blocks`, whether stored or derived. Storing it would
also be the second copy the contract refuses for item text (ADR-029 §f2),
and INV-S5 ("`normalized_text` is the readable filing") would have to admit
`##`, `**`, `|---|` and backslash escapes as readable filing text. The
rejection rests on those two counted rows — 812/812 spans and 46/46 lengths
— not on the anchor count, which is small precisely because Markdown is
mostly the text itself.

### f3. Corpus untouched

No fixture was added. Every case runs against committed filings — aapl-2025,
msft-2013, ge-1994, xom-2021, jnj-2016, bac-2006, cat-2023, intc-2002,
aapl-2026-10q — so ADR-021 §b8's populations and every figure derived from
them do not move. The S9 row's adversarial shapes (a styled-paragraph heading
that must not become `#`; a list rendered with bullet characters; the human's
own prose-and-tables example) all exist in the committed corpus and are
pinned on real material.

## g. Enforcement

Eleven cases, the adapter's self-check, three module self-checks, a browser
walk. Every case was **red at `origin/main`** (145fe4a) — `unknown check
type 'blocks'` / `'blocks_sane'` / `'markdown'` /
`'offsets_invariant_under_blocks'` (and `no tables in result` on
`blocks-offsets-invariant`'s `tables_sane`), `--suite fast` 98/108 = 0.907
with the ten cases that existed at that point all FAIL (a `--report` run
on the stashed tree, 2026-08-23 23:14; the per-case reasons are the
vocabulary lines above, and the run's own JSON was a working-tree artifact,
not kept — ADR-025 keeps cited reports only) — and then red again, on **content**, under nine one-line
mutations of the working implementation, so none of them passes on
vocabulary alone. One defect was found mid-build and became a case before it
was fixed (hard rule 2): `select_and_normalize`'s local `blocks =
split_documents(raw)` shadowed the new `blocks` parameter — the S7 `found`
collision again — so a primary `.htm` (no `<DOCUMENT>` wrapper, empty list)
got **no** annotation when asked and an SGML-wrapped filing got `blocks` and
`tables` **unasked** on the default path. Caught by the first all-fixture
sweep, before any commit; renamed `docs`; pinned on both shapes (M8).

| case | fixture · suite | labels (hand-transcribed from raw HTML; raw offsets in provenance) |
|---|---|---|
| `aapl-2025-blocks` | aapl-2025 · fast | Item 1A opening, normalized `[24697, 26464)`: promoted heading, 2 paragraphs, strong sub-heading, strong bold-italic lead sentence, paragraph (6 blocks); Note 11 window `[169407, 169989)`: strong, paragraph, the S7-labeled table, paragraph; both windows' Markdown (the table part is the S7 `table_markdown` string verbatim) |
| `msft-2013-blocks` | msft-2013 · fast | `[6361, 6833)`: strong `PART I`, promoted `ITEM 1. BUSINESS`, underlined `GENERAL` as a plain paragraph (the styled heading that must not become `#`), paragraph; `[9028, 9064)`: page number, `<h5>` → level 5, two running heads; `[10952, 11944)`: paragraph, 8 bullet tables, partially-bold paragraph (not strong); Markdown of windows 1 and 3 |
| `ge-1994-blocks` | ge-1994 · fast | one `pre` block `[0, 362717)`; item 1's opening `[4020, 4420)` as a fence |
| `xom-2021-blocks` | xom-2021 · fast | item 7 as extracted (promoted heading + pointer paragraph; Markdown by item); the MD&A window `[158704, 160012)` — running head, strong sub-heading, the Upstream results table, strong, italic paragraph (not strong), `Price –` paragraph whose only bold is a space (not strong), 3 paragraphs, footnote; Markdown of the post-table sub-window |
| `blocks-heading-two-cell-table` | jnj-2016 · fast | the `Item 1.` / `BUSINESS` two-cell heading table promoted to `## Item 1. BUSINESS` |
| `blocks-heading-index-table` | bac-2006 · fast | item 6's one-row table promoted; item 7's 72-row MD&A index table NOT promoted |
| `blocks-bullet-paragraphs` | cat-2023 · fast | six `<div>•text</div>` bullets are paragraphs, not list items; Markdown |
| `blocks-br-boundary` | intc-2002 · fast | one `<P>` with two `<BR>` is three strong blocks; Markdown |
| `blocks-refusal-path` | aapl-2026-10q · fast | `unsupported` still carries `blocks` + `tables` when asked, nothing when not; no promotion |
| `blocks-offsets-invariant` | aapl-2025 · **invariant** + fast | on-vs-off equality on a primary `.htm`; shape and coverage of all 698 blocks; 650–750 band |
| `blocks-wrapped-invariant` | msft-2013 · **invariant** + fast | the same on an SGML-wrapped `.htm`; 1,300–1,400 band |

Mutations (this working tree, 2026-08-23, each applied alone and restored;
run metric in parentheses, `blocks`/`bounds` over 61 labeled blocks):

| mutation | what went red |
|---|---|
| M1 `to_markdown` returns the raw slice | every `markdown` check: 6 cases `markdown differs`; blocks 61/61 — the renderer is pinned on content, not through the record |
| M2 promoted item headings at level 3 | 5 cases (`aapl`, `msft`, `xom`, both heading cases): `got {'kind': 'heading', …, 'level': 3}` (blocks **53/61 = 0.9138**, bounds 1.0) |
| M2b `<hN>` level + 1 | `msft-2013-blocks` window 2, `blocks-heading-index-table`: the `<h5>` at level 6 (blocks 56/61) |
| M3 `strong` never recorded | 5 cases (blocks **48/61 = 0.8276**, bounds 61/61 — boundaries right, kinds wrong, the metric's two numbers separating as designed) |
| M4 table blocks dropped | 9 cases: every window with a table (`3 derived vs 4 labeled`), and `blocks_sane` on all nine: `visible text outside every block at 468: 'California 94-2404110…'` (blocks **45/61 = 0.7759**, bounds 45/61) |
| M5 block boundaries untightened | 6 cases via `blocks_sane` only: `block 57 slice is not tight: '\n\nprovide management with a comprehensiv…'` — the labeled windows hold no loose block, so the metric stays 61/61; the sanity check is the pin |
| M6 item-heading promotion off | 5 cases: `got {'kind': 'paragraph', 'start': 24697, …}` / `{'kind': 'table', 'start': 14698, …}` (blocks 53/61) |
| M7 promotion without the one-visible-row guard | `blocks-heading-index-table`: `got {'kind': 'heading', 'start': 54348, 'end': 55571, …}` (blocks 57/61) |
| M8 the `blocks`/`docs` shadowing re-introduced | 6 cases: `blocks ON emitted no blocks + tables lists` (aapl-2025, aapl-2026-10q), `blocks OFF emitted a blocks/tables key; default must change nothing` (msft-2013), `no blocks in result` on the three primary-.htm goldens (blocks **28/61 = 0.4828**) |
| M9 `<br>` does not close a block | `blocks-br-boundary` only: `1 derived vs 3 labeled in [68, 139)` — every other case stays green, which is why that case exists (blocks 58/61 = 0.9508) |

`src/sec10k/markdown.py::_demo` pins the synthetic shapes the fixtures do
not isolate (`<h2>`, a whole-bold `<div>`, a half-bold `<p>`, `<ul>`/`<ol>`
items with and without `</li>`, a clipped window, the `omit` rule, every
escape, the txt fence growing past a backtick run);
`src/sec10k/web/view.py::_demo` pins the inspector payload (Markdown
`display_text`, raw `text`, `truncated` from the span, a chrome block omitted
under both flags, absent `display_text` when the Markdown is the slice);
`src/sec10k/normalize.py::_demo` and `tables.py::_demo` keep their
three-tuple `normalize` calls green. `tasks/reviews/s9_markdown_walk.py`
drove the inspector in headless Chromium (record
`tasks/reviews/s9-markdown-walk.json` + three screenshots): aapl-2025 item 7
renders 1 `<h2>`, 106 `<p>`, 6 `<table>`; msft-2013 item 1 renders 1 `<h2>`,
121 `<p>`, 8 bullet tables, 14 `<b>`; ge-1994 item 1 renders one `<pre>`;
the S3 fixture banner reads `success — 18 extracted` with the box ticked;
with the box unticked the pane is the plain `<pre class="text">` and the
header carries no `markdown` label; `tasks/reviews/s3_browser_walk.py`
re-run on this build (record `tasks/reviews/s3-browser-walk-s9.json`) drives
the three S3 modes with the box unticked — fixture `success — 18 extracted`,
upload `ambiguous — 4 extracted`, url `failed`, `mode_failures: []`, font
fallback DEGRADES as before; every `ui-*` and `repo_hygiene` case
(contrast, layout, plumbing, ledger shape) is green with the new stylesheet
rules and the moved wire pins.

Gate after: `--suite invariant` 52/52, `--suite fast` 109/109, table fidelity
cells 400/400 = 1.0, rows 31/31 = 1.0, structure fidelity blocks 61/61 = 1.0,
bounds 61/61 = 1.0; every module self-check ok.

## h. Baseline move (hard rule 1)

First measured value, on the working tree that became this PR's first
commit: **`structure_blocks_fidelity = 1.0` (61/61), `structure_bounds_fidelity
= 1.0` (61/61)** over the twelve `blocks` checks of the eleven cases. To be
recorded by the runner, not by hand, with

```
python3 -m evals.run --suite fast --update-baseline
```

which rewrites `.eval-baseline.json` as `{"fast": 1.0, "table_cells_fidelity":
1.0, "table_rows_fidelity": 1.0, "structure_blocks_fidelity": 1.0,
"structure_bounds_fidelity": 1.0}` — the three existing keys unchanged, the
two new keys appended — and writes its own full report (ADR-025). The
addendum below records the move as made, on the committed code; PR #34 R1's
lesson is applied this time: the `history.jsonl` lines of the recording runs
are committed with the move.

**Addendum — the move as made, on the committed code (4730052, clean tree).**
`python3 -m evals.run --suite all` → `evals/report/20260823-234841-all.json`
(`git_sha` 4730052…, score 109/109, `structure_blocks_fidelity` 1.0,
`structure_bounds_fidelity` 1.0, table fidelity 1.0/1.0; per case:
aapl-2025-blocks 10/10 blocks · 10/10 bounds, msft-2013-blocks 18/18 · 18/18,
xom-2021-blocks 12/12 · 12/12, ge-1994-blocks 1/1 · 1/1, blocks-bullet-
paragraphs 8/8, blocks-heading-index-table 5/5, blocks-heading-two-cell-table
4/4, blocks-br-boundary 3/3). Then `python3 -m evals.run --suite fast
--update-baseline` → `evals/report/20260823-234923-fast.json` and the
runner's own line `baseline['fast'] = 1.000 (recorded); baseline
['table_cells_fidelity'] = 1.0; baseline['table_rows_fidelity'] = 1.0;
baseline['structure_blocks_fidelity'] = 1.0; baseline
['structure_bounds_fidelity'] = 1.0`. The committed `.eval-baseline.json`
diff is exactly the runner's write: three keys unchanged, two appended. The
`history.jsonl` lines of both recording runs (sha `4730052`, `dirty: false`)
**are committed** with this move, together with the line the pre-commit
hook appended while making 4730052 itself (sha `145fe4a`, `dirty: true` —
the hook runs before the commit object exists) — PR #34 R1's gap, closed the
way it asked; the time series for the two keys therefore starts with the
recording runs.

That the gate is real and not a printed number: with a baseline holding
**only** the two structure keys (no `fast` key, so the score gate cannot be
what fires) and mutation M3 applied, `python3 -m evals.run --suite fast
--baseline <metric-only>` prints `structure fidelity: blocks 0.7869 (48/61),
bounds 1.0000 (61/61)` and exits 1 with `REGRESSION: structure_blocks_fidelity
0.7869 < baseline 1.0000` (2026-08-23, restored after).
