"""Eval adapter for repo_hygiene — structural checks on the repo's own
documentation (specs/decisions/, evals/report/ citations), not on filing
extraction. Case shape:

    "task": "repo_hygiene",
    "input": {"checks": ["adr_headers", "adr_index"]}   # names below, in CHECKS

Checks are hardcoded functions, selected by name so one adapter can back
several distinct invariant cases (ADR-025 added report_citations).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "specs" / "decisions"
REPORT_DIR = ROOT / "evals" / "report"
# same locations ADR-025's prune treated as "outside evals/report/" — a
# citation anywhere else is a report of record and must resolve on disk
CITE_SCAN = ["docs", "specs", "tasks", "README.md", "src", "evals/golden",
             "evals/adversarial", "evals/heldout", "prompts", ".github"]
REPORT_REF_RE = re.compile(r"evals/report/([0-9]{8}-[0-9]{6}-[A-Za-z0-9_]+\.json)")


def check_adr_headers():
    """Every ADR carries a Ruling/Because/Enforced-by block, <=3 lines, before a `---`."""
    bad = []
    for f in sorted(DECISIONS.glob("ADR-*.md")):
        lines = f.read_text().splitlines()
        starts = [i for i, l in enumerate(lines) if l.startswith("**Ruling**:")]
        if not starts:
            bad.append(f"{f.name}: no **Ruling**: block")
            continue
        i = starts[0]
        ends = [k for k in range(i, len(lines)) if lines[k].strip() == "---"]
        if not ends:
            bad.append(f"{f.name}: **Ruling** block has no closing ---")
            continue
        block = [l for l in lines[i:ends[0]] if l.strip()]
        if len(block) > 3:
            bad.append(f"{f.name}: ruling block has {len(block)} lines (>3)")
        if not any(l.startswith("**Because**:") for l in block):
            bad.append(f"{f.name}: missing **Because**:")
        if not any(l.startswith("**Enforced by**:") for l in block):
            bad.append(f"{f.name}: missing **Enforced by**:")
    return bad


def check_index():
    """INDEX.md exists and has exactly one entry (bullet line) per ADR file.

    Only the line's own bullet is counted, not incidental "amended by
    ADR-0NN" cross-references elsewhere in the same line.
    """
    idx = DECISIONS / "INDEX.md"
    adrs = sorted(f.stem for f in DECISIONS.glob("ADR-*.md"))
    if not idx.exists():
        return ["INDEX.md missing"]
    entries = re.findall(r"^- (ADR-\d+)\b", idx.read_text(), re.M)
    bad = []
    for name in adrs:
        num = name.split("-")[1]
        hits = entries.count(f"ADR-{num}")
        if hits != 1:
            bad.append(f"INDEX.md: ADR-{num} has {hits} entries (want 1)")
    return bad


def check_report_citations():
    """Every evals/report/<ts>-*.json cited outside evals/report/ must exist
    on disk — the invariant a prune (ADR-025) must never violate."""
    bad = []
    for rel in CITE_SCAN:
        p = ROOT / rel
        files = [p] if p.is_file() else (p.rglob("*") if p.is_dir() else [])
        for f in files:
            if not f.is_file():
                continue
            try:
                text = f.read_text(errors="ignore")
            except Exception:
                continue
            for name in REPORT_REF_RE.findall(text):
                if not (REPORT_DIR / name).exists():
                    bad.append(f"{f.relative_to(ROOT)}: cites missing evals/report/{name}")
    return bad


CHECKS = {
    "adr_headers": check_adr_headers,
    "adr_index": check_index,
    "report_citations": check_report_citations,
}


def run_case(case):
    names = case.get("input", {}).get("checks") or ["adr_headers", "adr_index"]
    failures = []
    for name in names:
        failures += CHECKS[name]()
    return {"passed": not failures, "failures": failures}
