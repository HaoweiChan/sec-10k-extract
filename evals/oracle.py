#!/usr/bin/env python3
"""evals/oracle.py — T11 silent-failure cross-check ORACLE.

Dev instrument only. `src/` must NEVER import this module, it changes no
pipeline behaviour, no eval case, and no baseline. It runs the real pipeline
(`src.sec10k.extract.extract_items`) over every fixture and screens confident
items in `success`/`success_with_warning` docs — the silent-failure
population metric 6 (evals/metrics.py) can only bound from below, because the
pre-commit gate forces every SCORED check green by construction. The ~447
confident items no declared check targets are exactly what this instrument
exists to look at.

This is a SCREEN, not a gate: thresholds are chosen to favour sensitivity
over precision (see each constant's comment) — flagging a legitimate item is
cheap, a human triages the dump afterwards (`--self-check` proves the checks
can fire at all; `failure-triage` skill owns what happens after).

Four checks, each deliberately NOT the pipeline's own method:

1. **Span coverage** — total chars inside span-carrying items (`extracted` +
   `incorporated_by_reference`) / len(normalized_text), per document.
   `src/sec10k/validate.py`'s `unattributed_content` measures only the region
   before the first span and after the last (the "outer hull"); an interior
   hole between two ACCEPTED spans is invisible to it by definition. Under
   `assign_boundaries` (segment.py), two accepted spans are contiguous by
   construction — `end[i] == start[i+1]` — on 29 of the 36 fixtures MEASURED
   2026-08-19, so coverage there equals `1 - unattributed_content`'s own
   "outside" fraction exactly. On the other 7 (the `EXEC_OFFICERS_RE` clip,
   ADR-019 §f/§d), that identity breaks: coverage reads up to 9.7 points below
   `1 - unattributed_content`, because the clip opens a real interior gap the
   outer hull can't see.
   **Restated 2026-08-19 (T12, ADR-020 §g): the corpus is now 37 fixtures and
   the EO clip is no longer the only exception.** `axp-2008`, moved into
   `evals/fixtures/` when its held-out case was burned, is an 8th
   non-contiguous fixture — gap 0.1264, above the 0.0971 ceiling below — and
   it is NOT an `EXEC_OFFICERS_RE` fixture: its gap is the un-found combined
   Part III block (ADR-020 §c row 7). All per-fixture numbers in this
   docstring, and ADR-019 §d's table, describe the 36-fixture corpus at their
   own SHA and are left as measured; whether a second, non-EO gap source
   weakens the redundancy argument below is a question for whoever revisits
   ADR-019 §d's debt row, and is deliberately not answered here.
   (2026-08-19 post-commit review: this was first verified contiguous on all
   34 fixtures then committed; the EO fix landed after and is the sole
   exception.) Full per-fixture table: ADR-019 §d. That makes checks 1 and 2
   algebraically redundant with `unattributed_content` FOR THIS PIPELINE'S
   CURRENT ARCHITECTURE except on those 7 fixtures — not because span
   coverage is a bad idea (ADR-015 §5
   still calls it "the obvious missing member of the battery"), but because
   a hole here does not show up as absence, it shows up as a NEIGHBOURING
   SPAN THAT SILENTLY GREW to cover text that belongs to a different, unfound
   code ("mis-assigned rather than missing", ADR-013's phrase, still open per
   ADR-015 §5). That failure shape is Target FY2002's (item 4 swallowed 81%
   of the document, doc_status `success`, zero warnings) — and coverage would
   NOT have caught it either, because the swallowed text is still "covered",
   just by the wrong item. Both checks are still computed and reported (the
   milestone asks for the distribution and the debt row is real), but they do
   not drive flags on their own; check 4 is what can actually catch a
   mis-assignment, by relocating the code's real heading independently.

2. **Largest interior gap** — the widest run of chars between two
   consecutively ACCEPTED spans, as a fraction of the document. Per check 1,
   this was 0.0 on 29 of the 36 fixtures measured 2026-08-19 and nonzero only
   on the 7 `EXEC_OFFICERS_RE` fixtures, 0.0019 to 0.0971 of the document (see
   check 1's restatement: at 37 fixtures `axp-2008` is an 8th, non-EO, at
   0.1264) — the clip
   is a deliberate exclusion (ADR-019 §f), so the gap check correctly
   reports the one intentional gap source this pipeline has, rather than
   finding nothing. Full table: ADR-019 §d. `--self-check` proves the metric
   can detect a gap via a synthetic, hand-built input bypassing
   `assign_boundaries` — still the only proof independent of which real
   fixtures happen to carry a gap this run, the same "proved at the layer,
   not by a fixture" treatment `validate.py` gives `boundary_hygiene`
   (ADR-016).

3. **Implausibly short span for a canonical item** — the `ba-2003` shape:
   a span-carrying item under `SHORT_SPAN_FLOOR` chars in a
   `success`/`success_with_warning` document. ADR-005 rule 1 makes trivial
   bodies ("[Reserved]", "None.") legitimately `extracted`, and rules
   explicitly that "triviality is signalled by span length ... never by
   status" — i.e. this is the validator ADR-005 asked for and nothing in
   `validate.py` implements it. The measured length distribution (below) has
   NO clean empty band near the floor: legitimate reserved/none-applicable
   stubs and the one known real defect (`ba-2003` items 11/13, 34 and 59
   chars) occupy the same range, so this check WILL co-flag legitimate items
   by design — each flag carries a body-text excerpt so a human can tell in
   one glance.

4. **Independent heading locator** — deliberately NOT the pipeline's method.
   `segment.py`'s `find_candidates`/`filter_candidates` score title
   similarity against era aliases (`SIM_FLOOR`) and suppress dense recurring
   runs as tables of contents (`_toc_runs`). This locator does neither: it
   matches a bare, line-anchored `item <code>` regex with NO title check at
   all, collects every hit, and disambiguates by a completely different
   signal — for each hit, the RUNWAY to the next heading-shaped line of ANY
   code; the hit with the largest runway wins. The idea is that a real body
   heading is followed by a long run of prose before the next item, while a
   table-of-contents row is followed almost immediately by the next
   TOC row. It disagrees with the pipeline where a code's span does not
   CONTAIN the located offset, or where a `missing`/`omitted` code turns up
   a plausible heading (runway >= `LOCATOR_RUNWAY_FLOOR`) that the pipeline
   never resolved.
   HONEST LIMITATION, found by running this against all 34 fixtures and
   reading every divergence by hand (recorded in the findings dump): 10 of
   the 11 real divergences are this method's OWN false positives, not
   pipeline defects — it prefers an early table-of-contents/index row over
   the pipeline's correct body heading whenever that row happens to sit
   before an unrelated large blank/structural run (page-number whitespace,
   an exhibit block, a trivial "[Reserved]"-shaped item where BOTH
   candidates have near-zero runway). This is the price of a locator that
   does not know what a table of contents is; the pipeline's own TOC
   suppression is far better at that specific job, which is exactly why an
   oracle reusing it could never disagree with it. Reported anyway, with the
   raw evidence, because a screen's job is to surface candidates, not to be
   right.

CLI:
    python3 -m evals.oracle                 # distribution, flags, screened rate
    python3 -m evals.oracle --json out.json  # also dump machine-readable results
    python3 -m evals.oracle --self-check     # assert-based synthetic proof
"""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.sec10k.extract import extract_items  # noqa: E402 — read-only src/ imports: the
from src.sec10k.web.fixtures import fixture_file  # noqa: E402 — extractor + the fixture rule (D1)

