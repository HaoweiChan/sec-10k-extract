"""Layers 4-7: candidates -> TOC/false-candidate filter -> boundaries -> status.

Mechanism: docs/architecture/overview.md. Rulings: ADR-004 (pointer items),
ADR-005 (trivial bodies / absent headings), ADR-007 (T4 thresholds, measured).

Self-check: python3 -m src.sec10k.segment
"""
import difflib
import re
from datetime import date

# ---------------------------------------------------------------- taxonomy

# code -> (part, [title aliases]). Aliases are era variants: the same code was
# retitled over the decades (Item 6 became "[Reserved]" in 2021; Item 4 was
# "Submission of Matters to a Vote of Security Holders" before Mine Safety).
TITLES = {
    "1":  ("I", ["Business"]),
    "1A": ("I", ["Risk Factors"]),
    "1B": ("I", ["Unresolved Staff Comments"]),
    "1C": ("I", ["Cybersecurity"]),
    "2":  ("I", ["Properties"]),
    "3":  ("I", ["Legal Proceedings"]),
    "4":  ("I", ["Mine Safety Disclosures",
                 "Submission of Matters to a Vote of Security Holders",
                 # 2010-02-28 (Release 33-9089A) removed the vote item;
                 # Mine Safety arrived 2011-12-15. In the window filers wrote
                 # "RESERVED" / "(Removed and Reserved)" — wmt-2010 is the
                 # eval case; the longer variants clear SIM_FLOOR by ratio.
                 "Reserved"]),
    "5":  ("II", ["Market for Registrant's Common Equity, Related Stockholder "
                  "Matters and Issuer Purchases of Equity Securities",
                  "Market for the Registrant's Common Stock and Related "
                  "Stockholder Matters"]),
    "6":  ("II", ["[Reserved]", "Selected Financial Data"]),
    "7":  ("II", ["Management's Discussion and Analysis of Financial Condition "
                  "and Results of Operations"]),
    "7A": ("II", ["Quantitative and Qualitative Disclosures About Market Risk"]),
    "8":  ("II", ["Financial Statements and Supplementary Data"]),
    "9":  ("II", ["Changes in and Disagreements with Accountants on Accounting "
                  "and Financial Disclosure"]),
    "9A": ("II", ["Controls and Procedures"]),
    "9B": ("II", ["Other Information"]),
    "9C": ("II", ["Disclosure Regarding Foreign Jurisdictions that Prevent "
                  "Inspections"]),
    "10": ("III", ["Directors, Executive Officers and Corporate Governance",
                   "Directors and Executive Officers of the Registrant"]),
    "11": ("III", ["Executive Compensation"]),
    "12": ("III", ["Security Ownership of Certain Beneficial Owners and "
                   "Management and Related Stockholder Matters"]),
    "13": ("III", ["Certain Relationships and Related Transactions, and "
                   "Director Independence"]),
    "14": ("III", ["Principal Accountant Fees and Services",
                   "Exhibits, Financial Statement Schedules, and Reports on "
                   "Form 8-K"]),
    "15": ("IV", ["Exhibits, Financial Statement Schedules",
                  "Exhibits and Financial Statement Schedules"]),
    "16": ("IV", ["Form 10-K Summary"]),
}

# When each code joined the form, by fiscal-period end date. Dates are the
# rule's effective date except where the eval set pins it tighter — see
# ADR-007 for the 9C boundary, which sandston-2021 constrains.
ADDED = {
    "1A": date(2005, 12, 1), "1B": date(2005, 12, 1),
    "1C": date(2023, 12, 15),
    "7A": date(1997, 6, 15),
    "9A": date(2003, 8, 14), "9B": date(2003, 8, 14),
    # 9C's rule keys on FILING date (annual reports filed on/after 2022-01-01),
    # and this table keys on period end — a different date. Filing date is not
    # recoverable from a modern primary .htm (2 of 15 fixtures carry an SGML
    # header), so the boundary is the earliest period end whose report can land
    # after the cutoff. Calendar-FY2021 filers, the largest cohort of that
    # season, file in Feb-Mar 2022 and MUST address 9C; keyed at 2022-01-01
    # they lost it entirely and its text was annexed to Item 9B. Filers who
    # legitimately have no 9C heading fall through to `omitted` (see classify).
    "9C": date(2021, 10, 1),
    "15": date(2003, 8, 14),   # Exhibits moved 14 -> 15 when 14 became Fees
    "16": date(2016, 6, 1),
}
ORDER = ["1", "1A", "1B", "1C", "2", "3", "4", "5", "6", "7", "7A", "8", "9",
         "9A", "9B", "9C", "10", "11", "12", "13", "14", "15", "16"]

