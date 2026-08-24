"""Cover-page field resolution (ADR-034) — opt-in, offsets-only, no edit.

`resolve(text, region_end)` returns the ADR-034 §e record dict for the cover
region `text[0:region_end]`. Every resolved field carries the offsets of its
value in the WHOLE `normalized_text`, so `normalized_text[start:end] == value`
is checkable by a caller that never saw this module — the same discipline
INV-S2 puts on an item span.

The pivot is the EIN, not the caption (ADR-034 §b2). Normalization flattens
the cover's two-column typesetting, so the value pair and the caption pair end
up on different lines and in filer-specific orders — four committed filings
produce four caption layouts. `\\d{2}-\\d{7}` produces one shape on all 38
non-refused fixtures, and it sits BETWEEN the two values the caption pair
describes, which is what makes the state readable without reconstructing the
table.
"""
import re

from src.sec10k.normalize import COVER_DATE_RE, _parse_date
from src.sec10k.validate import BASE_MISSING, BASE_STRICT, BASE_WEAK

# An EIN is two digits, a hyphen, seven digits. Nothing else on a 10-K cover
# has that shape — checked against all 38 non-refused fixtures (ADR-034 §a3).
EIN_RE = re.compile(r"\b(\d{2}-\d{7})\b")
# `Commission File Number: 001-36743` / `Commission file number 1-35` /
# `Commission File No. 333-192107`. The value stops at whitespace-run, newline,
# or the `or` that opens the transition-report clause.
CFN_RE = re.compile(r"(?i)commission file (?:number|no\.?)\s*:?\s*"
                    r"([0-9][-0-9A-Za-z()]*(?:[ ][0-9A-Za-z]+)?)")
# the name caption, in the wordings the corpus uses (ADR-034 §b3). The
# orientation is decided at the call site from the caption's own punctuation,
# not from the wording. `small business issuer` is the pre-2008 small-filer
# wording.
# `[^)\n:]*` excludes the colon on purpose: in orientation B the caption and
# its value share a line (`...in its charter: Bank of America Corporation`), so
# a greedy run to end-of-line would swallow the value into the caption match.
# `[ \t]*` and NOT `\s*` after the paren: `\s` includes the newline, so a
# leading `\s*` starts the match on the blank line ABOVE the caption and every
# line-relative test below (own_line, the trailing colon, the line above) then
# reads the wrong line. bac-2006 is where that showed.
NAME_CAP_RE = re.compile(r"(?i)(\()?[ \t]*(?:exact name of (?:the )?registrant"
                         r"|name of small business issuer)[^)\n:]*(\))?\s*(:)?")
# The 12(b) COLUMN HEADER, not the words "trading symbol" (cold review, finding
# 3): reac-2015's cover says "...held by non-affiliates and no trading symbol."
# in prose, and a bare substring gate read that negation as evidence of the
# column. The column is a header ROW — it always carries a second header cell
# beside the symbol one — so requiring the neighbour is what distinguishes the
# table from a sentence about it.
SYMBOL_HDR_RE = re.compile(r"(?i)trading\s+symbol\(?s?\)?")
SYMBOL_NEIGHBOUR_RE = re.compile(r"(?i)title of each class|name of each exchange")
# where the 12(b) block ends. Without a stop the symbol scan runs to the end of
# the cover region and picks the first capitalised token it finds anywhere —
# on sgrp-2019, whose own value row is `N/A N/A N/A`, that was the `YES` of a
# check-mark line 700 characters later.
SYMBOL_STOP_RE = re.compile(r"(?i)indicate by check mark|securities registered "
                            r"pursuant to section 12\(g\)|aggregate market value")
SYMBOL_WINDOW = 500   # max chars of value rows read after the header row
# a ticker as filers typeset it in that column: 1-5 upper-case letters, alone
# on its run. The em-dash rows (Apple's listed notes) carry no symbol, and
# `N/A` is the filer saying there is none (sgrp-2019) — neither is a ticker,
# and a column that carries neither reports `missing`, not a guess.
# `(?<![/\w])`/`(?![/\w])` and NOT `\b`: a word boundary sits happily on both
# sides of the slash in `N/A`, so `\b([A-Z]{1,5})\b` rejects the N and then
# publishes the A as a ticker (sgrp-2019, whose value row is `N/A N/A N/A`).
SYMBOL_RE = re.compile(r"(?<![/\w])([A-Z]{1,5})(?![/\w])")
# A caption fragment, never a value. Normalization breaks the two-column
# caption pair across lines in filer-specific places, so the text before an EIN
# is as often a piece of a caption as it is the state — gs-2002 and intc-2002
# leave `incorporation or organization)` there, bac-2006 leaves the whole
# `IRS Employer Identification No.:` line.
CAPTION_WORD_RE = re.compile(r"(?i)jurisdiction|incorporat|organizat|identificat"
                             r"|employer|commission|registrant|i\.?r\.?s")