FIXTURES_DIR = ROOT / "evals" / "fixtures"
SUCCESS_STATUSES = {"success", "success_with_warning"}
SPAN_STATUSES = {"extracted", "incorporated_by_reference"}
CONFIDENT = 0.8  # same population cutoff evals/metrics.py's metric 6 uses

# ---------------------------------------------------------------- thresholds
# Measured first (run with no args to see the full distributions this comes
# from), chosen after, per this repo's own rule (ADR-007/008 precedent).

# Coverage among success(-with-warning) docs has a clean empty band
# 0.272 (cvx-2015) .. 0.561 (tgt-2002) over the 28 such fixtures measured
# 2026-08-19. Floor at the midpoint. All three fixtures below it were
# investigated against the actual filing text (findings dump): all three are
# the SAME legitimate shape — `assign_boundaries`' TAIL_RE correctly stops the
# last item at "Signatures", and 70-76% of the file is a circulated annual
# report or exhibit attachments that carry no item heading of their own. Not
# silent failures; kept as flags anyway per the screen's own rule (sensitivity
# over precision), with that finding attached to each one.
COVERAGE_FLOOR = 0.42

# Span-length distribution over 529 span-carrying items in success(-with-
# warning) docs has NO clean empty band near the bottom (see check 3's
# docstring): legitimate "[Reserved]"/"None." stubs run from 29 chars up
# through the same range as ba-2003's own 34/59-char defect. Floor sits at the
# ~11th percentile (60/529 fall below it) — generous on purpose, so the known
# defect clears it with margin while still being a small enough slice of the
# corpus to triage by hand.
SHORT_SPAN_FLOOR = 100