# The alias lists above already carry the era variants, but nothing selected
# between them: every pre-2003 filing shipped item 14 as "Principal Accountant
# Fees and Services", part III, over a span whose text is the exhibit index —
# the label contradicted the content and the part contradicted the filing
# (pre-B audit finding 3). TITLES[code][1][0] applies from this date; the
# second alias applies before it.
ALIAS_FROM = {
    "4": date(2011, 12, 15),   # Mine Safety replaced Submission of Matters
    "5": date(2005, 12, 1),    # retitled to add Issuer Purchases
    "6": date(2021, 2, 10),    # S-K amendment: Selected Financial Data -> [Reserved]
    "10": date(2003, 8, 14),
    "14": date(2003, 8, 14),   # 14 became Fees when Exhibits moved to 15
    "15": date(2003, 8, 14),
}
# ...and one code changes PART, not just title, at the same boundary.
LEGACY_PART = {"14": "IV"}


def item_label(code, period_end):
    """(part, title) for a code as of the filing's era. Not cosmetic: the
    inspector renders this over the item's text, so an era-wrong label is a
    statement to the reader that the extraction is something it is not."""
    part, titles = TITLES[code]
    # Item 4's Reserved window sits between its two ALIAS_FROM phases. Keyed
    # on period end like everything here: Jan-2010+ period ends file after the
    # 2010-02-28 effective date; Dec-2009 enders mostly filed before it.
    if code == "4" and period_end and date(2010, 1, 1) <= period_end < ALIAS_FROM["4"]:
        return part, "Reserved"
    legacy = code in ALIAS_FROM and not (period_end and period_end >= ALIAS_FROM[code])
    if legacy:
        return LEGACY_PART.get(code, part), titles[min(1, len(titles) - 1)]
    return part, titles[0]


def expected_items(period_end):
    """Codes the filing's era requires, in document order."""
    return [c for c in ORDER
            if c not in ADDED or (period_end and period_end >= ADDED[c])]


# ---------------------------------------------------------------- candidates

# One line, one heading. `\s*` is deliberately NOT used: it matches newlines,
# which would let a bare TOC/page-furniture "Item 8" swallow the next line as
# its title. The letter suffix must not be followed by another letter, or
# "Item 1 above" parses as item 1A; the optional parenthetical absorbs the
# real-world "Item 9A(T)" / "Item 9A(I)" template leftovers.
HEADING_RE = re.compile(
    r"(?im)^[ \t\xa0]*(?:part[ \t]+[ivx]+[ \t]*[-–—.:]?[ \t]*)?"
    r"item[ \t\xa0]*(\d{1,2})(?:[ \t]?([A-Da-d]))?(?![A-Za-z])"
    r"(?:\([A-Za-z]{1,2}\))?[ \t]*[.:)\-–—]?[ \t]*(.*)$")

# ADR-007, measured over all 12 10-K fixtures: accepted headings score
# 0.593 at worst (median 1.0); the best-scoring false candidate scores 0.141.
# The floor sits at the midpoint of that empty band, erring toward accepting
# odd real titles — a missed heading costs an item, a false one is caught by
# the canonical-code and ordering rules downstream.
SIM_FLOOR = 0.37
TOC_CLUSTER_MIN = 5       # distinct codes needed before a dense run counts as an index
TOC_GAP_MAX = 400         # ADR-007: real short items sit ~43 chars apart too,
                          # so the gap alone never decides — recurrence does


def _norm_title(s):
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


def title_similarity(code, title):
    """Best match against the code's era aliases, 0..1."""
    t = _norm_title(title)
    if not t:
        return 0.0
    return max(difflib.SequenceMatcher(None, t, _norm_title(a)).ratio()
               for a in TITLES[code][1])


def _next_lines(text, pos, n=2, window=600):
    """The next `n` non-empty lines after pos. A filer may put the item code and
    its title in separate markup blocks, which normalization renders as
    'Item 1.\\n\\nBUSINESS'."""
    out = []
    for line in text[pos:pos + window].split("\n"):
        if line.strip():
            out.append(line.strip())
            if len(out) == n:
                break
    return out + [""] * (n - len(out))


