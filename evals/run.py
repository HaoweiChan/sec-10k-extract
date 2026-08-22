#!/usr/bin/env python3
"""Task-agnostic eval runner.

Case contract (one JSON file per case, under evals/golden/ or evals/adversarial/):

    {
      "id": "unique-case-id",
      "task": "sec10k",                  # -> src/<task>/eval_adapter.py
      "suites": ["fast", "invariant"],   # default ["fast"]
      "input": { ... },                  # task-defined
      "expect": { ... }                  # task-defined
    }

Each task implements src/<task>/eval_adapter.py with:

    def run_case(case: dict) -> dict    # {"passed": bool, ...anything else}

The runner owns: discovery, suite filtering, scoring, baseline gating,
report history. Adapters own: how to run a case and judge it.

Report policy (ADR-025): every run appends one line to
evals/report/history.jsonl — that line is the time series. A full per-case
report (evals/report/<ts>-<suite>.json) is written only when it earns its
keep: --report was passed, --suite all, a --dir held-out run (never
traceless), or the run is red (any scored case failed, or score fell below
baseline). --no-report suppresses the full report even on red — for the
high-frequency PostToolUse invariant hook — but never suppresses the
history line, and never overrides a --dir run.
"""
import argparse
import importlib
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASE_DIRS = [ROOT / "evals" / "golden", ROOT / "evals" / "adversarial"]
BASELINE = ROOT / ".eval-baseline.json"
REPORT_DIR = ROOT / "evals" / "report"


def load_cases(suite, dir_arg=None):
    if dir_arg:
        p = Path(dir_arg)
        dirs = [p if p.is_absolute() else ROOT / p]
    else:
        dirs = CASE_DIRS
    cases = []
    for d in dirs:
        for f in sorted(d.glob("*.json")):  # non-recursive: no stray nested JSON joins a suite
            case = json.loads(f.read_text())
            try:
                case["_file"] = str(f.relative_to(ROOT))
            except ValueError:
                case["_file"] = str(f)
            case["_kind"] = d.name  # golden | adversarial | <--dir basename>
            # a "debt" case loads under every suite, not just --suite all: it
            # documents a known-red limitation and main()'s debt split already
            # excludes it from scoring, so loading it everywhere costs nothing
            # and is what "debt runs every run" is supposed to mean
            case_suites = case.get("suites", ["fast"])
            if suite == "all" or suite in case_suites or "debt" in case_suites:
                cases.append(case)
    return cases


def git_sha():
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
            text=True, timeout=5, check=True,
        ).stdout.strip()
        # a report's sha must not claim code the run wasn't actually on. -uno:
        # every run writes an untracked report into evals/report/, so without
        # it the second run in a session always stamps -dirty on identical
        # code. evals/report/history.jsonl is excluded the same way: once
        # committed it's a TRACKED file this same run is about to append a
        # line to, so without the exclusion every run after the first would
        # report -dirty on an otherwise-identical tree — the exact bug -uno
        # exists to prevent, one file later. This is the one place dirty is
        # decided; history's "sha"/"dirty" fields (main(), below) are derived
        # from this same string so the two never disagree.
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "-uno", "--",
             ".", ":!evals/report/history.jsonl"],
            cwd=ROOT, capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
        return sha + "-dirty" if dirty else sha
    except Exception:  # git absent, not a repo, etc. — never crash the runner over this
        return None


