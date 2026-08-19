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
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_DIRS = ("golden", "adversarial", "heldout")

# metric 6/8 threshold. Provisional and stated as such: ADR-008 says the
# confidence scale is uncalibrated, so this is a reporting convention, not a
# validated decision boundary.
CONFIDENT = 0.8

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


def _unmatched_failures(rows, cases):
    """Failures whose check JSON matches nothing the case currently declares —
    the report predates a rewrite of that case's checks. Error-path rows (Fix
    2) have no failures list, so they never contribute here."""
    n = 0
    for r in rows:
        case = cases.get(r["id"], {})
        declared_keys = {json.dumps(c, sort_keys=True)
                          for c in case.get("expect", {}).get("checks", [])}
        for f in r.get("failures", []):
            if json.dumps(f["check"], sort_keys=True) not in declared_keys:
                n += 1
    return n


def compute(report, cases):
    results = report["results"]
    checks_total, checks_failed = Counter(), Counter()
    failed_items = set()          # (case_id, item) with at least one failing check
    targeted_items = set()

    for r in results:
        case = cases.get(r["id"], {})
        declared = case.get("expect", {}).get("checks", [])
        failed_keys = [json.dumps(f["check"], sort_keys=True) for f in r.get("failures", [])]
        # a crashed run (evals/run.py's exception path) has no failures list at
        # all, so every declared check of that case counts as failed rather
        # than silently passing by omission
        crashed = "error" in r
        for chk in declared:
            t = chk["type"]
            checks_total[t] += 1
            key = json.dumps(chk, sort_keys=True)
            item = chk.get("item")
            if item:
                targeted_items.add((r["id"], item))
            if crashed or key in failed_keys:
                checks_failed[t] += 1
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

    # --- 8: calibration, per distinct confidence value. Scored rows use the
    # targeted_items/failed_items join above (untouched). Debt rows get their
    # own small join, same case-lookup logic, added ONLY here — metrics 1-7
    # and 9-11 never see debt. Old-style debt rows (pre this change, no
    # items_summary) are skipped rather than crashing.
    debt_targeted_items, debt_failed_items = set(), set()
    for r in report.get("debt", []):
        if "items_summary" not in r:
            continue
        case = cases.get(r["id"], {})
        declared = case.get("expect", {}).get("checks", [])
        failed_keys = [json.dumps(f["check"], sort_keys=True) for f in r.get("failures", [])]
        for chk in declared:
            item = chk.get("item")
            if not item:
                continue
            key = (r["id"], item)
            debt_targeted_items.add(key)
            if json.dumps(chk, sort_keys=True) in failed_keys:
                debt_failed_items.add(key)

    # metric 6 never reads report["debt"] — its unaudited count (`unaudited`
    # above) is scored-suite only. A debt row's own confident-but-untargeted
    # items are counted here, and nowhere else, so metric 8's note can stop
    # claiming metric 6 covers them.
    debt_unaudited = 0
    for r in report.get("debt", []):
        if "items_summary" not in r:
            continue
        for it in r.get("items_summary", []):
            if (it.get("confidence") or 0) < CONFIDENT:
                continue
            if (r["id"], it.get("item")) not in debt_targeted_items:
                debt_unaudited += 1

    conf_rows = {}

    def _bump(r_id, it, targeted, failed, scored):
        c = it.get("confidence")
        key = (r_id, it.get("item"))
        if c is None or key not in targeted:
            return
        row = conf_rows.setdefault(c, {"confidence": c, "n_targeted": 0, "failed": 0,
                                        "n_debt_targeted": 0, "debt_failed": 0})
        if scored:
            row["n_targeted"] += 1
            row["failed"] += key in failed
        else:
            row["n_debt_targeted"] += 1
            row["debt_failed"] += key in failed

    for r in results:
        for it in r.get("items_summary", []):
            _bump(r["id"], it, targeted_items, failed_items, scored=True)
    for r in report.get("debt", []):
        for it in r.get("items_summary", []):
            _bump(r["id"], it, debt_targeted_items, debt_failed_items, scored=False)

    calib = sorted(conf_rows.values(), key=lambda row: -row["confidence"])

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
                     f"wrongly bounded. This value is BOUNDED BY THE GATE, not a measurement: "
                     f"the pre-commit gate forces every declared check green, so untargeted "
                     f"items are the only place a real failure could show up here, and it never "
                     f"will while the gate holds. The actual silent-failure rate is measured by "
                     f"sampling the untargeted population outside this metric entirely — see "
                     f"ADR-019 (T11): 1/30 adjudicated = 3.3%, 95% CI [0.1%, 17.2%]"},
            {"n": 7, "name": "doc-level success rate (golden)",
             "value": _rate(ok(golden), len(golden)), "sample": len(golden),
             "note": f"golden filings only. Pooled over the whole suite it reads "
                     f"{_rate(docs_ok, len(results))}, which is MISLEADING: "
                     f"{len(other) - ok(other)} of {len(other)} non-golden cases "
                     f"deliberately refuse or flag (10-Q, truncated download, stripped "
                     f"items), and refusing correctly is the desired behaviour there"},
            {"n": 8, "name": "confidence calibration", "value": calib,
             "note": "the scored suite is gated green, so scored pass rates here are UPPER "
                     "BOUNDS, not accuracy — nothing scored is currently failing by "
                     "construction. debt rows (evals/run.py's unscored 'debt' suite) are the "
                     "only current-code failure channel and are enumerated in full here, not "
                     "sampled. scored unaudited confident items — not targeted by any check — "
                     f"are counted in metric 6's note, not here. metric 6 never reads debt rows, "
                     f"so debt rows' own unaudited confident items are counted here as "
                     f"debt_unaudited={debt_unaudited} and nowhere else"},
            {"n": 9, "name": "latency p50 / p95 (s)",
             "value": [pct(0.5), pct(0.95)], "sample": len(secs)},
            {"n": 10, "name": "cost per filing (USD)", "value": 0.0, "sample": len(results),
             "note": "structurally zero: no paid dependency exists in the pipeline. "
                     "A reported result, not an estimate"},
            {"n": 11, "name": "deterministic coverage",
             "value": _rate(det, len(methods)), "sample": len(methods),
             "note": "VACUOUS BY CONSTRUCTION, not a measurement: no code path emits "
                     "`llm_fallback`, so this reads 1.0 whatever the pipeline does. It is a "
                     "dependence monitor for the day a fallback exists, and was never able to "
                     "justify or kill one. The non-circular number that ruled on the fallback "
                     "stage is the fallback-ADDRESSABLE surface — items on which any honest "
                     "trigger would fire — counted as `status: missing` in this report's own "
                     "items_summary and then checked against the filing. See ADR-020 (T12), "
                     "which ruled the stage not justified: 4 of 989 items across both eval sets "
                     "are improvable, all from one filing's combined-item heading, and a "
                     "heading-shape change reaches them identically at $0"},
        ],
        "unaudited_confident_items": unaudited,
        "debt_unaudited_confident_items": debt_unaudited,
        "unmatched_failures": (_unmatched_failures(results, cases)
                                + _unmatched_failures(report.get("debt", []), cases)),
    }