# Runway floor for a `missing`/`omitted` code where the locator found SOME
# heading-shaped line anyway. Measured over all 34 fixtures: only two such
# hits exist in the entire corpus, both bare table-of-contents rows in
# already-`ambiguous` docs (heading-unnumbered item 8, runway 58;
# malformed-html item 1A, runway 28) — i.e. noise, not a missed real heading.
# 300 sits comfortably above both; reuses this repo's own IBR_REMAINDER_MAX
# (segment.py) as a precedented round number rather than inventing a new one.
LOCATOR_RUNWAY_FLOOR = 300

# ------------------------------------------------------------ fixture I/O

def iter_fixtures(root=FIXTURES_DIR):
    """(name, path) for every fixture directory under `root` — a directory
    holding exactly one file, the filing (src/sec10k/web/fixtures.py: the
    same rule /api/meta lists by and `_fixture_file` serves by, D1). Before
    D1 this yielded the largest non-.md file of EVERY directory, so
    `repo_hygiene/` (14 regression stubs) was a dev fixture to the bench."""
    for d in sorted(root.iterdir()):
        f = fixture_file(d) if d.is_dir() else None
        if f is not None:
            yield d.name, f


# ------------------------------------------------------------ check 1 + 2

def span_metrics(text, items):
    """(coverage, largest_gap_frac, gap_between, spans) for one document.

    `spans` is every span-carrying item (start, end, code), sorted by start.
    `gap_between` is the (code, code) pair bordering the largest interior
    gap, or None if fewer than two spans exist.
    """
    n = max(len(text), 1)
    spans = sorted(((i["start"], i["end"], i["item"]) for i in items
                     if i.get("start") is not None and i.get("end") is not None),
                    key=lambda t: t[0])
    covered = sum(e - s for s, e, _ in spans)
    coverage = covered / n
    gap, gap_between = 0, None
    for (_, e1, c1), (s2, _, c2) in zip(spans, spans[1:]):
        g = s2 - e1
        if g > gap:
            gap, gap_between = g, (c1, c2)
    return coverage, gap / n, gap_between, spans


# ------------------------------------------------------------ check 3

def check_short_span(text, item, success):
    """None, or a `short_span` finding for a span-carrying item under the floor."""
    if not success or item.get("status") not in SPAN_STATUSES:
        return None
    start, end = item.get("start"), item.get("end")
    if start is None or end is None:
        return None
    chars = end - start
    if chars >= SHORT_SPAN_FLOOR:
        return None
    body = text[start:end]
    excerpt = body.split("\n", 1)[1].strip()[:120] if "\n" in body else ""
    return {"check": "short_span", "chars": chars, "floor": SHORT_SPAN_FLOOR,
            "heading_text": item.get("heading_text"), "body_excerpt": excerpt}


# ------------------------------------------------------------ check 4