# a label the filer put INSIDE the EIN cell (wfc-2008: `No. 41-0449260`)
EIN_LABEL_RE = re.compile(r"(?i)(?:i\.?r\.?s\.?\s*)?(?:employer\s*)?"
                          r"(?:identification\s*)?(?:no\.?|number)\s*:?\s*$")
# the SIC code a small filer puts in a THIRD column between state and EIN
# (sgrp-2019: `Nevada 2821 38-4045138`). Four bare digits are never a state.
SIC_RE = re.compile(r"\s+\d{4}\s*$")


def _rec(value=None, start=None, end=None, status="missing",
         confidence=BASE_MISSING, method="era_gate"):
    return {"value": value, "start": start, "end": end, "status": status,
            "confidence": confidence, "method": method}


def _resolved(text, start, end, method, confidence=BASE_STRICT):
    return _rec(text[start:end], start, end, "resolved", confidence, method)


def _line_bounds(text, i):
    """[start, end) of the line containing offset `i`."""
    return text.rfind("\n", 0, i) + 1, (text.find("\n", i) + 1 or len(text) + 1) - 1


def _clean_state(v):
    """None if `v` is not a state value, else the value with the filer's own
    in-cell label and SIC column removed. Order matters: the SIC code is
    stripped before the label test so `Nevada 2821` is not read as a label."""
    v = v.strip()
    while True:
        before = v
        v = SIC_RE.sub("", v).strip()
        v = EIN_LABEL_RE.sub("", v).strip()
        if v == before:
            break
    if not v or not _is_name(v) or CAPTION_WORD_RE.search(v) or v.endswith((")", ":")):
        return None
    # a state is a short proper name, never a sentence or a number
    if len(v) > 30 or any(ch.isdigit() for ch in v):
        return None
    return v


def _is_name(v):
    """A company name — or a state — contains letters. A fixed-width .txt cover
    underlines its values with a rule (`24HOLDINGS INC.` over
    `---------------`, ksb-2007), and without this every caption orientation
    reads the rule instead of the value it underlines."""
    return sum(ch.isalpha() for ch in v) >= 2


def _lines_back(region, i, limit=6):
    """(start, end, text) of each non-empty line at or before offset `i`,
    nearest first."""
    out = []
    end = i
    while end > 0 and len(out) < limit:
        ls = region.rfind("\n", 0, end) + 1
        raw = region[ls:end]
        if raw.strip():
            off = ls + (len(raw) - len(raw.lstrip()))
            out.append((off, off + len(raw.strip()), raw.strip()))
        end = ls - 1
    return out


def _ein_and_state(region):
    """(ein record, state record). The state is the nearest text before the EIN
    that survives `_clean_state` — on the EIN's own line first, then walking
    back over the caption lines normalization left between them."""
    m = EIN_RE.search(region)
    if not m:
        return _rec(method="ein_regex"), _rec(method="ein_pivot")
    ein = _resolved(region, m.start(1), m.end(1), "ein_regex")
    for off, _end, raw in _lines_back(region, m.start(1)):
        v = _clean_state(raw)
        if v is None:
            continue
        # `v` is a prefix of `raw` after stripping — locate it rather than
        # arithmetic, so the published offsets cannot drift from the value
        i = region.index(v, off)
        return ein, _resolved(region, i, i + len(v), "ein_pivot")
    return ein, _rec(method="ein_pivot")


def _commission_file_number(region):
    m = CFN_RE.search(region)
    if not m:
        return _rec(method="caption_anchored")
    s, e = m.start(1), m.end(1)
    # trailing sentence punctuation is not part of the number (`1-6991.`)
    while e > s and region[e - 1] in ".,;:":
        e -= 1
    return _resolved(region, s, e, "caption_anchored")


