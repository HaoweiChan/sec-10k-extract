"""Derived Markdown view over the ADR-031 `blocks` annotation. Ruling: ADR-031.

`extract_items(path, blocks=True)` adds one envelope key, `blocks` (and the
ADR-029 `tables` it points into): a list, in document order and
non-overlapping, of `{kind, start, end, ...}` records with offsets into
`normalized_text` — kind `heading` (+`level`; +`item` when it is an item
heading the segmenter identified), `paragraph` (+`strong` when the whole
block was bold in the HTML), `list_item` (+`ordered`), `table` (+`table`, the
index of the ADR-029 record), or `pre` (the one block a txt-era filing is).
Nothing is stored twice: a block's text IS `normalized_text[start:end]`, as
an item's is (INV-S2), so the Markdown below is a function of the envelope,
never a field of it — `tables.to_markdown` and `boilerplate.strip_chrome`
follow the same rule.

Self-check: python3 -m src.sec10k.markdown
"""
import bisect
import re

from src.sec10k import tables as _tables
from src.sec10k.boilerplate import strip_chrome

_WS = re.compile(r"\s+")
# CommonMark: a backslash before ASCII punctuation is that character, literally.
# Escaped everywhere: the inline-syntax characters. Escaped at line start
# only: what would open a block construct there.
_INLINE_ESC = re.compile(r"([\\*_`\[\]<>~#])")
_LEAD_ESC = re.compile(r"^([>+=|-]|\d+[.)])")


def _inline(s):
    s = _INLINE_ESC.sub(r"\\\1", s)
    m = _LEAD_ESC.match(s)
    if m:
        s = s[:m.end() - 1] + "\\" + s[m.end() - 1:]
    return s


def _fence(s):
    n = max((len(m) for m in re.findall(r"`+", s)), default=0)
    return "`" * max(3, n + 1)


def to_markdown(text, blocks, tables, start=0, end=None, omit=()):
    """GitHub-flavoured Markdown for `text[start:end]` (the whole document by
    default; an item by its offsets). A block straddling the window is
    CLIPPED to it — its clipped slice renders as its kind, except a clipped
    table, which has no grid and renders as a paragraph. `omit` (ADR-026
    chrome runs, when the caller also asked for exclusion) is removed from
    every block's rendered text exactly as `boilerplate.strip_chrome` removes
    it from an item — from a paragraph's slice, a heading's, a table's cells
    — and a block, row or table left empty by that disappears (PR #45 R1: on
    jpm-2024 every chrome run sits inside a two-cell table block, so
    "leave out a block wholly inside a run" omitted nothing). Paragraph and
    heading text is escaped so no filing prose can open a Markdown
    construct; a table renders through `tables.to_markdown`; `pre` renders
    in a fence longer than any backtick run inside it. Blocks are joined by
    one blank line."""
    end = len(text) if end is None else end
    starts = [o["start"] for o in omit]   # non-overlapping, document order (contract)
    out = []
    for b in blocks:
        s, e = max(b["start"], start), min(b["end"], end)
        if s >= e:
            continue
        # the runs that can touch this block: the one that may straddle `s`
        # and every one that starts before `e`
        lo = max(bisect.bisect_right(starts, s) - 1, 0)
        runs = [o for o in omit[lo:bisect.bisect_left(starts, e)] if o["end"] > s]
        slice_ = strip_chrome(text, runs, s, e) if runs else text[s:e]
        if not slice_.strip():
            continue
        k, whole = b["kind"], (s, e) == (b["start"], b["end"])
        if k == "table" and whole:
            out.append(_tables.to_markdown(text, tables[b["table"]], omit=runs))
        elif k == "heading":
            out.append("#" * b["level"] + " " + _inline(_WS.sub(" ", slice_).strip()))
        elif k == "list_item":
            out.append(("1. " if b.get("ordered") else "- ") + _inline(slice_.strip()))
        elif k == "pre":
            f = _fence(slice_)
            out.append(f + "\n" + slice_ + "\n" + f)
        else:
            t = _inline(slice_.strip())
            out.append("**" + t + "**" if b.get("strong") else t)
    return "\n\n".join(x for x in out if x)


def blocks_in(blocks, start, end):
    """The blocks overlapping [start, end) — an item's blocks, by the same
    offsets the item itself is read through (a straddling block included,
    since the renderer clips it)."""
    return [b for b in blocks if b["start"] < end and b["end"] > start]