def render(m):
    r = m["report"]
    out = [f"suite={r['suite']}  score={r['score']}  cases={r['n_cases']}  git={r['git_sha']}", ""]
    if m.get("unmatched_failures"):
        out.append(f"!! {m['unmatched_failures']} failure(s) match no check the case currently "
                    f"declares — report predates current case files; failed columns undercount")
        out.append("")
    for x in m["metrics"]:
        v = x["value"]
        if isinstance(v, list) and x["n"] == 8:
            out.append(f"{x['n']:>2}. {x['name']}")
            for b in v:
                out.append(f"       conf={b['confidence']:<5} n_targeted={b['n_targeted']:<4} "
                           f"failed={b['failed']:<4} n_debt_targeted={b['n_debt_targeted']:<4} "
                           f"debt_failed={b['debt_failed']}")
        else:
            out.append(f"{x['n']:>2}. {x['name']:<32} {v}   (n={x.get('sample')})")
        if x.get("note"):
            out.append(f"       note: {x['note']}")
    return "\n".join(out)


def _self_check():
    cases = {
        "c1": {"id": "c1", "expect": {"checks": [
            {"type": "item_present", "item": "1", "status": "extracted"},
            {"type": "item_present", "item": "7", "status": "extracted"},
            {"type": "text_contains", "item": "1", "value": "x"}]}},
        "d1": {"id": "d1", "expect": {"checks": [
            {"type": "item_present", "item": "1", "status": "extracted"}]}},
        # a case whose run crashed: evals/run.py's exception path emits
        # {"passed": False, "error": ...} with no failures/items_summary at
        # all, so a naive join finds no failing check JSON and every declared
        # check of the case looks green by omission.
        "c2": {"id": "c2", "expect": {"checks": [
            {"type": "item_present", "item": "5", "status": "extracted"}]}},
    }
    report = {"suite": "fast", "score": 0.0, "git_sha": "abc1234", "results": [{
        "id": "c1", "kind": "golden", "passed": False, "doc_status": "success", "seconds": 0.5,
        "failures": [{"check": {"type": "item_present", "item": "7", "status": "extracted"},
                      "why": "x"},
                     # a stale failure: this check isn't in c1's declared checks
                     # above (the case file was rewritten after this report ran)
                     {"check": {"type": "min_chars", "item": "1", "value": 999},
                      "why": "stale, case no longer declares this check"}],
        "items_summary": [
            {"item": "1", "status": "extracted", "confidence": 0.95, "method": "heading_strict"},
            {"item": "7", "status": "missing", "confidence": 0.95, "method": "status_keyword"},
            {"item": "9", "status": "extracted", "confidence": 0.95, "method": "heading_strict"},
        ]},
        {"id": "c2", "kind": "golden", "passed": False, "error": "boom", "seconds": 0}],
        # a failing debt case (evals/run.py's unscored suite) targeting item 1
        # at the same confidence, plus an old-style debt row (pre this change,
        # no items_summary) that must not crash the join.
        "debt": [
            {"id": "d1", "kind": "adversarial", "passed": False, "doc_status": "success",
             "seconds": 0.1,
             "failures": [{"check": {"type": "item_present", "item": "1", "status": "extracted"},
                           "why": "y"}],
             "items_summary": [
                 {"item": "1", "status": "missing", "confidence": 0.95, "method": "status_keyword"},
                 # untargeted by any declared check -> debt_unaudited, not metric 6
                 {"item": "9", "status": "extracted", "confidence": 0.95, "method": "heading_strict"},
             ]},
            {"id": "d2", "passed": True},
        ]}
    m = compute(report, cases)
    by = {x["n"]: x for x in m["metrics"]}
    # c2's declared item_present check must count as FAILED (denominator +1,
    # numerator +0), not silently pass because the error row has no failures
    assert by[1]["value"] == round(1 / 3, 4) and by[1]["sample"] == 3, by[1]
    assert by[3]["value"] == 1.0, by[3]          # the anchor passed
    # item 7 is confident, targeted, and failed -> silent failure. Item 9 is
    # confident but targeted by nothing -> excluded, counted as unaudited.
    assert by[6]["value"] == 0.5 and by[6]["sample"] == 2, by[6]
    assert m["unaudited_confident_items"] == 1, m
    # d1's item 9 is confident, in a debt row, and targeted by nothing declared
    # -> debt_unaudited, which metric 6 (scored-only) never sees
    assert m["debt_unaudited_confident_items"] == 1, m
    # c1's stale failure matches nothing declared -> counted, not silently 0
    assert m["unmatched_failures"] == 1, m
    assert by[11]["value"] == 1.0, by[11]        # no llm_fallback anywhere
    assert by[10]["value"] == 0.0
    # metric 8: one row for confidence 0.95 — scored columns unchanged by the
    # debt join, debt columns pick up d1's failing item and ignore d2.
    calib95 = next(row for row in by[8]["value"] if row["confidence"] == 0.95)
    assert calib95["n_targeted"] == 2 and calib95["failed"] == 1, calib95
    assert calib95["n_debt_targeted"] == 1 and calib95["debt_failed"] == 1, calib95
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