def _registrant_name(region, ein_state, cfn):
    """Caption in either orientation, else position (ADR-034 §b3)."""
    m = NAME_CAP_RE.search(region)
    if m:
        cap_ls, cap_le = _line_bounds(region, m.start())
        own_line = not region[cap_ls:m.start()].strip()
        parenthesised = bool(m.group(1) or m.group(2))
        trailing_colon = bool(m.group(3)) and not region[m.end():cap_le].strip()
        if own_line and parenthesised:
            # orientation A — a parenthesised caption on its own line describes
            # the line ABOVE it (aapl, ge-1994, premier-pacific, wfc)
            for off, end, raw in _lines_back(region, cap_ls - 1):
                if _is_name(raw) and not EIN_RE.search(raw):
                    return _resolved(region, off, end, "caption_anchored")
        elif own_line and trailing_colon:
            # orientation C — an unparenthesised caption line ending in a colon
            # describes the NEXT line (bac-2006's alternating stack). Reading it
            # as orientation A publishes the commission file number as the
            # company name, which is what the first resolver did.
            nxt = region[cap_le + 1:]
            for line in nxt.split("\n"):
                if _is_name(line):
                    v = line.strip()
                    off = region.index(v, cap_le)
                    return _resolved(region, off, off + len(v), "caption_anchored")
        else:
            # orientation B — caption and value share a line, colon-separated
            _, le = _line_bounds(region, m.end())
            v = region[m.end():le].strip()
            if v:
                off = m.end() + region[m.end():le].index(v)
                return _resolved(region, off, off + len(v), "caption_anchored")
    # no caption anywhere: the non-empty line between the commission file
    # number and the EIN-pivot line. One filing in 38 (msft-2013), so it is
    # deliberately BASE_WEAK — a positional guess must not read like a match.
    lo = cfn["end"] if cfn["status"] == "resolved" else 0
    hi = ein_state["start"] if ein_state["status"] == "resolved" else len(region)
    lines = [l.strip() for l in region[lo:hi].split("\n")
             if _is_name(l)]
    if not lines:
        return _rec(method="positional")
    v = lines[-1]
    off = region.rindex(v, lo, hi)
    return _resolved(region, off, off + len(v), "positional", BASE_WEAK)


def _fiscal_year_end(region):
    """`normalize.COVER_DATE_RE`, not a second regex — a private copy would be
    free to drift from the one the pipeline already runs.

    It reports `missing` on three fixtures whose `meta.period_end` IS known
    (ibm-1997, ibr-security-holders, jpm-2024): there the date came from the
    SGML header or a dei fact, neither of which survives into
    `normalized_text`, so there is no span to point at. Under-reporting is the
    correct answer for a COVER field — the value is already published in
    `meta.period_end`, and a cover record with no offsets would be exactly the
    bare assertion ADR-034 §e exists to forbid. The method is named for the
    regex it reuses and NOT `reused_meta`: this function never reads `meta`,
    and a name that says it does is the drift the check types cannot see.

    `_parse_date` guards the capture for the same reason `normalize.period_end`
    does — the group is `[A-Z][a-z]{2,8}...`, which a non-month satisfies."""
    m = COVER_DATE_RE.search(region)
    if not m or _parse_date(m.group(1)) is None:
        return _rec(method="cover_date_re")
    return _resolved(region, m.start(1), m.end(1), "cover_date_re")


def _trading_symbol(region):
    """The 2019+ cover-page taxonomy column. The gate is the COLUMN HEADER ROW's
    presence, not the filing's era and not the words alone: `format_era ==
    "ixbrl"` reports `not_in_era` on sgrp-2019, a legacy-HTML filing that has
    the column, and a bare `trading symbol` substring reports `resolved` on
    reac-2015, whose cover says "and no trading symbol" in prose (ADR-034 §c,
    corrected twice). A header row always carries a neighbouring header cell;
    a sentence about symbols does not."""
    for cap in SYMBOL_HDR_RE.finditer(region):
        ls, le = _line_bounds(region, cap.start())
        if not SYMBOL_NEIGHBOUR_RE.search(region[ls:le]):
            continue                      # prose, not the column header row
        window = region[le:le + SYMBOL_WINDOW]
        stop = SYMBOL_STOP_RE.search(window)
        window = window[:stop.start()] if stop else window
        m = SYMBOL_RE.search(window)
        if m:
            off = le + m.start(1)
            return _resolved(region, off, off + len(m.group(1)), "caption_anchored")
        # the column exists and carries no ticker (`N/A`, or an em-dash row).
        # `missing` is the honest answer: the era has the field, we found none.
        return _rec(method="caption_anchored")
    return _rec(status="not_in_era", confidence=BASE_STRICT, method="era_gate")