def run_case(case):
    t0 = time.monotonic()
    try:
        mod = importlib.import_module(f"src.{case['task']}.eval_adapter")
        result = mod.run_case(case)
    except Exception:
        result = {"passed": False, "error": traceback.format_exc(limit=3)}
    result.setdefault("passed", False)
    result["seconds"] = round(time.monotonic() - t0, 2)
    result["id"] = case.get("id", case["_file"])
    result["kind"] = case["_kind"]
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="fast")
    ap.add_argument("--baseline", default=str(BASELINE))
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--report", action="store_true",
                     help="force a full per-case report even on a routine green run")
    ap.add_argument("--no-report", action="store_true",
                     help="suppress the full report even on a red run (history line still "
                          "written); for the high-frequency PostToolUse hook. Ignored on "
                          "--dir runs, which always write a report")
    ap.add_argument("--dir", default=None,
                     help="discover cases from only this directory (e.g. evals/heldout), "
                          "instead of CASE_DIRS")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    cases = load_cases(args.suite, args.dir)
    if not cases:
        print(f"[eval] suite '{args.suite}': no cases yet — nothing to gate on. "
              "Add cases under evals/golden/ or evals/adversarial/.")
        return 0

    t0 = time.monotonic()
    # A "debt" case documents a limitation we have decided NOT to fix yet. It
    # is committed, it RUNS every time, and its result is printed — but it is
    # excluded from the score, because scoring it would force the choice
    # between breaking the gate and rewriting the case to assert the bug as
    # correct. The B-exit checklist calls for exactly this: adversarial cases
    # "green or enumerated as debt with triage notes". If a debt case ever goes
    # green the run says so, which is the signal to promote it back.
    debt = [c for c in cases if "debt" in c.get("suites", [])]
    cases = [c for c in cases if "debt" not in c.get("suites", [])]

    results = [run_case(c) for c in cases]
    passed = sum(r["passed"] for r in results)
    score = passed / len(results) if results else 0.0
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"[{mark}] {r['id']} ({r['kind']}, {r['seconds']}s)")
        if not r["passed"] and "error" in r:
            print(f"       {r['error'].strip().splitlines()[-1]}")

    debt_results = [run_case(c) for c in debt]
    for c, r in zip(debt, debt_results):
        state = "STILL RED" if not r["passed"] else "NOW GREEN — promote it"
        print(f"[DEBT] {r['id']}: {state} — {c.get('triage', {}).get('class', 'known limitation')}")

    print(f"[eval] suite '{args.suite}': {passed}/{len(results)} = {score:.3f}"
          + (f"  (+{len(debt)} enumerated debt, unscored)" if debt else ""))
    # ADR-029 §c: table fidelity, micro-averaged over every `table` check the
    # scored cases ran (debt excluded, like the score). None when no case in
    # this suite labels a table — reported as absent, never as a number.
    fid = {"cells": [0, 0], "rows": [0, 0]}
    for r in results:
        for k, (ok, tot) in r.get("table_fidelity", {}).items():
            fid[k][0] += ok
            fid[k][1] += tot
    table_metric = {f"table_{k}_fidelity": (round(ok / tot, 4) if tot else None)
                    for k, (ok, tot) in fid.items()}
    if fid["cells"][1]:
        print(f"[eval] table fidelity: cells {table_metric['table_cells_fidelity']:.4f} "
              f"({fid['cells'][0]}/{fid['cells'][1]}), rows "
              f"{table_metric['table_rows_fidelity']:.4f} ({fid['rows'][0]}/{fid['rows'][1]})")
    wall_s = round(time.monotonic() - t0, 2)

    baseline_path = Path(args.baseline)
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    is_red = passed < len(results) or (args.suite in baseline and score < baseline[args.suite])
    # the metric is gated like the score: against the value `--update-baseline`
    # recorded, only when this run measured it (ADR-016: reported-but-never-
    # compared is a claim, not a check)
    metric_red = [k for k, v in table_metric.items()
                  if v is not None and k in baseline and v < baseline[k]]
    is_red = is_red or bool(metric_red)

    # Report policy (ADR-025): a full per-case dump is expensive (one JSON per
    # case) and most runs are routine — only worth keeping in full when it's
    # the record of a `--suite all` sweep, a held-out run (never traceless,
    # per docs/evals/evaluation-strategy.md), a red run (debugging needs the
    # detail), or explicitly requested with --report. Every OTHER run still
    # gets exactly one line in history.jsonl — that line is the time series.
    write_full = args.report or args.suite == "all" or bool(args.dir) or is_red or args.update_baseline
    if args.no_report:
        if args.dir:
            print("[eval] --no-report ignored for --dir runs: writing report anyway")
        else:
            write_full = False

    sha = git_sha()
    dirty = bool(sha) and sha.endswith("-dirty")
    short_sha = (sha[:-len("-dirty")] if dirty else sha)[:7] if sha else None

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    report_name = None
    if write_full:
        report = {"suite": args.suite, "score": score, "git_sha": sha,
                   **table_metric, "results": results, "debt": debt_results}
        report_name = f"{stamp}-{args.suite}.json"
        (REPORT_DIR / report_name).write_text(json.dumps(report, indent=2))

    history_line = {
        "ts": stamp, "suite": args.suite, "sha": short_sha, "dirty": dirty,
        "passed": passed, "total": len(results), "score": round(score, 4),
        "wall_s": wall_s,
        # structurally zero, not measured: no paid dependency exists anywhere
        # in this pipeline (metric 10 / ADR-020).
        "cost_usd": 0.0,
        "report": report_name,
        "debt_count": len(debt),
        **table_metric,   # ADR-029: null on a suite with no table labels
    }
    if args.dir:
        history_line["dir"] = args.dir
    with (REPORT_DIR / "history.jsonl").open("a") as f:
        f.write(json.dumps(history_line) + "\n")

    if args.update_baseline:
        baseline[args.suite] = score
        for k, v in table_metric.items():
            if v is not None:   # a suite that measured no table leaves the key alone
                baseline[k] = v
        baseline_path.write_text(json.dumps(baseline, indent=2) + "\n")
        print(f"[eval] baseline['{args.suite}'] = {score:.3f} (recorded)"
              + "".join(f"; baseline['{k}'] = {v}" for k, v in table_metric.items()
                        if v is not None))
        return 0
    if args.suite == "invariant" and passed < len(results):
        print("[eval] INVARIANT VIOLATION: invariants are absolute, 100% required",
              file=sys.stderr)
        return 1
    if args.suite in baseline and score < baseline[args.suite]:
        print(f"[eval] REGRESSION: {score:.3f} < baseline {baseline[args.suite]:.3f}",
              file=sys.stderr)
        return 1
    if metric_red:
        print("[eval] REGRESSION: " + ", ".join(
            f"{k} {table_metric[k]:.4f} < baseline {baseline[k]:.4f}" for k in metric_red),
            file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