# Deliberately cruder than segment.py's HEADING_RE: no title capture, no
# "title on next line" promotion — just "is 'item <code>' the first thing on
# this line". Used both to find candidate offsets for one code and (as
# GENERIC_HEADING_RE) to build the "next heading of any kind" list the runway
# rule measures against.
GENERIC_HEADING_RE = re.compile(
    r"(?im)^[ \t\xa0]*item[ \t\xa0]*(\d{1,2})[ \t]?([A-Da-d])?(?![A-Za-z0-9])")


def _code_re(code):
    m = re.match(r"(\d+)([A-Za-z]?)", code)
    digits, letter = m.group(1), m.group(2)
    if letter:
        return re.compile(rf"(?im)^[ \t\xa0]*item[ \t\xa0]*{digits}[ \t]?{letter}(?![A-Za-z0-9])")
    return re.compile(rf"(?im)^[ \t\xa0]*item[ \t\xa0]*{digits}(?![A-Za-z0-9])")


def locate_heading(text, code, all_offsets):
    """Independent location for `code`: every line-start match, disambiguated
    by which one has the longest run of text before the next heading-shaped
    line of ANY code. Returns (best_offset_or_None, runway, n_hits)."""
    hits = [m.start() for m in _code_re(code).finditer(text)]
    if not hits:
        return None, 0, 0

    def runway(pos):
        nxt = next((o for o in all_offsets if o > pos), len(text))
        return nxt - pos

    best = max(hits, key=runway)
    return best, runway(best), len(hits)


def check_locator(text, item, all_offsets):
    """None, or a `heading_divergence`/`missing_but_located` finding."""
    off, runway, n_hits = locate_heading(text, item["item"], all_offsets)
    start, end = item.get("start"), item.get("end")
    if start is not None:
        if off is not None and not (start <= off < end):
            return {"check": "heading_divergence", "pipeline_start": start,
                     "pipeline_end": end, "located_offset": off, "runway": runway,
                     "n_hits": n_hits, "pipeline_heading": text[start:start + 80],
                     "located_heading": text[off:off + 80]}
        return None
    if off is not None and runway >= LOCATOR_RUNWAY_FLOOR:
        return {"check": "missing_but_located", "located_offset": off, "runway": runway,
                 "n_hits": n_hits, "located_heading": text[off:off + 80]}
    return None


# ------------------------------------------------------------ orchestration

def analyze(name, path):
    """Run the real pipeline on one fixture and return its full oracle record."""
    r = extract_items(str(path))
    text, items, doc_status = r["normalized_text"], r["items"], r["doc_status"]
    success = doc_status in SUCCESS_STATUSES
    coverage, gap_frac, gap_between, _ = span_metrics(text, items)
    all_offsets = sorted(m.start() for m in GENERIC_HEADING_RE.finditer(text))

    rows = []
    for it in items:
        checks = [c for c in (check_short_span(text, it, success),
                               check_locator(text, it, all_offsets)) if c]
        if success and coverage < COVERAGE_FLOOR:
            checks.append({"check": "low_span_coverage", "coverage": round(coverage, 4),
                            "floor": COVERAGE_FLOOR})
        if success and gap_frac > 0:
            checks.append({"check": "large_interior_gap", "gap_frac": round(gap_frac, 4),
                            "between": gap_between})
        conf = it.get("confidence") or 0
        rows.append({
            "item": it["item"], "status": it["status"], "confidence": it.get("confidence"),
            "start": it.get("start"), "end": it.get("end"),
            "confident_population": bool(success and conf >= CONFIDENT),
            "checks": checks,
        })
    return {"fixture": name, "doc_status": doc_status, "n_chars": len(text),
            "coverage": round(coverage, 4), "gap_frac": round(gap_frac, 6),
            "gap_between": gap_between, "items": rows}


def run_all():
    return [analyze(name, path) for name, path in iter_fixtures()]


def screened_rate(records):
    total = flagged = 0
    for r in records:
        for it in r["items"]:
            if it["confident_population"]:
                total += 1
                if it["checks"]:
                    flagged += 1
    return flagged, total


