"""Layers 4-7: candidates -> TOC/false-candidate filter -> boundaries -> status.

Mechanism: docs/architecture/overview.md. Rulings: ADR-004 (pointer items),
ADR-005 (trivial bodies / absent headings), ADR-007 (T4 thresholds, measured).

Self-check: python3 -m src.sec10k.segment
"""
import difflib
import itertools
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
                  # "Common EQUITY", not "Common Stock" (ADR-023 §a): the item
                  # tracks Reg S-K Item 201, "Market price of and dividends on
                  # the registrant's common equity...", and all 8 pre-2005
                  # fixtures write Equity. Stock was never any era's caption.
                  "Market for the Registrant's Common Equity and Related "
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
                   "Management and Related Stockholder Matters",
                   # the suffix is the equity-compensation-plan table's
                   # (Release 33-8048); before it the item stopped at
                   # "Management" — ADR-023 §b.
                   "Security Ownership of Certain Beneficial Owners and "
                   "Management"]),
    "13": ("III", ["Certain Relationships and Related Transactions, and "
                   "Director Independence",
                   # ...and this suffix is Release 33-8732A's, four years
                   # later again. ADR-023 §c.
                   "Certain Relationships and Related Transactions"]),
    "14": ("III", ["Principal Accountant Fees and Services",
                   "Exhibits, Financial Statement Schedules, and Reports on "
                   "Form 8-K",
                   # 2002-08-29 (Release 33-8124) inserted Controls and
                   # Procedures HERE and pushed Exhibits to Item 15;
                   # 2003-08-14 (Release 33-8238) moved it to Item 9A. Item 4
                   # has the same shape of history — see SOX_INTERIM.
                   "Controls and Procedures"]),
    "15": ("IV", ["Exhibits, Financial Statement Schedules",
                  # Item 15 inherited item 14's full caption when Controls and
                  # Procedures took 14 in 2002; the "Reports on Form 8-K"
                  # clause outlived that by two years and died with Release
                  # 33-8400. The alias that used to sit here ("Exhibits and
                  # Financial Statement Schedules") is a filer variant of the
                  # modern caption, not an era of it — ADR-023 §e.
                  "Exhibits, Financial Statement Schedules, and Reports on "
                  "Form 8-K"]),
    "16": ("IV", ["Form 10-K Summary"]),
}

