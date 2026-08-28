"""Layer 8: the label-free validator battery, and layer 9 confidence.

These validators need no annotations, so they run on EVERY filing — including
held-out ones the eval set has never seen. That is where robustness beyond the
labeled fixtures comes from.

Policy (failure-taxonomy F7): every validator is itself a false-positive
source, so validators emit warnings and move confidence; none hard-fails a run
alone, and only the five named in `AMBIGUOUS_CODES` may push `doc_status` to
`ambiguous`. Every threshold below states its measured basis or names itself
a judgment call (SUBSTANTIVE_MIN, and MISSING_MAX's floor-not-midpoint), and
each is pinned from both sides of its measured empty band by a committed case
(ADR-027 §c, ADR-030 §f and ADR-035 §f list the pins); ADR-008 carries the
original distributions and the priors this battery REJECTED after measuring
them.

Self-check: python3 -m src.sec10k.validate
"""
import re

from src.sec10k.segment import EXTERNAL_DOC_RE, HEADING_RE

# ADR-008, measured over 13 fixtures: clean modern filings leave 0.7-7.6% of
# the document before the first span / after the last; IBR-heavy and
# appendix-carrying filings leave 26.5-76.9%. The floor sits in that empty
# band. Re-measured 2026-08-22 over 36 span-bearing fixtures (ADR-027 §c): the
# band is now (0.1242 wmt-2010, 0.2646 fy2021-item9c), pinned by
# `warning_absent` on wmt-2010 and `warning_present` on sandston-2021.
UNATTRIBUTED_MAX = 0.17
# JPM 2024 puts its whole financial appendix after the Item 15 exhibit index,
# so the last item swallows 83.3% of the document. Next highest in the set is
# 18.9% (Textron's exhibit list). Band midpoint. Re-measured 2026-08-22: band
# (0.1892 textron-2001, 0.7063 xom-2021), pinned on both (ADR-027 §c).
LAST_ITEM_MAX = 0.50
# ADR-030 (D3): the NON-last spans have their own distribution — a real
# filing's Item 1/7/8 is legitimately up to half the document, where the last
# item (the exhibit list) is legitimately small. Measured 2026-08-23 over the
# 37 span-bearing dev fixtures (26 real filings, 11 synthetic) and, read-only,
# the 5 held-out: the largest non-last span of a real filing is
# jnj-2016's Item 8 at 0.5336 (`success`, the financial statements); the
# smallest that must fire is items-stripped's Item 4 at 0.5723 (eight
# headings gone, the span swallowed them). Band (0.5336, 0.5723), midpoint;
# pinned by `warning_absent` on jnj-bare-headings and `warning_present` on
# items-stripped-escalation. The thinnest margin in this battery (1.03x over
# the worst real filing) — stated, not smoothed; the held-out set reads 0.5274
# at most (mrk-1995, read-only, not tuned on). ADR-015 §0's Target failure
# (item 4 at 0.81, NOT the last span) is the shape this catches and
# `last_item_dominates` structurally cannot.
ITEM_MAX = 0.55
# content-shape validators cannot judge a pointer paragraph: GE's Item 8 is
# "See index under item 14." (86 chars) and NVDA's is a 209-char internal
# pointer, both legitimately `extracted` per ADR-004 shape 2. A judgment call,
# not a band midpoint (ADR-008) — but the band IS measured (2026-08-22, ADR-027
# §c): the longest extracted span that would misfire if judged is ko-1997's
# 930-char Item 8 IBR list; the shortest span a case needs judged is
# spans-transposed's 22,955-char Item 8. Pinned on both.
SUBSTANTIVE_MIN = 5000

# ADR-035 (D8): the per-item near-empty floor ADR-031 §i named as unbuilt, and
# the item-level half ADR-019 §e left open. It applies to the three items whose
# answer is never legitimately one sentence — Business, MD&A, Financial
# Statements — because those three are the only ones with a measured empty
# band. Measured 2026-08-26 over the 90 extracted item-1/7/8 spans of the 38
# span-bearing dev fixtures at 820cf0c: all 14 spans under 2,094 chars are pointers or
# stubs (censused in ADR-035 §b1) and every span at or above it is substantive.
# Band (930 ko-1997 item 8, 2,094 tgt-2002 item 1), midpoint 1,512, taken to
# two significant figures as ITEM_MAX was; margins 1.40x under the smallest
# legitimate span and 1.61x over the largest pointer. Pinned on both edges
# (`tgt-2002-shallow` `warning_absent`, `ko-1997-shallow` `warning_present`).
# NOT the same question as SUBSTANTIVE_MIN, which shares the 930-char lower
# edge: that constant asks "is there enough text here to JUDGE by vocabulary or
# density"; this one asks "is this the item's content at all". Items 1A and 7A
# are deliberately out — "not required for smaller reporting companies" is a
# complete and correct answer, and 6 dev fixtures give item 1A a span of 41-129
# chars for exactly that reason, so those codes have no empty band at all.
SPAN_FLOOR = 1500
SUBSTANCE_ITEMS = ("1", "7", "8")

