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
import re

from src.sec10k import tables as _tables

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
    table, which has no grid and renders as a paragraph. A block lying wholly
    inside any `omit` span (ADR-026 chrome runs, when the caller also asked
    for exclusion) is left out. Paragraph and heading text is escaped so no
    filing prose can open a Markdown construct; a table renders through
    `tables.to_markdown`; `pre` renders in a fence longer than any backtick
    run inside it. Blocks are joined by one blank line."""
    end = len(text) if end is None else end
    out = []
    for b in blocks:
        s, e = max(b["start"], start), min(b["end"], end)
        if s >= e:
            continue
        if any(o["start"] <= b["start"] and b["end"] <= o["end"] for o in omit):
            continue
        k, whole = b["kind"], (s, e) == (b["start"], b["end"])
        if k == "table" and whole:
            out.append(_tables.to_markdown(text, tables[b["table"]]))
        elif k == "heading":
            out.append("#" * b["level"] + " " + _inline(_WS.sub(" ", text[s:e])))
        elif k == "list_item":
            out.append(("1. " if b.get("ordered") else "- ") + _inline(text[s:e]))
        elif k == "pre":
            f = _fence(text[s:e])
            out.append(f + "\n" + text[s:e] + "\n" + f)
        else:
            t = _inline(text[s:e])
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
    # omit: a block wholly inside a chrome run is left out, a partial overlap is not
    b3 = blocks[3]
    assert "Half bold" not in to_markdown(text, blocks, tabs, omit=[{"start": b3["start"], "end": b3["end"]}])
    assert "Half bold" in to_markdown(text, blocks, tabs, omit=[{"start": b3["start"] + 1, "end": b3["end"]}])
    # txt era: one pre block, fenced longer than any backtick run inside
    t2, _, b2 = normalize("Item 1.  Business\n   fixed ``` width\n", "txt", blocks=True)
    assert b2 == [{"kind": "pre", "start": 0, "end": len(t2)}], b2
    assert to_markdown(t2, b2, []) == "````\n" + t2 + "\n````"
    assert to_markdown(t2, b2, [], 0, 7) == "```\nItem 1.\n```"          # an item's window
    print("[markdown self-check] ok")


if __name__ == "__main__":
    _demo()
