"""Cross-reference index resolution (ADR-042).

Two of the largest real filings in this corpus organize themselves the same
way, and the ordinary segmenter is right to fail on both. Intel FY2025's body
is a business narrative whose ONLY `Item N.` headings sit in a `Form 10-K
Cross-Reference Index` on the last two pages. Citigroup's FY2025 10-K carries
the same index at the FRONT, writes its entries WITHOUT the word "Item"
(`1. Business 4-36, 121-127, ...`) and never writes the word "Page" — so the
segmenter finds no candidate anywhere in 1,163,303 characters and reports
every item `missing` at coverage 0.0000.

What the two filings have in common is that they answer the question
somewhere else and say exactly where, in a machine-readable table, in printed
page numbers a reader is expected to follow. This module reads that table and
follows those page numbers.

Two things it deliberately does not do:

* it does not put the resolved regions in `start`/`end`. Intel's page ranges
  OVERLAP and NEST — item 3, Legal Proceedings, is pages 102-105, inside item
  8's 56-108, because Intel answers it in Note 19 to the financial statements;
  Citi's item 7A (64-120, 165-169, 190-228, 235-278) is threaded through item
  8's 134-298 — so no assignment of them to spans can satisfy INV-S1. They are
  published under `evidence.cross_reference`, the shape and the reasoning
  ADR-031 already established for the footnote case.
* it does not soften `doc_status`. `low_item_coverage` stays fired and the
  document stays `ambiguous`, because the primary spans really are index
  entries. Resolution adds an answer; it does not withdraw the admission.

Self-check: python3 -m src.sec10k.xref
"""
import bisect
import re

from src.sec10k.segment import SIM_FLOOR, title_similarity

ALIGN_SIM_FLOOR = max(SIM_FLOOR, 0.70)

INDEX_TITLE_RE = re.compile(
    r"(?im)^[ \t]*(form\s*10-?k\s+)?cross[ -]?reference\s+index[ \t]*$")

# how far past its title an index may run. Intel FY2025's is 1,786 chars, Citi's
# 2,733; the cap exists so a filing that merely MENTIONS the phrase cannot
# turn half the document into an entry table.
INDEX_MAX = 12_000

# An entry opens a line: `Item 1A.` (Intel) or `1A.` (Citi). The trailing
# period is REQUIRED and load-bearing, not decoration: without it every page
# number the furniture prints on its own line (`\n\n14\n\n`) reads as an
# entry, and on a filing whose index sits at the FRONT — Citi's does — the
# first page numbers of the body then land inside the index and destroy the
# ascending-order test that identifies it. Both filers write the period.
ENTRY_RE = re.compile(r"(?im)^[ \t]*(?:item[ \t]+)?(\d{1,2}[A-D]?)\.\s")

# Intel spells the column: "Pages 3-5, 18" / "Page 2". Citi does not, and puts
# the numbers where a page column would be — at the END of the entry.
PAGE_KEYWORD_RE = re.compile(r"(?i)\bpages?[ \t]+((?:\d+(?:\s*[-–—]\s*\d+)?)"
                             r"(?:\s*,\s*\d+(?:\s*[-–—]\s*\d+)?)*)")
TRAILING_PAGES_RE = re.compile(r"(\d+(?:\s*[-–—]\s*\d+)?"
                               r"(?:\s*,[\s\n]*\d+(?:\s*[-–—]\s*\d+)?)*)"
                               r"[\s*†‡.]*$")
RANGE_RE = re.compile(r"(\d+)(?:\s*[-–—]\s*(\d+))?")

# a page number printed on its own line — the page furniture ADR-026 reports
# as chrome, read here for its one useful fact: where page N ends.
NUM_LINE_RE = re.compile(r"(?m)^[ \t]*(\d{1,4})[ \t]*$")

# below this the "ladder" is numeric noise (a column of small integers), not
# pagination. Intel's is 117 rungs, Citi's 306; a filing short enough to fall
# under this is one the ordinary segmenter has no trouble with.
MIN_LADDER = 20