def resolve(text, region_end):
    """ADR-034 §e's `cover` record for `text[0:region_end]`."""
    region = text[:region_end]
    ein, state = _ein_and_state(region)
    cfn = _commission_file_number(region)
    return {
        "registrant_name": _registrant_name(region, state, cfn),
        "state_of_incorporation": state,
        "ein": ein,
        "commission_file_number": cfn,
        "fiscal_year_end": _fiscal_year_end(region),
        "trading_symbol": _trading_symbol(region),
    }


def _demo():
    # the four committed layouts, in miniature — each is the shape ADR-034 §b2
    # says no caption rule reads, and the EIN pivot does.
    aapl = ("Commission File Number: 001-36743\n\nApple Inc.\n\n(Exact name of "
            "Registrant as specified in its charter)\n\nCalifornia 94-2404110\n\n"
            "(State or other jurisdiction\n\nof incorporation or organization)\n"
            "(I.R.S. Employer Identification No.)\n")
    r = resolve(aapl, len(aapl))
    assert r["state_of_incorporation"]["value"] == "California", r["state_of_incorporation"]
    assert r["ein"]["value"] == "94-2404110"
    assert r["registrant_name"]["value"] == "Apple Inc."
    assert r["commission_file_number"]["value"] == "001-36743"
    # every resolved field is verbatim at its own offsets — the property the
    # `cover` check type re-derives rather than trusting
    for f, rec in r.items():
        if rec["status"] == "resolved":
            assert aapl[rec["start"]:rec["end"]] == rec["value"], f

    # values on two lines, captions on four (premier-pacific)
    pp = ("Commission File No. 333-192107\n\nPREMIER PACIFIC CONSTRUCTION, INC.\n\n"
          "(exact name of registrant as specified in its charter)\n\nNEVADA\n\n"
          "90-0920687\n\n(State or other jurisdiction\n\n")
    r = resolve(pp, len(pp))
    assert r["state_of_incorporation"]["value"] == "NEVADA", r["state_of_incorporation"]
    assert r["registrant_name"]["value"] == "PREMIER PACIFIC CONSTRUCTION, INC."

    # no name caption at all -> positional, and it must NOT read as strict
    ms = ("Commission File Number 0-14278\n\nMICROSOFT CORPORATION\n\n"
          "WASHINGTON 91-1144442\n\n(STATE OF INCORPORATION) (I.R.S. ID)\n")
    r = resolve(ms, len(ms))
    assert r["registrant_name"]["value"] == "MICROSOFT CORPORATION", r["registrant_name"]
    assert r["registrant_name"]["method"] == "positional"
    assert r["registrant_name"]["confidence"] == BASE_WEAK
    assert r["state_of_incorporation"]["value"] == "WASHINGTON"

    # caption BEFORE the value, colon-separated (bac-2006)
    bac = ("Commission file number: 1-6523 Exact name of registrant as specified "
           "in its charter: Bank of America Corporation\n\nDelaware 56-0906609\n")
    r = resolve(bac, len(bac))
    assert r["registrant_name"]["value"] == "Bank of America Corporation", r["registrant_name"]

    # the era gate is a POSITIVE claim, and it is the caption's absence
    assert resolve(aapl, len(aapl))["trading_symbol"]["status"] == "not_in_era"
    sym = "Title of each class Trading Symbol(s) Name of each exchange\n\nCommon Stock AAPL The Nasdaq\n"
    assert resolve(sym, len(sym))["trading_symbol"]["value"] == "AAPL"

    # a cover with no EIN at all degrades, it does not crash
    r = resolve("FORM 10-K\n", 10)
    assert r["ein"]["status"] == "missing" and r["ein"]["confidence"] == BASE_MISSING
    print("[cover] ok")


if __name__ == "__main__":
    _demo()
