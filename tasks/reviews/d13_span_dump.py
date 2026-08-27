"""D13 evidence instrument: the verbatim span of every item D13 adjudicates,
and whether the content that span POINTS AT lands inside any span.

Throwaway measurement script, same standing as `d9_class_scan.py` — not a
pipeline stage, not on any gate path, imports nothing from `src/` but the
public `extract_items`. It exists so ADR-038 quotes spans and prints figures
it DERIVED rather than retyped (the `prompts/` rule added 2026-08-27 after a
cost figure was wrong twice from retyped inputs).

    python3 tasks/reviews/d13_span_dump.py                  # human dump
    python3 tasks/reviews/d13_span_dump.py --json           # machine dump
    python3 tasks/reviews/d13_span_dump.py --table          # verdict inputs
    python3 tasks/reviews/d13_span_dump.py --auditor-input  # blind sample

Per item it reports, from one DEFAULT-FLAG `extract_items` run per filing:

  * status / confidence / method / review_required / heading_text
  * span chars, and the body (span minus the heading line) VERBATIM
  * for each TARGET the body names, a hand-chosen anchor for the content at
    that target, and WHERE that anchor's matches land: a count per owning
    item plus a count outside every span
  * per document: normalized chars, chars inside some span, `meta.coverage`,
    and every contiguous region outside every span with its size

**The script does not decide "reached".** A regex cannot tell the content
itself from a cross-reference TO it — `d9_class_scan.py` makes the same
concession for its Class B hits and prints them for a human. So the anchor
distribution and the outside-regions table are printed as evidence and
adjudicated by hand in ADR-038. The anchors are hand-chosen and printed with
the output: a reader who thinks one names the wrong content can move it.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.sec10k.extract import extract_items            # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]

# fixture -> item -> [(target as the body names it, anchor for its content)]
# An empty target list means the body names no location to resolve.
TARGETS = {
    "evals/fixtures/cvx-2015": {
        "2":  [("page 3 under Item 1. Business", r"(?i)table i\b"),
               ("Tables I–VII, pages FS-61..FS-71", r"FS-61\b"),
               ("Note 16, page FS-41", r"(?i)properties, plant and equipment")],
        "6":  [("page FS-60", r"FS-60\b")],
        "7":  [("index on page FS-1", r"(?i)consolidated statement of income")],
        "7A": [("page FS-15", r"FS-15\b"), ("page FS-35", r"FS-35\b")],
        "8":  [("index on page FS-1", r"(?i)consolidated statement of income")],
    },
    "evals/fixtures/ge-1994": {
        "8":  [("index under item 14", r"(?i)statement of financial position")],
    },
    "evals/fixtures/jpm-2024": {
        "1C": [("pages 153–156, Operational Risk Management",
                r"(?i)operational risk management")],
        "7":  [("pages 52–167, MD&A", r"(?i)consolidated statements of income")],
        "7A": [("pages 141–149, Market Risk Management",
                r"(?i)market risk management")],
        "8":  [("pages 169–321, financial statements",
                r"(?i)consolidated statements of income")],
    },
    "evals/fixtures/bac-2006": {
        "3":  [("Note 13, page 137", r"Litigation and Regulatory Matters")],
        "6":  [("Table 5 in the MD&A, page 21", r"(?i)consolidated statement of income")],
        "7A": [("Market Risk Management in the MD&A, page 72",
                r"Market Risk Management")],
    },
    "evals/fixtures/spatz-2014": {
        "8":  [("pages 15 through 22 of this report",
                r"(?i)report of independent registered public accounting firm")],
    },
    "evals/fixtures/nvda-2024": {
        "8":  [("our Consolidated Financial Statements, in this Form 10-K",
                r"(?i)consolidated statements of income")],
    },
    "evals/fixtures/xom-2021": {
        "7":  [("MD&A section of the Financial Section",
                r"(?i)consolidated statement of income")],
        "7A": [("“Market Risks” in the Financial Section", r"(?i)market risks")],
        "8":  [("financial statements in the Financial Section",
                r"(?i)report of independent registered public accounting firm")],
        "15": [("Table of Contents of the Financial Section",
                r"(?i)consolidated statement of income")],
    },
    "evals/heldout/fixtures/mrk-1995": {
        "5":  [("pages 37 and 51 of the 1995 Annual Report to stockholders", None)],
        "7":  [("pages 28 through 37 of the 1995 Annual Report to stockholders", None)],
    },
}

# The blind sample handed to the extraction-auditor: chosen to straddle every
# distinction the ruling turns on WITHOUT naming any of them.
AUDITOR_SAMPLE = [
    ("cvx-2015", "2"), ("cvx-2015", "6"), ("cvx-2015", "7A"), ("cvx-2015", "8"),
    ("bac-2006", "3"), ("bac-2006", "6"),
    ("spatz-2014", "8"), ("jpm-2024", "7"), ("mrk-1995", "5"),
]


def fixture_file(d):
    """The single filing in a fixture dir (evals/oracle.py's own rule)."""
    files = [p for p in sorted(d.iterdir()) if p.is_file() and p.suffix != ".md"]
    return files[0] if len(files) == 1 else None


def collect():
    out = []
    for rel, per_item in TARGETS.items():
        d = ROOT / rel
        f = fixture_file(d)
        if f is None:
            raise SystemExit(f"no single filing in {rel}")
        res = extract_items(str(f))
        text = res.get("normalized_text", "")
        spans = sorted((i["start"], i["end"], i["item"]) for i in res["items"]
                       if i.get("start") is not None)
        in_span = sum(e - s for s, e, _ in spans)
        n = len(text)
        outside = []
        cur = 0
        for s0, e0, _ in spans:
            if s0 > cur:
                outside.append((cur, s0, s0 - cur))
            cur = max(cur, e0)
        if cur < n:
            outside.append((cur, n, n - cur))

        def owner(off):
            return next((c for s, e, c in spans if s <= off < e), None)

        by_code = {i["item"]: i for i in res["items"]}
        for code, targets in per_item.items():
            it = by_code.get(code)
            if it is None:
                raise SystemExit(f"{d.name}: no item {code} in output")
            s, e = it.get("start"), it.get("end")
            span = text[s:e] if s is not None else ""
            body = span.split("\n", 1)[1] if "\n" in span else ""
            tgt = []
            for label, anchor in targets:
                if anchor is None:                  # target is another document
                    tgt.append({"target": label, "anchor": None,
                                "resolvable_here": False, "hits": None,
                                "by_owner": {}, "hits_outside": None,
                                "offsets": []})
                    continue
                hits = [m.start() for m in re.finditer(anchor, text)]
                # matches inside the pointing item's OWN span are the pointer
                # sentence itself, not the content it names — excluded.
                other = [(h, owner(h)) for h in hits if owner(h) != code]
                by_owner = {}
                for _, o in other:
                    if o:
                        by_owner[o] = by_owner.get(o, 0) + 1
                tgt.append({
                    "target": label, "anchor": anchor,
                    "resolvable_here": True,
                    "hits": len(hits),
                    "by_owner": dict(sorted(by_owner.items())),
                    "hits_outside": sum(1 for _, o in other if o is None),
                    "offsets": [h for h, _ in other][:20],
                })
            out.append({
                "fixture": d.name, "file": f.name, "item": code,
                "status": it.get("status"), "confidence": it.get("confidence"),
                "method": it.get("method"),
                "review_required": it.get("review_required"),
                "heading_text": it.get("heading_text"),
                "start": s, "end": e,
                "span_chars": (e - s) if s is not None else None,
                "span": span, "body": body,
                "targets": tgt,
                "doc_status": res.get("doc_status"),
                "doc_warnings": [(w["code"], w.get("item")) for w in res["warnings"]],
                "doc_norm_chars": n, "doc_in_span_chars": in_span,
                "doc_coverage": res["meta"].get("coverage"),
                "doc_outside_span_chars": n - in_span,
                "doc_outside_regions": outside,
            })
    return out


def dump(rows):
    print("anchors are hand-chosen and movable; each names the CONTENT the "
          "item's body points at\n")
    seen = set()
    for r in rows:
        if r["fixture"] not in seen:
            seen.add(r["fixture"])
            print(f"\n########## {r['fixture']}/{r['file']}  "
                  f"doc_status={r['doc_status']}  warnings={r['doc_warnings']}")
            print(f"           norm_chars={r['doc_norm_chars']}  "
                  f"in_spans={r['doc_in_span_chars']}  "
                  f"meta.coverage={r['doc_coverage']}  "
                  f"outside_every_span={r['doc_outside_span_chars']}")
            print(f"           regions outside every span "
                  f"[start,end,chars]: {r['doc_outside_regions']}")
        print(f"\n--- item {r['item']}  {r['status']}  conf={r['confidence']}  "
              f"review_required={r['review_required']}  "
              f"span=[{r['start']},{r['end']}) {r['span_chars']} chars")
        print(f"    heading: {r['heading_text']!r}")
        print(f"    body:    {r['body']!r}")
        for t in r["targets"]:
            if not t["resolvable_here"]:
                print(f"    target {t['target']!r} -> NOT IN THIS DOCUMENT")
                continue
            print(f"    target {t['target']!r} anchor={t['anchor']!r}\n"
                  f"        matches={t['hits']}  by owning item={t['by_owner']}"
                  f"  outside every span={t['hits_outside']}\n"
                  f"        offsets(<=20, excl. this item's own span)="
                  f"{t['offsets']}")


def table(rows):
    hdr = (f"{'fixture':<12}{'item':>5}{'chars':>7}{'conf':>6}{'rr':>7}"
           f"{'doc_status':<22}{'cov':>8}{'tail_chars':>11}  "
           f"anchor matches per target (by owning item | outside)")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        tail = r["doc_outside_regions"][-1][2] if r["doc_outside_regions"] else 0
        parts = []
        for t in r["targets"]:
            if not t["resolvable_here"]:
                parts.append(f"{t['target'][:30]}=EXTERNAL-DOCUMENT")
            else:
                parts.append(f"{t['target'][:30]}={t['by_owner']}|out={t['hits_outside']}")
        print(f"{r['fixture']:<12}{r['item']:>5}{r['span_chars']:>7}"
              f"{r['confidence']:>6}{str(r['review_required']):>7}"
              f"{r['doc_status']:<22}{r['doc_coverage']:>8}{tail:>11}  "
              + "; ".join(parts))


def auditor_input(rows):
    idx = {(r["fixture"], r["item"]): r for r in rows}
    print("Each block below is one item as the pipeline published it, with the "
          "item's span text verbatim.\n")
    for key in AUDITOR_SAMPLE:
        r = idx[key]
        print("=" * 72)
        print(f"FILING {r['fixture']}  ({r['file']})   ITEM {r['item']}")
        print(f"  document: doc_status={r['doc_status']}  "
              f"meta.coverage={r['doc_coverage']}  "
              f"normalized chars={r['doc_norm_chars']}  "
              f"chars inside some item span={r['doc_in_span_chars']}")
        print(f"  document warnings (code, item): {r['doc_warnings']}")
        print(f"  item: status={r['status']}  confidence={r['confidence']}  "
              f"review_required={r['review_required']}  "
              f"method={r['method']}")
        print(f"  item span: [{r['start']},{r['end']}) = {r['span_chars']} chars")
        print(f"  span text VERBATIM:\n{r['span']!r}")
        print()


def main():
    rows = collect()
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=2))
    elif "--table" in sys.argv:
        table(rows)
    elif "--auditor-input" in sys.argv:
        auditor_input(rows)
    else:
        dump(rows)


if __name__ == "__main__":
    main()
