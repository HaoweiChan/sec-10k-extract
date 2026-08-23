"""Derived views over the ADR-029 `tables` annotation. Ruling: ADR-029.

`extract_items(path, tables=True)` adds one envelope key, `tables`: a list of
`{start, end, header, rows}` records in document order. `start`/`end` index
`normalized_text`; `rows` is a list of rows, each a list of cells, each cell
`[start, end]` or `[start, end, colspan]` (colspan only when > 1). `header`
is how many leading rows are header rows (all-<th>). Nothing here is stored
twice: a cell's text IS `normalized_text[start:end]`, exactly as an item's
text is (INV-S2), so the grid and the Markdown below are functions of the
envelope, never fields of it — the same rule `boilerplate.strip_chrome`
follows for the stripped view (ADR-026).

Self-check: python3 -m src.sec10k.tables
"""
import re

_WS = re.compile(r"\s+")


def cell_text(text, cell):
    """One cell as a single line: the verbatim slice with its internal
    whitespace (a <div> inside the cell breaks the line) collapsed."""
    return _WS.sub(" ", text[cell[0]:cell[1]]).strip()


def grid(text, table):
    """[[str, ...], ...] — every row padded to the table's width; a colspan-n
    cell is its text followed by n-1 empty cells, so columns line up the way
    the filer's browser lined them up. rowspan is not expanded (ADR-029 §e)."""
    rows = []
    for row in table["rows"]:
        out = []
        for c in row:
            out.append(cell_text(text, c))
            out.extend([""] * (c[2] - 1 if len(c) > 2 else 0))
        rows.append(out)
    width = max((len(r) for r in rows), default=0)
    return [r + [""] * (width - len(r)) for r in rows]


def to_markdown(text, table):
    """GitHub-flavoured Markdown for one table record. Header = the first
    visible row (Markdown has exactly one header row, whatever `header`
    says). Rows and columns that are empty in EVERY cell — iXBRL filers'
    column-width and spacer rows — are dropped from the VIEW only; the record
    keeps them. `|` in a cell is escaped."""
    g = [r for r in grid(text, table) if any(r)]
    if not g:
        return ""
    keep = [j for j in range(len(g[0])) if any(r[j] for r in g)]
    g = [[r[j].replace("|", "\\|") for j in keep] for r in g]
    line = lambda r: "| " + " | ".join(r) + " |"  # noqa: E731
    return "\n".join([line(g[0]), "|" + "---|" * len(keep)] + [line(r) for r in g[1:]])


def tables_in(tables, start, end):
    """The records lying wholly inside [start, end) — an item's tables, by the
    same offsets the item itself is read through."""
    return [t for t in tables if start <= t["start"] and t["end"] <= end]


def _demo():
    from src.sec10k.normalize import normalize
    html = ("<html><body><p>Before.</p>"
            "<table><tr><th colspan=2>Years</th><th>%</th></tr>"
            "<tr><td><div>Net</div><div>sales</div></td><td>$</td><td>1,234</td></tr>"
            "<tr><td>a|b</td><td>&nbsp;</td><td> 5 </td></tr>"
            "<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr></table>"
            "<table><tr><td>&nbsp;</td></tr></table>"      # spacer: no text, dropped
            "<p>After.</p><table><tr><td>x</td></tr></table></body></html>")
    text, tabs, _ = normalize(html, "html", tables=True)
    assert normalize(html, "html", tables=False) == (text, None, None)  # identical text
    assert len(tabs) == 2, tabs                                        # spacer dropped
    t = tabs[0]
    assert t["header"] == 1 and len(t["rows"]) == 4, t
    # every cell is a verbatim slice; a colspan cell carries its span
    assert t["rows"][0][0][2] == 2 and text[slice(*t["rows"][0][0][:2])] == "Years", t
    g = grid(text, t)
    assert g == [["Years", "", "%"], ["Net sales", "$", "1,234"], ["a|b", "", "5"],
                 ["", "", ""]], g
    md = to_markdown(text, t)
    assert md == ("| Years |  | % |\n|---|---|---|\n| Net sales | $ | 1,234 |\n"
                  "| a\\|b |  | 5 |"), md              # the all-empty 4th row is not shown
    # a column empty in every row is dropped from the VIEW only
    t2 = {"start": 0, "end": 0, "header": 0,
          "rows": [[[0, 0], t["rows"][1][2]], [[0, 0], t["rows"][2][2]]]}
    assert to_markdown(text, t2) == "| 1,234 |\n|---|\n| 5 |", to_markdown(text, t2)
    assert grid(text, t2) == [["", "1,234"], ["", "5"]], grid(text, t2)
    assert text[t["start"]:t["end"]].startswith("Years") and \
        text[t["start"]:t["end"]].endswith("5"), text[t["start"]:t["end"]]
    # the record sits between its neighbours, and tables_in joins on offsets
    b, a = text.index("Before."), text.index("After.")
    assert b < t["start"] < t["end"] < a < tabs[1]["start"], (b, a, tabs)
    assert tables_in(tabs, 0, a) == [t] and tables_in(tabs, a, len(text)) == [tabs[1]]
    # an offset inside a collapsed whitespace run never lands outside its cell
    for row in t["rows"]:
        for c in row:
            s, e = c[0], c[1]
            assert 0 <= s <= e <= len(text) and text[s:e] == text[s:e].strip(), c
    # ADR-029 §e: a nested table is its own record, inside the outer cell's
    # span, and records come back in start order (inner closes first)
    nested = ("<table><tr><td>outer<table><tr><td>inner</td></tr></table></td>"
              "<td>after</td></tr></table>")
    ntext, ntabs, _ = normalize(nested, "html", tables=True)
    assert len(ntabs) == 2 and ntabs[0]["start"] < ntabs[1]["start"], ntabs
    outer_cell = ntabs[0]["rows"][0][0]
    assert ntext[outer_cell[0]:outer_cell[1]] == "outer\n\ninner", ntext[outer_cell[0]:outer_cell[1]]
    assert grid(ntext, ntabs[1]) == [["inner"]] and grid(ntext, ntabs[0]) == [["outer inner", "after"]]
    print("[tables self-check] ok")


if __name__ == "__main__":
    _demo()
