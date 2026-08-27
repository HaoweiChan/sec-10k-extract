"""D16 evidence instrument: the corpus-wide fire/no-fire census for
`internal_pointer_unreached` (ADR-039), and the derivation of its two bands.

Throwaway measurement script, same standing as `d13_span_dump.py` — not a
pipeline stage, not on any gate path. It imports the SHIPPED constants and
regexes from `src.sec10k.validate` / `src.sec10k.segment`, so this census
cannot drift from the implementation: re-running it after any constant move
reprints the truth.

    python3 tasks/reviews/d16_census.py        # committed at d16-census.txt

Per extracted item whose body matches INTERNAL_PTR_RE it prints: body chars,
`meta.coverage`, whether the body names an external document
(EXTERNAL_DOC_RE), whether a warning already carries the item's code, whether
the document escalates (any AMBIGUOUS_CODES warning), and the verdict —
FIRE, or the single prong that excludes it. Then the two band derivations
ADR-039 §c quotes, over exactly the populations it defines.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from evals.oracle import iter_fixtures                              # noqa: E402
from src.sec10k.extract import extract_items                        # noqa: E402
from src.sec10k.segment import EXTERNAL_DOC_RE                      # noqa: E402
from src.sec10k.validate import (AMBIGUOUS_CODES, INTERNAL_PTR_RE,  # noqa: E402
                                 PTR_BODY_MAX, PTR_COVERAGE_MIN)

ROOT = pathlib.Path(__file__).resolve().parents[2]


def census():
    rows, n_docs = [], 0
    for root, label in ((ROOT / "evals" / "fixtures", "dev"),
                        (ROOT / "evals" / "heldout" / "fixtures", "held-out")):
        for name, path in iter_fixtures(root):
            n_docs += 1
            try:
                r = extract_items(str(path))
            except Exception as exc:                    # noqa: BLE001
                rows.append({"fixture": name, "set": label, "error": str(exc)[:80]})
                continue
            text = r.get("normalized_text", "")
            cov = (r.get("meta") or {}).get("coverage")
            doc_esc = any(w["code"] in AMBIGUOUS_CODES
                          for w in r.get("warnings", []))
            # the pre-fire state: which items OTHER codes carry. The census
            # runs on the shipped pipeline, so the new code's own warnings
            # must not count as "already warned" for their own items — that
            # would suppress every fire out of its own census.
            flagged = {w.get("item") for w in r.get("warnings", [])
                       if w.get("item")
                       and w["code"] != "internal_pointer_unreached"}
            fired = {w.get("item") for w in r.get("warnings", [])
                     if w["code"] == "internal_pointer_unreached"}
            for it in r.get("items", []):
                if it.get("status") != "extracted" or it.get("start") is None:
                    continue
                span = text[it["start"]:it["end"]]
                body = span.split("\n", 1)[1] if "\n" in span else ""
                if not INTERNAL_PTR_RE.search(body):
                    continue
                ext = bool(EXTERNAL_DOC_RE.search(body))
                warned = it["item"] in flagged
                # the prongs, in the order validate() applies them; the FIRST
                # excluding prong is reported (one is enough — no ranking)
                if doc_esc:
                    verdict = "no-fire: document escalates (prong 2)"
                elif warned:
                    verdict = "no-fire: item already warned (prong 2)"
                elif ext:
                    verdict = "no-fire: names an external document (prong 1)"
                elif len(body) > PTR_BODY_MAX:
                    verdict = f"no-fire: body {len(body):,} > PTR_BODY_MAX (prong 1)"
                elif cov >= PTR_COVERAGE_MIN:
                    verdict = f"no-fire: coverage {cov} >= PTR_COVERAGE_MIN (prong 3)"
                else:
                    verdict = "FIRE"
                # self-consistency: the census's re-derivation must agree
                # with what the shipped pipeline actually emitted
                assert (verdict == "FIRE") == (it["item"] in fired), \
                    (name, it["item"], verdict, sorted(fired))
                rows.append({"fixture": name, "set": label, "item": it["item"],
                             "body": len(body), "cov": cov, "ext": ext,
                             "warned": warned, "doc_esc": doc_esc,
                             "verdict": verdict})
    return rows, n_docs


def main():
    rows, n_docs = census()
    errs = [r for r in rows if "error" in r]
    rows = [r for r in rows if "error" not in r]
    print(f"constants under census: PTR_BODY_MAX={PTR_BODY_MAX}  "
          f"PTR_COVERAGE_MIN={PTR_COVERAGE_MIN}\n"
          f"INTERNAL_PTR_RE={INTERNAL_PTR_RE.pattern!r}\n"
          f"EXTERNAL_DOC_RE={EXTERNAL_DOC_RE.pattern!r}\n")
    print(f"{n_docs} documents scanned (dev + held-out); "
          f"{len(rows)} extracted spans have a body matching INTERNAL_PTR_RE\n")
    hdr = (f"{'set':<9}{'fixture':<24}{'item':>5}{'body':>8}{'cov':>8}"
           f"{'ext':>5}{'warned':>8}{'doc_esc':>9}  verdict")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(rows, key=lambda r: (r["set"], r["fixture"], r["item"])):
        print(f"{r['set']:<9}{r['fixture']:<24}{r['item']:>5}{r['body']:>8}"
              f"{r['cov']:>8}{str(r['ext']):>5}{str(r['warned']):>8}"
              f"{str(r['doc_esc']):>9}  {r['verdict']}")
    for e in errs:
        print(f"ERROR {e['fixture']}: {e['error']}")

    fires = [r for r in rows if r["verdict"] == "FIRE"]
    print(f"\nFIRES ({len(fires)}):")
    for r in fires:
        print(f"  {r['set']} {r['fixture']} item {r['item']}  "
              f"body={r['body']}  cov={r['cov']}")

    print("\nexclusion tallies:")
    tally = {}
    for r in rows:
        k = r["verdict"] if r["verdict"] == "FIRE" else r["verdict"].split("(")[0].strip()
        tally[k] = tally.get(k, 0) + 1
    for k, v in sorted(tally.items()):
        print(f"  {v:>4}  {k}")

    # --- band derivations, over ADR-039 SS-c's own populations ------------
    print("\nPTR_BODY_MAX band — items passing every prong but the body cap")
    pop = sorted((r for r in rows
                  if not (r["doc_esc"] or r["warned"] or r["ext"])
                  and r["cov"] < PTR_COVERAGE_MIN),
                 key=lambda r: r["body"])
    for r in pop:
        side = "FIRE side" if r["body"] <= PTR_BODY_MAX else "no-fire side"
        print(f"  {r['body']:>8,}  {r['fixture']:<20} item {r['item']:<4} {side}")
    lo = max((r["body"] for r in pop if r["body"] <= PTR_BODY_MAX), default=None)
    hi = min((r["body"] for r in pop if r["body"] > PTR_BODY_MAX), default=None)
    print(f"  empty band ({lo}, {hi}); midpoint "
          f"{(lo + hi) / 2 if lo and hi else '?'} -> {PTR_BODY_MAX}")

    print("\nPTR_COVERAGE_MIN band — documents with a prong-1+2-passing item")
    docs = {}
    for r in rows:
        if not (r["doc_esc"] or r["warned"] or r["ext"]) and r["body"] <= PTR_BODY_MAX:
            docs.setdefault((r["set"], r["fixture"], r["cov"]), []).append(r["item"])
    for (label, name, cov), items in sorted(docs.items(), key=lambda x: x[0][2]):
        side = "FIRE side" if cov < PTR_COVERAGE_MIN else "no-fire side"
        print(f"  {cov:>8}  {label:<9} {name:<20} items {','.join(items):<12} {side}")
    covs = sorted(c for (_, _, c) in docs)
    lo = max((c for c in covs if c < PTR_COVERAGE_MIN), default=None)
    hi = min((c for c in covs if c >= PTR_COVERAGE_MIN), default=None)
    print(f"  empty band ({lo}, {hi}); midpoint "
          f"{round((lo + hi) / 2, 4) if lo and hi else '?'} -> {PTR_COVERAGE_MIN}")


if __name__ == "__main__":
    main()
