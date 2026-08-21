"""Parses README.md's capability lists into structured data for the
inspector's `/api/capabilities` panel (S4).

Why this exists: INV-S2 says item text has no second copy to drift from its
offsets; this module applies the same argument to docs. The footer used to
just link to "the README's works-well and difficult/unsupported lists" — a
prose promise nobody could verify stayed true, and a hand-copied HTML table
would immediately be a second copy. Parsing the SAME markdown README already
carries, at request time, means a README edit either lands in the UI
automatically or the capabilities-parse eval case
(src/repo_hygiene/eval_adapter.py) goes red — there is no second list to
silently go stale.

Pure stdlib, no fastapi import, so it can be imported by the repo_hygiene
eval adapter (and unit-tested) without pulling in the web dependency stack —
same convention as view.py.

Self-check: python3 -m src.sec10k.web.capabilities
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
README = ROOT / "README.md"

WORKS_WELL_HEADING = "## What works well"
DIFFICULT_HEADING = "## What is difficult, unreliable, or unsupported"


def _section(text, heading):
    """Text between `heading` and the next `## ` heading, or "" if absent."""
    i = text.find(heading)
    if i < 0:
        return ""
    start = i + len(heading)
    m = re.search(r"\n## ", text[start:])
    return text[start: start + m.start()] if m else text[start:]


def _strip_md(s):
    """Bold/italic/code/link markup -> plain text, for a UI table cell or
    list item. Bold must strip before italic — `**bold**` would otherwise
    leave `*bold*` behind for the single-asterisk rule to mangle further
    (R4: README prose like `*ahead*` was shipping into the panel with its
    asterisks still attached, because italic had no rule at all)."""
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)   # [text](url) -> text
    s = re.sub(r"`([^`]+)`", r"\1", s)                # `code` -> code
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)          # **bold** -> bold
    s = re.sub(r"\*([^*]+)\*", r"\1", s)              # *italic* -> italic
    s = re.sub(r"(?<![\w])_([^_]+)_(?![\w])", r"\1", s)  # _italic_ -> italic
    return re.sub(r"\s+", " ", s).strip()


_LEAD_RE = re.compile(r"^\*\*(.+?)\*\*\s*(.*)$", re.S)


def _split_lead(raw):
    """A difficult-list item's leading `**Term**` -> (term, detail), both
    markdown-stripped (V3: the panel needs term and detail as separate
    table columns, not one fused string). Covers both shapes the README
    uses: a `- **Term.** detail...` bullet, and a bare `**Heading** —
    detail...` paragraph (the "Explicitly unsupported" group, which has no
    bullets under it at all). An item with no bold lead at all — a shape
    surprise, not a case the README currently produces — falls back to
    (whole text, "") rather than raising.
    """
    m = _LEAD_RE.match(raw.strip())
    if not m:
        return _strip_md(raw), ""
    term, detail = m.group(1).strip(), m.group(2).strip()
    detail = re.sub(r"^[—\-–:]\s*", "", detail)  # the dash/colon after the lead, not content
    return _strip_md(term), _strip_md(detail)


def _parse_table(section):
    """The first `| a | b | c |` markdown table in `section` -> a list of
    dicts keyed by its header row. [] if no table is found."""
    lines = [l.strip() for l in section.splitlines() if l.strip().startswith("|")]
    if len(lines) < 3:  # header + separator + >=1 data row
        return []
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(header):
            continue  # a malformed row is dropped, not guessed at
        rows.append({h: _strip_md(c) for h, c in zip(header, cells)})
    return rows


def _parse_difficult(section):
    """Bold-lead paragraphs -> [{"heading": str, "items": [{"term", "detail"}, ...]}, ...].

    Blank lines split the section into blocks, but the README (real
    example: "Fails today") runs consecutive `- ` bullets back to back with
    no blank line between them, so one block can hold several items — each
    is split out by its own leading `- `, with a non-`- ` line folded into
    the item above it as a wrapped continuation.

    A block that does NOT open with `- ` and starts `**Text**` opens a new
    group instead. If content follows the bold lead in that SAME block (as
    with "Explicitly unsupported", which has no `- ` bullets under it at
    all), the whole block is also that group's one entry. A block of plain
    prose (the section's lead-in sentence) matches neither shape and is
    skipped.

    Each item is split (via `_split_lead`) into its bolded term and the
    detail that follows, rather than kept as one fused string (V3): the
    panel renders these as separate table columns, so a reader can scan
    issues without reading full paragraphs.
    """
    blocks = re.split(r"\n\s*\n", section.strip())
    groups, current = [], None
    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue
        if lines[0].startswith("- "):
            items, cur = [], None
            for line in lines:
                if line.startswith("- "):
                    items.append(line[2:])
                    cur = len(items) - 1
                elif cur is not None:
                    items[cur] += " " + line
            if current is not None:
                current["items"].extend(
                    {"term": t, "detail": d} for t, d in (_split_lead(raw) for raw in items))
            continue
        joined = " ".join(lines)
        m = re.match(r"^\*\*(.+?)\*\*(.*)$", joined, re.S)
        if not m:
            continue
        heading, rest = m.group(1).strip(), m.group(2).strip()
        current = {"heading": heading, "items": []}
        groups.append(current)
        if rest:
            term, detail = _split_lead(joined)
            current["items"].append({"term": term, "detail": detail})
    return groups


def parse_readme(path=README):
    """-> {"works_well": [...], "difficult": [...]}. An honest empty state —
    never fabricated rows — if the file or its sections are missing."""
    try:
        text = Path(path).read_text()
    except OSError:
        return {"works_well": [], "difficult": []}
    return {
        "works_well": _parse_table(_section(text, WORKS_WELL_HEADING)),
        "difficult": _parse_difficult(_section(text, DIFFICULT_HEADING)),
    }


def _demo():
    import os
    import tempfile

    sample = """## What works well

blah

| Stratum | Examples | Result |
|---|---|---|
| A | b, c | `x` works |
| D | e | **bold** result |

## What is difficult, unreliable, or unsupported

lead-in sentence.

**Group one**

- **Term one.** detail one, wrapped onto
  a second line with no blank line above it.
- **Term two.** detail two, with `code`, *italic*, _also italic_,
  a snake_case_name that must survive, and [a link](http://x).

**Group two** — inline detail, no bullets beneath it at all.

## Next section
irrelevant
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(sample)
        p = f.name
    try:
        data = parse_readme(p)
        assert data["works_well"] == [
            {"Stratum": "A", "Examples": "b, c", "Result": "x works"},
            {"Stratum": "D", "Examples": "e", "Result": "bold result"},
        ], data["works_well"]
        assert len(data["difficult"]) == 2
        g1, g2 = data["difficult"]
        assert g1["heading"] == "Group one"
        # V3: term and detail are separate fields, not one fused string
        assert g1["items"] == [
            {"term": "Term one.",
             "detail": "detail one, wrapped onto a second line with no blank line above it."},
            {"term": "Term two.",
             "detail": "detail two, with code, italic, also italic, a snake_case_name "
                       "that must survive, and a link."},
        ], g1["items"]
        assert g2["heading"] == "Group two"
        assert g2["items"] == [
            {"term": "Group two", "detail": "inline detail, no bullets beneath it at all."}]
        # missing file -> honest empty state, never a fabricated row
        assert parse_readme(Path("/nonexistent/README.md")) == {
            "works_well": [], "difficult": []}
    finally:
        os.unlink(p)

    # R4 regression: single-asterisk/underscore emphasis must not leak into
    # the panel as literal markdown characters
    assert _strip_md("plain *em* and _em2_ and **bold**") == "plain em and em2 and bold"
    assert _strip_md("a snake_case_ident stays intact") == "a snake_case_ident stays intact"

    # the real, committed README must still yield a non-trivial parse —
    # this is what the capabilities-parse eval case also asserts
    real = parse_readme()
    assert len(real["works_well"]) >= 8, real["works_well"]
    real_items = [it for g in real["difficult"] for it in g["items"]]
    assert len(real_items) >= 3, real_items
    assert all(set(it) == {"term", "detail"} for it in real_items), real_items
    # R4 regression, pinned to real content: the README's "Closed since
    # B-freeze" bullet contains `*ahead*` — it must come out asterisk-free
    joined = " ".join(it["detail"] for it in real_items)
    assert "*ahead*" not in joined and "*" not in joined, \
        f"R4 regression: italic emphasis leaked into the panel: {joined!r}"
    print("[capabilities self-check] ok")


if __name__ == "__main__":
    _demo()
