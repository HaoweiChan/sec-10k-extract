#!/usr/bin/env python3
"""evals/oracle_oss.py — T11 OSS second-extractor CROSS-CHECK ORACLE.

Dev instrument only. Nothing under `src/` may import this module, and
neither may `evals/run.py` or `evals/metrics.py` — it never runs in CI or the
pre-commit gate, and it fixes nothing (findings only; a triaged finding
becomes an `evals/adversarial/` case, watched RED, per CLAUDE.md rule 2).

WHY A SECOND TOOL AT ALL: this repo's own pipeline (`src.sec10k.extract`) is
the only implementation of 10-K item-boundary detection in the codebase, so
every eval case it passes was, by construction, checked against itself. This
module runs an INDEPENDENT, third-party 10-K parser over the same fixtures
and flags where the two disagree — disagreement is the only thing an oracle
built this way can find that the eval set structurally cannot.

TOOL CHOICE (a throwaway spike already settled this — see
scratchpad/t11-oss-spike.md, not reproduced here):
  - `sec-parser` is RULED OUT: its taxonomy is 10-Q only, it never classifies
    Items 1A/7/8 as sections, and on plain-text-era filings it emits
    confidently mislabeled sections (a false-agreement risk worse than a
    crash). Do not use it.
  - `edgartools==5.50.0` is the adopted tool, via its low-level,
    network-free entry point ONLY:
        from edgar.documents import HTMLParser, ParserConfig
        doc = HTMLParser(ParserConfig(form="10-K")).parse(html_string)
        doc.sections   # {'part_i_item_1': Section(item='1', ...), ...}
    NOT `Filing`/`TenK`, which touch the network in normal use.
  - `Section.start_offset`/`end_offset` are DEAD FIELDS (always 0) on this
    detection path — confirmed directly, not assumed. Comparison is
    therefore on SECTION TEXT CONTENT only, never offsets.
  - Zero plain-text-era coverage, by edgartools' own documented design
    (`TenK.document` docstring: returns None "for older 10-Ks filed as
    plain text"). Calling `HTMLParser.parse()` directly on plain text
    confirms this: 0 sections, no exception. This gap is reported below as
    a finding, never papered over.

NETWORK SAFETY (C7): re-verified in a FRESH process for this deliverable —
not taken on the spike's word — by monkey-patching BOTH
`socket.socket.connect` and `socket.getaddrinfo` to raise, then parsing three
fixtures including the largest committed one (jpm-2024, 12.8MB) through
`HTMLParser.parse()`. All three parsed cleanly with no network call
attempted. This module enforces the same guard on every run (`_NoNetwork`
below) rather than resting on that one-time check: any future edgartools
release that starts dialing out fails loudly here, immediately, rather than
silently phoning home from a dev instrument.

DEPENDENCY ISOLATION (ADR-003): edgartools must NOT be added to
`requirements.txt` or `pyproject.toml` — the shipped pipeline stays
stdlib-only. This file imports edgartools lazily; if it's missing, it prints
the exact venv recipe and exits non-zero rather than crashing with a raw
ImportError traceback or silently skipping the comparison.

REPRODUCE THE VENV THIS WAS MEASURED WITH:
    python3 -m venv .venv-oracle-oss
    .venv-oracle-oss/bin/pip install -r evals/oracle-oss-requirements.txt
    .venv-oracle-oss/bin/python3 -m evals.oracle_oss [--json out.json]
`evals/oracle-oss-requirements.txt` is the FULL `pip freeze` of that venv
(edgartools' own declared deps are loose ranges, not pins — the headline
package alone is not reproducible six months from now).

COMPARISON RULES:
  1. STATUS/PRESENCE disagreement (highest-value class, reported first):
     edgartools resolves a section for an item this pipeline reports
     `missing`/`omitted`, or vice versa. This is the class most likely to be
     a real silent failure, because it means one tool found text where the
     other found none.
  2. CONTENT disagreement, for items BOTH tools resolved: `difflib.
     SequenceMatcher` ratio on NORMALIZED text (whitespace-collapsed — see
     `_normalize`; the two tools flatten whitespace differently, and diffing
     raw text manufactures disagreements that normalization would erase).
     Char-length ratio (`min/max`) is also reported: cheaper, and catches a
     gross span-size mismatch a similarity ratio can mask (e.g. one tool
     grabbing 3x the text at 90% textual overlap with the smaller span).
  3. THRESHOLD: chosen from the measured distribution, not picked in
     advance (this repo's standing rule, ADR-007/008 precedent) — see
     `choose_cut`: the cut sits at the midpoint of the largest gap in the
     sorted similarity-ratio distribution, computed fresh every run and
     printed alongside the full distribution so an ADR can quote both.

ERA HANDLING: `.txt` fixtures (pre-2001-ish plain-text/SGML submissions) get
zero edgartools coverage by the tool's own design (above) — these are
listed explicitly, never silently absent. `.htm`/`.html` fixtures are the
HTML/iXBRL stratum this oracle actually covers. A fixture whose OWN pipeline
already refuses the document at the doc level (`doc_status` `failed` or
`unsupported` — a truncated download, a non-10-K form) has no per-item
`items` list to compare and is listed separately: that's an already-loud
refusal, not a silent-failure candidate.

CLI:
    python3 -m evals.oracle_oss                 # distribution, cut, dump
    python3 -m evals.oracle_oss --json out.json  # also write JSON
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.sec10k.extract import extract_items  # noqa: E402 — the only src/ import; read-only

FIXTURES_DIR = ROOT / "evals" / "fixtures"
HTML_SUFFIXES = {".htm", ".html"}
TXT_SUFFIXES = {".txt"}


# ------------------------------------------------------------ edgartools import

def _load_edgartools():
    try:
        from edgar.documents import HTMLParser, ParserConfig
    except ImportError as e:
        print("ERROR: edgartools is not importable in this interpreter.\n"
              "This is a dev-only oracle — edgartools is intentionally NOT in\n"
              "requirements.txt/pyproject.toml (ADR-003, stdlib-only pipeline).\n"
              "Recreate the venv this was measured with:\n"
              "    python3 -m venv .venv-oracle-oss\n"
              "    .venv-oracle-oss/bin/pip install -r evals/oracle-oss-requirements.txt\n"
              "    .venv-oracle-oss/bin/python3 -m evals.oracle_oss\n"
              f"(original error: {e})", file=sys.stderr)
        sys.exit(1)
    return HTMLParser, ParserConfig


class _NoNetwork:
    """Enforced on every run, not just tested once: any attempted network
    call during edgartools parsing raises immediately and loudly. C7-safety
    for this instrument is a property of every invocation, not a one-time
    spike finding taken on faith."""

    def __enter__(self):
        import socket
        self._connect, self._gai = socket.socket.connect, socket.getaddrinfo

        def _blocked(*a, **k):
            raise RuntimeError(
                "oracle_oss: edgartools attempted a network call mid-parse — "
                "this violates the network-free contract this instrument "
                "was built and verified on. Aborting rather than proceeding "
                "on an unverified assumption.")
        socket.socket.connect = _blocked
        socket.getaddrinfo = _blocked
        return self

    def __exit__(self, *exc):
        import socket
        socket.socket.connect, socket.getaddrinfo = self._connect, self._gai


# ------------------------------------------------------------ fixture I/O

def iter_fixtures():
    """(name, path) for the largest non-.md file in each evals/fixtures/ dir
    — same convention evals/oracle.py uses."""
    for d in sorted(FIXTURES_DIR.iterdir()):
        if not d.is_dir():
            continue
        files = [f for f in d.iterdir() if f.is_file() and f.suffix.lower() != ".md"]
        if files:
            yield d.name, max(files, key=lambda f: f.stat().st_size)


def _read_text(path):
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


# ------------------------------------------------------------ normalization

def _normalize(s):
    """Whitespace-collapse, minimum normalization per the task brief: the two
    tools flatten whitespace (line wraps, non-breaking spaces, multiple
    blank lines) differently, and un-normalized diffing would manufacture
    disagreements out of that alone, not out of real content differences."""
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def _content_metrics(repo_text, edgar_text):
    a, b = _normalize(repo_text), _normalize(edgar_text)
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    la, lb = len(a), len(b)
    length_ratio = (min(la, lb) / max(la, lb)) if max(la, lb) else 1.0
    return ratio, length_ratio


# ------------------------------------------------------------ edgartools sections

def _edgar_index(doc):
    """{item_code_upper: Section}. Verified empirically over all 30 HTML/
    iXBRL fixtures: no fixture ever produces two sections with the same
    `.item` value, so no tie-break is exercised in practice — but held-out
    input could, so ties go to the higher-confidence section."""
    index = {}
    for sec in doc.sections.values():
        code = sec.item
        if not code:
            continue
        code = code.upper()
        prior = index.get(code)
        if prior is None or (sec.confidence or 0) > (prior.confidence or 0):
            index[code] = sec
    return index


# ------------------------------------------------------------ per-fixture comparison

NOT_PRESENT_STATUSES = {"missing", "omitted"}


def compare_fixture(name, path, HTMLParser, ParserConfig):
    """One fixture's comparisons, or a dict describing why it was skipped/
    errored instead. Never raises — an edgartools failure IS the finding
    (CLAUDE.md hard rule 4), not something to swallow or fabricate around."""
    result = extract_items(str(path))
    if not result["items"]:
        return {"skip_reason": "doc_level_refusal",
                "doc_status": result["doc_status"]}

    raw_text = _read_text(path)
    try:
        with _NoNetwork():
            doc = HTMLParser(ParserConfig(form="10-K")).parse(raw_text)
    except Exception as e:  # noqa: BLE001 — deliberately broad: any edgartools
        # failure is itself the finding, never fabricated or silently skipped.
        return {"skip_reason": "edgartools_error",
                "error": f"{type(e).__name__}: {e}"}

    edgar_by_code = _edgar_index(doc)
    text = result["normalized_text"]
    comparisons = []
    for item in result["items"]:
        code = item["item"]
        repo_present = item["status"] not in NOT_PRESENT_STATUSES
        repo_text = text[item["start"]:item["end"]] if repo_present else ""
        edgar_sec = edgar_by_code.get(code)
        edgar_present = edgar_sec is not None
        edgar_text = edgar_sec.text() if edgar_present else ""

        row = {
            "fixture": name, "item": code,
            "repo_status": item["status"], "repo_present": repo_present,
            "repo_chars": len(repo_text),
            "edgar_present": edgar_present, "edgar_chars": len(edgar_text),
            "edgar_confidence": getattr(edgar_sec, "confidence", None),
            "edgar_method": getattr(edgar_sec, "detection_method", None),
        }
        if repo_present != edgar_present:
            row["class"] = "presence"
            row["direction"] = ("repo_missing_edgar_found" if edgar_present
                                 else "repo_found_edgar_missing")
            row["repo_excerpt"] = _normalize(repo_text)[:160]
            row["edgar_excerpt"] = _normalize(edgar_text)[:160]
        elif repo_present and edgar_present:
            ratio, length_ratio = _content_metrics(repo_text, edgar_text)
            row["class"] = "content"
            row["similarity"] = round(ratio, 4)
            row["length_ratio"] = round(length_ratio, 4)
            row["repo_excerpt"] = _normalize(repo_text)[:160]
            row["edgar_excerpt"] = _normalize(edgar_text)[:160]
        else:
            row["class"] = "agree_absent"
        comparisons.append(row)
    return {"comparisons": comparisons}


# ------------------------------------------------------------ distribution + cut

def _percentiles(xs, ps):
    if not xs:
        return {p: None for p in ps}
    xs = sorted(xs)
    out = {}
    for p in ps:
        k = (len(xs) - 1) * p
        f, c = int(k), min(int(k) + 1, len(xs) - 1)
        out[p] = xs[f] if f == c else xs[f] + (xs[c] - xs[f]) * (k - f)
    return out


def describe(xs, label):
    if not xs:
        print(f"  {label}: n=0 (no content-comparable items)")
        return {}
    ps = _percentiles(xs, [0, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 1.0])
    mean = sum(xs) / len(xs)
    print(f"  {label}: n={len(xs)} "
          f"min={ps[0]:.4f} p5={ps[.05]:.4f} p10={ps[.10]:.4f} "
          f"p25={ps[.25]:.4f} median={ps[.50]:.4f} p75={ps[.75]:.4f} "
          f"p90={ps[.90]:.4f} p95={ps[.95]:.4f} max={ps[1.0]:.4f} mean={mean:.4f}")
    return {"n": len(xs), "percentiles": {str(p): v for p, v in ps.items()}, "mean": mean}


def choose_cut(ratios):
    """ADR-007/008 precedent: the cut sits at the MIDPOINT OF THE LARGEST GAP
    in the sorted measured distribution, computed fresh every run — never a
    number picked in advance. Returns (cut, (gap_size, lo, hi)) or (None,
    None) if fewer than 2 points exist to form a gap."""
    if len(ratios) < 2:
        return None, None
    xs = sorted(ratios)
    gap, lo, hi = max((xs[i + 1] - xs[i], xs[i], xs[i + 1])
                       for i in range(len(xs) - 1))
    return (lo + hi) / 2, (gap, lo, hi)


# ------------------------------------------------------------ self-check

def self_check():
    """Assert-based proof the non-trivial logic (normalization, similarity/
    length-ratio metrics, gap-based cut selection) behaves as documented,
    without needing edgartools or any fixture. Same `--self-check`
    convention as evals/oracle.py."""
    assert _normalize("Item  7.\xa0 MD&A\n\n") == "Item 7. MD&A"
    ratio, length_ratio = _content_metrics("Item 7. Hello world", "Item 7. Hello world!")
    assert length_ratio == 19 / 20
    assert ratio > 0.9
    # a clean gap between two clusters: cut lands in the empty band, not on either cluster
    cut, (gap, lo, hi) = choose_cut([0.95, 0.97, 1.0, 0.98, 0.10, 0.05])
    assert lo == 0.10 and hi == 0.95 and abs(cut - 0.525) < 1e-9
    assert choose_cut([0.5]) == (None, None)
    ps = _percentiles([1, 2, 3, 4, 5], [0, 0.5, 1.0])
    assert ps[0] == 1 and ps[0.5] == 3 and ps[1.0] == 5
    print("self-check OK")


# ------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", metavar="PATH", help="also write machine-readable results")
    ap.add_argument("--self-check", action="store_true",
                     help="run assert-based checks on the comparison logic and exit")
    args = ap.parse_args()

    if args.self_check:
        self_check()
        return

    HTMLParser, ParserConfig = _load_edgartools()

    skipped_no_coverage = []      # .txt: edgartools has zero coverage, by design
    skipped_refusal = []          # .htm but doc_status failed/unsupported
    skipped_errors = []           # .htm but edgartools raised
    all_comparisons = []

    for name, path in iter_fixtures():
        suffix = path.suffix.lower()
        if suffix in TXT_SUFFIXES:
            skipped_no_coverage.append(name)
            continue
        if suffix not in HTML_SUFFIXES:
            continue
        outcome = compare_fixture(name, path, HTMLParser, ParserConfig)
        if "skip_reason" in outcome:
            if outcome["skip_reason"] == "doc_level_refusal":
                skipped_refusal.append((name, outcome["doc_status"]))
            else:
                skipped_errors.append((name, outcome["error"]))
            continue
        all_comparisons.extend(outcome["comparisons"])

    print("=" * 78)
    print("T11 OSS cross-check oracle (edgartools 5.50.0, HTML/iXBRL stratum)")
    print("=" * 78)

    print(f"\nNO OSS COVERAGE (plain-text era, edgartools returns 0 sections by "
          f"design) — {len(skipped_no_coverage)} fixture(s):")
    for name in skipped_no_coverage:
        print(f"  - {name}")

    print(f"\nEXCLUDED — doc-level refusal, not a silent-failure candidate "
          f"({len(skipped_refusal)} fixture(s)):")
    for name, status in skipped_refusal:
        print(f"  - {name} (doc_status={status})")

    if skipped_errors:
        print(f"\nEDGARTOOLS ERRORS ({len(skipped_errors)} fixture(s)) — the "
              f"error IS the finding, not fabricated around:")
        for name, err in skipped_errors:
            print(f"  - {name}: {err}")

    presence = [c for c in all_comparisons if c["class"] == "presence"]
    content = [c for c in all_comparisons if c["class"] == "content"]
    agree_absent = [c for c in all_comparisons if c["class"] == "agree_absent"]
    ratios = [c["similarity"] for c in content]
    lens = [c["length_ratio"] for c in content]

    n_fixtures = len({c["fixture"] for c in all_comparisons})
    print(f"\nCOVERED: {n_fixtures} HTML/iXBRL fixture(s), "
          f"{len(all_comparisons)} item-comparisons "
          f"({len(presence)} presence-comparable-only, {len(content)} "
          f"both-present/content-comparable, {len(agree_absent)} agree-absent)")

    print("\nDISTRIBUTION over both-present items:")
    sim_stats = describe(ratios, "similarity ratio")
    len_stats = describe(lens, "length ratio (min/max chars)")

    cut, gap_info = choose_cut(ratios)
    if cut is not None:
        gap, lo, hi = gap_info
        print(f"\nCHOSEN CUT: {cut:.4f} (largest gap in the measured "
              f"distribution: {gap:.4f} wide, between {lo:.4f} and {hi:.4f})")
    else:
        print("\nCHOSEN CUT: n/a (fewer than 2 content-comparable items)")

    content_disagreements = [c for c in content if cut is not None and c["similarity"] < cut]

    print(f"\n{'=' * 78}\nRANKED DISAGREEMENTS\n{'=' * 78}")
    print(f"\nClass 1 — STATUS/PRESENCE disagreement "
          f"({len(presence)} found, highest-value class):")
    for c in presence:
        print(f"  {c['fixture']:22s} item {c['item']:3s} "
              f"repo={c['repo_status']:10s}({c['repo_chars']:>6d}c)  "
              f"edgar_present={c['edgar_present']!s:5s}({c['edgar_chars']:>6d}c)  "
              f"[{c['direction']}]")

    print(f"\nClass 2 — CONTENT disagreement below cut "
          f"({len(content_disagreements)} of {len(content)} both-present items):")
    for c in sorted(content_disagreements, key=lambda r: r["similarity"]):
        print(f"  {c['fixture']:22s} item {c['item']:3s} "
              f"similarity={c['similarity']:.4f} length_ratio={c['length_ratio']:.4f} "
              f"repo={c['repo_chars']:>6d}c edgar={c['edgar_chars']:>6d}c")

    # tgt-2002 item 4: T9/ADR-015 recorded ~81% document swallow. Check, don't assume.
    tgt4 = next((c for c in all_comparisons
                 if c["fixture"] == "tgt-2002" and c["item"] == "4"), None)
    print(f"\n{'=' * 78}\nT9/ADR-015 RE-CHECK: tgt-2002 item 4\n{'=' * 78}")
    if tgt4 is None:
        print("  tgt-2002 item 4 not in the comparable set (fixture skipped or "
              "item not in this era's expected set).")
    else:
        print(f"  repo:  status={tgt4['repo_status']} chars={tgt4['repo_chars']}")
        print(f"  edgar: present={tgt4['edgar_present']} chars={tgt4['edgar_chars']}")
        if tgt4["class"] == "content":
            print(f"  similarity={tgt4['similarity']:.4f} "
                  f"length_ratio={tgt4['length_ratio']:.4f}")
        print(f"  repo excerpt:  {tgt4.get('repo_excerpt', '')!r}")
        print(f"  edgar excerpt: {tgt4.get('edgar_excerpt', '')!r}")

    if args.json:
        payload = {
            "tool": "edgartools", "tool_version": "5.50.0",
            "skipped_no_oss_coverage": skipped_no_coverage,
            "skipped_doc_level_refusal": [{"fixture": n, "doc_status": s}
                                           for n, s in skipped_refusal],
            "edgartools_errors": [{"fixture": n, "error": e}
                                   for n, e in skipped_errors],
            "comparisons": all_comparisons,
            "similarity_distribution": sim_stats,
            "length_ratio_distribution": len_stats,
            "chosen_cut": cut,
            "cut_basis": ({"gap": gap_info[0], "lo": gap_info[1], "hi": gap_info[2]}
                          if gap_info else None),
            "tgt_2002_item_4": tgt4,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2, default=str))
        print(f"\nWrote {args.json}")


if __name__ == "__main__":
    main()