# an index must name at least this many items before it is believed to be one
MIN_ENTRIES = 8


def page_ladder(text):
    """`{page number: offset just past that page's printed number}`.

    A filing's page furniture is the only run of standalone integers that
    climbs monotonically through the whole document, so the ladder is the
    longest strictly increasing subsequence of those integers in document
    order. Financial tables contribute plenty of standalone integers; none of
    them climb by one across a hundred pages, and the subsequence discards
    what does not fit rather than needing a rule per table.
    """
    marks = [(int(m.group(1)), m.end()) for m in NUM_LINE_RE.finditer(text)]
    if len(marks) < MIN_LADDER:
        return {}
    tails, ends, prev = [], [], [-1] * len(marks)
    for i, (n, _) in enumerate(marks):
        k = bisect.bisect_left(tails, n)
        if k == len(tails):
            tails.append(n)
            ends.append(i)
        else:
            tails[k], ends[k] = n, i
        prev[i] = ends[k - 1] if k else -1
    if len(tails) < MIN_LADDER:
        return {}
    out, i = {}, ends[len(tails) - 1]
    while i != -1:
        n, off = marks[i]
        out[n] = off
        i = prev[i]
    return out


def find_index(text, expected):
    """`(start, end)` of a cross-reference index, or None.

    Believed only when it names `MIN_ENTRIES` distinct expected item codes in
    ascending order — the property that separates the index from a table of
    contents fragment or a sentence naming the phrase.
    """
    best = None
    for m in INDEX_TITLE_RE.finditer(text):
        lo, cap = m.end(), min(len(text), m.end() + INDEX_MAX)
        hits = [e for e in ENTRY_RE.finditer(text, lo, cap)
                if e.group(1).upper() in expected]
        order = [e.group(1).upper() for e in hits]
        if len(set(order)) < MIN_ENTRIES or order != sorted(
                order, key=lambda c: expected.index(c)):
            continue
        # the index ends where its LAST ROW ends, not at the window cap. The
        # cap is a guard against a runaway match; using it as the end put a
        # front-of-document index (Citi's) on top of the first 25 pages of the
        # body, and every region resolving into those pages was then dropped
        # as "inside the index" — 4 of the 5 items in the self-check below.
        tail = text.find("\n\n", hits[-1].end())
        hi = min(cap, tail if tail != -1 else cap)
        if best is None or len(set(order)) > best[2]:
            best = (m.start(), hi, len(set(order)))
    return best[:2] if best else None


def parse_entries(text, span, expected):
    """`{code: (entry_start, entry_end)}` — the index's own rows, in order.

    Rows partition the index region, so they are non-overlapping and ordered
    by construction, which is what lets them stand in as spans (INV-S1).
    """
    lo, hi = span
    hits = [(m.group(1).upper(), m.start(), m.end())
            for m in ENTRY_RE.finditer(text, lo, hi)]
    hits = [h for h in hits if h[0] in expected]
    out = {}
    for i, (code, s, _) in enumerate(hits):
        if code in out:
            continue
        out[code] = (s, hits[i + 1][1] if i + 1 < len(hits) else hi)
    return out


def _pages(body):
    """The page numbers an index row names, as `(lo, hi)` ranges.

    Two typographies, and which one applies is read off the row rather than
    configured: a row that spells "Pages 3-5, 18" is parsed by that keyword,
    wherever it appears and however many times (Intel gives item 1 three
    sub-rows, each with its own "Pages"). A row that does not is Citi's shape,
    where the numbers sit in a page COLUMN at the end of the row — and only
    the trailing run is read, which is what keeps `3. Legal Proceedings—See
    Note 30 to the Consolidated Financial Statements 287-293` from resolving
    to page 30.
    """
    runs = [m.group(1) for m in PAGE_KEYWORD_RE.finditer(body)]
    if not runs:
        m = TRAILING_PAGES_RE.search(body.rstrip())
        runs = [m.group(1)] if m else []
    out = []
    for run in runs:
        for a, b in RANGE_RE.findall(run):
            a = int(a)
            b = int(b) if b else a
            if a <= b:
                out.append((a, b))
    return out