# ADR-035 §d: the fraction of the document that lands inside SOME item span —
# published at `meta.coverage`, and NOT the same number as
# `1 - unattributed_content`, which measures only the preamble and the tail and
# understates true non-coverage by up to 9.7 points on the 7 EXEC_OFFICERS_RE
# fixtures (ADR-019 §d). Unlike `unattributed_content` this one escalates: the
# ADR-008 argument that keeps that code out of AMBIGUOUS_CODES is about
# IBR-heavy filings being NORMAL, and it holds up to a point — the lowest real
# dev filing is ge-1994 at 0.2306, then cvx-2015 at 0.2718 — but a document
# whose items hold 3% of it did not resolve. Measured band (0.0303
# `xref-index-collapse`, 0.2306 ge-1994), midpoint 0.1305 → 0.13, 1.77x under
# the lowest real filing. Held-out, read-only, not tuned on: intc-2025 0.0033,
# c-2025 0.0.
COVERAGE_MIN = 0.13

# Only these may push doc_status to `ambiguous`. `unattributed_content` is
# deliberately NOT among them: for IBR-heavy filings (IBM 1997 leaves 43% of
# the document outside every item, Textron 28%) that shape is normal and the
# honest report is a warning, not "we could not resolve this".
# `item_dominates` IS (ADR-030 §c): one span over half the document is the
# same shape whether it sits last or not, the last already escalates, and the
# measured false-positive set at ITEM_MAX is empty on every committed real
# filing — ADR-013's cost asymmetry decides the rest (a false `ambiguous` is a
# report a consumer can inspect; a false `success` on a swallowed document is
# the silent failure this battery exists for).
# `low_item_coverage` IS (ADR-035 §d): its threshold is two orders of magnitude
# below the shape ADR-008 was protecting, and the demo's Intel document — every
# item resolved to a cross-reference-index row, 0.3% of the text spanned —
# reported `success_with_warning` over a column of 0.95s because nothing here
# escalated on it. `item_span_near_empty` is deliberately NOT among them: one
# pointer item is a fact about that item, not a verdict on the document, and
# escalating it would take 9 real dev filings to `ambiguous` (ADR-035 §c).
AMBIGUOUS_CODES = {"toc_manifest_mismatch", "last_item_dominates",
                   "expected_items_mostly_missing", "item_dominates",
                   "low_item_coverage"}

# ADR-039 (D16): the pointer-SHAPE escalation. ADR-038 rules cvx-2015 items
# 2/6/7A `defect` at the escalation layer — internal page pointers published
# clean at 0.95 while their targets sit in the 294,291-char region outside
# every span — and no code above can carry them: `item_span_near_empty`
# reaches items 1/7/8 only, and TD-5's measured counter-evidence forbids
# widening its item set (items 1A/7A/1B/4/6/9/9B/9C/16 are legitimately one
# sentence — ADR-027 §c's vacuous_coverage finding, closed, stays closed),
# while length alone cannot discriminate (cvx item 7A's 453-char span is
# longer than several correctly-flagged items). The trigger is the SHAPE
# plus the unplaced mass — three prongs mirroring ADR-038 §b's own rule
# (R1 class gate, R3 "already said it", R3 reached-or-not): the body is an
# internal page/index pointer naming no external document (INTERNAL_PTR_RE
# is d9_class_scan.py's PAGE_PTR verbatim; the external test reuses
# segment.EXTERNAL_DOC_RE so this layer cannot drift from ADR-004's),
# nothing has said it yet, and coverage says most of the document lies
# outside every span, so an internal pointer's target is plausibly there.
# Both constants measured 2026-08-28 over dev + held-out
# (tasks/reviews/d16_census.py, output committed): body band (515 cvx-2015
# item 2, 1,814 cvx-2015 item 5) WITHIN the sub-PTR_COVERAGE_MIN population
# — corpus-wide the length populations OVERLAP (ba-2003 item 5's mixed body
# is 508 chars, under cvx item 2's 515), so the cap separates only in
# conjunction with the coverage prong, stated in ADR-039 §c2 rather than
# smoothed; coverage band (0.2718 cvx-2015, 0.9285 bac-2006 — the filing
# ADR-038 §c4 rules correct precisely because its pointers' targets land
# inside other items' spans). Midpoints, two significant figures; both
# edges of both bands pinned by committed cases (ADR-039 §g).
PTR_BODY_MAX = 1200
PTR_COVERAGE_MIN = 0.60
INTERNAL_PTR_RE = re.compile(
    r"(?i)\b(?:on\s+)?pages?\s+(?:FS-)?\d"   # "on page FS-1", "pages 37-51"
    r"|\bFS-\d"                              # bare FS-page reference
    r"|\bsee\s+index\b")                     # ge-1994: "See index under item 14."

# H1: JNJ 2016 lost 18 of 21 items and still reported success_with_warning,
# because `expected_item_missing` is per-item and is not an escalating code —
# so no VOLUME of it could ever move doc_status. Measured over all 17
# non-refused dev fixtures: fifteen lose ZERO items, and the only two that lose
# any (heading-unnumbered 0.043, malformed-html 0.048) already escalate by
# another route. Held-out JNJ sat at 0.857. Empty band 0.048–0.857.
#
# The floor is 0.25, not the band midpoint this repo usually takes: the cost
# asymmetry differs from a content-shape validator. A false `ambiguous` is a
# conservative report a consumer can inspect; a false `success_with_warning` on
# a collapsed document is the silent failure the whole battery exists to
# prevent. 0.25 still sits 5x above the worst real filing in the set.
#
# 2026-08-22 (ADR-027 §c): the band has narrowed since — axp-2008 (burned
# held-out, ADR-020) loses 4 of 20 items = 0.20 and must NOT escalate, so the
# measured empty band is now (0.20, 0.381 items-stripped) and the 5x margin is
# 1.25x. Pinned on both sides; the floor stays.
MISSING_MAX = 0.25

