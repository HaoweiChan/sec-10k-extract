"""Default-flag envelope snapshot — the re-runnable half of an "this changed
nothing" claim (ADR-026 §d, ADR-029 §d, ADR-032 §d, ADR-033 §d).

An opt-in annotation is only honest if the DEFAULT output is byte-identical
before and after it. Run this against two trees and compare:

    python3 evals/snapshot.py <tree-root> <out.json>
    cmp before.json after.json

It extracts every fixture under `<tree>/evals/fixtures` and
`<tree>/evals/heldout/fixtures` with `extract_items(path)` — default flags,
nothing else — and records only what the contract publishes: the normalized
text's sha256 (not the text, so the file stays small), `norm_chars`,
`doc_status`, `warnings`, the sorted envelope key list (so a new key is a
difference), and every item's identity, status, offsets, confidence, method
and heading. Timings, cost and trace are excluded: they legitimately vary run
to run, exactly as the adapter's DETERMINISM_FIELDS excludes them.

Self-check: python3 evals/snapshot.py --self-check
"""
import hashlib
import json
import os
import sys

FIELDS = ("item", "status", "start", "end", "confidence", "method", "heading_text")


def corpus(root, rel):
    """{"<fixture>/<file>": digest-dict} for every filing under `rel`."""
    out = {}
    d = os.path.join(root, rel)
    if not os.path.isdir(d):
        return out
    from src.sec10k.extract import extract_items
    for name in sorted(os.listdir(d)):
        sub = os.path.join(d, name)
        if not os.path.isdir(sub):
            continue
        for f in sorted(os.listdir(sub)):
            p = os.path.join(sub, f)
            if not os.path.isfile(p) or f.endswith(".md"):
                continue
            r = extract_items(p)                      # DEFAULT FLAGS
            out[f"{name}/{f}"] = {
                "sha": hashlib.sha256(r["normalized_text"].encode()).hexdigest(),
                "norm_chars": r["meta"].get("norm_chars"),
                "doc_status": r["doc_status"],
                "warnings": r["warnings"],
                "keys": sorted(r),
                "items": [{k: i.get(k) for k in FIELDS} for i in r["items"]],
            }
    return out


def snapshot(root):
    snap = {}
    for label, rel in (("dev", "evals/fixtures"),
                       ("heldout", "evals/heldout/fixtures")):
        snap[label] = corpus(root, rel)
        blob = json.dumps(snap[label], sort_keys=True, ensure_ascii=False).encode()
        print(f"[snapshot] {label}: {len(snap[label])} files  "
              f"sha256={hashlib.sha256(blob).hexdigest()}")
    return snap


def _demo():
    """The property that makes the comparison meaningful: an added envelope
    key is a DIFFERENCE, and a timing is not."""
    a = {"normalized_text": "abc", "doc_status": "success", "warnings": [],
         "meta": {"norm_chars": 3}, "items": [], "timings": {"total_ms": 1.0}}
    b = {**a, "timings": {"total_ms": 999.0}}
    c = {**a, "images": []}
    dig = lambda r: {"sha": hashlib.sha256(r["normalized_text"].encode()).hexdigest(),  # noqa: E731
                     "norm_chars": r["meta"].get("norm_chars"),
                     "doc_status": r["doc_status"], "warnings": r["warnings"],
                     "keys": sorted(r),
                     "items": [{k: i.get(k) for k in FIELDS} for i in r["items"]]}
    assert dig(a) == dig(b), "a timing must not count as a difference"
    assert dig(a) != dig(c), "an added envelope key MUST count as a difference"
    print("[snapshot self-check] ok")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        _demo()
    else:
        root = os.path.abspath(sys.argv[1])
        sys.path.insert(0, root)
        json.dump(snapshot(root), open(sys.argv[2], "w"),
                  sort_keys=True, ensure_ascii=False)