def _region(ladder, lo, hi):
    """Characters of pages `lo`..`hi` inclusive. The number is printed at the
    FOOT of its page, so page N's text lies between page N-1's number and page
    N's. A page whose number the ladder dropped — a full-bleed table page
    carries no visible folio — falls back to the nearest rung below, widening
    the region rather than losing it."""
    below = [p for p in ladder if p < lo]
    at_or_below = [p for p in ladder if p <= hi]
    if not at_or_below:
        return None
    return (ladder[max(below)] if below else 0), ladder[max(at_or_below)]


def _merge(regions):
    """Merge overlapping regions, keeping each survivor's page labels: an item
    naming four ranges that land in three places publishes three regions, each
    labelled with what produced it."""
    out = []
    for s, e, label in sorted(regions):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e), out[-1][2] + [label])
        else:
            out.append((s, e, [label]))
    return out


def _section_title(row):
    """Index-row title before its page column, including wrapped text."""
    m = ENTRY_RE.search(row)
    if not m:
        return ""
    tail = row[m.end():]
    pages = PAGE_KEYWORD_RE.search(tail)
    if pages:
        tail = tail[:pages.start()]
    else:
        pages = TRAILING_PAGES_RE.search(tail.rstrip())
        if pages:
            tail = tail[:pages.start()]
    return " ".join(tail.split()).strip(" :")


def _align_start(text, code, region, row, first_page_end):
    """Advance a coarse page start to the mapped body heading."""
    s, e, label = region
    window = text[s:min(e, first_page_end)]
    title = _section_title(row)
    exact = (list(re.finditer(rf"(?im)^[ \t]*{re.escape(title)}[ \t]*$", window))
             if title else [])
    if exact:
        return s + exact[-1].start(), e, label
    for line in re.finditer(r"(?m)^[ \t]*(\S[^\n]{0,239}?)[ \t]*$", window):
        if title_similarity(code, line.group(1)) >= ALIGN_SIM_FLOOR:
            return s + line.start(), e, label
    return region


def pointer_entries(text, span, entries, parts):
    """Footnote-backed incorporation pointers tied to their marked index rows."""
    tail = text[span[1]:min(len(text), span[1] + 2000)]
    pointers = {m.group(1): (span[1] + m.start(), span[1] + m.end(),
                              (re.search(r"(?i)\bpart\s+(iv|iii|ii|i)\b", m.group(0)) or [None, None])[1])
                for m in re.finditer(r"(?im)^\(([a-z])\)\s+incorporated\s+by\s+reference[^\n]*$", tail)}
    out = {}
    for code, (start, end) in entries.items():
        row = text[start:end]
        marker = re.search(r"\(([a-z])\)", row, re.I)
        if marker and marker.group(1).lower() in pointers:
            part = parts.get(code)
            if part:
                a, b, pointed_part = pointers[marker.group(1).lower()]
                if pointed_part and pointed_part.upper() != part.upper():
                    continue
                out[code] = {"start": a, "end": b, "part": part,
                             "marker": marker.group(1).lower()}
    return out


