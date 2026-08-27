#!/usr/bin/env python3
"""D11's router sensor, measured on the DEV corpus only.

Re-derives — rather than cites — the two D8 signals ADR-035 shipped, because
D11's whole cost argument rests on how often they fire:

  * `low_item_coverage`  (doc-level, escalating, ADR-035 §d)
  * `item_span_near_empty` (item-level, non-escalating, ADR-035 §c)

For every filing under `evals/fixtures` it prints: normalized chars, published
`meta.coverage`, `doc_status`, which of the two codes fired, and — for every
`item_span_near_empty` hit — the item's WHOLE span, so the "is this a pointer
or a stub?" adjudication is a thing a reader checks rather than believes.

Held-out is NOT read. D11 builds against dev proxies only
(`evals/heldout/README.md` burn rule); the held-out figures this scan does not
produce are the ones ADR-035 §b4 already published.

    python3 tasks/reviews/d11_trigger_scan.py           # census
    python3 tasks/reviews/d11_trigger_scan.py --rates   # census + the rates

Deterministic, offline, $0 — it is the extractor and nothing else.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from src.sec10k.extract import extract_items          # noqa: E402
from src.sec10k.validate import COVERAGE_MIN, SPAN_FLOOR, SUBSTANCE_ITEMS  # noqa: E402

FIXTURES = os.path.join(ROOT, "evals", "fixtures")
# `evals/fixtures/repo_hygiene/` holds mutated COPIES OF THE INSPECTOR — HTML
# and Python files that exist to prove a repo_hygiene check catches its own
# defect. They are not filings, and feeding them to `extract_items` produces a
# refusal, not a document. `evals/snapshot.py` sweeps them anyway (it is a
# byte-identity harness and does not care), which is why its file count is 58
# and this scan's document count is not.
NOT_FILINGS = {"repo_hygiene"}
# self-created filings — derivatives and hand-built shapes. From
# `evals/fixtures/README.md`, which is the provenance of record. Used ONLY to
# split the published rate two ways, never to drop a document from the census.
SYNTHETIC = {
    "amended-cover-2021", "caps-cover-2016", "comma-cover-2016",
    "fy2021-item9c", "heading-unnumbered", "ibr-pointer-first",
    "ibr-security-holders", "interior-span-dominates", "items-stripped",
    "malformed-html", "spaced-letter-heading", "spans-transposed",
    "toc-titled", "truncated-download", "xref-index-collapse",
}


def documents():
    for name in sorted(os.listdir(FIXTURES)):
        sub = os.path.join(FIXTURES, name)
        if not os.path.isdir(sub) or name in NOT_FILINGS:
            continue
        for f in sorted(os.listdir(sub)):
            p = os.path.join(sub, f)
            if os.path.isfile(p) and not f.endswith(".md"):
                yield name, p


def scan():
    rows = []
    for name, path in documents():
        r = extract_items(path)
        codes = [w["code"] for w in r["warnings"]]
        near = [w["item"] for w in r["warnings"]
                if w["code"] == "item_span_near_empty"]
        spans = {}
        for i in r["items"]:
            if i["item"] in near and i.get("start") is not None:
                spans[i["item"]] = r["normalized_text"][i["start"]:i["end"]]
        rows.append({
            "fixture": name, "file": os.path.basename(path),
            "chars": len(r["normalized_text"]),
            "coverage": r["meta"].get("coverage"),
            "doc_status": r["doc_status"],
            "low_item_coverage": "low_item_coverage" in codes,
            "near_empty_items": near,
            "near_empty_spans": spans,
            # the three substance items' span lengths, whether or not they fired
            "substance": {i["item"]: (i["end"] - i["start"])
                          for i in r["items"]
                          if i["item"] in SUBSTANCE_ITEMS
                          and i.get("start") is not None},
        })
    return rows


def main():
    rows = scan()
    print(f"# D11 trigger scan — {len(rows)} dev documents, "
          f"SPAN_FLOOR={SPAN_FLOOR}, COVERAGE_MIN={COVERAGE_MIN}\n")
    print(f"{'fixture':34} {'chars':>9} {'cov':>7} {'doc_status':22} "
          f"{'lowcov':>6}  near_empty")
    for r in rows:
        cov = "—" if r["coverage"] is None else f"{r['coverage']:.4f}"
        print(f"{r['fixture'][:34]:34} {r['chars']:>9} {cov:>7} "
              f"{r['doc_status']:22} {'FIRE' if r['low_item_coverage'] else '':>6}  "
              f"{','.join(r['near_empty_items']) or '—'}")

    print("\n## every item_span_near_empty hit, span in full — adjudicate here")
    hits = 0
    for r in rows:
        for code, span in sorted(r["near_empty_spans"].items()):
            hits += 1
            body = " ".join(span.split())
            print(f"\n[{r['fixture']} · item {code} · {len(span)} chars]\n  {body}")
    print(f"\n{hits} item-level hits total")

    if "--rates" in sys.argv:
        n = len(rows)
        real = [r for r in rows if r["fixture"] not in SYNTHETIC]
        spanned = [r for r in rows if r["coverage"] is not None]
        lowcov = [r for r in rows if r["low_item_coverage"]]
        near = [r for r in rows if r["near_empty_items"]]
        either = [r for r in rows if r["low_item_coverage"] or r["near_empty_items"]]
        rate = lambda k, d: f"{len(k)}/{len(d)} = {len(k) / len(d):.4f}"  # noqa: E731
        print("\n## escalation rates over the dev corpus")
        print(f"  filing documents                             {n}"
              f"  ({len(real)} real EDGAR, {n - len(real)} self-created)")
        print(f"  non-refusal (items published)                {len(spanned)}")
        print(f"  low_item_coverage fires   all                {rate(lowcov, rows)}"
              f"  -> {[r['fixture'] for r in lowcov]}")
        print(f"                            real filings only  "
              f"{rate([r for r in lowcov if r['fixture'] not in SYNTHETIC], real)}")
        print(f"                            non-refusal only   {rate(lowcov, spanned)}")
        print(f"  item_span_near_empty      all                {rate(near, rows)}")
        print(f"                            real filings only  "
              f"{rate([r for r in near if r['fixture'] not in SYNTHETIC], real)}")
        print(f"  either code               all                {rate(either, rows)}")
        print(f"  item-level hits                              {hits}")
        print("\n  fixtures with item_span_near_empty: "
              + ", ".join(f"{r['fixture']}({','.join(r['near_empty_items'])})"
                          for r in near))
        # the scope question the ADR must rule on: is any committed dev filing
        # text-less (the scanned / image-only class)? A text-less input dies at
        # `normalization_collapse` BEFORE any item exists, so it can never
        # reach either trigger code — that structural fact, not a preference,
        # is what the scope ruling turns on.
        textless = [r for r in rows if r["coverage"] is None]
        print(f"\n  refused before any item exists               {len(textless)}"
              f"  -> {[(r['fixture'], r['doc_status']) for r in textless]}")

        # RECALL needs the misses, and a miss can only live just above a
        # threshold — so both near-miss bands are printed rather than asserted
        # empty. Anything listed here is a candidate the sensor did NOT flag.
        print("\n## near-miss band 1 — doc coverage in [COVERAGE_MIN, 0.35): "
              "would a small nudge have caught a collapse?")
        for r in sorted((r for r in spanned if r["coverage"] < 0.35),
                        key=lambda r: r["coverage"]):
            print(f"  {r['coverage']:.4f}  {r['fixture']:24} "
                  f"{'FIRED' if r['low_item_coverage'] else 'not flagged'}")
        print("\n## near-miss band 2 — item 1/7/8 spans in [SPAN_FLOOR, 4000), "
              "the shortest spans the floor let through")
        band = sorted(((n, r["fixture"], code)
                       for r in rows for code, n in r["substance"].items()
                       if SPAN_FLOOR <= n < 4000))
        for n, fixture, code in band:
            print(f"  {n:>6}  {fixture:24} item {code}")
        print(f"  ({len(band)} spans; each must be adjudicated substantive for "
              "recall to be 1.000)")


if __name__ == "__main__":
    main()