# per-item vocabulary priors: does this span READ like its label?
FINGERPRINTS = {
    "1A": ["risk", "adversely", "could"],
    "3": ["legal", "proceedings"],
    "8": ["total", "net"],
    "9A": ["internal control", "disclosure controls"],
}


def coverage(text, items):
    """Fraction of `text` that lies inside SOME item's span (ADR-035 §d).

    Spans are disjoint and ordered (INV-S1), so the sum is exact. IBR pointer
    spans count: they are real, addressable text this pipeline attributed to an
    item (ADR-011), and the question here is how much of the document was
    placed at all, not how much of it is substantive prose.
    """
    return sum(i["end"] - i["start"] for i in items
               if i.get("start") is not None) / max(len(text), 1)


def _density(s):
    """digit/$/% ratio — Item 8 runs high, Item 1A near zero."""
    return sum(c.isdigit() or c in "$%" for c in s) / max(len(s), 1)


def validate(text, items, accepted, manifest):
    """Returns a list of warning dicts. Never raises, never mutates."""
    warns = []
    n = max(len(text), 1)
    spans = {i["item"]: (i["start"], i["end"]) for i in items
             if i["status"] == "extracted"}
    body = {c: text[s:e] for c, (s, e) in spans.items()}
    # ADR-011: IBR items carry pointer-text offsets. They stay OUT of the
    # content-shape validators below — coverage, domination and density were
    # all measured over extracted spans, and a pointer paragraph has no
    # vocabulary or numeric profile to judge — but their boundaries are checked
    # like any other span. Before this, an IBR span was invisible to all six.
    hygiene_spans = dict(spans)
    hygiene_spans.update({i["item"]: (i["start"], i["end"]) for i in items
                          if i["status"] == "incorporated_by_reference"
                          and i["start"] is not None})

    def warn(code, msg, item=None):
        warns.append({"code": code, "item": item, "message": msg})

    # 1. TOC manifest cross-check — the filing's own declared item list. The
    # trap doubles as a checklist: it is the only free, label-free statement of
    # what SHOULD be here that the document itself provides.
    if manifest:
        found = {c for c in accepted}
        missing = [c for c in manifest if c not in found]
        if missing:
            warn("toc_manifest_mismatch",
                 f"filing's own table of contents lists {missing} but no heading was resolved")

    # 1b. Missing PROPORTION, not missing count. The per-item
    # `expected_item_missing` warnings are emitted upstream and are informative
    # but non-escalating; on their own they let a document that lost most of
    # its items present as a qualified success. The contract calls doc_status
    # "the frontend's headline banner" and invites consumers to threshold on
    # it, so losing a quarter of the expected items is a refusal to resolve,
    # not a footnote.
    if items:
        missing = [i for i in items if i["status"] == "missing"]
        frac = len(missing) / len(items)
        if frac > MISSING_MAX:
            warn("expected_items_mostly_missing",
                 f"{len(missing)} of {len(items)} expected items ({frac:.0%}) have no "
                 f"heading: {[i['item'] for i in missing][:8]}"
                 f"{'…' if len(missing) > 8 else ''}")

    # 2. Unattributed content — the preamble (before the first span) plus the
    # tail (after the last), NOT every gap: interior gaps between spans are not
    # counted. ADR-019 §d measured them — nonzero only on the 7 EXEC_OFFICERS_RE
    # fixtures, where this figure understates true non-coverage by up to 9.7
    # points (ibm-1997). Preamble is the cover page, tail is signatures, and a
    # large one means a whole region went unlabelled.
    if spans:
        first = min(s for s, _ in spans.values())
        last = max(e for _, e in spans.values())
        outside = (first + (n - last)) / n
        if outside > UNATTRIBUTED_MAX:
            warn("unattributed_content",
                 f"{outside:.0%} of the document lies outside every item "
                 f"({first:,} chars before the first, {n - last:,} after the last)")

    # 3. Last-item domination — the tail-bleed detector. An exhibit index is
    # never the largest thing in a 10-K; if it is, the span swallowed an
    # appendix (ADR-004 shape 2 content that carries no heading of its own).
    # 3b (ADR-030, D3). Non-last domination — the interior-bleed detector the
    # last-span check structurally cannot be: a span that is not the last one
    # and still holds most of the document swallowed the items after it (their
    # headings went unresolved — few enough to sit under MISSING_MAX, or not
    # missing at all but resolved to stubs further down, ADR-015 §0's Target
    # shape). Its own threshold, because its own distribution: see ITEM_MAX.
    # The two are disjoint by construction: the last span is judged by 3 only,
    # every other span by 3b only, so no span can carry both codes.
    if spans:
        last_code = max(spans, key=lambda c: spans[c][0])
        for code, (s, e) in spans.items():
            frac = (e - s) / n
            if code == last_code and frac > LAST_ITEM_MAX:
                warn("last_item_dominates",
                     f"item {code} is {frac:.0%} of the document — its span most "
                     "likely swallowed unlabelled content that follows it",
                     item=code)
            elif code != last_code and frac > ITEM_MAX:
                warn("item_dominates",
                     f"item {code} is {frac:.0%} of the document — its span most "
                     "likely swallowed the items that follow it",
                     item=code)

    # 4. Boundary hygiene — every span must open with its own heading. Cheap,
    # and it is the one thing that must never be wrong. A layer-consistency
    # assertion (ADR-016 §2), so it reads the heading with the SAME regex that
    # produced the offset — a hand copy of it drifted ("Item 9 A." matched
    # upstream, not here) and the only live path was a false positive
    # (gates-2026-08-22 T5-3; `spaced-letter-heading`).
    # ADR-042 §d: a span the cross-reference resolver produced was cut by
    # `xref.ENTRY_RE`, so THAT is the regex this assertion must read it back
    # with. Citi FY2025 writes its index rows as `1. Business`, never as
    # `Item 1.`, so HEADING_RE calls 11 correct spans broken — which is the
    # hand-copy failure mode the comment above already warns about, arriving
    # from the other direction.
    from src.sec10k.xref import ENTRY_RE as XREF_ENTRY_RE
    produced_by = {i["item"]: i.get("method") for i in items}
    for code, (s, e) in hygiene_spans.items():
        head = text[s:s + 60].split("\n")[0]
        if produced_by.get(code) == "cross_reference_index":
            m = XREF_ENTRY_RE.match(head + "\n")
            ok = bool(m) and m.group(1).upper() == code
        else:
            m = HEADING_RE.match(head)
            ok = bool(m) and m.group(1) + (m.group(2) or "").upper() == code
        if not ok:
            warn("boundary_hygiene", f"item {code} span does not start with its heading",
                 item=code)

    # 5. Numeric density, RELATIVE within the filing — absolute bands overlap
    # across filers (measured), the ordering does not: financials are denser
    # than risk factors in 9 of 9 filings where both are substantive.
    if len(body.get("8", "")) >= SUBSTANTIVE_MIN and len(body.get("1A", "")) >= SUBSTANTIVE_MIN:
        d8, d1a = _density(body["8"]), _density(body["1A"])
        if d8 <= d1a:
            warn("numeric_density_inversion",
                 f"item 8 is no denser in figures than item 1A ({d8:.3f} vs {d1a:.3f}) "
                 "— the two spans may be mislabelled", item="8")

    # 6. Keyword fingerprints — does a substantive span read like its label?
    for code, words in FINGERPRINTS.items():
        span = body.get(code, "")
        if len(span) < SUBSTANTIVE_MIN:
            continue  # a pointer paragraph has no vocabulary to judge (measured basis: full span)
        # cold review: the heading line itself ("Item 1A. Risk Factors") always
        # satisfies its own fingerprint, and plain substring matching let "net"
        # match "internet"/"network" — strip the heading, match whole words only.
        # A one-line strip assumes the title lives on line 1; ADR-013's bare-
        # heading shape promotes it to its OWN next line ("Item 1A.\n\nRISK
        # FACTORS\n\n<body>"), which survives that strip and satisfies 1A's own
        # fingerprint. accepted[code]["heading_end"] is find_candidates' own cut
        # (already advanced past a promoted title) — prefer it when it actually
        # falls inside this span, else fall back to the line-1 strip.
        s, e = spans[code]
        heading_end = (accepted.get(code) or {}).get("heading_end")
        if heading_end is not None and s < heading_end < e:
            low = text[heading_end:e].lower()
        else:
            low = span.split("\n", 1)[-1].lower()
        if not any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in words):
            warn("keyword_fingerprint",
                 f"item {code} contains none of {words} — span may not be its item",
                 item=code)

    # 7 (ADR-035 §c). The per-item span floor. Carries the item CODE, which is
    # the whole point: before this, the four item-targeted codes could not fire
    # on a stub or a pointer at all, so `WARN_PENALTY` never reached the 0.95
    # the demo showed (postmortem §1). It does not escalate `doc_status` and it
    # does not change `status` — ADR-004's ruling that a pointer sentence is
    # the item's own `extracted` body stands, and this says only that the span
    # is too short to BE the item's content, which is a review flag, not a
    # correction. IBR spans stay out, as they do from every content-shape check
    # (ADR-011): an IBR pointer is already labelled and already scores 0.85.
    for code in SUBSTANCE_ITEMS:
        if code in spans:
            chars = spans[code][1] - spans[code][0]
            if chars < SPAN_FLOOR:
                warn("item_span_near_empty",
                     f"item {code}'s span is {chars:,} chars, under the "
                     f"{SPAN_FLOOR:,}-char floor for this item — a pointer or a "
                     "stub, not the item's own content", item=code)

    # 8 (ADR-035 §d). Document coverage, the escalating half. Check 2 above
    # measures the preamble and the tail; this measures what the items actually
    # hold. On a document whose spans collapsed onto index rows the two diverge
    # by nothing at all — but check 2 does not escalate by ADR-008's ruling and
    # must not start to, so the low end gets its own code and its own constant.
    cov = coverage(text, items) if items else None
    if items and cov < COVERAGE_MIN:
        warn("low_item_coverage",
             f"only {cov:.1%} of the document lies inside an item span "
             f"({round(cov * n):,} of {n:,} chars) — the spans did not "
             "resolve to the filing's content")

    # 9 (ADR-039 §b, D16). The pointer-shape escalation: an extracted item
    # whose whole body is an internal page/index pointer, in a document most
    # of which lies outside every span, is the shape ADR-038 convicts — the
    # answer the body names is plausibly in the unplaced region, and before
    # this check nothing could say so on an item outside SUBSTANCE_ITEMS.
    # Runs LAST because prong 2 is ADR-038 R3's "already said it" bullet read
    # off the warning list this function just built: an item some warning
    # already carries has said it (cvx-2015 7/8, ge-1994 8, spatz-2014 8 —
    # their 0.80 must not move to 0.65), and a document with an escalating
    # code says it for every item via ADR-027 §a's 0.75 cap (jpm-2024,
    # xom-2021, intc-2025). The external-document exclusion keeps ADR-004
    # shape-1 territory out (proxy/ARS pointers — ge-1994 item 6 is the
    # committed pin). No status change, and NOT in AMBIGUOUS_CODES: one
    # pointer item is a fact about that item, not a verdict on the document
    # (ADR-035 §c's argument, re-applied — item_span_near_empty is this
    # code's exact peer).
    if spans and cov is not None and cov < PTR_COVERAGE_MIN \
            and not any(w["code"] in AMBIGUOUS_CODES for w in warns):
        flagged = {w["item"] for w in warns if w.get("item")}
        for code, (s, e) in spans.items():
            if code in flagged:
                continue
            span = text[s:e]
            ptr_body = span.split("\n", 1)[1] if "\n" in span else ""
            if (len(ptr_body) <= PTR_BODY_MAX and INTERNAL_PTR_RE.search(ptr_body)
                    and not EXTERNAL_DOC_RE.search(ptr_body)):
                warn("internal_pointer_unreached",
                     f"item {code}'s body is an internal page pointer and only "
                     f"{cov:.1%} of the document lies inside item spans — the "
                     "content it names is likely in the unplaced region, not "
                     "in this span", item=code)

    return warns