def find_candidates(text, expected):
    """Every plausible heading for an expected code, with its features."""
    out = []
    for m in HEADING_RE.finditer(text):
        code = m.group(1) + (m.group(2) or "").upper()
        if code not in expected:
            continue  # INV-S3: era-invalid and non-canonical codes never surface
        title = m.group(3).strip()
        line = m.group(0).strip()
        heading_end = m.end()
        # A bare code line is USUALLY page furniture or a TOC cell, which is why
        # "no title on the heading line" is a free filter. But JNJ 2016 puts the
        # code and the title in separate blocks for 18 of 21 items, so there the
        # rule rejects every real heading — the discriminator inverts (H1
        # triage). Take the next line as the title when it reads like one, and
        # let the TOC-cluster rule decide what is furniture: measured, real body
        # headings sit a median 2,824 chars apart while TOC runs sit 50-59
        # apart, so the existing cluster thresholds already separate them and no
        # new number is introduced here.
        via_next = False
        if not title:
            nxt, after = _next_lines(text, m.end())
            # ...but if ANOTHER item code follows immediately, the pair is an
            # index row, not a heading and its body. The TOC-cluster rule would
            # catch a full contents page; this catches a run shorter than
            # TOC_CLUSTER_MIN, which no real 10-K produces but which nothing
            # else would stop.
            if title_similarity(code, nxt) >= SIM_FLOOR and not HEADING_RE.match(after):
                title, via_next = nxt, True
                # heading_end MUST advance past the promoted title. Leaving it
                # at the end of the bare code line leaks the title into the
                # body, which shifts the sentence boundaries classify() reads —
                # that is how JNJ's Part III proxy pointers came back
                # `extracted` at 0.95 instead of incorporated_by_reference
                # (pre-B audit finding 2).
                j = text.find(nxt, m.end())
                if j != -1:
                    heading_end = j + len(nxt)
        out.append({
            "item": code, "start": m.start(), "heading_end": heading_end,
            "heading_text": line, "title": title,
            "similarity": round(title_similarity(code, title), 3),
            "titled": bool(title), "title_on_next_line": via_next,
            "upper": bool(line) and line == line.upper(),
        })
    return out


# ---------------------------------------------------------------- filtering

def _toc_runs(cands, universe=None):
    """(indices to drop, codes the run declares) for table-of-contents runs.

    A TOC is a manifest: inside a dense run of codes, entries whose codes are
    used AGAIN further down were indexing those later uses. Density alone can
    never decide — Part III's one-line IBR items sit as close together as any
    TOC and must survive. Recurrence is what makes a manifest a manifest.

    The two return values deliberately differ. Only recurring entries are
    DROPPED, because a TOC sits close enough to the body it indexes that the
    run usually swallows the first real heading, whose code does not recur —
    dropping the whole run would delete that heading. But the manifest reports
    EVERY code in the run, including the non-recurring ones: an item the filing
    lists in its own contents and then never heads is exactly the mismatch
    layer 8 exists to catch, and filtering by recurrence would hide it.
    """
    runs, run = [], [0] if cands else []
    for i in range(1, len(cands)):
        if cands[i]["start"] - cands[i - 1]["start"] <= TOC_GAP_MAX:
            run.append(i)
        else:
            runs.append(run)
            run = [i]
    runs.append(run)

    universe = cands if universe is None else universe
    drop, manifest = set(), []
    for run in runs:
        codes = {cands[i]["item"] for i in run}
        if len(codes) < TOC_CLUSTER_MIN:
            continue
        recurs = {i for i in run
                  if any(c["item"] == cands[i]["item"] and c["start"] > cands[i]["start"]
                         for c in universe)}
        # a run is an index if most of what it names turns up again below it
        if len({cands[i]["item"] for i in recurs}) * 2 < len(codes):
            continue
        drop |= recurs
        manifest += [cands[i]["item"] for i in run]
    return drop, manifest