def resolve(text, expected):
    """`(index_span, entries, regions)`, or `(None, {}, {})`.

    `entries` is `{code: (start, end)}` into the index itself — the row the
    filing wrote for that item. `regions` is `{code: [{pages, start, end}]}` —
    where the row says the answer lives. A region overlapping the index is
    dropped: a row pointing at its own page is not an answer.
    """
    span = find_index(text, expected)
    if span is None:
        return None, {}, {}
    ladder = page_ladder(text)
    if not ladder:
        return None, {}, {}
    entries = parse_entries(text, span, expected)
    regions = {}
    for code, (s, e) in entries.items():
        found = []
        for lo, hi in _pages(text[s:e]):
            r = _region(ladder, lo, hi)
            if r and r[0] < r[1] and (r[1] <= span[0] or r[0] >= span[1]):
                first_page_end = next((ladder[p] for p in sorted(ladder)
                                       if p >= lo), r[1])
                found.append(_align_start(
                    text, code, (*r, f"{lo}-{hi}" if hi != lo else str(lo)),
                    text[s:e], first_page_end))
        if found:
            regions[code] = [{"pages": ",".join(lab), "start": a, "end": b}
                             for a, b, lab in _merge(found)]
    return (span if regions else None), entries, regions


def _demo():
    exp = ["1", "1A", "1B", "1C", "2", "3", "4", "5", "6", "7", "7A", "8",
           "9", "9A", "15"]
    # pages long enough that the whole document exceeds INDEX_MAX — otherwise
    # the index region would swallow the body and every region resolve inside it
    body = "".join(f"page {p} body text here. " + "filler prose. " * 20 +
                   f"\n\n{p}\n\n" for p in range(1, 61))
    rows = ("Item 1. Business\nPages 3-5\n\nItem 1A. Risk Factors\nPages 10-12\n\n"
            "Item 1B. Unresolved Staff Comments\nNone\n\nItem 1C. Cybersecurity\nPage 14\n\n"
            "Item 2. Properties\nPage 15\n\nItem 3. Legal Proceedings\nNone\n\n"
            "Item 4. Mine Safety\nNone\n\nItem 5. Market\nPage 18\n\n"
            "Item 7. MD&A\nPages 20-24\n\nItem 8. Financial Statements\nPages 30-55\n")
    intel = body + "Form 10-K Cross-Reference Index\n\nItem Number Item\n\n" + rows
    span, entries, regs = resolve(intel, exp)
    assert span and {"1", "1A", "7", "8"} <= set(regs), (span, sorted(regs))
    s, e = regs["1"][0]["start"], regs["1"][0]["end"]
    assert "page 3 body" in intel[s:e] and "page 5 body" in intel[s:e]
    assert "page 6 body" not in intel[s:e] and "page 2 body" not in intel[s:e]
    # entries partition the index: ordered and non-overlapping (INV-S1)
    got = [entries[c] for c in sorted(entries, key=exp.index)]
    assert all(a[1] <= b[0] for a, b in zip(got, got[1:])), got

    # Citi's shape: index at the FRONT, bare "N.", no "Page" keyword, en dash,
    # and a row whose TITLE carries a number that must not be read as a page
    citi = ("FORM 10-K CROSS-REFERENCE INDEX\n\nItem Number Page\n\n"
            "1. Business 3–5\n\n1A. Risk Factors 10–12\n\n"
            "1B. Unresolved Staff Comments Not Applicable\n\n"
            "1C. Cybersecurity 14\n\n2. Properties Not Applicable\n\n"
            "3. Legal Proceedings—See Note 30 to the Financial Statements 40–42\n\n"
            "4. Mine Safety Not Applicable\n\n5. Market 18\n\n"
            "7. MD&A 20–24\n\n8. Financial Statements 30–55\n\n") + body
    span, entries, regs = resolve(citi, exp)
    assert span and {"1", "1A", "3", "7", "8"} <= set(regs), sorted(regs)
    s, e = regs["3"][0]["start"], regs["3"][0]["end"]
    assert "page 40 body" in citi[s:e] and "page 30 body" not in citi[s:e], citi[s:e][:80]
    for rs in regs.values():          # nothing resolves into the index itself
        for r in rs:
            assert r["end"] <= span[0] or r["start"] >= span[1]

    # a filing that merely names the phrase is not an index
    assert resolve("See the cross-reference index on page 4.\n" + body, exp)[0] is None
    print("xref demo ok")


if __name__ == "__main__":
    _demo()