# --------------------------------------------------------------- confidence

# ADR-008: coarse and clamped — no fake precision. Every input is recorded in
# the item's evidence{} so an auditor can recompute or dispute the number.
#
# ADR-027 §b: the strict/weak title cut, measured 2026-08-22 over the 553
# extracted spans of the 40-fixture corpus. title_similarity: min 0.5, median
# 1.0; 5 spans sit below 0.8 (ba-2003 item 8 0.5, textron-2001 item 1 0.593,
# jnj-2016 item 7 0.718, ko-1997 item 9 0.727, msft-2013 item 1A 0.727), the
# next value up is 0.841 (intc-2002 item 5). The cut sits inside that empty
# band (0.727, 0.841) and is pinned on both edges (msft-2013 1A at 0.75 /
# `heading_lenient`, intc-2002 item 5 at 0.95 / `heading_strict`). It is an
# evidence-strength tier, not a correctness boundary: 4 of the 5 weak-title
# spans are case-asserted correct extractions. `method` is derived from the
# same constant (extract.py), so the envelope cannot say "strict" where the
# score says weak.
STRICT_SIM = 0.8
BASE_STRICT, BASE_WEAK = 0.95, 0.75
BASE_IBR, BASE_OMITTED = 0.85, 0.80
# ADR-018: was 0.55. Every missing item carries its own expected_item_missing
# warning (the only item-targeted warning a missing item can ever catch), so
# the old constant double-counted that status into the penalty and never
# actually landed — every missing item scored 0.55 - 0.15 = 0.40. Collapsed
# the phantom: 0.40 is now the published base, and the restating warning is
# excluded from the penalty below.
BASE_MISSING = 0.40
WARN_PENALTY = 0.15
# CEIL is the "never 1.0" guard (ADR-018 §7) and, since ADR-027 §a, the cap an
# `ambiguous` document replaces with BASE_WEAK: the document-level verdict
# bounds every item, so no item in a document the pipeline could not resolve
# can outrank a weak-title item in one it did. The old FLOOR (0.20) is gone —
# the four item-targeted codes can take a weak item to 0.15 only on hand-built
# warnings, because boundary_hygiene cannot fire on pipeline output (ADR-016
# §2); the three that can leave a weak item at 0.30 at worst, so the clamp
# was decorative (gates-2026-08-22 T5-4).
CEIL = 0.95


