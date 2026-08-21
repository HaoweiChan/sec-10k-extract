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
    """Bold/code/link markup -> plain text, for a UI table cell or list item."""
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)   # [text](url) -> text
    s = re.sub(r"`([^`]+)`", r"\1", s)                # `code` -> code
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)          # **bold** -> bold
    return re.sub(r"\s+", " ", s).strip()


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
    """Bold-lead paragraphs -> [{"heading": str, "items": [str, ...]}, ...].

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
                current["items"].extend(_strip_md(t) for t in items)
            continue
        joined = " ".join(lines)
        m = re.match(r"^\*\*(.+?)\*\*(.*)$", joined, re.S)
        if not m:
            continue
        heading, rest = m.group(1).strip(), m.group(2).strip()
        current = {"heading": heading, "items": []}
        groups.append(current)
        if rest:
            current["items"].append(_strip_md(joined))
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
- **Term two.** detail two, with `code` and [a link](http://x).

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
        assert g1["items"] == [
            "Term one. detail one, wrapped onto a second line with no blank line above it.",
            "Term two. detail two, with code and a link."]
        assert g2["heading"] == "Group two"
        assert g2["items"] == [
            "Group two — inline detail, no bullets beneath it at all."]
        # missing file -> honest empty state, never a fabricated row
        assert parse_readme(Path("/nonexistent/README.md")) == {
            "works_well": [], "difficult": []}
    finally:
        os.unlink(p)

    # the real, committed README must still yield a non-trivial parse —
    # this is what the capabilities-parse eval case also asserts
    real = parse_readme()
    assert len(real["works_well"]) >= 8, real["works_well"]
    assert sum(len(g["items"]) for g in real["difficult"]) >= 3, real["difficult"]
    print("[capabilities self-check] ok")


if __name__ == "__main__":
    _demo()
