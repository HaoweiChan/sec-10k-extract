"""Python mirror of the inspector's client-side heading-anchor algorithm
(src/sec10k/web/static/index.html: coreOf/buildSourceIndex/findAnchor), kept
in lockstep so the anchor CONTRACT is gateable even though the DOM half
(iframe, TreeWalker, getBoundingClientRect) cannot be reached from Python.

Why this exists (PR #21 round 2, then round 3): the inspector's compare pane
locates each item's heading in the ORIGINAL filing by searching a
concatenated text index built by walking every visible text node — a
heading is frequently split across tags, so no single node need contain it
whole. Three defects shipped across two rounds, and all three are decidable
from fixture text without a browser, so hard rule 2 says they belong here as
a case:

  (a) round 2: the per-node join added exactly one boundary space between
      every pair of nodes REGARDLESS of whether either node's own text
      already ended or started with whitespace, so a heading spanning that
      boundary could produce a double space in the index and never
      literal-match a needle built by collapsing whitespace to single
      spaces.
  (b) round 2: disambiguating between multiple occurrences of the same
      heading (every 10-K's table of contents repeats every item heading
      before the real section) picked the occurrence whose SOURCE-byte
      fraction was closest to the extractor's NORMALIZED-text fraction for
      that item — those two fractions are not comparable, and on jpm-2024
      it locked onto the front cross-reference table and reported several
      items ANCHORED while showing a different item's heading. A
      confidently wrong anchor is worse than an honest miss (hard rule 4).
  (c) round 3, caught by THIS module's own full-fixture-set check before
      shipping: the round-3 fix for (a) still assumed exactly ONE separator
      character belongs between any two adjacent nodes. cat-2023 falsified
      that in the other direction — `<b>Item 1.</b>Business.` renders with
      ZERO characters between the nodes, not one, so an inserted boundary
      space broke the match this time.

(a)-(c) share one root cause: how much whitespace separates two DOM text
nodes when rendered is an arbitrary, per-filing markup choice this repo has
now seen go three different ways on committed fixtures. Rather than modelling
it, whitespace is dropped from the matching problem ENTIRELY: `core_of`
strips it out on both the needle and the haystack, so two runs of text are
"the same" here iff their non-whitespace characters agree in order — no
separator-counting left to get wrong. A parallel raw-offset index still
allows translating a match back to a DOM (node, offset) for scrolling.

Body agreement (b)'s fix, unchanged in spirit: among every occurrence of a
heading, the one whose FOLLOWING core text shares the longest run with the
opening of the item's own extracted `text` (itself core-ified, with its own
heading prefix stripped first — item.text starts with its own heading, so
comparing it as-is against "whatever follows the heading in the source"
compares apples to oranges) is the real section. Below AGREEMENT_MIN
agreeing core characters, the result is `None` (unanchored) rather than a
guess.

Pure stdlib (html.parser for the HTML-to-visible-text half), no fastapi
import, same convention as view.py/capabilities.py.

Self-check: python3 -m src.sec10k.web.anchor
"""
from html.parser import HTMLParser

AGREEMENT_WINDOW = 400   # raw chars of the source scanned per candidate
AGREEMENT_MIN = 15       # core (whitespace-free) chars that must agree


def core_of(s):
    """Lowercased, whitespace-free core of a string — used for MATCHING
    only. See the module docstring (c): whether two adjacent runs of text
    are joined by no space, one space, or several is an arbitrary
    rendering choice, so it is simply not part of what "the same text"
    means here."""
    return "".join(ch.lower() for ch in (s or "") if not ch.isspace())


class _VisibleTextCollector(HTMLParser):
    """Collects text-node-shaped chunks the way a browser's TreeWalker over
    `doc.body` would: script/style contents are never visible text, and
    nothing before <body> counts (title, meta, head scripts). SEC HTML
    filings are not adversarial toward their own parser, so this stdlib
    parser is a faithful enough stand-in for the DOM without needing one."""

    _SKIP = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chunks = []
        self._skip_depth = 0
        self._in_body = False
        self._body_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self._in_body = True
            self._body_depth = 1
            return
        if self._in_body:
            self._body_depth += 1
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        if self._in_body:
            self._body_depth -= 1
            if self._body_depth <= 0:
                self._in_body = False

    def handle_data(self, data):
        if self._in_body and not self._skip_depth and data:
            self.chunks.append(data)