def score(item, warns, doc_ambiguous=False):
    """Confidence for one item, from recorded evidence only.

    `doc_ambiguous` is the document-level verdict (extract.py's ladder): when
    True every item is capped at BASE_WEAK (ADR-027 §a) — the only input to an
    item's score that is not the item's own evidence, and the reason the
    envelope can no longer read `ambiguous` over a column of 0.95s.
    """
    ev = dict(item.get("evidence") or {})
    if item["status"] == "extracted":
        base = BASE_STRICT if ev.get("title_similarity", 0) >= STRICT_SIM else BASE_WEAK
    elif item["status"] == "incorporated_by_reference":
        base = BASE_IBR
    elif item["status"] == "omitted":
        base = BASE_OMITTED
    else:
        base = BASE_MISSING  # missing: we expected it and found nothing
    # ADR-018: expected_item_missing restates the status that already set
    # BASE_MISSING — it is the one item-targeted warning a missing item can
    # ever catch, so counting it too double-counts the same fact.
    hits = [w["code"] for w in warns if w.get("item") == item["item"]
            and w["code"] != "expected_item_missing"]
    conf = min(BASE_WEAK if doc_ambiguous else CEIL, base - WARN_PENALTY * len(hits))
    ev["warnings"] = hits
    ev["confidence_base"] = base
    return round(conf, 2), ev


