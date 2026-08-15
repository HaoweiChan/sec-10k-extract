"""Eval adapter for sec10k — owns the check vocabulary and item registry.

Case shape:
    "input":  {"path": "evals/fixtures/<name>/<file>"}
    "expect": {"checks": [{"type": ..., ...}, ...]}
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# item -> part. Union of modern + legacy codes; era validity is a case concern
# (an adversarial case asserts item_absent for era-invalid codes).
CANONICAL = {
    "1": "I", "1A": "I", "1B": "I", "1C": "I", "2": "I", "3": "I", "4": "I",
    "5": "II", "6": "II", "7": "II", "7A": "II", "8": "II", "9": "II",
    "9A": "II", "9B": "II", "9C": "II",
    "10": "III", "11": "III", "12": "III", "13": "III",
    "14": "III",  # modern: Accountant Fees; pre-2003: Exhibits (Part IV)
    "15": "IV", "16": "IV",
}
STATUSES = {"extracted", "missing", "incorporated_by_reference", "omitted"}


def item_text(result, entry):
    return result["normalized_text"][entry["start"]:entry["end"]]


def run_case(case):
    from src.sec10k.extract import extract_items
    result = extract_items(str(ROOT / case["input"]["path"]))

    by_code = {i["item"]: i for i in result["items"]}
    extracted = [i for i in result["items"] if i["status"] == "extracted"]
    failures = []

    def fail(chk, why):
        failures.append({"check": chk, "why": why})

    for chk in case["expect"]["checks"]:
        t = chk["type"]
        entry = by_code.get(chk.get("item"))
        if t == "item_present":
            if entry is None or entry["status"] != chk.get("status", "extracted"):
                fail(chk, f"item {chk['item']} not {chk.get('status', 'extracted')}: "
                          f"{entry and entry['status']}")
        elif t == "item_absent":
            if entry is not None and entry["status"] == "extracted":
                fail(chk, f"item {chk['item']} was extracted but must not exist here")
        elif t == "text_contains":
            if entry is None or chk["value"] not in item_text(result, entry):
                fail(chk, f"item {chk['item']} missing text {chk['value']!r}")
        elif t == "text_not_contains":
            if entry is not None and chk["value"] in item_text(result, entry):
                fail(chk, f"item {chk['item']} contains forbidden {chk['value']!r}")
        elif t == "min_chars":
            n = entry and (entry["end"] - entry["start"]) or 0
            if n < chk["value"]:
                fail(chk, f"item {chk['item']} has {n} chars < {chk['value']}")
        elif t == "known_items_only":
            bad = [i["item"] for i in result["items"] if i["item"] not in CANONICAL]
            bad += [i["item"] for i in result["items"] if i["status"] not in STATUSES]
            if bad:
                fail(chk, f"non-canonical items or statuses: {bad}")
        elif t == "no_overlap_ordered":
            spans = [(i["start"], i["end"], i["item"]) for i in extracted]
            for (s1, e1, a), (s2, e2, b) in zip(spans, spans[1:]):
                if s2 < e1:
                    fail(chk, f"items {a} and {b} overlap or are out of order")
                    break
        elif t == "verbatim":
            n = len(result["normalized_text"])
            for i in extracted:
                if not (0 <= i["start"] < i["end"] <= n):
                    fail(chk, f"item {i['item']} offsets outside normalized_text")
                    break
        elif t == "no_empty_success":
            if not extracted or all(i["end"] - i["start"] < 100 for i in extracted):
                fail(chk, "pipeline returned success with (near-)empty output")
        else:
            fail(chk, f"unknown check type {t!r}")

    return {"passed": not failures, "failures": failures,
            "n_items": len(result["items"]), "n_extracted": len(extracted)}