def visible_text_chunks(raw, is_html):
    """raw file content -> a list of text-node-shaped chunks. HTML is run
    through the stdlib parser (body only, script/style excluded) to mirror
    the DOM's text nodes; `.txt` filings are served as a single `text/plain`
    response, which a browser renders as ONE giant text node inside one
    implicit <pre> — confirmed live in round 1 (ibm-1997) — so the whole
    file is returned as one chunk, not split into lines."""
    if not is_html:
        return [raw] if raw else []
    p = _VisibleTextCollector()
    try:
        p.feed(raw)
    except Exception:
        pass
    # A malformed/truncated document may never open <body> (or may lack one
    # entirely) — fall back to the whole file as HTML.parser saw it, rather
    # than silently returning no visible text at all.
    if p.chunks:
        return p.chunks
    p2 = _VisibleTextCollector()
    p2._in_body = True
    try:
        p2.feed(raw)
    except Exception:
        pass
    return p2.chunks


def build_source_index(chunks):
    """-> (core_text, nodes). `core_text` is the whitespace-free, lowercased
    concatenation of every chunk's own characters, in order, with NO
    separator inserted between chunks (whitespace carries no matching
    information — see core_of — and the risk of two unrelated chunks
    accidentally fusing into a false match for a 15+ char heading needle is
    negligible). `nodes[i]` = {"start", "core_len", "raw_index_of",
    "chunk_i"}: `raw_index_of[k]` maps `core_text[start+k]` back to that
    chunk's own raw character index, for translating a match to a DOM
    (node, offset) — `chunk_i` stands in for the DOM node reference
    index.html keeps directly."""
    parts, nodes = [], []
    cursor = 0
    for chunk_i, raw in enumerate(chunks):
        core_chars, raw_index_of = [], []
        for i, ch in enumerate(raw):
            if ch.isspace():
                continue
            core_chars.append(ch.lower())
            raw_index_of.append(i)
        if not core_chars:
            continue
        core = "".join(core_chars)
        nodes.append({"start": cursor, "core_len": len(core),
                      "raw_index_of": raw_index_of, "chunk_i": chunk_i})
        parts.append(core)
        cursor += len(core)
    return "".join(parts), nodes


def raw_offset(nodes, core_offset):
    """core_text offset -> {"chunk_i", "offset"} (the chunk's own raw
    character index), via binary search over `nodes` (built in ascending
    `start` order)."""
    lo, hi, hit = 0, len(nodes) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        n = nodes[mid]
        if core_offset < n["start"]:
            hi = mid - 1
        elif core_offset >= n["start"] + n["core_len"]:
            lo = mid + 1
        else:
            hit = n
            break
    if hit is None:
        return None
    return {"chunk_i": hit["chunk_i"], "offset": hit["raw_index_of"][core_offset - hit["start"]]}