def _demo():
    text = ("Item 1. Business\n" + "We sell things. " * 400 +
            "\nItem 15. Exhibits\n" + "x" * 40)
    cut = text.index("Item 15.")  # computed, never hand-typed — the demo's own
    items = [{"item": "1", "part": "I", "status": "extracted", "start": 0,
              "end": cut, "evidence": {"title_similarity": 1.0}},
             {"item": "15", "part": "IV", "status": "extracted", "start": cut,
              "end": len(text), "evidence": {"title_similarity": 1.0}}]
    w = validate(text, items, {"1": {}, "15": {}}, [])
    assert not [x for x in w if x["code"] == "boundary_hygiene"], w

    # ...and the positive case, which ONLY exists here. No fixture can fire
    # boundary_hygiene: spans are built from heading matches, so a span always
    # opens with its heading by construction, and the check re-applies a copy
    # of the regex that produced the offset. It is a consistency assertion
    # between two layers, not a statement about any document — so it is proved
    # against the layer boundary, on offsets a caller could only produce by
    # being wrong. ADR-016 records why that is the honest place for it.
    off = [{**items[0], "start": items[0]["start"] + 40}, items[1]]
    codes = [x["code"] for x in validate(text, off, {"1": {}, "15": {}}, [])]
    assert "boundary_hygiene" in codes, codes
    # an IBR span is checked the same way (ADR-011): before that extension an
    # IBR item's offsets were invisible to every validator here
    ibr = [{**items[0], "status": "incorporated_by_reference",
            "start": items[0]["start"] + 40}]
    codes = [x["code"] for x in validate(text, ibr, {"1": {}}, [])]
    assert "boundary_hygiene" in codes, codes
    # ...and it must read headings with segmentation's own regex: "Item 9 A."
    # (optional space before the letter) is a heading upstream, so it is one
    # here too. A hand copy of the regex said otherwise — T5-3's false positive,
    # pinned on a fixture by `spaced-letter-heading`; this is the layer echo.
    sp_text = "Item 9 A. Controls and Procedures\n" + "fine. " * 50 + "\nItem 15. Exhibits\nx"
    sp_cut = sp_text.index("Item 15.")
    sp_items = [{"item": "9A", "part": "II", "status": "extracted", "start": 0, "end": sp_cut,
                 "evidence": {}},
                {"item": "15", "part": "IV", "status": "extracted", "start": sp_cut,
                 "end": len(sp_text), "evidence": {}}]
    codes = [x["code"] for x in validate(sp_text, sp_items, {"9A": {}, "15": {}}, [])]
    assert "boundary_hygiene" not in codes, codes

    # a manifest naming an item we never resolved is a strong, free signal
    w = validate(text, items, {"1": {}}, ["1", "7", "8"])
    assert [x["code"] for x in w if x["code"] == "toc_manifest_mismatch"], w

    # last-item domination: one span swallowing the document
    big = "Item 1. Business\nshort\n" + "Item 15. Exhibits\n" + "y" * 5000
    cut2 = big.index("Item 15.")
    items2 = [{"item": "1", "part": "I", "status": "extracted", "start": 0, "end": cut2,
               "evidence": {}},
              {"item": "15", "part": "IV", "status": "extracted", "start": cut2,
               "end": len(big), "evidence": {}}]
    codes = [x["code"] for x in validate(big, items2, {"1": {}, "15": {}}, [])]
    assert "last_item_dominates" in codes, codes
    # ADR-030: ...and the mirror image — a NON-last span swallowing the
    # document fires item_dominates, and only that (the last span here is
    # tiny, so last_item_dominates must stay silent). Before 3b existed this
    # envelope carried no domination warning at all.
    big2 = "Item 1. Business\n" + "y" * 5000 + "\nItem 15. Exhibits\nshort"
    cut3 = big2.index("Item 15.")
    items3 = [{"item": "1", "part": "I", "status": "extracted", "start": 0, "end": cut3,
               "evidence": {}},
              {"item": "15", "part": "IV", "status": "extracted", "start": cut3,
               "end": len(big2), "evidence": {}}]
    w3 = validate(big2, items3, {"1": {}, "15": {}}, [])
    codes = [x["code"] for x in w3]
    assert "item_dominates" in codes and "last_item_dominates" not in codes, codes
    assert [x["item"] for x in w3 if x["code"] == "item_dominates"] == ["1"], w3
    assert "item_dominates" in AMBIGUOUS_CODES  # ADR-030 §c: it escalates

    # keyword_fingerprint on item 1A: no committed fixture can prove this red
    # (the only candidate, spans-transposed, has transposed financial prose
    # that still carries "risk"/"could" as whole words), so — same treatment
    # as boundary_hygiene above, ADR-016's precedent — it is proved at the
    # validator's own layer instead. A span whose body is genuinely clean of
    # the fingerprint vocabulary must still warn; the heading alone ("Item 1A.
    # Risk Factors") must not be enough to satisfy it.
    clean_body = "We sell widgets to customers worldwide. " * 200
    assert not re.search(r"\b(risk|adversely|could)\b", clean_body, re.I), clean_body
    fp_text = "Item 1A. Risk Factors\n" + clean_body + "\nItem 15. Exhibits\n" + "z" * 40
    fp_cut = fp_text.index("Item 15.")
    fp_items = [{"item": "1A", "part": "I", "status": "extracted", "start": 0, "end": fp_cut,
                 "evidence": {}},
                {"item": "15", "part": "IV", "status": "extracted", "start": fp_cut,
                 "end": len(fp_text), "evidence": {}}]
    codes = [x["code"] for x in validate(fp_text, fp_items, {"1A": {}, "15": {}}, [])
             if x.get("item") == "1A"]
    assert "keyword_fingerprint" in codes, codes

    # ADR-013 bare-heading shape: title promoted to its OWN line ("Item 1A.\n\n
    # RISK FACTORS\n\n<body>"). A one-line strip only removes "Item 1A." and
    # leaves "RISK FACTORS" in the judged text, which satisfies 1A's own
    # fingerprint on the heading alone — the same bug as above, different
    # shape. heading_end (find_candidates already advances it past a promoted
    # title, ADR-013) is the correct cut; it must come from accepted[code], not
    # a fixed strip.
    title_line = "RISK FACTORS"
    fp2_text = ("Item 1A.\n\n" + title_line + "\n\n" + clean_body +
                "\nItem 15. Exhibits\n" + "z" * 40)
    fp2_cut = fp2_text.index("Item 15.")
    fp2_heading_end = fp2_text.index(title_line) + len(title_line)  # computed, not hand-typed
    fp2_items = [{"item": "1A", "part": "I", "status": "extracted", "start": 0, "end": fp2_cut,
                  "evidence": {}},
                 {"item": "15", "part": "IV", "status": "extracted", "start": fp2_cut,
                  "end": len(fp2_text), "evidence": {}}]
    fp2_accepted = {"1A": {"heading_end": fp2_heading_end}, "15": {}}
    codes = [x["code"] for x in validate(fp2_text, fp2_items, fp2_accepted, [])
             if x.get("item") == "1A"]
    assert "keyword_fingerprint" in codes, codes

    # ADR-035 §c: the per-item floor. A pointer-sized item 8 beside a
    # substantive item 1 fires on 8 and only 8, and the code carries the item.
    ptr = ("Item 1. Business\n" + "We sell things. " * 400 +
           "\nItem 8. Financial Statements and Supplementary Data\n"
           "See the index on page F-1.\n" + "Item 15. Exhibits\n" + "x" * 40)
    c8 = ptr.index("Item 8.")
    c15 = ptr.index("Item 15.")
    p_items = [{"item": "1", "part": "I", "status": "extracted", "start": 0,
                "end": c8, "evidence": {}},
               {"item": "8", "part": "II", "status": "extracted", "start": c8,
                "end": c15, "evidence": {}},
               {"item": "15", "part": "IV", "status": "extracted", "start": c15,
                "end": len(ptr), "evidence": {}}]
    pw = validate(ptr, p_items, {"1": {}, "8": {}, "15": {}}, [])
    near = [x for x in pw if x["code"] == "item_span_near_empty"]
    assert [x["item"] for x in near] == ["8"], pw
    assert "item_span_near_empty" not in AMBIGUOUS_CODES  # §c: it does not escalate
    # ...and an item OUTSIDE SUBSTANCE_ITEMS is not floored, however short: a
    # smaller reporting company's whole answer to item 1A is one sentence.
    assert "1A" not in SUBSTANCE_ITEMS and "7A" not in SUBSTANCE_ITEMS

    # ADR-035 §d: coverage is the placed fraction, IBR spans included, and the
    # doc-level code escalates. The pointer document above places nearly all of
    # itself, so it must stay silent; a document that places 3% must not.
    assert coverage(ptr, p_items) > 0.99, coverage(ptr, p_items)
    assert not [x for x in pw if x["code"] == "low_item_coverage"], pw
    stub = "x" * 10000 + "\nItem 1. Business\n"
    s_items = [{"item": "1", "part": "I", "status": "extracted",
                "start": stub.index("Item 1."), "end": len(stub), "evidence": {}}]
    assert round(coverage(stub, s_items), 4) == 0.0017, coverage(stub, s_items)
    codes = [x["code"] for x in validate(stub, s_items, {"1": {}}, [])]
    assert "low_item_coverage" in codes and "item_span_near_empty" in codes, codes
    assert "low_item_coverage" in AMBIGUOUS_CODES
    # an IBR pointer span counts as placed — it is attributed text (ADR-011)
    ibr_only = [{**s_items[0], "status": "incorporated_by_reference"}]
    assert coverage(stub, ibr_only) == coverage(stub, s_items)
    # ...and the figure THIS function thresholds on is that same one. The line
    # above pins coverage(); this pins the call site at §d above, which is the
    # only place the thresholded number ever surfaces (PR #57 R5).
    ibr_w = [x for x in validate(stub, ibr_only, {"1": {}}, [])
             if x["code"] == "low_item_coverage"]
    assert "0.2%" in ibr_w[0]["message"], ibr_w

    # ADR-039 (D16): the pointer-shape check, all three prongs. A document
    # placing ~40% of itself (inside [COVERAGE_MIN, PTR_COVERAGE_MIN)), with
    # a substantive item 1 and an item-2 body that is an internal page
    # pointer: fires on 2 and only 2, carrying the item code.
    lo = ("Item 1. Business\n" + "We sell things. " * 250 +
          "\nItem 2. Properties\nDescribed on page 3 under Item 1 above.\n" +
          "Item 15. Exhibits\nexhibit index\n" + "tail text " * 600)
    l2 = lo.index("Item 2.")
    l15 = lo.index("Item 15.")
    l_end = lo.index("exhibit index") + len("exhibit index")  # tail stays OUTSIDE
    lo_items = [{"item": "1", "part": "I", "status": "extracted", "start": 0,
                 "end": l2, "evidence": {}},
                {"item": "2", "part": "I", "status": "extracted", "start": l2,
                 "end": l15, "evidence": {}},
                {"item": "15", "part": "IV", "status": "extracted", "start": l15,
                 "end": l_end, "evidence": {}}]
    lo_acc = {"1": {}, "2": {}, "15": {}}
    assert COVERAGE_MIN < coverage(lo, lo_items) < PTR_COVERAGE_MIN, \
        coverage(lo, lo_items)
    lw = [x for x in validate(lo, lo_items, lo_acc, [])
          if x["code"] == "internal_pointer_unreached"]
    assert [x["item"] for x in lw] == ["2"], lw
    assert "internal_pointer_unreached" not in AMBIGUOUS_CODES  # §b4: no escalation
    # ...an EXTERNAL pointer of the same shape stays out (ADR-004 shape 1
    # territory; ge-1994 item 6 is the committed fixture pin). Same-length
    # replacement so every offset in lo_items still lands where it did.
    old_body, new_body = ("Described on page 3 under Item 1 above.",
                          "See page 3 of the proxy statement here.")
    assert len(old_body) == len(new_body)
    ext = lo.replace(old_body, new_body)
    codes = [x["code"] for x in validate(ext, lo_items, lo_acc, [])]
    assert "internal_pointer_unreached" not in codes, codes
    # ...a document that places (nearly) everything stays out — the pointer's
    # target is then necessarily inside some span (ADR-038 §c4's bac-2006
    # ground; the committed pins are bac-2006-shallow's warning_absent ×3)
    hi_items = [lo_items[0], lo_items[1], {**lo_items[2], "end": len(lo)}]
    assert coverage(lo, hi_items) > PTR_COVERAGE_MIN
    codes = [x["code"] for x in validate(lo, hi_items, lo_acc, [])]
    assert "internal_pointer_unreached" not in codes, codes
    # ...and an item another warning already carries has ALREADY SAID IT
    # (ADR-038 R3's second bullet): the same pointer under item 8 catches
    # item_span_near_empty (SPAN_FLOOR) and must NOT be double-penalised.
    lo8 = lo.replace("Item 2. Properties", "Item 8. Financials")
    lo8_items = [dict(i, item="8") if i["item"] == "2" else i for i in lo_items]
    w8 = validate(lo8, lo8_items, {"1": {}, "8": {}, "15": {}}, [])
    codes8 = [x["code"] for x in w8 if x.get("item") == "8"]
    assert codes8 == ["item_span_near_empty"], w8

    # confidence: warnings on an item pull it down, others leave it alone
    it = {"item": "8", "status": "extracted", "evidence": {"title_similarity": 1.0}}
    assert score(it, [])[0] == BASE_STRICT
    assert score(it, [{"code": "keyword_fingerprint", "item": "8"}])[0] < BASE_STRICT
    assert score(it, [{"code": "keyword_fingerprint", "item": "1"}])[0] == BASE_STRICT
    assert score({"item": "9", "status": "missing", "evidence": {}}, [])[0] == BASE_MISSING

    # ADR-018: a missing item ALWAYS carries its own expected_item_missing warning
    # in the real pipeline, and that warning must not double-count against the
    # base that already encodes the status.
    miss = {"item": "9", "status": "missing", "evidence": {}}
    assert score(miss, [{"code": "expected_item_missing", "item": "9"}])[0] == BASE_MISSING

    # ADR-027 §a: an `ambiguous` document caps EVERY item at BASE_WEAK — the
    # strict item, the IBR item, the omitted item; the missing item is already
    # below the cap and is untouched. Red before the cap existed: 0.95 / 0.85.
    assert score(it, [], doc_ambiguous=True)[0] == BASE_WEAK
    ibr_it = {"item": "10", "status": "incorporated_by_reference", "evidence": {}}
    assert score(ibr_it, [], doc_ambiguous=True)[0] == BASE_WEAK
    assert score(ibr_it, [])[0] == BASE_IBR
    assert score(miss, [], doc_ambiguous=True)[0] == BASE_MISSING
    # ADR-027 §b: the strict/weak cut is STRICT_SIM, pinned at both edges of
    # its measured empty band (0.727, 0.841] — see the constant's comment.
    weak = {"item": "1A", "status": "extracted", "evidence": {"title_similarity": 0.727}}
    strong = {"item": "5", "status": "extracted", "evidence": {"title_similarity": 0.841}}
    assert score(weak, [])[0] == BASE_WEAK and score(strong, [])[0] == BASE_STRICT
    # no floor: four item-targeted hits on a weak item read 0.15, honestly
    four = [{"code": c, "item": "8"} for c in ("last_item_dominates", "boundary_hygiene",
                                              "numeric_density_inversion", "keyword_fingerprint")]
    assert score({"item": "8", "status": "extracted", "evidence": {"title_similarity": 0.5}},
                 four)[0] == 0.15
    print("[validate self-check] ok")


if __name__ == "__main__":
    _demo()