def span_length_distribution(records):
    """chars for every span-carrying item in a success(-with-warning) doc,
    regardless of confidence — the population check 3's floor is measured
    against."""
    out = []
    for r in records:
        if r["doc_status"] not in SUCCESS_STATUSES:
            continue
        for it in r["items"]:
            if it["status"] in SPAN_STATUSES and it["start"] is not None:
                out.append(it["end"] - it["start"])
    return sorted(out)


# ------------------------------------------------------------------ report

def render(records):
    out = []
    out.append("=== per-fixture distribution (coverage, largest interior gap) ===")
    for r in sorted(records, key=lambda r: r["coverage"]):
        out.append(f"  {r['fixture']:<24} {r['doc_status']:<20} n={r['n_chars']:<9} "
                    f"coverage={r['coverage']:<7} gap_frac={r['gap_frac']}")

    lens = span_length_distribution(records)
    out.append("")
    out.append(f"=== span-length distribution, {len(lens)} span-carrying items in "
                "success(-with-warning) docs ===")
    if lens:
        pcts = (0.01, 0.05, 0.10, 0.15, 0.25, 0.50)
        out.append("  " + "  ".join(f"p{int(p*100)}={lens[int(len(lens)*p)]}" for p in pcts))
        out.append(f"  min={lens[0]} max={lens[-1]}")

    out.append("")
    out.append("=== thresholds chosen ===")
    out.append(f"  COVERAGE_FLOOR={COVERAGE_FLOOR}  (band 0.272..0.561 among success(-with-"
                "warning) docs, midpoint)")
    out.append(f"  SHORT_SPAN_FLOOR={SHORT_SPAN_FLOOR}  (~11th pct of the distribution above, "
                "no clean band exists)")
    out.append(f"  LOCATOR_RUNWAY_FLOOR={LOCATOR_RUNWAY_FLOOR}  (both noise hits found in the "
                "corpus sit at runway 28/58)")

    # ba-2003 instrument validation
    ba = next((r for r in records if r["fixture"] == "ba-2003"), None)
    out.append("")
    out.append("=== instrument validation: ba-2003 (the one known real silent failure) ===")
    if ba is None:
        out.append("  !! ba-2003 fixture not found — cannot validate")
    else:
        by_item = {it["item"]: it for it in ba["items"]}
        all_ok = True
        for code in ("11", "13"):
            it = by_item.get(code)
            fired = bool(it and any(c["check"] == "short_span" for c in it["checks"]))
            all_ok = all_ok and fired
            chars = next((c["chars"] for c in it["checks"] if c["check"] == "short_span"), None) \
                if it else None
            out.append(f"  item {code}: status={it['status'] if it else '?'} "
                        f"confidence={it['confidence'] if it else '?'} chars={chars} "
                        f"short_span_fired={fired}")
        out.append(f"  doc_status={ba['doc_status']}")
        out.append(f"  RESULT: {'PASS' if all_ok else 'FAIL'} — "
                    f"{'both items 11 and 13 flagged' if all_ok else 'instrument did NOT flag the known defect'}")

    flagged, total = screened_rate(records)
    out.append("")
    out.append("=== flags (confident items in success(-with-warning) docs) ===")
    by_check = {}
    for r in records:
        for it in r["items"]:
            for c in it["checks"]:
                by_check.setdefault(c["check"], 0)
                by_check[c["check"]] += 1
    for name, n in sorted(by_check.items()):
        out.append(f"  {name}: {n} item-check hits (includes non-headline items)")
    out.append(f"  screened rate: {flagged}/{total} = "
                f"{round(flagged/total, 4) if total else None}")
    return "\n".join(out)


# --------------------------------------------------------------- self-check