def filter_candidates(cands):
    """(survivors, toc_manifest, rejections) — every drop carries its reason."""
    kept, rejected = [], []
    for c in cands:
        if not c["titled"]:
            # TOC cells and running page headers ("Item 8" alone on a line,
            # 42x in MSFT 2013) share this shape; real headings never do
            rejected.append({**c, "why": "no title on heading line"})
        elif c["similarity"] < SIM_FLOOR:
            # "Item 2, 3, 4, 5" (page furniture), "Item 14(a)" (cross-ref)
            rejected.append({**c, "why": f"title similarity {c['similarity']}"})
        else:
            kept.append(c)

    toc_idx, manifest = _toc_runs(kept)
    rejected += [{**kept[i], "why": "table-of-contents cluster"} for i in sorted(toc_idx)]
    kept = [c for i, c in enumerate(kept) if i not in toc_idx]

    # The manifest is worth having even when the TOC died at the no-title rule,
    # which is the usual case: it is the filing's own declared item list, the
    # only free label-free statement of what SHOULD be here, and layer 8
    # cross-checks it. Recover it from the bare candidates the same way.
    if not manifest:
        bare = [c for c in cands if not c["titled"]]
        # recurrence is judged against ALL candidates, not just the bare ones:
        # a bare TOC entry recurs as a TITLED body heading, never as another bare
        manifest = _toc_runs(bare, cands)[1]
    return kept, manifest, rejected


# ---------------------------------------------------------------- boundaries

# trap 8: a txt-era 10-K block runs on past the report itself (GE 1994 carries
# the whole ~280K-char annual report after SIGNATURES)
TAIL_RE = re.compile(r"(?im)^[ \t]*(SIGNATURES?|Pursuant to the requirements "
                     r"of Section 13)\b")


def assign_boundaries(survivors, expected, text):
    """Greedy ordered assignment: earliest surviving candidate after the last
    accepted boundary wins, so duplicates and disorder resolve by construction."""
    accepted, cursor = {}, 0
    for code in expected:
        for c in survivors:
            if c["item"] == code and c["start"] >= cursor:
                accepted[code] = c
                cursor = c["heading_end"]
                break

    picks = sorted(accepted.values(), key=lambda c: c["start"])
    for i, c in enumerate(picks):
        c["end"] = picks[i + 1]["start"] if i + 1 < len(picks) else len(text)
    if picks:  # last item stops at the signature block, not at end-of-file
        tail = TAIL_RE.search(text, picks[-1]["heading_end"])
        if tail:
            picks[-1]["end"] = tail.start()
    return accepted


# ---------------------------------------------------------------- status

# ADR-004: IBR is for pointers to a DIFFERENT document. An internal "appears on
# pages 52-167" pointer (JPM Items 7/8) stays `extracted`.
EXTERNAL_DOC_RE = re.compile(
    r"(?i)(proxy statement|information statement|annual report to (share|stock)"
    r"[ ]?(holders|owners)|annual report to its (share|stock)[ ]?(holders|owners))")
IBR_RE = re.compile(r"(?i)incorporated (herein )?by reference|"
                    r"is incorporated by reference|reported on pages|refer to (page|the section)")
# Non-pointer prose a body may carry and still count as "the content is
# elsewhere". Measured over all 34 pointer-bearing bodies in the fixture set:
# genuine whole-item pointers leave 0-166 chars of non-pointer remainder (the
# 166 is NIKE's Item 10, whose remainder is itself a pointer phrased without
# the trigger words), while bodies with real inline content start at 414
# (IBM 1997 Item 5: stockholders of record, exchange listings) and run to
# 3,186 (the ibr-pointer-first officer table). Floor sits in that empty band.
IBR_REMAINDER_MAX = 300


def _sentences(flat):
    """Split on sentence punctuation, but NOT on the period of an item
    cross-reference: 10-K proxy captions read “Item 1. Election of Directors”,
    and splitting there truncates a pointer sentence before the words that name
    the other document (pre-B audit finding 2)."""
    parts = re.split(r"(?<=[.;])\s", flat)
    out = []
    for p in parts:
        if out and re.search(r"(?i)\bitem\s*\d{1,2}[A-D]?\.$", out[-1]):
            out[-1] += " " + p          # rejoin: that period ended a reference
        elif out and re.search(r"(?i)\bno\.$", out[-1]) and re.match(r"\d", p):
            # "Proposal No. 2" — an ordinal, not a stop. Splitting here cut
            # wmt-2010 item 14's pointer sentence before "Proxy Statement",
            # hiding the external-document evidence (ibr-pointer-window).
            out[-1] += " " + p
        else:
            out.append(p)
    return out


