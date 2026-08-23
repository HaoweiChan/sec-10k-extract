# ledger-table-shape-regression fixture

Hand-written, 2026-08-23 (L1). Two Markdown tables; the `ledger_table_shape`
check must report EXACTLY nine failures here and not one more — the rows
marked `ok` are the shapes that must NOT fire (a pipe-free code span, a
Markdown link, a strikethrough row with the right count, and a second table
whose header is narrower than the first).

| Debt | Where | Why |
|---|---|---|
| ok — plain row with a `pipe-free code span` and a [link](../../../tasks/TODO.md) | here | fine |
| one cell too many | here | why | extra |
| one cell too few | here |
| unescaped pipe inside a code span: `grep 'a|b'` | here | why |
| escaped pipe inside a code span: `grep 'a\|b'` | here | why |
| escaped pipe outside any span, GFM-legal but counts \| here | here | why |
| ~~struck row with an extra cell~~ — CLOSED | here | why | extra |
| ~~ok — struck row with the right count~~ — CLOSED | here | why |

Prose between tables ends the first table, so the next header sets a new width.

| Fixture | Bytes |
|---|---|
| ok — two cells | 12 |
| three cells in a two-column table | 12 | extra |
