# 015 — S7: structured tables as offsets, and a metric that says how wrong (2026-08-23)

The S7 row asked for table structure "preserved through the pipeline instead
of flattened into the text run", rendered to Markdown for the item body, and
scored by a cell/row-fidelity metric — post-freeze, ADR first. Ruling:
[ADR-029](../specs/decisions/ADR-029-structured-tables-annotation.md).

## The prompt decisions that mattered

- **"Preserve structure" and "never edit `normalized_text`" are the same
  requirement, not a trade-off.** The first instinct is to rewrite the text
  run — emit Markdown rows, or at least tab-separated cells — and every
  offset downstream of the first table moves. ADR-026 had already paid for
  the insight that the only way to remove text under INV-S2 is to not remove
  it; the mirror holds for adding structure: the only way to add it is to
  not add it to the text. The HTML walk already emits every cell as a
  separate word, in order; recording where each `<table>`/`<tr>`/`<td>`
  starts and ends against the text it is already emitting is the whole
  capability. A cell becomes a slice, exactly as an item is, and "on and off
  are byte-identical" is true by construction rather than by care.

- **The row says "render to Markdown for the item body"; the ADR answers
  "as a derived view" and says why.** A stored Markdown string — or stored
  cell strings — is the second copy the contract already refuses for item
  text. `tables.grid()` and `tables.to_markdown()` are functions of the
  envelope, like `strip_chrome`. What "the item body" means for a consumer
  had to be named explicitly so the reading could not drift: still the
  verbatim slice; the tables-as-Markdown composition is something a consumer
  asks for by offsets.

- **Opt-in, measured.** jpm-2024 is +20% time and +98% envelope bytes with
  the flag on. That is a price a caller chooses; the inspector serializes
  envelopes to a browser and does not ask. Same shape as ADR-026, so the
  precedent did the arguing.

- **A metric that is 1.0 by construction on a green suite is still worth
  gating — if you say so out loud.** Every table golden asserts exact
  equality, so the metric's gate fires together with the suite's gate, never
  instead of it. The honest framing is that its value *today* is magnitude and
  history (one lost attribute is a 21% cell loss, not a binary), and that it
  becomes an independent gate only when a tolerance-labelled or held-out
  table set exists — written as Debt rather than implied.

- **"Decide and rule" on layout tables meant refusing to classify.** A
  third of msft-2013's 178 tables are bullets and footnotes typeset as
  `<TABLE>`. Dropping them needs a definition of "data table" no committed
  label set pins, and a false negative is a silently missing table — the
  silent-failure class the repo exists to refuse. Every `<table>` with visible
  text is a record; the consumer decides from the record.

## Assumption → Eval contradiction → Correction

- **Assumed:** recording offsets in the one-pass HTML walk and mapping them
  through `_tidy` is enough; the spans come out right.
- **Eval said:** 10,177 "cells outside their table" on jpm-2024 in the first
  sanity sweep. All of them empty cells in iXBRL width-setting rows, whose
  offsets sat two characters before the table's tightened start — the table
  span had been pulled in past the whitespace the empty cells lived in.
- **Corrected:** empty cells are clamped inside `[start, end]` after
  tightening; `tables_sane` asserts every cell inside its own table and every
  slice tight, on all seven cases, and M4 in ADR-029 §g shows it red.

- **Assumed:** threading the normalization result through `extract.py` under
  a local named `found` was a harmless choice of name.
- **Eval said:** on the `unsupported` path, with the flag OFF, every envelope
  carried `tables: "10-Q"` — the refusal branch already had a local `found =
  meta["form_type"] or "none"` for its warning text, and the later name won.
  Caught by the first all-fixture sweep (`"tables" not in off` failed on
  aapl-2026-10q), before any commit.
- **Corrected:** renamed, and — hard rule 2 — pinned: `tables-refusal-path`
  asserts no key when off and a list when on, on that path; M5 re-introduces
  the collision and the case goes red three ways (`envelope_shape`,
  `offsets_invariant_under_tables`, `tables_sane`).

- **Assumed:** a one-row table's Markdown with an all-empty first row is
  fine — Markdown needs a header, the first row is the header.
- **Eval said:** the first table rendered on a real iXBRL filing opened with
  `|  |  |  |  |  |  |  |` — every Workiva table starts with a width-setting row
  of 18 empty `<td/>`, so every Markdown header was blank.
- **Corrected:** rows empty in every cell and columns empty in every row are
  dropped from the *view* only; the record keeps them (the golden grids label
  all of them) and `table_markdown` pins the view on four real tables.

- **Assumed:** a bullet-table provenance could say "well over 60" of
  msft-2013's one-row tables are the bullet shape.
- **Eval said:** measured over the derived grids, 88 one-row tables: 57
  bullets, 29 footnote rows, 2 cover check-boxes.
- **Corrected:** the numbers, before commit. Counts are measured or not
  written.

- **Assumed:** `&nbsp;`-only cells would need a synthetic fixture.
- **Eval said:** msft-2013's Note 18 table has 21 of them among 78 cells, and
  `'&nbsp;&nbsp;0.20&nbsp;-&nbsp;$&nbsp;&nbsp;0.23'` beside them; tgt-2002
  types the parenthesised deduction as two cells, `($322` and `)`, and uses
  `&#151;` for the em dash. Real material is better adversarial input than
  anything hand-written (ADR-026 §f3's rule held again).
- **Corrected:** no fixture added; every case runs on committed filings and
  the corpus-dependent figures ADR-021 derives do not move.