# When each code joined the form, by fiscal-period end date. Dates are the
# rule's effective date except where the eval set pins it tighter — see
# ADR-007 for the 9C boundary, which sandston-2021 constrains.
ADDED = {
    "1A": date(2005, 12, 1), "1B": date(2005, 12, 1),
    "1C": date(2023, 12, 15),
    "7A": date(1997, 6, 15),
    "9A": date(2003, 8, 14),
    # 9B "Other Information" is NOT 9A's twin: it arrived with the Form 8-K
    # overhaul, Release 33-8400 (adopted 2004-03-16, effective 2004-08-23), a
    # full year later. Dated 2003-08-14 the pipeline expected an item that did
    # not exist yet and reported it `missing` — ba-2003 (FY2003, zero
    # occurrences of "Item 9B" in the document) is the case. Boundary is the
    # earliest period end whose report necessarily lands after the effective
    # date, the ADR-010 ruling-2 convention.
    "9B": date(2004, 5, 23),
    # 9C's rule keys on FILING date (annual reports filed on/after 2022-01-01),
    # and this table keys on period end — a different date. Filing date is not
    # recoverable from a modern primary .htm (2 of 15 fixtures carry an SGML
    # header), so the boundary is the earliest period end whose report can land
    # after the cutoff. Calendar-FY2021 filers, the largest cohort of that
    # season, file in Feb-Mar 2022 and MUST address 9C; keyed at 2022-01-01
    # they lost it entirely and its text was annexed to Item 9B. Filers who
    # legitimately have no 9C heading fall through to `omitted` (see classify).
    "9C": date(2021, 10, 1),
    # Exhibits moved 14 -> 15 at 2002-08-29, when Controls and Procedures took
    # Item 14 — a year BEFORE 14 became Fees. Dated 2003-08-14 this table kept
    # Item 15 out of `expected` for every filing in the interim window, so
    # find_candidates never made its heading a candidate, it could not reach the
    # TOC manifest to raise a mismatch, and its exhibit section was annexed to
    # item 14 in silence: gs-2002 (burned held-out), intc-2002 and tgt-2002 are
    # three independent confirmations. See SOX_INTERIM for the boundary.
    "15": date(2002, 6, 1),
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
# Four of these dates were 2003-08-14 because the SOX renumbering was the era
# boundary this table was built around; only two of them belong to it (ADR-023).
# A retitle is its own rule with its own date, and each one below now names the
# release it comes from. Every date here keys on period end AND is written by a
# rule that keys on fiscal-period end too, except "5" — see ADR-023 §f.
ALIAS_FROM = {
    "4": date(2011, 12, 15),   # Mine Safety replaced Submission of Matters
    "5": date(2005, 12, 1),    # retitled to add Issuer Purchases
    "6": date(2021, 2, 10),    # S-K amendment: Selected Financial Data -> [Reserved]
    # Release 33-8048 put the equity-compensation-plan table in item 12 and
    # lengthened its caption: FY ends on/after 2002-03-15 (ADR-023 §b).
    "12": date(2002, 3, 15),
    # Release 33-8732A gave item 10 "and Corporate Governance" and item 13
    # "and Director Independence" in one stroke: FY ends on/after 2006-12-15.
    # NOT the SOX date — ba-2003 and nike-2006 rendered a 2006 caption over a
    # heading that reads the older one for three years (ADR-023 §c, §d).
    "10": date(2006, 12, 15),
    "13": date(2006, 12, 15),
    "14": date(2003, 8, 14),   # 14 became Fees when Exhibits moved to 15
    # Item 15 kept "and Reports on Form 8-K" until Release 33-8400 killed the
    # 8-K listing requirement — the SAME release that created 9B, so this reuses
    # 9B's period-end boundary above rather than inventing a second one.
    "15": date(2004, 5, 23),
}
# ...and one code changes PART, not just title, at the same boundary.
LEGACY_PART = {"14": "IV"}

# The Sarbanes-Oxley interim window: Item 14 is neither Exhibits (before) nor
# Principal Accountant Fees (after) but "Controls and Procedures", in Part III,
# with Exhibits at Item 15. Release 33-8124 took effect 2002-08-29 and keys on
# FILING date; this table keys on period end, so the boundary is the earliest
# period end whose report necessarily lands after that date under the then-90-day
# deadline — the same one-sided compromise ADR-010 ruling 2 made for Item 9C, and
# it sits inside the empty band the fixtures measure (textron-2001 ends 2001-12-29
# on the old numbering; gs-2002, the earliest interim filing in the set, ends
# 2002-11-29).
SOX_INTERIM = (date(2002, 6, 1), date(2003, 8, 14))


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
    # ...and Item 14 has its own, for the same reason: a third phase between the
    # two ALIAS_FROM neighbours. Without it a filing in the window renders
    # "Exhibits, Financial Statement Schedules, and Reports on Form 8-K" (Part
    # IV) over Controls-and-Procedures text — a correct span under a label that
    # tells the reader it is something else.
    if code == "14" and period_end and SOX_INTERIM[0] <= period_end < SOX_INTERIM[1]:
        return "III", "Controls and Procedures"
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

    Recurrence ignores occurrences inside an ECHO run. A filing may repeat its
    item list a second time at the end: Intel 2002 and Target 2002 both close
    with a compact cross-reference index, and counting that repeat made every
    real body heading "recur", so the front run's trailing member — the first
    real heading, the one this rule exists to protect — was dropped with the
    rest, and greedy assignment resolved every code to the 18-to-490-char stubs
    at the end of the file. Intel reported `success_with_warning` on 0.47% of its
    own text; Target reported plain `success` while item 4 swallowed 81% of the
    document.

    An echo is defined by what it REPEATS, not by where it sits: a dense run
    whose codes mostly appeared already, as headings outside any dense run. That
    definition is the whole of it, and two cheaper ones were tried and discarded
    against real documents (ADR-015 §0a). "All but the run's last member" breaks
    a dormant shell, whose one-line item bodies put the contents page and the
    body in a single run. "All but members of this same run" breaks the same
    shell with cover furniture between its contents page and Part I, which is the
    ordinary layout — there the body is its own dense run, so nothing in it
    counted, and every code resolved to a contents row. Both are ADR-015 §0's own
    failure rebuilt on a different document.

    No new threshold: `len(pre) * 2 >= len(codes)` is the same shape of majority
    test as the forward one below, and "dense" is exactly the
    TOC_CLUSTER_MIN/TOC_GAP_MAX test used everywhere here.
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
    dense = [r for r in runs if len({cands[i]["item"] for i in r}) >= TOC_CLUSTER_MIN]
    clustered = {cands[i]["start"] for r in dense for i in r}
    # A dense run is an ECHO if most of the codes it names ALREADY appeared as a
    # heading somewhere outside any dense run — i.e. it is repeating the body
    # rather than announcing it. Same shape of test as the forward one below, and
    # the same two thresholds; nothing new is introduced.
    echoed = set()
    for r in dense:
        codes = {cands[i]["item"] for i in r}
        pre = {cands[i]["item"] for i in r
               if any(c["item"] == cands[i]["item"] and c["start"] < cands[i]["start"]
                      and c["start"] not in clustered for c in universe)}
        if len(pre) * 2 >= len(codes):
            echoed |= {cands[i]["start"] for i in r}
    drop, manifest = set(), []
    for run in runs:
        codes = {cands[i]["item"] for i in run}
        if len(codes) < TOC_CLUSTER_MIN:
            continue
        recurs = {i for i in run
                  if any(c["item"] == cands[i]["item"] and c["start"] > cands[i]["start"]
                         and c["start"] not in echoed
                         for c in universe)}
        # a run is an index if most of what it names turns up again below it
        if len({cands[i]["item"] for i in recurs}) * 2 < len(codes):
            continue
        # A leading chain of dense TOC clusters may run directly into the first
        # body heading. Retain its last candidate when its code was declared in
        # that chain: later page headers would otherwise make the body heading
        # look like a recurring TOC entry too. A standalone candidate ends the
        # chain, so an independent later index cannot inherit that exception.
        last = cands[run[-1]]
        if (any(c["item"] == last["item"] and c["start"] in clustered
                for c in cands[:run[-1]])
                and all(c["start"] in clustered for c in cands[:run[-1]])):
            recurs.discard(run[-1])
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

# trap 9: Item 401(b) of Reg S-K requires "Executive Officers of the
# Registrant" as a named disclosure but assigns it no item code, so filers
# place it as an unnumbered section wherever they like in Part I/II -- end of
# Item 1, end of Item 4, even mid-Item-2 (IBM 1997). Recurs across 7 fixtures,
# 1997-2016 (T11 recurrence scan). When it lands inside a NON-item-10 span it
# is orphaned content, not that item's answer, so it terminates the item
# exactly as TAIL_RE terminates the last item at Signatures. Item 10 itself
# ("Directors, Executive Officers and Corporate Governance") legitimately
# carries this heading as its own subsection and must NOT be clipped there.
# `(?!\.)` excludes a wrapped-prose false match: GE 1994 item 1 reads "...for
# information about\nExecutive Officers of the Registrant.\n\nOther" -- a
# sentence that happens to start a wrapped line, not a heading; real headings
# never carry a trailing period.
EXEC_OFFICERS_RE = re.compile(
    r"(?im)^[ \t]*executive officers of (the )?(registrant|company)\b(?!\.)")


# trap 10: a trailing ANNEX the filing typesets AFTER its final item. Simon
# Property FY2024 and MetLife FY2024 both close with `Item 16. Form 10-K
# Summary` whose entire body is the word "None." and then print the exhibit
# index (SPG, 23,401 chars) or the glossary and exhibit index (MetLife,
# 38,153) before the signature block — so the last item's span, which runs to
# TAIL_RE, swallows the annex and the envelope attributes 23-38 KB of exhibit
# list to an item that says "None.", at 0.95, with no warning. It is the exact
# mirror of `item_span_near_empty`, which can only see a span that is too
# SMALL. Clipped on the LAST item only, and never when that item is 15, whose
# subject matter the exhibit index IS. Where the annex then belongs is left to
# `unattributed_content` to report rather than guessed at.
ANNEX_RE = re.compile(r"(?im)^[ \t]*(exhibit index|index to exhibits|"
                      r"index of exhibits|glossary)[ \t]*$")


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
        if c["item"] != "10":
            eo = EXEC_OFFICERS_RE.search(text, c["heading_end"], c["end"])
            if eo:
                c["end"] = eo.start()
    if picks and picks[-1]["item"] != "15":  # trap 10
        annex = ANNEX_RE.search(text, picks[-1]["heading_end"], picks[-1]["end"])
        if annex:
            picks[-1]["end"] = min(picks[-1]["end"], annex.start())
    if picks:  # last item stops at the signature block, not at end-of-file
        tail = TAIL_RE.search(text, picks[-1]["heading_end"])
        if tail:
            # min(), not =: the EO clip above may have already pulled this
            # item's end below tail.start() (trap 9 on the last item) — an
            # unconditional overwrite would revert that clip.
            picks[-1]["end"] = min(picks[-1]["end"], tail.start())
    return accepted


# ---------------------------------------------------------------- status

# ADR-004: IBR is for pointers to a DIFFERENT document. An internal "appears on
# pages 52-167" pointer (JPM Items 7/8) stays `extracted`.
# `security` is the SEC's own term for the same document (Rule 14a-3(b), Form
# 10-K General Instruction G(2)); without it a whole-item pointer naming the
# "Annual Report to Security Holders" reported `extracted` at 0.95 — cold-review
# finding T4-1 (tasks/reviews/gates-2026-08-22.json), `ibr-security-holders`.
EXTERNAL_DOC_RE = re.compile(
    r"(?i)(proxy statement|information statement|annual report to (its )?"
    r"(share|stock|security)[ ]?(holders|owners))")
# "incorporated ... by reference" tolerates an interposed phrase: Wells Fargo
# 2008 writes "incorporated INTO THIS REPORT by reference" on ten of its items,
# and both of the old fixed alternatives missed it, so every one of them
# reported `extracted` at 0.95 over a 300-char pointer. `[^.]` keeps the window
# inside one sentence.
IBR_RE = re.compile(r"(?i)incorporated\b[^.]{0,40}?\bby reference|"
                    r"reported on pages|refer to (page|the section)")
# Non-pointer prose a body may carry and still count as "the content is
# elsewhere".
#
# RE-MEASURED 2026-08-17 over all 126 pointer-bearing bodies that reach this
# test across the 31-fixture set (the ADR-010 numbers below described 34 bodies
# and are kept because they are what chose the constant). Genuine whole-item
# pointers now leave 0-186 chars of non-pointer remainder — the 186 is ko-1997
# item 5, and the old top of 166 was NIKE item 10, whose remainder is itself a
# pointer phrased without the trigger words. Bodies with real inline content now
# start at 338 (ko-1997 item 8), not 414 (IBM 1997 item 5: stockholders of
# record, exchange listings), and still run to 3,186 (the ibr-pointer-first
# officer table).
#
# So the empty band is 186..338, width 152, and the floor sits inside it with
# 114 chars of margin below and only 38 above — NOT the comfortable gap the
# original wording implied. The floor is deliberately NOT moved to the new
# midpoint (262): no body in the set lies between 262 and 300, so the change
# would be untestable, and moving a threshold no case can distinguish is a
# behaviour change with no evidence behind it. The named trigger instead: the
# first body that lands in 300..338 moves the floor to the band midpoint, with
# its own ADR. ADR-015 §3's `_sentences` and INTERNAL_REF_RE rules widened this
# band rather than narrowing it (152 chars against 71 for the same bodies under
# the old rules), which is the check that they did not merely loosen the test.
IBR_REMAINDER_MAX = 300
# ...and a sentence that sends the reader to another ITEM OF THIS SAME REPORT is
# navigation, not content, so it does not count toward that remainder either.
# ADR-004 already rules that an internal pointer cannot by itself make an item
# IBR — this is the other side of the same coin: it cannot make one `extracted`
# either. Intel 2002 item 12 is three sentences, all of them pointers (one to
# the proxy, two to Items 7 and 8 of this Form 10-K) and none of them the
# beneficial-ownership content the item is named for; counting the two internal
# ones as 530 chars of "inline prose" reported the item `extracted`, telling a
# consumer the content was in the span when the span says it is not.
INTERNAL_REF_RE = re.compile(
    r"(?i)\bitem\s*\d{1,2}[A-D]?\b[^.]{0,200}?\bthis (form\s*10-?K|annual report|report)\b")


def _sentences(flat):
    """Split on sentence punctuation, but NOT on the period of an item
    cross-reference: 10-K proxy captions read “Item 1. Election of Directors”,
    and splitting there truncates a pointer sentence before the words that name
    the other document (pre-B audit finding 2).

    A semicolon is not sentence punctuation and no longer splits. Enumerated
    pointers are a house style — Target 2002 item 2 reads “Leases, Page 32;
    Owned and Leased Store Locations, Page 32, and the list of store locations
    ... are incorporated herein by reference.” — and cutting at the first
    semicolon left sents[0] as “Leases, Page 32;”, hiding the words that name
    the other document. Third instance of the same family (ADR-014 §2 was the
    ordinal “Proposal No. 2”, the pre-B finding was the item caption); this one
    removes a splitter rather than adding a rejoin.
    """
    parts = re.split(r"(?<=[.])\s", flat)
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

    def _pointer(s):
        return bool(IBR_RE.search(s) or EXTERNAL_DOC_RE.search(s)
                    or INTERNAL_REF_RE.search(s))

    # ADR-010 ruling 3 required both signals in sents[0]. The requirement that
    # the pointer OPENS the body is load-bearing and stays: textron-2001 item 5
    # ends with "The price range is incorporated by reference to the Annual
    # Report to Shareholders" after two sentences of real market data, and it is
    # `extracted` — an item that mentions a pointer last is not an item whose
    # content is elsewhere.
    #
    # What does NOT survive is "exactly one sentence". The commonest
    # institutional phrasing splits the pointer across two adjacent sentences:
    # "Information in response to this Item 7 can be found in the 2008 Annual
    # Report to Stockholders under ... . That information is incorporated into
    # this report by reference." — Wells Fargo 2008 writes it that way on ten
    # items, each of which reported `extracted` at 0.95 over a 300-char pointer.
    # So the window is the LEADING RUN of pointer sentences, and both signals
    # must appear inside it.
    lead = list(itertools.takewhile(_pointer, sents))
    joined = " ".join(lead)
    if not (IBR_RE.search(joined) and EXTERNAL_DOC_RE.search(joined)):
        return "extracted"
    rest = sum(len(s) for s in sents[len(lead):] if not _pointer(s))
    return "incorporated_by_reference" if rest <= IBR_REMAINDER_MAX else "extracted"


# ADR-031 (D4): a heading whose line ends in a typographic footnote marker and
# whose body is EMPTY, resolved by a footnote anywhere in the document that
# begins with the SAME marker, names this item's code and names an external
# document. Boeing FY2003 marks Items 5, 10, 11, 13 and 14 with a bare `*` and
# says once, in a footnote inside item 14's body, "* Certain information
# required by Items 5, 10, 11, 13 and 14 is incorporated herein by reference to
# the registrant's definitive proxy statement" — so items 11 and 13, whose
# bodies are whitespace, read `extracted` 0.95 over nothing, the silent-failure
# shape. The marker family is asterisk runs only: measured over all 47
# committed documents (42 dev + 5 held-out), the only marked headings are
# ba-2003's five, all `*`; `**`/`***` occur as table-footnote markers in the
# same filing, which is why the run must match exactly. Daggers and `(1)`-style
# numerals are not claimed. The body must be empty: items 5 and 10 carry the
# same marker over real content and stay `extracted` (ADR-004 shape 3 — the
# footnote says "certain information"); item 14 holds the footnote in its own
# body and is IBR by `classify` already.
MARKER_TAIL_RE = re.compile(r"(\*+)\s*$")
FOOTNOTE_RE = re.compile(r"(?m)^[ \t]*(\*+)[ \t]*(?=\S)")
ITEM_LIST_RE = re.compile(r"(?i)\bitems?\s+((?:\d{1,2}[A-D]?\b[\s,]*(?:and\s+)?)+)")
PARA_END_RE = re.compile(r"\n[ \t]*\n")


# ADR-042 §c: a Part addressed COLLECTIVELY, with no per-item heading at all.
# Berkshire Hathaway FY2024's whole of Part III is one sentence — "information
# required by this Part (Items 10, 11, 12, 13 and 14) is incorporated by
# reference to the definitive proxy statement" — so all five items reported
# `missing`, an honest miss but the wrong diagnosis in kind: the filing is not
# silent about them, it says where they are and that it is another document.
# Requires THREE codes, not two, because two-code phrases ("see Items 7 and 8
# of this report") are ordinary internal navigation and appear in filings that
# also carry the real headings; and requires both the IBR phrasing and an
# external-document name, so an internal pointer cannot reach this path
# (ADR-004 shape 1 only).
COLLECTIVE_CODES_RE = re.compile(r"(?i)\bitems?\s+(\d{1,2}[A-D]?"
                                 r"(?:\s*,?\s*(?:and\s+)?\d{1,2}[A-D]?){2,})\b")
CODE_RE = re.compile(r"\d{1,2}[A-D]?")


def collective_pointer(text, unassigned):
    """`{item code: (start, end)}` — the pointer SENTENCE for each item of
    `unassigned` a collective Part-level IBR names.

    The span is the sentence, and it is the same span for every code it names,
    so it is published under `evidence.collective_reference` and NOT as the
    items' own offsets: INV-S1 forbids five items sharing one range, exactly
    as ADR-031 found for the footnote case.
    """
    out = {}
    for m in COLLECTIVE_CODES_RE.finditer(text):
        codes = [c.upper() for c in CODE_RE.findall(m.group(1))]
        if len(set(codes) & set(unassigned)) < 3:
            continue
        # the sentence around the match: back to the previous stop, forward to
        # the next one. `_sentences` splits a flattened body; this reads the
        # raw text, so it does its own bounded scan.
        lo = max(text.rfind(". ", 0, m.start()), text.rfind("\n\n", 0, m.start()))
        lo = lo + 2 if lo != -1 else max(0, m.start() - 400)
        hi = text.find(". ", m.end())
        hi = hi + 1 if hi != -1 else min(len(text), m.end() + 400)
        sent = text[lo:hi]
        if not (IBR_RE.search(sent) and EXTERNAL_DOC_RE.search(sent)):
            continue
        for c in codes:
            if c in unassigned:
                out.setdefault(c, (lo, hi))
    return out


def footnote_pointer(code, heading_text, body, text):
    """(start, end) into `text` of the footnote that incorporates `code` by
    reference, or None. Only for a marked heading over an empty body.
    ponytail: empty means whitespace-only, which is what the corpus has; a body
    of page furniture alone ('122 / Table of Contents') would not qualify — add
    a furniture strip here when a fixture shows it."""
    m = MARKER_TAIL_RE.search(heading_text or "")
    if not m or body.strip():
        return None
    marker = m.group(1)
    for f in FOOTNOTE_RE.finditer(text):
        if f.group(1) != marker:
            continue
        pe = PARA_END_RE.search(text, f.end())      # txt-era footnotes wrap
        end = pe.start() if pe else len(text)
        flat = re.sub(r"\s+", " ", text[f.start(1):end])
        named = {c.upper() for lst in ITEM_LIST_RE.findall(flat)
                 for c in re.findall(r"(?i)\d{1,2}[A-D]?", lst)}
        # the same two signals classify() demands of a body pointer
        if code in named and IBR_RE.search(flat) and EXTERNAL_DOC_RE.search(flat):
            return f.start(1), end
    return None


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
    # the Sarbanes-Oxley interim window: Exhibits already at 15, Controls not
    # yet at 9A. Three real filings live here (gs-2002, intc-2002, tgt-2002)
    # and the era table had none of them.
    assert "15" in expected_items(date(2002, 12, 28))
    assert "9A" not in expected_items(date(2002, 12, 28))
    assert "15" not in expected_items(date(2001, 12, 29))       # textron, before
    assert item_label("14", date(2002, 12, 28)) == ("III", "Controls and Procedures")
    assert item_label("14", date(2001, 12, 29))[0] == "IV"      # Exhibits, Part IV
    assert item_label("14", date(2004, 12, 31)) == ("III", "Principal Accountant "
                                                    "Fees and Services")
    # 9B arrived with Release 33-8400, a year after 9A — ba-2003 has 9A and no 9B
    assert "9A" in expected_items(date(2003, 12, 31))
    assert "9B" not in expected_items(date(2003, 12, 31))
    assert "9B" in expected_items(date(2004, 12, 31))

    # ADR-023: a retitle is its own rule with its own date. The eval cases pin
    # these on real filings (era-label-*.json); the boundaries themselves are
    # asserted here, on both sides, because a date is cheaper to check than a
    # fixture and the corpus has no filing at some of these edges.
    assert item_label("12", date(2001, 12, 29))[1].endswith("Management")   # 33-8048,
    assert item_label("12", date(2002, 3, 15))[1].endswith("Matters")       # both sides
    assert item_label("10", date(2006, 5, 31))[1] == "Directors and Executive " \
        "Officers of the Registrant"                                       # nike-2006
    assert item_label("10", date(2006, 12, 15))[1] == "Directors, Executive " \
        "Officers and Corporate Governance"                                # 33-8732A
    assert item_label("13", date(2006, 5, 31))[1] == "Certain Relationships and " \
        "Related Transactions"
    assert item_label("13", date(2006, 12, 15))[1].endswith("Director Independence")
    assert item_label("15", date(2003, 12, 31))[1].endswith("Reports on Form 8-K")
    assert item_label("15", date(2004, 5, 23)) == ("IV", "Exhibits, Financial "
                                                   "Statement Schedules")
    # ...and the one that has no boundary to move: item 5's legacy caption is a
    # wording fix, not a date fix (Reg S-K Item 201 says "common equity").
    assert "Common Equity" in item_label("5", date(1993, 12, 31))[1]
    # Item 5's DATE, however, does move, and until PR #17 R1 nothing could see
    # it: era-label-bac-2006 asserts the modern caption at period end
    # 2006-12-31, which bounds ALIAS_FROM["5"] from ABOVE and is blind to every
    # earlier value — including 2004-03-15, the one ADR-023 §f argues is
    # probably right. Two-sided here, so §f's own candidate move goes red.
    # This deliberately pins a value §f doubts: while there is no fixture in
    # the 2004-03-15 → 2005-12-01 band to decide it, moving the constant has to
    # be a decision someone makes in the open, not a silent edit.
    assert item_label("5", date(2005, 11, 30))[1].startswith(
        "Market for the Registrant's Common Equity")            # day before
    assert item_label("5", date(2005, 12, 1))[1].endswith(
        "Issuer Purchases of Equity Securities")                # ...and the day of
    # Item 6 (PR #17 R5): setting it to date(1990, 1, 1) relabels "Selected
    # Financial Data" as "[Reserved]" on 26 committed fixtures and the gate
    # stayed green. WHICH DATE THIS
    # PINS, plainly: 2021-02-10, the constant in force — Release 33-10890's
    # effective date, from which a filer MAY write "[Reserved]". The mandatory
    # date is 2021-08-09 (FY ends on/after), and ADR-023 §g leaves the choice
    # between them open because either one mislabels somebody in the six-month
    # window and no fixture sits inside it to decide. So this assert is not a
    # claim that 2021-02-10 is right; it is the claim that changing it is a
    # decision, which is exactly what §g says is still owed.
    assert item_label("6", date(2021, 2, 9))[1] == "Selected Financial Data"
    assert item_label("6", date(2021, 2, 10))[1] == "[Reserved]"
    # Item 4 carries the same shape and was not asserted until PR #17 R8:
    # item_label's Reserved-window guard reads `< ALIAS_FROM["4"]`, so the
    # guard and the constant move together and an in-band move goes unseen —
    # date(2016, 1, 1) renders "Reserved" over msft-2013, spatz-2014, cvx-2015
    # and reac-2015, date(2010, 1, 31) renders "Mine Safety Disclosures" over
    # wmt-2010, and the gate stayed green for both. These two lines assert the
    # 2011-12-15 boundary from each side.
    assert item_label("4", date(2011, 12, 14))[1] == "Reserved"
    assert item_label("4", date(2011, 12, 15))[1] == "Mine Safety Disclosures"

    # a trailing cross-reference index must not make the real body headings
    # look like a table of contents (intc-2002 / tgt-2002: every code resolved
    # to the echo and the filing reported success on 0.47% of its own text)
    body = "".join(f"Item {c}. {t}\n" + "z" * 3000 + "\n" for c, t in
                   [("1", "Business"), ("2", "Properties"), ("3", "Legal Proceedings"),
                    ("5", "Market for the Registrant's Common Equity and Related "
                          "Stockholder Matters"), ("6", "Selected Financial Data")])
    echo = "".join(f"Item {c}. {t}\n" for c, t in
                   [("1", "Business"), ("2", "Properties"), ("3", "Legal Proceedings"),
                    ("5", "Market for the Registrant's Common Equity and Related "
                          "Stockholder Matters"), ("6", "Selected Financial Data")])
    exp3 = ["1", "2", "3", "5", "6"]
    got3 = assign_boundaries(filter_candidates(find_candidates(echo + body + echo, exp3))[0],
                             exp3, echo + body + echo)
    assert all(got3[c]["end"] - got3[c]["start"] > 2000 for c in exp3), \
        {c: got3[c]["end"] - got3[c]["start"] > 2000 for c in exp3}

    # trap 9's clip on the LAST accepted item: TAIL_RE used to overwrite
    # picks[-1]["end"] unconditionally, reverting the EO clip whenever the
    # last item is not item 10 and carries an EO heading before SIGNATURES.
    # No fixture reaches this (confirmed by the T11 reviewer), so it is
    # proved here, same "at the layer" treatment ADR-016 gives
    # boundary_hygiene. Fix: picks[-1]["end"] = min(picks[-1]["end"], tail.start()).
    eo_text = ("Item 1. Business\nWe make things. " + "x" * 3000 + "\n"
              "Item 2. Properties\nWe own buildings. " + "y" * 3000 + "\n"
              "Executive Officers of the Registrant\n" + "z" * 500 + "\n"
              "SIGNATURES\n" + "Signed, sealed, delivered. " * 20)
    exp5 = ["1", "2"]
    got5 = assign_boundaries(filter_candidates(find_candidates(eo_text, exp5))[0],
                             exp5, eo_text)
    assert "Executive Officers" not in eo_text[got5["2"]["start"]:got5["2"]["end"]], \
        eo_text[got5["2"]["start"]:got5["2"]["end"]][-80:]

    # ...and the MIRROR shape, in BOTH its layouts. A dormant shell answers
    # "None." to most items, so its bodies sit closer than TOC_GAP_MAX and the
    # body is a dense run of its own. Two cheaper definitions of "echo" both
    # collapsed this filing to its contents page — one when the contents page
    # runs straight into the body, the other when cover furniture separates them,
    # which is the ordinary layout. Both layouts are asserted because each one
    # caught a different wrong rule (ADR-015 §0a). Found by review, not by a
    # fixture: no filing in either set reaches it, and §0a records the search.
    shell_codes = [("1", "Business"), ("1A", "Risk Factors"), ("2", "Properties"),
                   ("3", "Legal Proceedings"),
                   ("5", "Market for the Registrant's Common Equity and Related "
                         "Stockholder Matters")]
    shell_toc = "".join(f"Item {c}. {t} .... {i + 3}\n"
                        for i, (c, t) in enumerate(shell_codes))
    shell_body = "".join(f"Item {c}. {t}\nNone. The Company is a shell corporation. \n"
                         for c, t in shell_codes)
    exp4 = [c for c, _ in shell_codes]
    for gap in ("", "\n" + "cover and signature furniture. " * 30 + "\n"):
        shell = "FORM 10-K\n" + shell_toc + gap + shell_body
        got4 = assign_boundaries(filter_candidates(find_candidates(shell, exp4))[0],
                                 exp4, shell)
        assert all("None." in shell[got4[c]["start"]:got4[c]["end"]] for c in exp4), \
            (len(gap), {c: shell[got4[c]["start"]:got4[c]["end"]][:60] for c in exp4})

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

    # A front-matter TOC can run directly into the first real heading.  If
    # that item then has running headers, recurrence alone must not throw away
    # the trailing body candidate with the TOC entries.
    first_toc = ["1", "1A", "1B", "2", "3"]
    second_toc = ["4", "5", "6", "7", "1"]
    running_header = ([{"item": code, "start": i * 20}
                       for i, code in enumerate(first_toc)] +
                      [{"item": code, "start": 600 + i * 20}
                       for i, code in enumerate(second_toc)] +
                      [{"item": code, "start": 2000 + i * 1000}
                       for i, code in enumerate(first_toc + second_toc)])
    assert _toc_runs(running_header)[0] == set(range(9)), _toc_runs(running_header)

    # An independent index run must not inherit a duplicate from the leading
    # chain once a standalone body heading has appeared.
    first_run = ["1", "1A", "1B", "2", "3"]
    later_run = ["4", "5", "6", "7", "1"]
    independent = ([{"item": code, "start": i * 20}
                    for i, code in enumerate(first_run)] +
                   [{"item": "1", "start": 1000}] +
                   [{"item": code, "start": 2000 + i * 20}
                    for i, code in enumerate(later_run)] +
                   [{"item": code, "start": 4000 + i * 1000}
                    for i, code in enumerate(later_run)])
    assert _toc_runs(independent)[0] == set(range(6, 11)), _toc_runs(independent)

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
    # a semicolon is not a sentence end: cutting there hid the words naming the
    # other document (tgt-2002 item 2)
    assert classify("2", "Leases, Page 32; Owned and Leased Store Locations, Page 32, "
                    "of Registrant's 2002 Annual Report to Shareholders are "
                    "incorporated herein by reference.", True) == "incorporated_by_reference"
    # ...and a sentence pointing at another item of THIS report is navigation,
    # not the inline content that would make the item `extracted` (intc-2002 item 12)
    assert classify("12", "The information under \"Security Ownership\" in our 2003 "
                    "Proxy Statement is incorporated by reference. See the information "
                    "under \"Employee Stock Options\" within Item 7 of this Form 10-K "
                    "regarding shares authorized for issuance under equity compensation "
                    "plans approved by stockholders and not approved by stockholders.",
                    True) == "incorporated_by_reference"
    # the pointer may run across two adjacent sentences (wfc-2008, ten items),
    # and "incorporated INTO THIS REPORT by reference" is still a pointer...
    assert classify("7", "Information in response to this Item 7 can be found in the "
                    "2008 Annual Report to Stockholders under \"Financial Review\" on "
                    "pages 34-83. That information is incorporated into this report "
                    "by reference.", True) == "incorporated_by_reference"
    # ...but the pointer must OPEN the body. The textron-2001 item 5 assertion
    # above is the guard: an item that mentions a pointer LAST is not an item
    # whose content is elsewhere, and generalising the window without keeping
    # that requirement flipped nine committed items across the fixture set.
    assert classify("6", "[Reserved]", True) == "extracted"           # ADR-005 rule 1
    assert classify("16", "", False) == "omitted"                     # rule 2
    assert classify("1A", "", False) == "missing"                     # rule 3

    # ADR-031: a marked EMPTY heading resolved by a footnote that names the
    # item and an external document (ba-2003 items 11/13). The footnote may sit
    # anywhere; it must begin with the SAME marker run, name THIS code, and
    # carry both pointer signals.
    doc = ("Item 10. Directors*\n\nBios of the directors. " * 3 + "\n"
           "Item 11. Executive Compensation*\n\n"
           "Item 13. Certain Relationships *\n\n"
           "Item 14. Fees*\n\n* Certain information required by Items 10, 11,\n"
           "13 and 14 is incorporated herein by reference to the\n"
           "registrant's definitive proxy statement.\n\n122\n\nPART IV\n"
           "** Deliveries included intracompany units.\n")
    fn = doc.index("* Certain")
    assert footnote_pointer("11", "Item 11. Executive Compensation*", "\n\n", doc) \
        == (fn, doc.index("\n\n122"))                          # wrapped, txt-style
    assert footnote_pointer("13", "Item 13. Certain Relationships *", "\n\n", doc) \
        == (fn, doc.index("\n\n122"))                          # space before the marker
    assert footnote_pointer("10", "Item 10. Directors*", "\n\nBios.", doc) is None   # body not empty
    assert footnote_pointer("11", "Item 11. Executive Compensation", "\n\n", doc) is None  # no marker
    assert footnote_pointer("12", "Item 12. Security Ownership*", "\n\n", doc) is None  # not named
    assert footnote_pointer("11", "Item 11. Executive Compensation**", "\n\n", doc) is None  # `**` != `*`
    internal = doc.replace("the\nregistrant's definitive proxy statement",
                           "Item 7 of this\nForm 10-K")
    assert footnote_pointer("11", "Item 11. Executive Compensation*", "\n\n", internal) \
        is None                                                # internal target: ADR-004
    print("[segment self-check] ok")


if __name__ == "__main__":
    _demo()
