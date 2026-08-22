"""Layer 3b, OPTIONAL: boilerplate chrome detection. Ruling: ADR-026.

Off by default. `extract_items(path, exclude_boilerplate=True)` turns it on and
adds one envelope key, `boilerplate`; nothing else about the envelope changes.

The load-bearing property: detection NEVER edits `normalized_text`. It reports
`[start, end)` runs INTO it, so every offset the contract publishes keeps the
exact meaning INV-S2 gives it, with the flag on or off. The "stripped view" is
a derived string produced on demand by `strip_chrome()`; it is not stored,
because a second copy of the document is what INV-S2 exists to prevent.

Chrome is line-shaped, so the unit is one physical line of `normalized_text`
INCLUDING its terminating newline (indentation included — txt-era layout is
part of the line). Three kinds, resolved in this order, one kind per line:

  edgar_chrome  a line that is nothing but EDGAR SGML page/table furniture
                (<PAGE>, <TABLE>, </TABLE>, <CAPTION>, <S>, <C>, <FN>, ...).
                Survives normalization only in the txt era, where ADR-006
                ruling 2 passes the body through verbatim.
  running_head  a line whose exact text repeats >= MIN_REPEATS times, at
                REGULAR intervals (gap CV <= MAX_GAP_CV), spanning most of the
                document (>= MIN_SPREAD). Repetition alone is not evidence:
                '$' repeats 1,058 times in cvx-2015 and 'Total' 39 times in
                msft-2013. Regularity across the whole document is what a page
                header has and a table cell does not. Head vs foot is not
                recoverable once the page breaks are gone — both are
                `running_head`.
  page_number   a line that is only a number (optionally 'Page N' or '- N -'),
                ADJACENT to a boundary line — an edgar_chrome or running_head
                line, skipping blanks. Bare numbers on their own are table
                cells: cvx-2015 has 2,045 of them (lines where str.isdigit() is
                true) and no page numbers.

Self-check: python3 -m src.sec10k.boilerplate
"""
import re
import statistics
from collections import defaultdict

# Thresholds. ADR-026 §c owns the corpus definition, the sweep and every
# figure derived from them; it is deliberately not restated here. PR #25 R6
# found this comment saying "24 real EDGAR filings" where §c says 28 — a
# second copy of a number drifts, so there is now one copy.
MIN_REPEATS = 8    # measured: smallest TRUE chrome run is 8, first false
                   # positive is at 6 — nothing occurs exactly 7 times, so 7
                   # and 8 are the same gate on this corpus (§c1, not "the
                   # boundary": two counts of margin, one true run below it)
MAX_GAP_CV = 0.60  # measured: chrome tops out at 0.58, nearest non-chrome is 0.84.
                   # Raising it to anything below 0.84 changes NO output on any
                   # fixture, so no case can go red there and none should be
                   # written — 0.84 is where it starts being wrong, and
                   # boilerplate-near-miss goes red at exactly 0.84 (PR #25 R4).
MIN_SPREAD = 0.70  # measured: chrome bottoms out at 0.82, nearest non-chrome is 0.64
PAGE_DIGITS = 3    # judgment call, NOT measured — see ADR-026 §c4

# ponytail: no max-line-length gate. One was written and deleted — no line over
# 35 chars passes the other three gates anywhere in the corpus, so the gate
# constrained nothing any case could exercise (the ADR-010 sin). If a 200-char
# line really does repeat 8 times at page intervals across a whole filing, it
# is a repeated legal footer, and that is chrome.
# Upgrade trigger: the argument is corpus-bound, so re-open it when a fixture
# lands where a line passes THE THREE REPEAT GATES above — the gates a
# length gate would have joined — at more than 35 chars, and that long run is
# a false positive: real body text, not a repeated footer. Only that pair
# re-opens it; a long TRUE chrome line is the case above.
# Re-measured 2026-08-22 (S2) over the 38 measurable fixtures, still 35:
# the ceiling is jpm-2024's 'JPMorgan Chase & Co./2024 Form 10-K', and every
# other fixture's repeat-gated runs top out at 17 ('Table of Contents').
# Scoped deliberately (PR #31 R6): this says nothing about `edgar_chrome`,
# which reaches 127 chars on ge-1994 and ibr-pointer-first and is matched by
# SGML shape, not by repetition — worded over "detected chrome" the trigger
# would already be satisfied by six committed fixtures and could never fire
# as news.

SGML_FURNITURE = re.compile(r"(?:</?(?:PAGE|TABLE|CAPTION|S|C|FN)>\s*)+", re.I)
PAGE_NUMBER = re.compile(r"(?:page\s+)?[-–—\s]*\d{1,%d}[-–—.\s]*" % PAGE_DIGITS, re.I)


def _lines(text):
    """[(start, end, stripped)] per physical line; end swallows the newline."""
    out, pos, n = [], 0, len(text)
    for ln in text.split("\n"):
        out.append((pos, min(pos + len(ln) + 1, n), ln.strip()))
        pos += len(ln) + 1
    return out


def _running_head_lines(lines, n_chars):
    """Indices of lines belonging to a regular, document-spanning repeat."""
    occ = defaultdict(list)
    for i, (start, _end, s) in enumerate(lines):
        if s:
            occ[s].append((start, i))
    hits = set()
    for places in occ.values():
        if len(places) < MIN_REPEATS:
            continue
        starts = [p for p, _ in places]
        gaps = [b - a for a, b in zip(starts, starts[1:])]
        mean = statistics.mean(gaps)
        if not mean or statistics.pstdev(gaps) / mean > MAX_GAP_CV:
            continue
        if (starts[-1] - starts[0]) / n_chars < MIN_SPREAD:
            continue
        hits.update(i for _, i in places)
    return hits