def _common_prefix_len(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _target_core(item_text, needle):
    """The core text to require agreement on: the item's own extracted
    `text` starts with its own heading (view.py slices from the item's
    start offset, which IS the heading), so comparing it as-is against the
    source core text FOLLOWING a heading match would compare
    "companybackground..." to "item1.businesscompanybackground..." and
    never agree from character 0 — a real bug this module's own
    full-fixture-set check caught before it shipped (aapl-2025 scored 0 at
    BOTH the TOC and the correct body occurrence). Stripping the item's own
    heading prefix first makes both sides "whatever comes after the
    heading"."""
    core = core_of(item_text)
    if needle and core.startswith(needle):
        core = core[len(needle):]
    return core


def find_anchor(index_text, heading_text, item_text):
    """The fixed algorithm: body-agreement disambiguation over a
    whitespace-free core index. Mirrors index.html's `findAnchor`. ->
    matched core-text offset, or None (honest miss) when there is no
    single-occurrence heading and no candidate's following text agrees
    with `item_text` well enough."""
    needle = core_of(heading_text)
    if not needle:
        return None
    occurrences, frm = [], 0
    while True:
        i = index_text.find(needle, frm)
        if i < 0:
            break
        occurrences.append(i)
        frm = i + 1
    if not occurrences:
        return None
    if len(occurrences) == 1:
        return occurrences[0]
    target = _target_core(item_text, needle)
    if not target:
        return None
    best, best_score = occurrences[0], -1
    for occ in occurrences:
        following = index_text[occ + len(needle): occ + len(needle) + AGREEMENT_WINDOW]
        score = _common_prefix_len(following, target)
        if score > best_score:
            best_score, best = score, occ
    # A genuinely short item ("None.", "Not applicable.") can never reach
    # AGREEMENT_MIN chars of agreement even at the CORRECT occurrence, since
    # there is nothing more of the target left to agree on — require the
    # full target instead once it is shorter than the floor, rather than
    # rejecting every short item as unanchored (aapl-2025 Item 1B: target
    # "none." is 5 chars, a full, exact, unambiguous match).
    required = min(AGREEMENT_MIN, len(target))
    return best if best_score >= required else None


def find_anchor_frac(index_text, heading_text, expected_frac):
    """The ROUND-2 algorithm, kept only to reproduce and pin the bug it
    caused (round-3 finding V1b): nearest-occurrence-by-fraction
    disambiguation, where `expected_frac` is the extractor's `item.start`
    offset as a fraction of normalized_text. Comparing that against a
    source-core-character fraction is the defect — the two are not
    comparable, and this locks onto a front cross-reference table on
    filings like jpm-2024. Not used by the fixed pipeline; exists so the
    regression case can demonstrate what "watched red" looked like against
    the algorithm actually shipped in round 2."""
    needle = core_of(heading_text)
    if not needle:
        return None
    best, best_dist, frm = None, float("inf"), 0
    while True:
        i = index_text.find(needle, frm)
        if i < 0:
            break
        if expected_frac is None:
            return i
        dist = abs(i / max(1, len(index_text)) - expected_frac)
        if dist < best_dist:
            best_dist, best = dist, i
        frm = i + 1
    return best


def _demo():
    # core_of: drops ALL whitespace, case-folds -- no separator counting
    assert core_of("  Item 7.  ") == "item7."
    assert core_of("Management’s") == "management’s"

    # (a)/(c): a heading split across two nodes with EXTRA whitespace at the
    # join (round-2 bug) and, separately, with NO whitespace at all between
    # them (round-3 bug, cat-2023's real `<b>Item 1.</b>Business.` shape) --
    # both must literal-match now that whitespace isn't part of matching.
    extra_ws_text, _ = build_source_index(["Item 7. ", " Management's Discussion"])
    assert core_of("Item 7. Management's Discussion") in extra_ws_text
    zero_ws_text, _ = build_source_index(["Item 1.", "Business."])
    assert core_of("Item 1.Business.") in zero_ws_text

    # (b): TOC vs body -- two occurrences, only the second is followed by
    # the item's own prose. item_text below deliberately STARTS WITH ITS
    # OWN HEADING, exactly like the real pipeline's `it.text`.
    chunks = ["Item 7. Management's Discussion", "20",
              "Item 7A. Quant", "21",
              "Item 7. Management's Discussion",
              "The following discussion should be read in conjunction with statements"]
    text2, nodes2 = build_source_index(chunks)
    anchor = find_anchor(text2, "Item 7. Management's Discussion",
                          "Item 7. Management's Discussion\n\nThe following discussion should be read")
    second_node = [n for n in nodes2 if n["chunk_i"] == 4][0]
    assert second_node["start"] <= anchor < second_node["start"] + second_node["core_len"], \
        f"picked the wrong occurrence: anchor={anchor}, second node starts at {second_node['start']}"

    # below-threshold agreement -> None (honest miss), never a guess
    assert find_anchor(text2, "Item 7. Management's Discussion",
                        "Item 7. Management's Discussion\n\nCompletely unrelated text sharing nothing") is None

    # a single occurrence is accepted even with no body to check against --
    # there is no ambiguity to break
    text3, _ = build_source_index(["Item 99. Unique Heading", "some body text right after"])
    assert find_anchor(text3, "Item 99. Unique Heading", "") == 0

    # raw_offset round-trips a match back to a (chunk, raw index)
    hit = raw_offset(nodes2, anchor)
    assert hit["chunk_i"] == 4

    # find_anchor_frac (the round-2 algorithm) reproduces the jpm-2024-style
    # bug: given the SAME two candidates, an `expected_frac` that happens to
    # sit closer to the TOC occurrence's own fraction picks it over the
    # correct, later body occurrence -- exactly the "confidently wrong"
    # failure round 3 found live.
    toc_frac = 0 / len(text2)
    wrong = find_anchor_frac(text2, "Item 7. Management's Discussion", toc_frac + 0.001)
    first_node = [n for n in nodes2 if n["chunk_i"] == 0][0]
    assert first_node["start"] <= wrong < first_node["start"] + first_node["core_len"], \
        "find_anchor_frac did not reproduce the TOC-lock bug it exists to pin"

    # visible_text_chunks: HTML pulls body text only (script/style/head
    # excluded); a .txt filing is one single chunk, matching how a browser
    # renders a text/plain response as one giant text node
    html = "<html><head><title>x</title></head><body>Hello <script>evil()</script>World</body></html>"
    assert visible_text_chunks(html, True) == ["Hello ", "World"]
    assert visible_text_chunks("plain text file", False) == ["plain text file"]

    print("[anchor self-check] ok")


if __name__ == "__main__":
    _demo()
