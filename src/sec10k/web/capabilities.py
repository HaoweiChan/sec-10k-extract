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


_DECISION_RE = re.compile(r"^-\s*\[(ADR-\d+)\]\(([^)]+)\)\s*[—\-–]\s*(.+)$")


def _parse_decisions(section):
    """`- [ADR-010](url) — one-liner.` bullets anywhere in `section` (the
    difficult section's collapsed decision log) -> [{"id", "url", "note"},
    ...], in document order. [] if the section carries no such log.

    `url` is rewritten from the README-relative `specs/decisions/FILE.md`
    path to the app route that actually serves it (`/api/decisions/FILE.md`,
    src/sec10k/web/app.py) — the README's link works because GitHub renders
    relative paths against the repo tree; the panel has no repo tree, so it
    needs the file served directly, wherever this is deployed.
    """
    out = []
    for line in section.splitlines():
        m = _DECISION_RE.match(line.strip())
        if not m:
            continue
        url = m.group(2).strip()
        if url.startswith("specs/decisions/"):
            url = "/api/decisions/" + url[len("specs/decisions/"):]
        out.append({"id": m.group(1), "url": url, "note": _strip_md(m.group(3))})
    return out


def parse_readme(path=README):
    """-> {"works_well": [...], "difficult": [...], "decisions": [...]}.
    works_well/difficult are flat lists of dicts keyed by their table's
    header row — one shape, one parser (`_parse_table`) for both. decisions
    is the difficult section's collapsed `- [ADR-N](url) — note` log,
    parsed from that SAME section so the panel's ADR references can never
    drift from the README's. An honest empty state — never fabricated rows
    — if the file or a section is missing."""
    try:
        text = Path(path).read_text()
    except OSError:
        return {"works_well": [], "difficult": [], "decisions": []}
    difficult_section = _section(text, DIFFICULT_HEADING)
    return {
        "works_well": _parse_table(_section(text, WORKS_WELL_HEADING)),
        "difficult": _parse_table(difficult_section),
        "decisions": _parse_decisions(difficult_section),
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

| Limitation | Detail |
|---|---|
| Term one | detail one, with `code`, *italic*, _also italic_, a snake_case_name that must survive, and [a link](http://x) |
| Term two | detail two |

<details>
<summary>log</summary>

- [ADR-001](specs/decisions/ADR-001-x.md) — one-liner with `code` and *italic*.
- [ADR-002](specs/decisions/ADR-002-y.md) — another one-liner.

</details>

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
        assert data["difficult"] == [
            {"Limitation": "Term one",
             "Detail": "detail one, with code, italic, also italic, a snake_case_name "
                       "that must survive, and a link"},
            {"Limitation": "Term two", "Detail": "detail two"},
        ], data["difficult"]
        assert data["decisions"] == [
            {"id": "ADR-001", "url": "/api/decisions/ADR-001-x.md",
             "note": "one-liner with code and italic."},
            {"id": "ADR-002", "url": "/api/decisions/ADR-002-y.md",
             "note": "another one-liner."},
        ], data["decisions"]
        # missing file -> honest empty state, never a fabricated row
        assert parse_readme(Path("/nonexistent/README.md")) == {
            "works_well": [], "difficult": [], "decisions": []}
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
    assert len(real["difficult"]) >= 3, real["difficult"]
    assert len(real["decisions"]) >= 3, real["decisions"]
    assert all(d["id"].startswith("ADR-") and d["url"].startswith("/api/decisions/")
               and d["note"] for d in real["decisions"]), real["decisions"]
    real_cells = [v for row in real["difficult"] for v in row.values()]
    # R4 regression, pinned to real content: markdown emphasis/links/code in
    # the difficult table must come out plain, not as literal markup chars
    assert "*" not in " ".join(real_cells), \
        f"R4 regression: italic emphasis leaked into the panel: {real_cells!r}"
    print("[capabilities self-check] ok")


if __name__ == "__main__":
    _demo()