def _demo():
    from src.sec10k.normalize import normalize
    html = ("<html><body><h2>Title <i>x</i></h2><p>Plain *para* with_under and #tag.</p>"
            "<div style='font-weight:700'><span>Bold line</span></div>"
            "<p><b>Half</b> bold</p>"
            "<ul><li>one</li><li>two<li>three</ul><ol><li>first</li></ol>"
            "<table><tr><td>a</td><td>b</td></tr></table>"
            "<p>- looks like a bullet</p><p>1. looks ordered</p><p>| pipe</p>"
            "<p>tail<br>after br</p><p> </p>text outside any tag</body></html>")
    text, tabs, blocks = normalize(html, "html", blocks=True)
    assert normalize(html, "html") == (text, None, None)                     # identical text
    assert normalize(html, "html", tables=True)[:2] == (text, tabs)          # blocks imply tables
    kinds = [(b["kind"], text[b["start"]:b["end"]]) for b in blocks]
    assert kinds == [("heading", "Title x"), ("paragraph", "Plain *para* with_under and #tag."),
                     ("paragraph", "Bold line"), ("paragraph", "Half bold"),
                     ("list_item", "one"), ("list_item", "two"), ("list_item", "three"),
                     ("list_item", "first"), ("table", "a b"),
                     ("paragraph", "- looks like a bullet"), ("paragraph", "1. looks ordered"),
                     ("paragraph", "| pipe"), ("paragraph", "tail"), ("paragraph", "after br"),
                     ("paragraph", "text outside any tag")], kinds
    assert blocks[0]["level"] == 2 and blocks[2].get("strong") and not blocks[3].get("strong")
    assert [b.get("ordered") for b in blocks[4:8]] == [False, False, False, True]
    assert blocks[8]["table"] == 0 and tabs[0]["start"] == blocks[8]["start"]
    # non-overlapping, in order, tight, and together they cover every visible character
    for a, b in zip(blocks, blocks[1:]):
        assert a["end"] <= b["start"], (a, b)
    for b in blocks:
        assert text[b["start"]:b["end"]] == text[b["start"]:b["end"]].strip()
    covered = set()
    for b in blocks:
        covered.update(range(b["start"], b["end"]))
    assert all(ch.isspace() for i, ch in enumerate(text) if i not in covered)
    md = to_markdown(text, blocks, tabs)
    assert md == ("## Title x\n\nPlain \\*para\\* with\\_under and \\#tag.\n\n**Bold line**\n\n"
                  "Half bold\n\n- one\n\n- two\n\n- three\n\n1. first\n\n"
                  "| a | b |\n|---|---|\n\n"
                  "\\- looks like a bullet\n\n1\\. looks ordered\n\n\\| pipe\n\n"
                  "tail\n\nafter br\n\ntext outside any tag"), md
    # a window clips: the heading's tail and the table's head, the clipped
    # table rendered as a paragraph, not a grid
    s, e = text.index("x") , tabs[0]["start"] + 1
    assert to_markdown(text, blocks, tabs, s, e).startswith("## x\n\n"), to_markdown(text, blocks, tabs, s, e)
    assert to_markdown(text, blocks, tabs, s, e).endswith("\n\na")
    assert blocks_in(blocks, s, e)[0] is blocks[0] and blocks_in(blocks, s, e)[-1] is blocks[8]
    # omit: chrome inside a block leaves the rendered text exactly as
    # strip_chrome would take it — a whole block disappears, a partial run
    # is cut out of the slice, a chrome run inside a table cell leaves the
    # cell and an emptied row drops (PR #45 R1: jpm-2024's running heads all
    # sit inside two-cell tables)
    b3 = blocks[3]
    assert "Half bold" not in to_markdown(text, blocks, tabs, omit=[{"start": b3["start"], "end": b3["end"]}])
    part = to_markdown(text, blocks, tabs, omit=[{"start": b3["start"] + 5, "end": b3["end"]}])
    assert "Half" in part and "Half bold" not in part, part
    chrome_html = ("<p>Prose.</p><table><tr><td>ACME 10-K</td><td>7</td></tr>"
                   "<tr><td>x</td><td>y</td></tr></table><p>More.</p>")
    ct, ctabs, cblocks = normalize(chrome_html, "html", blocks=True)
    run = [{"start": ct.index("ACME"), "end": ct.index("7") + 1, "kind": "running_head"}]
    assert to_markdown(ct, cblocks, ctabs, omit=run) == "Prose.\n\n| x | y |\n|---|---|\n\nMore.", \
        to_markdown(ct, cblocks, ctabs, omit=run)
    assert "ACME 10-K" in to_markdown(ct, cblocks, ctabs)          # the record itself is untouched
    # ...and a table whose only text was chrome vanishes with it
    only = ("<p>A</p><table><tr><td>ACME 10-K</td><td>7</td></tr></table><p>B</p>")
    ot, otabs, oblocks = normalize(only, "html", blocks=True)
    orun = [{"start": ot.index("ACME"), "end": ot.index("7") + 1, "kind": "running_head"}]
    assert to_markdown(ot, oblocks, otabs, omit=orun) == "A\n\nB"
    # txt era: one pre block, fenced longer than any backtick run inside
    t2, _, b2 = normalize("Item 1.  Business\n   fixed ``` width\n", "txt", blocks=True)
    assert b2 == [{"kind": "pre", "start": 0, "end": len(t2)}], b2
    assert to_markdown(t2, b2, []) == "````\n" + t2 + "\n````"
    assert to_markdown(t2, b2, [], 0, 7) == "```\nItem 1.\n```"          # an item's window
    print("[markdown self-check] ok")


if __name__ == "__main__":
    _demo()