def find_chrome(text):
    """[{start, end, kind}] for every boilerplate line, in document order.

    Offsets are into `text` — the same `normalized_text` the contract's item
    offsets index. Nothing is removed here; see strip_chrome().
    """
    if not text:
        return []
    lines = _lines(text)
    kinds = {}
    for i, (_start, _end, s) in enumerate(lines):
        if s and SGML_FURNITURE.fullmatch(s):
            kinds[i] = "edgar_chrome"
    for i in _running_head_lines(lines, len(text)):
        kinds.setdefault(i, "running_head")

    # page numbers last: they are defined BY adjacency to the boundary lines
    # found above, so that set has to be complete first.
    def neighbour(i, step):
        j = i + step
        while 0 <= j < len(lines) and not lines[j][2]:
            j += step
        return j

    for i, (_start, _end, s) in enumerate(lines):
        if not s or i in kinds or not PAGE_NUMBER.fullmatch(s):
            continue
        if kinds.get(neighbour(i, -1)) or kinds.get(neighbour(i, 1)):
            kinds[i] = "page_number"

    return [{"start": lines[i][0], "end": lines[i][1], "kind": kinds[i]}
            for i in sorted(kinds)]


def strip_chrome(text, spans, start=0, end=None):
    """`text[start:end]` with every chrome run inside that window removed.

    The stripped VIEW. `spans` are absolute offsets into `text` (what
    find_chrome returns and what the envelope publishes), so this is also how a
    caller gets one item's stripped body: pass that item's own start/end.
    Reconstruction is the identity `text[start:end]` — the original characters
    are never touched, which is the whole provenance argument (ADR-026 §d).
    """
    end = len(text) if end is None else end
    out, cursor = [], start
    for sp in spans:
        s, e = max(sp["start"], start), min(sp["end"], end)
        if s >= e or e <= cursor:
            continue
        out.append(text[cursor:s])
        cursor = max(cursor, e)
    out.append(text[cursor:end])
    return "".join(out)


def _demo():
    """Fails if either direction of the rule, or a threshold, breaks."""
    # 12 "pages": running head, unique prose, page number.
    text = "\n".join("ACME CORPORATION 2024 Form 10-K\n"
                     "Body prose for page %d, unique and it must survive.\n%d" % (p, p)
                     for p in range(1, 13))
    spans = find_chrome(text)
    kinds = [s["kind"] for s in spans]
    assert kinds.count("running_head") == 12, kinds
    # 11, not 12: the last page's number has prose before it and nothing after,
    # so no boundary is adjacent to it. A trailing page number is the one
    # recall hole adjacency leaves, and it is one line per document.
    assert kinds.count("page_number") == 11, kinds
    assert not any("Body prose" in text[s["start"]:s["end"]] for s in spans), spans
    for a, b in zip(spans, spans[1:]):     # never overlapping, always ordered
        assert a["end"] <= b["start"], (a, b)

    # the stripped view drops the chrome and keeps the prose; the original is
    # untouched, so text[start:end] still reconstructs the raw run (INV-S2)
    stripped = strip_chrome(text, spans)
    assert "ACME CORPORATION" not in stripped, stripped
    assert "Body prose for page 7," in stripped, stripped
    assert text[spans[0]["start"]:spans[0]["end"]] == "ACME CORPORATION 2024 Form 10-K\n"
    # windowing is how a caller strips one item's body
    assert strip_chrome(text, spans, start=0, end=37) == "Body ", \
        repr(strip_chrome(text, spans, start=0, end=37))

    # regularity is load-bearing: the same line, repeated as often, but
    # CLUSTERED, is a table column and must not fire
    clustered = "\n".join(["Total"] * 12 + ["filler line %d" % i for i in range(400)])
    assert find_chrome(clustered) == [], find_chrome(clustered)[:3]

    # under MIN_REPEATS nothing fires, however regular it looks
    few = "\n".join("HEAD\nprose %d here\n%d" % (i, i) for i in range(MIN_REPEATS - 1))
    assert find_chrome(few) == [], find_chrome(few)[:3]

    # EDGAR txt furniture, including the <S>/<C> column-marker line shape
    got = [(s["kind"], s) for s in find_chrome(
        "<PAGE>\n<TABLE>\n<CAPTION>\n<S>        <C>       <C>\nreal row\n</TABLE>\n")]
    assert [k for k, _ in got] == ["edgar_chrome"] * 5, got

    # a bare number with no chrome beside it is a table cell, not a page number
    assert find_chrome("alpha\n17\nbeta\n") == []
    # a page-number-shaped figure inside prose is not even a candidate: the
    # WHOLE line has to be the number
    assert find_chrome("<PAGE>\nwe opened 17 stores\n") == \
        [{"start": 0, "end": 7, "kind": "edgar_chrome"}]
    # 4+ digits is a year, not a page number (ibm-1997's '1997' beside <TABLE>)
    assert [s["kind"] for s in find_chrome("<PAGE>\n1997\n")] == ["edgar_chrome"]

    assert find_chrome("") == [] and strip_chrome("", []) == ""
    print("[boilerplate self-check] ok")


if __name__ == "__main__":
    _demo()