def classify(code, body, present):
    """Status per ADR-004/005. `body` is the span minus its heading line."""
    if not present:
        # ADR-005 rule 2 vs 3: era permits the absence, or the era expects it
        return "omitted" if code in ("16", "9C") else "missing"
    # Phrase matching runs on a whitespace-flattened copy: txt-era filings are
    # fixed-width, so the very phrases this depends on wrap across lines
    # ("definitive proxy\nstatement", "incorporated by\nreference"). Offsets are
    # never derived from this copy — classification only.
    # No length cutoff: measured, IBR bodies span 93-1,875 chars while 106 of
    # 191 extracted bodies also fall in that range, so length separates nothing
    # here. Shape decides (ADR-007).
    flat = re.sub(r"\s+", " ", body).strip()
    if not IBR_RE.search(flat):
        return "extracted"
    # IBR means the content lives ELSEWHERE. Two corrections over the T4 rule,
    # both from ibr-pointer-first:
    #  - the external-document evidence must be in the POINTER SENTENCE, not
    #    anywhere in the body. Searching `flat` let "proxy statement" 40,000
    #    chars away justify a first-sentence pointer.
    #  - a body that also carries substantive inline prose is `extracted`
    #    however many pointers it opens with. Sentence order decided this
    #    before, so moving two paragraphs flipped a 4,805-char item to IBR —
    #    silently, since IBR spans are excluded from every layer-8 validator.
    sents = _sentences(flat)
    if not (IBR_RE.search(sents[0]) and EXTERNAL_DOC_RE.search(sents[0])):
        return "extracted"
    rest = sum(len(s) for s in sents[1:]
               if not (IBR_RE.search(s) or EXTERNAL_DOC_RE.search(s)))
    return "incorporated_by_reference" if rest <= IBR_REMAINDER_MAX else "extracted"


def _demo():
    exp = expected_items(date(2025, 9, 27))
    assert exp[:4] == ["1", "1A", "1B", "1C"] and len(exp) == 23, exp
    assert len(expected_items(date(1993, 12, 31))) == 14
    assert "7A" not in expected_items(date(1993, 12, 31))
    assert len(expected_items(date(1997, 12, 31))) == 15
    # a calendar-FY2021 filer files in early 2022 and MUST address 9C; 1C is
    # the one still to come. This assertion read 21 with the comment "no 9C/1C
    # yet" — the same wrong belief the ADDED table and sandston-2021-shallow
    # carried, which is how the FY2021 cohort lost the item three ways at once.
    assert len(expected_items(date(2021, 12, 31))) == 22   # 9C yes, 1C not yet
    assert "9C" not in expected_items(date(2021, 6, 30))   # filed before cutoff
    assert len(expected_items(date(2016, 12, 31))) == 21

    text = ("Item 1.\nBusiness\nItem 1A.\nRisk Factors\n"          # bare TOC
            "Item 1. Business\nWe make things. " + "x" * 3000 + "\n"
            "Item 1A. Risk Factors\nThings may break.\n")
    exp2 = ["1", "1A"]
    cands = find_candidates(text, exp2)
    assert len(cands) == 4, cands
    kept, manifest, rej = filter_candidates(cands)
    assert [c["item"] for c in kept] == ["1", "1A"], kept        # TOC dropped
    assert all(c["start"] > 30 for c in kept), kept              # the LATER pair
    got = assign_boundaries(kept, exp2, text)
    assert text[got["1"]["start"]:got["1"]["end"]].startswith("Item 1. Business")
    assert "Item 1A" not in text[got["1"]["start"]:got["1"]["end"]]

    # page furniture and prose refs never become headings
    junk = find_candidates("Item 2, 3, 4, 5\nItem 1 above, Part III is\n", ["1", "2"])
    assert not filter_candidates(junk)[0], junk

    # ADR-004 shapes
    assert classify("10", "The information required by this Item will be included "
                    "in the Company's definitive proxy statement and is incorporated "
                    "herein by reference.", True) == "incorporated_by_reference"
    assert classify("7", "Management's Discussion appears on pages 52-167 of this "
                    "Annual Report on Form 10-K.", True) == "extracted"
    assert classify("5", "Our Common Stock is traded on the New York Stock Exchange. "
                    "At December 29, 2001, there were approximately 21,000 holders. "
                    "The price range is incorporated by reference to the Annual "
                    "Report to Shareholders.", True) == "extracted"
    # the same pointer wrapped across lines, as fixed-width txt filings do
    assert classify("12", "Incorporated by reference to \"Information relating to "
                    "Directors\" in the registrant's definitive proxy\nstatement.",
                    True) == "incorporated_by_reference"
    assert classify("6", "[Reserved]", True) == "extracted"           # ADR-005 rule 1
    assert classify("16", "", False) == "omitted"                     # rule 2
    assert classify("1A", "", False) == "missing"                     # rule 3
    print("[segment self-check] ok")


if __name__ == "__main__":
    _demo()
