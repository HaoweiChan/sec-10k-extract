"""Metrics over a committed eval report — the numbers the analysis report quotes.

Reads a report JSON produced by `evals.run` plus the case JSONs it references,
and computes the eleven metrics in docs/evals/evaluation-strategy.md. Stdlib
only, so CI's dependency-free job can run it.

Design rule this file exists to enforce: **a metric that cannot be computed
honestly is reported as unavailable, never as a number.** Several of these are
proxies, and each one says so in its own `note`. `evals/report/*.json` remains
the raw record; this is a view over it.

Run: python3 -m evals.metrics [report.json]     (default: newest --suite all)
Self-check: python3 -m evals.metrics --self-check
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_DIRS = ("golden", "adversarial", "heldout")

# metric 6/8 threshold. Provisional and stated as such: ADR-008 says the
# confidence scale is uncalibrated, so this is a reporting convention, not a
# validated decision boundary.
CONFIDENT = 0.8
BUCKETS = [(0.0, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 1.01)]

# checks that assert something about a named item, grouped by what they reveal
PRESENCE = {"item_present"}
STATUS = {"item_present"}          # item_present carries the status assertion
ANCHOR = {"text_contains"}
BAND = {"min_chars", "max_chars"}
FALSE_POS = {"item_absent", "known_items_only", "text_not_contains", "only_items"}


def load_cases():
    out = {}
    for d in CASE_DIRS:
        for p in (ROOT / "evals" / d).glob("*.json"):
            try:
                c = json.loads(p.read_text())
            except Exception:
                continue
            if isinstance(c, dict) and "id" in c:
                out[c["id"]] = c
    return out


def _rate(hit, total):
    return None if not total else round(hit / total, 4)


def compute(report, cases):
    results = report["results"]
    checks_total, checks_failed = {}, {}
    failed_items = set()          # (case_id, item) with at least one failing check
    targeted_items = set()

    for r in results:
        case = cases.get(r["id"], {})
        declared = case.get("expect", {}).get("checks", [])
        failed_keys = [json.dumps(f["check"], sort_keys=True) for f in r.get("failures", [])]
        for chk in declared:
            t = chk["type"]
            checks_total[t] = checks_total.get(t, 0) + 1
            key = json.dumps(chk, sort_keys=True)
            item = chk.get("item")
            if item:
                targeted_items.add((r["id"], item))
            if key in failed_keys:
                checks_failed[t] = checks_failed.get(t, 0) + 1
                if item:
                    failed_items.add((r["id"], item))

    def group(names):
        tot = sum(checks_total.get(n, 0) for n in names)
        bad = sum(checks_failed.get(n, 0) for n in names)
        return _rate(tot - bad, tot), tot

    # --- 6: silent failure. Confident items inside a doc the pipeline called a
    # success, that nonetheless fail a check. Denominator counts ONLY items some
    # check targets; untargeted confident items are reported separately rather
    # than silently counted as fine (evaluation-strategy is explicit about this).
    conf_targeted = conf_silent = unaudited = excluded_nonsuccess = 0
    for r in results:
        success = r.get("doc_status") in ("success", "success_with_warning")
        for it in r.get("items_summary", []):
            if (it.get("confidence") or 0) < CONFIDENT:
                continue
            if not success:
                # The metric's definition scopes it to docs the pipeline called
                # a success, which is defensible — but the pre-B audit caught
                # the PROSE quoting coverage as if this exclusion did not exist.
                # It is counted and published, not silently dropped.
                excluded_nonsuccess += 1
                continue
            key = (r["id"], it["item"])
            if key in targeted_items:
                conf_targeted += 1
                if key in failed_items:
                    conf_silent += 1
            else:
                unaudited += 1
    conf_total = conf_targeted + unaudited + excluded_nonsuccess

    # --- 8: calibration. Same join, bucketed.
    calib = []
    for lo, hi in BUCKETS:
        tot = bad = 0
        for r in results:
            for it in r.get("items_summary", []):
                c = it.get("confidence")
                if c is None or not (lo <= c < hi):
                    continue
                key = (r["id"], it["item"])
                if key not in targeted_items:
                    continue
                tot += 1
                if key in failed_items:
                    bad += 1
        calib.append({"bucket": f"[{lo:.1f},{hi:.2f})", "n_targeted": tot,
                      "empirical_pass_rate": _rate(tot - bad, tot)})

    # --- 9/10/11
    secs = sorted(r.get("seconds", 0) for r in results)
    def pct(p):
        return None if not secs else secs[min(len(secs) - 1, int(len(secs) * p))]
    methods = [it.get("method") for r in results for it in r.get("items_summary", [])
               if it.get("status") == "extracted"]
    det = sum(1 for m in methods if m != "llm_fallback")

    presence, n_pres = group(PRESENCE)
    anchor, n_anch = group(ANCHOR)
    band, n_band = group(BAND)
    fpos, n_fpos = group(FALSE_POS)
    # Metric 7 must be read per kind. An adversarial case whose whole point is
    # `unsupported` or `ambiguous` is CORRECT when it declines, so pooling it
    # with the goldens reports honest refusals as usability failures — the
    # single most misreadable number in this file.
    def ok(rs):
        return sum(1 for r in rs if r["passed"]
                   and r.get("doc_status") in ("success", "success_with_warning"))
    golden = [r for r in results if r.get("kind") == "golden"]
    other = [r for r in results if r.get("kind") != "golden"]
    docs_ok = ok(results)

    return {
        "report": {"suite": report.get("suite"), "score": report.get("score"),
                   "git_sha": report.get("git_sha", "")[:7], "n_cases": len(results)},
        "metrics": [
            {"n": 1, "name": "item presence recall", "value": presence, "sample": n_pres},
            {"n": 2, "name": "status accuracy", "value": presence, "sample": n_pres,
             "note": "same denominator as metric 1: item_present carries BOTH assertions, "
                     "so they cannot be separated without splitting the check type"},
            {"n": 3, "name": "anchor-containment accuracy", "value": anchor, "sample": n_anch},
            {"n": 4, "name": "boundary tightness (proxy)", "value": band, "sample": n_band,
             "note": "length-band pass rate. A PROXY — true IoU needs offset ground truth, "
                     "which cannot exist while normalized_text is extractor-owned"},
            {"n": 5, "name": "false-positive extraction rate",
             "value": None if fpos is None else round(1 - fpos, 4), "sample": n_fpos},
            {"n": 6, "name": "silent-failure rate",
             "value": _rate(conf_silent, conf_targeted), "sample": conf_targeted,
             "note": f"confident (>={CONFIDENT}) items in success docs that fail a check. "
                     f"COVERAGE {_rate(conf_targeted, conf_total)} of the {conf_total} confident "
                     f"items in the run: {unaudited} are targeted by NO check (unaudited, not "
                     f"verified) and {excluded_nonsuccess} more sit in non-success docs and are "
                     f"outside the metric's definition — including items this report names as "
                     f"wrongly bounded"},
            {"n": 7, "name": "doc-level success rate (golden)",
             "value": _rate(ok(golden), len(golden)), "sample": len(golden),
             "note": f"golden filings only. Pooled over the whole suite it reads "
                     f"{_rate(docs_ok, len(results))}, which is MISLEADING: "
                     f"{len(other) - ok(other)} of {len(other)} non-golden cases "
                     f"deliberately refuse or flag (10-Q, truncated download, stripped "
                     f"items), and refusing correctly is the desired behaviour there"},
            {"n": 8, "name": "confidence calibration", "value": calib,
             "note": "bucket edges provisional; ADR-008 states the scale is uncalibrated"},
            {"n": 9, "name": "latency p50 / p95 (s)",
             "value": [pct(0.5), pct(0.95)], "sample": len(secs)},
            {"n": 10, "name": "cost per filing (USD)", "value": 0.0, "sample": len(results),
             "note": "structurally zero: no paid dependency exists in the pipeline. "
                     "A reported result, not an estimate"},
            {"n": 11, "name": "deterministic coverage",
             "value": _rate(det, len(methods)), "sample": len(methods)},
        ],
        "unaudited_confident_items": unaudited,
    }


def render(m):
    r = m["report"]
    out = [f"suite={r['suite']}  score={r['score']}  cases={r['n_cases']}  git={r['git_sha']}", ""]
    for x in m["metrics"]:
        v = x["value"]
        if isinstance(v, list) and x["n"] == 8:
            out.append(f"{x['n']:>2}. {x['name']}")
            for b in v:
                out.append(f"       {b['bucket']:>12}  n={b['n_targeted']:<4} "
                           f"pass={b['empirical_pass_rate']}")
        else:
            out.append(f"{x['n']:>2}. {x['name']:<32} {v}   (n={x.get('sample')})")
        if x.get("note"):
            out.append(f"       note: {x['note']}")
    return "\n".join(out)


def _self_check():
    cases = {"c1": {"id": "c1", "expect": {"checks": [
        {"type": "item_present", "item": "1", "status": "extracted"},
        {"type": "item_present", "item": "7", "status": "extracted"},
        {"type": "text_contains", "item": "1", "value": "x"}]}}}
    report = {"suite": "fast", "score": 0.0, "git_sha": "abc1234", "results": [{
        "id": "c1", "kind": "golden", "passed": False, "doc_status": "success", "seconds": 0.5,
        "failures": [{"check": {"type": "item_present", "item": "7", "status": "extracted"},
                      "why": "x"}],
        "items_summary": [
            {"item": "1", "status": "extracted", "confidence": 0.95, "method": "heading_strict"},
            {"item": "7", "status": "missing", "confidence": 0.95, "method": "status_keyword"},
            {"item": "9", "status": "extracted", "confidence": 0.95, "method": "heading_strict"},
        ]}]}
    m = compute(report, cases)
    by = {x["n"]: x for x in m["metrics"]}
    assert by[1]["value"] == 0.5, by[1]          # 1 of 2 item_present passed
    assert by[3]["value"] == 1.0, by[3]          # the anchor passed
    # item 7 is confident, targeted, and failed -> silent failure. Item 9 is
    # confident but targeted by nothing -> excluded, counted as unaudited.
    assert by[6]["value"] == 0.5 and by[6]["sample"] == 2, by[6]
    assert m["unaudited_confident_items"] == 1, m
    assert by[11]["value"] == 1.0, by[11]        # no llm_fallback anywhere
    assert by[10]["value"] == 0.0
    # empty report must not divide by zero
    m2 = compute({"suite": "x", "score": 0, "results": []}, {})
    assert {x["n"]: x for x in m2["metrics"]}[1]["value"] is None
    render(m); render(m2)
    print("[metrics self-check] ok")


def main(argv):
    if "--self-check" in argv:
        return _self_check()
    if len(argv) > 1:
        path = Path(argv[1])
    else:
        reps = sorted((ROOT / "evals" / "report").glob("*-all.json"))
        if not reps:
            print("no --suite all report found; run: python3 -m evals.run --suite all")
            return 1
        path = reps[-1]
    report = json.loads(path.read_text())
    m = compute(report, load_cases())
    print(f"# {path.name}\n")
    print(render(m))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
