# ADR-029 — S7: HTML tables are reported as offset records into an unchanged `normalized_text`; their grid and Markdown are derived; table fidelity is a gated per-run metric

Date: 2026-08-23. Status: accepted. Implements S7. Sanctioned exception to the
T8 feature freeze (`tasks/TODO.md`, **Freeze guard**), on the pattern
[ADR-020](ADR-020-fallback-not-justified.md) established for T12 and
[ADR-026](ADR-026-boilerplate-chrome-exclusion.md) applied for S6.

**Ruling**: structured tables ship as an **opt-in annotation, not an edit**. `extract_items(path, tables=True)` adds one envelope key, `tables` — a list of `{start, end, header, rows}` records, one per HTML `<table>` with visible text, in document order; `start`/`end` and every cell's `[start, end]` are offsets into `normalized_text`, which is byte-identical with the flag on and off, as are every item offset, `doc_status` and `warnings`. The row-of-strings grid and the Markdown rendering are *derived* by `src/sec10k/tables.grid()` / `to_markdown()` and never stored; the item body stays the verbatim slice INV-S2 defines, and "the item's tables in Markdown" is a view a consumer asks for by offsets (`tables_in`). Table quality is a per-run metric — cell fidelity and row fidelity against hand-labeled goldens — reported on every run, gated against the values the runner itself recorded with `--update-baseline`.
**Because**: the only way to "preserve table structure through the pipeline" and still satisfy INV-S2 is to not change the pipeline's text. Recording `<table>`/`<tr>`/`<td>` boundaries as offsets costs nothing the text run does not already have (the cells are already emitted, in order, as separate words), moves no offset anywhere, and makes "on and off are identical" true by construction; a rewritten `normalized_text` would move every published figure and every committed anchor (§f2), and a stored cell string or Markdown string is the second copy the contract already refuses for item text. A cell IS a slice, exactly as an item is.
**Enforced by**: `evals/golden/aapl-2025-table.json`, `evals/golden/msft-2013-table.json`, `evals/golden/tgt-2002-table-th.json`, `evals/adversarial/tables-cell-div.json`, `evals/adversarial/tables-layout-bullet.json`, `evals/adversarial/tables-refusal-path.json` (fast) and `evals/adversarial/tables-offsets-invariant.json` (invariant); `src/sec10k/eval_adapter.py` (`table`, `table_markdown`, `tables_sane`, `offsets_invariant_under_tables`, and `envelope_shape`'s `_tables_shape`); `evals/run.py` (the `table_cells_fidelity` / `table_rows_fidelity` gate); `src/sec10k/tables.py::_demo` and `src/sec10k/normalize.py::_demo` in `.github/workflows/ci.yml` — see §g.

---

## a. Why this is a sanctioned exception and not scope creep

The freeze guard says a post-T8 capability is scope creep "no matter how good
it looks". S7 is in scope for the same three reasons ADR-026 §a gave for S6,
each of which holds here and is re-checked rather than inherited:

1. **The human asked for it in writing, on the record** — the S7 row of
   `tasks/TODO.md`, 2026-08-22, which also demanded "its own ADR before any
   code". This document is that ADR; the code in this PR was written to it.
2. **ADR-020/026 set the shape: a post-freeze capability gets a written
   ruling with its cost named**, whichever way it goes. This one is ruled IN;
   the cost is measured on the largest fixture in §f.
3. **It changes no existing behaviour.** With the flag off — every existing
   caller, every existing eval case, the web inspector — not one byte of any
   envelope moves. §d proves it two ways: a 41-fixture main-vs-HEAD snapshot
   (normalized-text sha, every item's status/offsets/confidence/method/
   heading, `doc_status`, `warnings`) is byte-identical, and the equality is
   asserted on every run by `tables-offsets-invariant` (invariant suite).

What would have made it scope creep — rendering tables into `normalized_text`
as Markdown, or dropping them from it — is refused in §f2. The S7 row's own
words, "render to Markdown for the item body", are honoured as a *derived
view* and not as an edit; §b2 says exactly what a consumer gets.

## b. What is recorded, and what is derived

### b1. The record (`src/sec10k/normalize.py::_Plain`, `normalize(..., tables=True)`)

The existing one-pass HTML walk already emits every table's text: `table`,
`tr`, `thead`, `tbody` are `BLOCK_TAGS` (a newline), `td`/`th` emit one
separator space so cells stay separate words. With `tables=True` the same
walk also notes, against the running length of the text it is emitting, where
each `<table>` opens and closes, where each `<tr>` opens and closes, and where
each `<td>`/`<th>` opens and closes. It never emits anything extra: the
recorder reads the position counter, it does not write to the text.

Those positions are pre-`_tidy`. `_tidy` (whitespace canon, ADR-003) then
rewrites the text with the **same three `re.sub` calls it always made** — the
marks-carrying path calls `rx.sub(repl, text)` on the identical pattern and
replacement, so the text cannot differ from the marks-free path — and moves
each recorded offset along with the characters it sat on (an offset inside a
collapsed whitespace run lands on the run's replacement). Finally every
table and cell span is pulled in to its first/last non-space character, so a
cell slice never carries the separator `_Plain` emitted around it, and an
empty cell is clamped inside its table's span.

One record per `<table>` that has at least one row and at least one cell with
visible text:

| field | meaning |
|---|---|
| `start`, `end` | offsets into `normalized_text`, the table's own text (first to last visible character) |
| `header` | how many *leading* rows consist entirely of `<th>` cells (0 when none). `<thead>` is not used as a signal: the committed corpus has no `<thead>` anywhere and `<th>` in two fixtures (tgt-2002, intc-2002), so `<th>` is the only header evidence a case can pin |
| `rows` | list of rows in source order; each row a list of cells in source order; each cell `[start, end]`, or `[start, end, colspan]` when `colspan > 1`. A `<tr>` with no cells is dropped; a `<td>` outside any `<tr>` implies a row, as browsers do |

Closing rules follow browsers because `html.parser` synthesizes no end tags: a
new `<td>` closes the open cell, a new `<tr>` closes the open row, `</table>`
closes both. A `<table>` whose every cell is empty after tightening (iXBRL
spacer/rule tables: 8 of aapl-2025's 62, 1 of jpm-2024's 681) is not recorded
— there is no structure there for a reader to lose.

Cell text is `normalized_text[start:end]`. It can contain a newline: a
`<div>` or `<p>` inside a cell is a block boundary in the text run (ADR-006,
untouched). That is the one shape the flattened text cannot represent — the
row reads as two lines — and the record can (`tables-cell-div`).

### b2. The derived views (`src/sec10k/tables.py`) — and what "the item body" is

- `grid(text, table)` → `[[str, …], …]`: every cell's slice with internal
  whitespace collapsed to one space and stripped; a `colspan=n` cell is its
  text followed by `n-1` empty strings; rows padded to the table's width. So
  columns line up the way the filer's browser lined them up, and the grid is
  what a hand label is written against (§c).
- `to_markdown(text, table)` → GitHub-flavoured Markdown: rows that are empty
  in every cell and columns that are empty in every row (iXBRL width-setting
  rows, `&nbsp;` spacer columns) are dropped from the *view*; the first
  surviving row is the header row — Markdown has exactly one, so a second
  `<th>` row renders as a body row (tgt-2002 Schedule II, `header: 2`, is the
  pinned instance); `|` is escaped. The record keeps everything the view
  drops.
- `tables_in(tables, start, end)` → the records lying wholly inside an item's
  `[start, end)`.

**What "the item body" means for a consumer**: unchanged. `normalized_text
[start:end]` is the body, verbatim, for `extract_items`, the eval vocabulary,
`view.py` and the inspector; the README's description ("item text is readable
only through offsets") stays true. A consumer who wants the body *with* its
tables as Markdown composes it: body slice, plus `to_markdown` over
`tables_in(env["tables"], item.start, item.end)`. That composition is not a
field because storing it would be the second copy. Rendering it in the
inspector is out of S7's scope and is a Debt row (Origin: S7).

### b3. Opt-in, not always-on

`extract_items(path, tables=False)` is the default and `normalize()` without
the flag is the pre-S7 code path plus a no-op branch. Ruled opt-in on the cost
in §f: +20% time and +98% envelope bytes on jpm-2024 is a price a caller
should choose, and the inspector (which serializes envelopes to a browser)
does not ask. Same rule as ADR-026: the key exists only when asked; on a
refusal envelope (`unsupported`/`failed`) it is carried when asked, because
the tables were normalized before the refusal was decided
(`tables-refusal-path`).

## c. The table-quality metric

### c1. Definition

A hand-labeled golden pins one table with a `table` check:
`{"anchor": str, "rows": [[str, …], …], "header": int?, "index": int?}`.
The record is *located* as the first `tables` entry whose slice contains
`anchor` (`index` selects a later one; every committed anchor occurs exactly
once in its filing, provenance records the count). The labeled `rows` are
what `grid()` must derive — transcribed from the raw HTML, cell by cell, with
a `colspan=n` cell written as its text plus `n-1` empty strings, entities
decoded, in-cell line breaks collapsed.

Per check, `src/sec10k/eval_adapter.table_fidelity` computes:

- **cell fidelity** = positions `(i, j)` where labeled and derived text match
  exactly, over the **larger** of the labeled and derived cell counts (an
  extra or missing cell counts against, not for);
- **row fidelity** = rows reproduced exactly (same cells, same order), over
  the larger of the two row counts.

A table that cannot be located scores 0 over the labeled counts. The check
**passes only on an exact match** (and on `header` when labeled): a golden is
the truth, not a tolerance. The fractions are what the run reports.

Per run, `evals/run.py` micro-averages over every `table` check the *scored*
cases ran (debt excluded, exactly as the score is): `table_cells_fidelity`
and `table_rows_fidelity`, printed, written into the report JSON and into the
`history.jsonl` line (ADR-025 schema is extended, shared keys unchanged), and
`null` on a suite that labeled no table — reported as absent, never as a
number (`evals/metrics.py`'s rule).

### c2. Gate and baseline — and what the gate is honestly worth

`--update-baseline` records the two values next to the suite score in
`.eval-baseline.json` (only when the run measured them); every later run
compares, and a drop is a `REGRESSION` with exit 1, like the score. Hard rule
1 holds: the runner is the only writer, and this ADR records the move (§h).

What the metric gate is worth *today*, stated so it is not oversold: every
committed table golden asserts an exact match, so on a green suite the metric
is 1.0 by construction and a drop always coincides with a case going red — the
metric's gate fires together with the suite's, not instead of it. Its value
now is the **magnitude** (M1 in §g: 314/400 cells, 13/31 rows — "colspan
lost" is a 21% cell loss, not a binary) and the time series. It becomes an
independent gate the day a table case is labeled with a tolerance or a
held-out table set is scored unscored; both are Debt rows, neither is claimed.

## d. Offset invariance — the equality, asserted

As ADR-026 §d: `normalized_text`, `items`, `warnings`, `doc_status` are
identical with `tables` on and off, the key is present on exactly one side,
and this is **asserted on every run** by `offsets_invariant_under_tables` in
`tables-offsets-invariant` (jpm-2024, invariant suite) and
`tables-refusal-path` (aapl-2026-10q, the refusal path). Measured 2026-08-23
over all 41 committed dev fixtures and the 5 held-out fixtures: a snapshot of
(normalized-text sha256, `norm_chars`, `doc_status`, `warnings`, every item's
`item`/`status`/`start`/`end`/`confidence`/`method`/`heading_text`) at
`origin/main` (6c71ca6) and at HEAD, default flags, is **byte-identical** —
dev snapshot sha256 `0e276f60…8065b3f` both sides, held-out `91494914…a64b3`
both sides. Every published normalized-length figure, every ADR-021 bench
number and every case anchor therefore stands unchanged.

Also asserted: every record's offsets in bounds, records in document order,
every cell inside its own table, every cell slice tight (`tables_sane`, and
`envelope_shape`'s `_tables_shape` on the contract shape — a `tables` value
that is not a list of well-formed records is red on every case that asks for
tables, §g's M5).

## e. What is NOT claimed

Ruled out honestly; each out-of-scope item that someone might want is a Debt
row in `tasks/TODO.md` with `Origin: S7`.

| shape | ruling |
|---|---|
| `colspan` | **in**: recorded as the cell's third element when > 1; `grid`/Markdown pad it. 3,737 of aapl-2025's 6,443 `<td>` carry one, so without it no modern table aligns |
| `rowspan` | **out**: not recorded, not expanded (12 in aapl-2025, 180 in jpm-2024). A rowspan cell appears once, in the row it is written in; rows below are one cell short. Debt |
| nested tables | **recorded, not claimed**: an inner `<table>` is its own record and its cells also lie inside the outer cell's span (spans nest; records sorted by start). Zero nested tables in the 16 HTML fixtures surveyed, so the path is exercised only by `tables.py`'s self-check logic, not by a fixture. Debt |
| txt-era `<TABLE>`/`<S>`/`<C>` SGML layout | **out**: `normalize()` answers `[]` for the txt era. Those tables are fixed-width lines; their columns are not tagged and their SGML furniture is already what ADR-026 calls `edgar_chrome`. Debt |
| tables split across pages | **out**: two `<table>` elements are two records; nothing joins them. Debt |
| "is it a data table?" | **not classified, by ruling**: every `<table>` with visible text is a record — bullets typeset as four-cell tables (57 of msft-2013's 178), checkbox grids, signature blocks included. A heuristic that dropped "layout" tables would need a definition no committed label set pins, and a false negative is a silently missing table (INV-0's class). The consumer decides from the record (row count, numeric density). `tables-layout-bullet` pins the rule |
| `<thead>`/`<tfoot>` semantics | **out**: `header` counts leading all-`<th>` rows only (no `<thead>` exists in the corpus to pin) |
| Markdown of multi-row headers | **limited, stated**: one header row; further `<th>` rows render as body rows |
| inspector rendering, held-out table labels, bench figures for `tables=True` | **out of S7**: Debt rows |

## f. Cost, measured

`tables=True` on jpm-2024 (12,849,180 raw bytes, 1,213,284 normalized chars,
681 `<table>` / 59,363 `<td>` raw): 680 records, 5,586 rows, 59,347 cells;
extraction 0.58 s → 0.70 s (**+20%**); annotation 1,237,818 bytes of JSON on a
1,267,199-byte envelope (**+98%**). Across all 41 dev fixtures: 3,852 records,
332,916 cells, 6.47 MB of annotation in total, +6% to +20% time per fixture
(measured 2026-08-23, `ADR-029` working tree). The flag-off path pays nothing:
the marks-free `_tidy` branch is the original three `re.sub` calls. This is
why §b3 rules opt-in.

### f2. What was NOT done, and why

Rendering tables into `normalized_text` — as Markdown, or as tab-separated
rows — was considered and refused outright. Every offset after the first
table moves; every committed anchor's `min_chars`/`max_chars` band, every
ADR-021 figure and the normalized-character figures the T3 Debt row already
tracks as stale would need re-deriving a second time; and the stored Markdown
is the second copy. §d's byte-identical snapshot is the measurement that the annotation
route costs the frozen system nothing.

### f3. Corpus untouched

No fixture was added. Every case runs against committed filings —
aapl-2025, msft-2013, tgt-2002, jpm-2024, aapl-2026-10q — so ADR-021 §b8's
populations and every figure derived from them do not move. The shapes the
S7 row names as adversarial (nested `<div>` in a cell, `&nbsp;` padding
cells, a layout table) all exist in the committed corpus and are pinned on
real material rather than synthetic HTML.

## g. Enforcement

Seven cases, the adapter's self-check, two module self-checks. Every case was
**red at `origin/main`** (6c71ca6) — `unknown check type 'table'` /
`'table_markdown'` / `'tables_sane'` / `'offsets_invariant_under_tables'`, 7
FAIL rows on `--suite fast` — and then red again, on **content**, under six
one-line mutations of the working implementation, so none of them passes on
vocabulary alone:

| case | fixture · suite | labels (hand-transcribed from raw HTML; offsets in provenance) |
|---|---|---|
| `aapl-2025-table` | aapl-2025 · fast | Note 11 share-based-compensation table, raw `[1207289, 1213835)`: 4 rows × 18 cols, `colspan=3` throughout; its Markdown; and the cover checkbox grid, raw `[113265, 116920)`: 4 × 21 |
| `msft-2013-table` | msft-2013 · fast | Note 18 assumptions table, raw `[1508504, 1512584)`: 6 × 13, 21 `&nbsp;`-only cells that must be `""`; its Markdown |
| `tgt-2002-table-th` | tgt-2002 · fast | Schedule II, raw `[71129, 75122)`: two all-`<TH>` rows → `header: 2`; 6 × 12; `($322` / `)` kept as two cells; `&#151;` → `—`; its Markdown |
| `tables-cell-div` | aapl-2025 · fast | cover securities table, raw `[98543, 107622)`: a `<div>` inside one cell; 10 × 9; the flattened two-line shape pinned by `norm_contains` beside it |
| `tables-layout-bullet` | msft-2013 · fast | a four-cell bullet table, raw `[50620, 51146)`: recorded, not classified away (§e); its Markdown |
| `tables-offsets-invariant` | jpm-2024 · **invariant** + fast | on-vs-off equality; shape of all 680 records; 600–760 band |
| `tables-refusal-path` | aapl-2026-10q · fast | `unsupported` still carries the list when asked, nothing when not; the `found` name collision that the first build had on exactly this path (hard rule 2) |

Mutations (`ADR-029` working tree, 2026-08-23, each applied alone and
restored; run metric in parentheses):

| mutation | what went red |
|---|---|
| M1 `colspan` never recorded | 4 cases: aapl 49/72 + 71/84 cells, msft 74/78, tgt 62/72, cell-div 54/90 (run: cells **314/400 = 0.785**, rows 13/31) |
| M2 `to_markdown` returns the raw slice | every `table_markdown` check (4 cases); record checks stay green — the renderer is pinned on content |
| M3 header detection off | `tgt-2002-table-th`: `header rows 0 != 2` |
| M4 cell spans not tightened | all 7 cases via `tables_sane`: `cell [106, 191] slice is not tight: '\nANNUAL REPORT…'` |
| M5 the `found` collision re-introduced | `tables-refusal-path`: `envelope_shape: tables is str, not a list`; `offsets_invariant_under_tables: tables OFF emitted a tables key`; `tables_sane: tables is str` |
| M6 separator dropped before `<th>` | `tgt-2002-table-th`: `'olumn A' != 'Column A'`, 62/72 (run: cells 390/400 = 0.975) |

`src/sec10k/tables.py::_demo` and `src/sec10k/normalize.py::_demo` pin the
synthetic shapes the fixtures do not isolate (a spacer table dropped, a
`colspan` cell, a `|` in a cell, `&nbsp;` cells, `tables_in` on offsets,
text identical with the flag on and off) and are run by
`.github/workflows/ci.yml`'s unit-tests job — the gate case is the eval case,
the self-check is the floor (PR #25 R1).

Gate after: `--suite invariant` 46/46, `--suite fast` 94/94, table fidelity
cells 400/400 = 1.0, rows 31/31 = 1.0; every module self-check ok.

## h. Baseline move (hard rule 1)

First measured value, on the working tree that became this PR's first
commit: **`table_cells_fidelity = 1.0` (400/400), `table_rows_fidelity =
1.0` (31/31)** over the five table-labelling cases. Recorded by the runner,
not by hand, with

```
python3 -m evals.run --suite fast --update-baseline
```

which rewrites `.eval-baseline.json` as `{"fast": 1.0, "table_cells_fidelity":
1.0, "table_rows_fidelity": 1.0}` — `fast` unchanged, the two new keys
appended — and writes its own full report (ADR-025: a baseline move is a
decision, worth its evidence). The `--suite all` report of record and the
exact report filenames are cited in the S7 row of `tasks/TODO.md` and in
this section's addendum once the runner has written them on the committed
code.
