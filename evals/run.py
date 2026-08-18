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
        # a report's sha must not claim code the run wasn't actually on
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
            text=True, timeout=5, check=True,
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
    ap.add_argument("--no-report", action="store_true")
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

    report = {"suite": args.suite, "score": score, "git_sha": git_sha(),
              "results": results,
              "debt": debt_results}
    write_report = not args.no_report
    if args.no_report and args.dir:
        # held-out/--dir runs must never be traceless (docs/evals/evaluation-strategy.md)
        print("[eval] --no-report ignored for --dir runs: writing report anyway")
        write_report = True
    if write_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        (REPORT_DIR / f"{stamp}-{args.suite}.json").write_text(json.dumps(report, indent=2))

    baseline_path = Path(args.baseline)
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    if args.update_baseline:
        baseline[args.suite] = score
        baseline_path.write_text(json.dumps(baseline, indent=2) + "\n")
        print(f"[eval] baseline['{args.suite}'] = {score:.3f} (recorded)")
        return 0
    if args.suite == "invariant" and passed < len(results):
        print("[eval] INVARIANT VIOLATION: invariants are absolute, 100% required",
              file=sys.stderr)
        return 1
    if args.suite in baseline and score < baseline[args.suite]:
        print(f"[eval] REGRESSION: {score:.3f} < baseline {baseline[args.suite]:.3f}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
