#!/usr/bin/env python3
"""Blind reader for authoring HELD-OUT labels — imports NOTHING from src/.

`evals/heldout/README.md` requires a held-out case's labels to be written
before the filing is ever put through this repo's pipeline. That is only
meaningful if the author read the filing with a DIFFERENT instrument, so this
one is deliberately naive and deliberately independent: a regex tag strip, an
entity table with the handful of entities that matter, and counting. If it
disagrees with `src/sec10k/normalize.py` about something, that disagreement is
information — it is not a bug to be fixed by importing the real normalizer.

    python3 tasks/reviews/heldout_blind_scan.py <file.htm> [anchor ...]

Prints the cover-page facts, every `Item N` heading it can see with its line,
and an occurrence count for each anchor given on the command line (the count
is what `provenance` must record, per the case-authoring skill step 4).
"""
import html
import re
import sys

TAG = re.compile(r"<[^>]+>")
SCRIPT = re.compile(r"(?is)<(script|style)\b.*?</\1>")
WS = re.compile(r"[ \t ​]+")
BLANK = re.compile(r"\n{3,}")

# `Item 7A.` / `ITEM 1B` / `Item 9C —`. Deliberately looser than the
# extractor's: this instrument is for READING, so a false positive costs the
# author a glance and a false negative costs the case its label.
ITEM = re.compile(r"(?im)^[ \t]*(item)[ \t ]*(\d{1,2})[ \t]*([A-D])?[ \t]*[.:—–-]?[ \t]*(.{0,70})")
FY = re.compile(r"(?i)fiscal year ended[ \t]+([A-Za-z]+ \d{1,2},? \d{4})")
FORM = re.compile(r"(?im)^[ \t]*form[ \t]+(10-K(?:405|SB)?|NT[ \t]*10-K|10-Q)\b")


def strip(raw):
    t = SCRIPT.sub(" ", raw)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h[1-6]>", "\n", t)
    t = TAG.sub(" ", t)
    t = html.unescape(t)
    t = WS.sub(" ", t)
    t = "\n".join(l.strip() for l in t.split("\n"))
    return BLANK.sub("\n\n", t)


def main(path, anchors):
    raw = open(path, encoding="utf-8", errors="replace").read()
    text = strip(raw)
    print(f"# {path}")
    print(f"  raw bytes         {len(raw):,}")
    print(f"  stripped chars    {len(text):,}")
    print(f"  form line         {[m.group(1) for m in FORM.finditer(text)][:3]}")
    print(f"  fiscal year ended {sorted({m.group(1) for m in FY.finditer(text)})[:3]}")
    for probe in ("NT 10-K", "Notification of Late Filing", "General Instruction J",
                  "Cross-Reference Index", "incorporated by reference",
                  "Proxy Statement", "Form 10-K Summary"):
        print(f"  {probe!r:38} {text.count(probe)}")
    seen = {}
    for m in ITEM.finditer(text):
        code = m.group(2) + (m.group(3) or "").upper()
        seen.setdefault(code, []).append(m.group(4).strip()[:60])
    print(f"\n  item headings visible: {len(seen)} distinct codes")
    for code in sorted(seen, key=lambda c: (int(re.sub(r'\D', '', c) or 0), c)):
        hits = seen[code]
        print(f"    {code:>3}  x{len(hits)}  {hits[0]!r}")
    if anchors:
        print("\n  anchor counts (raw / stripped):")
        for a in anchors:
            print(f"    {a[:64]!r:70} {raw.count(a):>4} / {text.count(a):>4}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
