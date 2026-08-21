"""Eval adapter for repo_hygiene — structural checks on the repo's own
artifacts (specs/decisions/, the inspector stylesheet), not on filing
extraction. Case shape:

    "task": "repo_hygiene"
    "input": {"checks": ["adr_headers", "adr_index"]}   # default if omitted

Each check name maps to a function in CHECKS. The ADR checks need no case
input (there is one specs/decisions/ tree); `ui_stylesheet` is case-declared,
because WHICH text sits on WHICH ground is the reviewable part.
"""
import re
from pathlib import Path

from . import css_contrast

UI_STYLESHEET = "src/sec10k/web/static/index.html"

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "specs" / "decisions"


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


def check_ui_stylesheet(case):
    """WCAG AA over the inspector's token block + the .it selector-scoping rule.

    S3 restyled the inspector and introduced two defects nothing could see: the
    light palette's FILL colors used as text (2.40-3.51:1), and a bare
    `button:hover` rule outranking `.it[aria-current]`. Both are decidable from
    the file text, so hard rule 2 says they are a case, not a promise.
    """
    inp = case.get("input", {})
    css = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    grounds = inp["grounds"]
    pairs = [dict(p, on=grounds[p["on"]]) for p in inp["pairs"]]
    failures, measured = css_contrast.check_contrast(
        css, pairs, inp.get("min_ratio", 4.5))
    failures += css_contrast.check_button_specificity(css)
    return failures, {"measured": measured,
                      "min_ratio_measured": min(measured.values())}


CHECKS = {
    "adr_headers": lambda case: check_adr_headers(),
    "adr_index": lambda case: check_index(),
    "ui_stylesheet": check_ui_stylesheet,
}


def run_case(case):
    names = case.get("input", {}).get("checks") or ["adr_headers", "adr_index"]
    failures, info = [], {}
    for name in names:
        got = CHECKS[name](case)
        if isinstance(got, tuple):  # check also reports measurements
            got, extra = got
            info.update(extra)
        failures += got
    return {"passed": not failures, "failures": failures, **info}