def _demo():
    # 1. HOLED — span_metrics must find an interior gap given a deliberate
    # one; the real pipeline can never produce this input (see module
    # docstring), so it is proved here, against synthetic spans, instead.
    filler = "gap filler text that belongs to no item. " * 20
    text = "Item 1. Business\n" + "a" * 500 + "\n" + filler + "\nItem 2. Properties\n" + "b" * 500
    i1_end = text.index(filler)
    i2_start = text.index("Item 2.")
    items = [{"item": "1", "start": 0, "end": i1_end},
              {"item": "2", "start": i2_start, "end": len(text)}]
    coverage, gap_frac, gap_between, spans = span_metrics(text, items)
    assert gap_between == ("1", "2"), gap_between
    assert gap_frac > 0.05, gap_frac
    assert coverage < 1.0, coverage
    # two contiguous spans (the real pipeline's shape) must show NO gap
    contiguous = [{"item": "1", "start": 0, "end": 100}, {"item": "2", "start": 100, "end": 200}]
    assert span_metrics("x" * 200, contiguous)[1] == 0.0

    # 2. TRUNCATED — a real body heading whose span was cut down to almost
    # nothing must clear the short-span floor (the ba-2003 shape).
    body_text = "Item 11. Executive Compensation*\nItem 12. Security Ownership\n" + "z" * 3000
    trunc_item = {"item": "11", "status": "extracted", "start": 0,
                  "end": body_text.index("Item 12")}
    hit = check_short_span(body_text, trunc_item, success=True)
    assert hit and hit["chars"] == trunc_item["end"], hit
    normal_item = {"item": "12", "status": "extracted",
                   "start": body_text.index("Item 12"), "end": len(body_text)}
    assert check_short_span(body_text, normal_item, success=True) is None
    # scoped to success(-with-warning) docs only
    assert check_short_span(body_text, trunc_item, success=False) is None

    # 3. DISPLACED — a span that does not open on its own heading. Same shape
    # of proof as validate.py's boundary_hygiene positive case (ADR-016): no
    # committed fixture can be relied on to produce a wrong offset on demand,
    # since offsets come from a heading match by construction, so this is
    # proved against a span a caller could only produce by being wrong.
    disp_text = ("Item 8. Financial Statements\n" + "x" * 3000 +
                 "\nItem 9. Changes in Accountants\n" + "y" * 500)
    offsets = sorted(m.start() for m in GENERIC_HEADING_RE.finditer(disp_text))
    i9_start = disp_text.index("Item 9")
    displaced = {"item": "8", "status": "extracted", "start": 40, "end": i9_start}
    hit = check_locator(disp_text, displaced, offsets)
    assert hit and hit["check"] == "heading_divergence", hit
    correct = {"item": "8", "status": "extracted", "start": 0, "end": i9_start}
    assert check_locator(disp_text, correct, offsets) is None

    # a `missing` code whose real heading exists and carries a big runway
    # (the pipeline failed to resolve it, this locator would have) must fire
    miss_text = "Item 1. Business\n" + "a" * 500 + "\nItem 3. Legal Proceedings\n" + "b" * 3000
    offsets2 = sorted(m.start() for m in GENERIC_HEADING_RE.finditer(miss_text))
    missing_item = {"item": "3", "status": "missing", "start": None, "end": None}
    hit = check_locator(miss_text, missing_item, offsets2)
    assert hit and hit["check"] == "missing_but_located", hit
    # ...but a bare mention with no runway behind it (TOC-shaped) must not
    tiny_text = "Item 3. Legal Proceedings\nItem 4. Mine Safety\n" + "c" * 10
    offsets3 = sorted(m.start() for m in GENERIC_HEADING_RE.finditer(tiny_text))
    missing_item2 = {"item": "3", "status": "missing", "start": None, "end": None}
    assert check_locator(tiny_text, missing_item2, offsets3) is None

    print("[oracle self-check] ok")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None, help="also dump machine-readable results here")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args(argv[1:])

    if args.self_check:
        _demo()
        return 0

    records = run_all()
    print(render(records))

    if args.json:
        flagged, total = screened_rate(records)
        payload = {"records": records,
                    "thresholds": {"COVERAGE_FLOOR": COVERAGE_FLOOR,
                                    "SHORT_SPAN_FLOOR": SHORT_SPAN_FLOOR,
                                    "LOCATOR_RUNWAY_FLOOR": LOCATOR_RUNWAY_FLOOR,
                                    "CONFIDENT": CONFIDENT},
                    "screened_rate": {"flagged": flagged, "total": total}}
        Path(args.json).write_text(json.dumps(payload, indent=2, default=str))
        print(f"\n[oracle] wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
