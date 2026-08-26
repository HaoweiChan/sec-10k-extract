"""D9 evidence instrument: corpus prevalence of the two classes D9 rules on.

Throwaway measurement script, not a pipeline stage and not on any gate path
(CLAUDE.md hard rule: adding a permanent metric for a one-off count is the
speculative instrument this repo argues against).

    python3 tasks/reviews/d9_class_scan.py

Class A -- internal pointer to a paginated section (ADR-019 section e).
  Shape: the item HAS a heading and a span, status `extracted`, but the body
  is a short sentence naming a page/index location INSIDE the same document,
  while the real content sits outside every span.
  Detector: status == extracted AND body (span minus heading line, the same
  slice src/sec10k/extract.py:111 hands classify) matches PAGE_PTR and is
  shorter than BODY_MAX. Both knobs are printed so a reader can move them.

Class B -- combined multi-item heading (ADR-020 section c row 7).
  Shape: one heading names several item codes at once, so every per-code
  heading path in segment.py misses and all the named codes go `missing`.
  Detector: MULTI_CODE over normalized_text, hits printed WITH context so a
  human adjudicates each -- a regex cannot tell a body heading from a cover
  sentence or a proxy cross-reference, and that distinction is the whole
  question for this class.

Prints one row per fixture plus corpus totals. Real EDGAR filings and
SELF-CREATED (synthetic) fixtures are separated, as are dev and held-out.
"""
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from evals.oracle import iter_fixtures                    # noqa: E402
from src.sec10k.extract import extract_items              # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "evals" / "fixtures"
HELD = ROOT / "evals" / "heldout" / "fixtures"

BODY_MAX = 700           # chars; cvx-2015's are 280/189, intc-2025's 20..226
PAGE_PTR = re.compile(
    r"(?i)\b(?:on\s+)?pages?\s+(?:FS-)?\d"      # "on page FS-1", "Pages 37-51"
    r"|\bFS-\d"                                  # bare FS-page reference
    r"|\bsee\s+index\b"                          # ge-1994 "See index under item 14."
)
MULTI_CODE = re.compile(
    r"(?i)\bitems\s*\.?\s*(?:&nbsp;|\s)*\d{1,2}[A-C]?"
    r"(?:\s*,?\s*(?:&nbsp;|\s)*(?:and\s+)?\d{1,2}[A-C]?){1,6}"
)


def synthetic_names():
    """Fixture names the fixtures README marks SELF-CREATED."""
    rows = (ROOT / "evals" / "fixtures" / "README.md").read_text().splitlines()
    out = set()
    for line in rows:
        if line.startswith("|") and "SELF-CREATED" in line:
            m = re.search(r"`([^/`]+)/", line)
            if m:
                out.add(m.group(1))
    return out


def scan(root, label, synth):
    rows = []
    for name, path in iter_fixtures(root):
        try:
            r = extract_items(str(path))
        except Exception as exc:                          # noqa: BLE001
            rows.append((name, label, "ERROR", str(exc)[:60], 0, 0, 0, 0, []))
            continue
        text = r.get("normalized_text", "")
        items = r.get("items", [])
        a_hits, missing = [], []
        for it in items:
            s, e = it.get("start"), it.get("end")
            if it.get("status") == "missing":
                missing.append(it["item"])
            if s is None or e is None or it.get("status") != "extracted":
                continue
            span = text[s:e]
            body = span.split("\n", 1)[1] if "\n" in span else ""
            if len(span) < BODY_MAX and PAGE_PTR.search(body):
                a_hits.append((it["item"], e - s))
        b_hits = [(m.start(), m.group(0)[:60].replace("\n", " "))
                  for m in MULTI_CODE.finditer(text)]
        rows.append((name, label, r.get("doc_status"), "", len(items),
                     len(text), len(a_hits), len(b_hits), a_hits, b_hits,
                     missing, name in synth))
    return rows


def main():
    synth = synthetic_names()
    rows = scan(DEV, "dev", synth) + scan(HELD, "held-out", synth)
    print(f"knobs: BODY_MAX={BODY_MAX}  PAGE_PTR={PAGE_PTR.pattern!r}")
    print(f"synthetic fixtures per README: {sorted(synth)}\n")
    hdr = f"{'fixture':<24}{'set':<10}{'doc_status':<22}{'items':>6}{'A':>4}{'B':>4}{'missing':>9}  kind"
    print(hdr)
    print("-" * len(hdr))
    tot = {"dev": [0, 0], "held-out": [0, 0]}
    for r in rows:
        (name, label, ds, err, n_items, n_chars, n_a, n_b, a_hits, b_hits,
         missing, is_syn) = r
        kind = "synthetic" if is_syn else "real EDGAR"
        tot[label][0] += 1
        tot[label][1] += n_items
        print(f"{name:<24}{label:<10}{str(ds):<22}{n_items:>6}{n_a:>4}{n_b:>4}"
              f"{len(missing):>9}  {kind}")
    print()
    for label in ("dev", "held-out"):
        print(f"{label}: {tot[label][0]} fixtures, {tot[label][1]} items")
    print(f"total: {sum(t[0] for t in tot.values())} fixtures, "
          f"{sum(t[1] for t in tot.values())} items\n")

    print("=== CLASS A hits (item, span chars) ===")
    for r in rows:
        if r[6]:
            kind = "synthetic" if r[11] else "real EDGAR"
            lost = sum(1 for _ in r[8])
            print(f"  {r[0]} ({r[1]}, {kind}): {lost} items -> {r[8]}")
    print("\n=== CLASS B regex hits (offset, text) -- ADJUDICATE BY HAND ===")
    for r in rows:
        if r[7]:
            kind = "synthetic" if r[11] else "real EDGAR"
            print(f"  {r[0]} ({r[1]}, {kind}), missing={r[10]}")
            for off, txt in r[9]:
                print(f"      @{off} {txt!r}")


if __name__ == "__main__":
    main()
