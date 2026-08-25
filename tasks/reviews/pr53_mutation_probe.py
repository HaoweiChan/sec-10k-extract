"""PR #53 round-1: the six findings as one-defect mutations, re-runnable.

Every finding in that round was of one shape — `check_confidence_honesty`
asked whether TEXT WAS PRESENT and never whether it was REACHED, COMPLETE, or
CALLED. Three of the six were attacks that walked straight through the
docstring's word "unrepresentable" (R1 severed call, R2 dead code, R4 a
differently-spelled render site), and two more were defects in the shipped
page that no case could see (R3 folded badge tokens, R7 mislabelled figure).

This script is the falsification instrument for all of them. It writes a
byte-copy of the shipped `index.html` with EXACTLY ONE defect, runs
`ui-confidence-honesty` against it, and asserts the case goes red — plus one
control run on the unmodified file that must stay green.

WHY ONE DEFECT PER COPY. `evals/adversarial/ui-confidence-honesty-regression`
carries every shape at once at an exact count, which is this repo's pattern
and is where the GATE coverage lives. It is a poor instrument for asking
"would this single change have been caught", because every shape's failure
list is mixed with sixteen others — and that is precisely how R1/R2/R4
survived round 0. Both exist on purpose: the fixture guards the gate, this
guards the claim.

WHY A TEMPDIR, NOT evals/fixtures. `evals/snapshot.py` runs `extract_items`
on every file under `evals/fixtures`, so a mutation fixture committed there
joins the corpus digest — the standing debt row (Origin: D7) that already
makes "default-flag digests must not move" hard to read on a display-only
row. Six more would make it worse to prove a point about a different file.

Run:
    python3 tasks/reviews/pr53_mutation_probe.py
Exit code is non-zero if any mutation passes or the control fails, so this is
a check, not a demo.
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.repo_hygiene.eval_adapter import run_case  # noqa: E402

SRC = ROOT / "src/sec10k/web/static/index.html"
CASE = ROOT / "evals/adversarial/ui-confidence-honesty.json"

# (finding, what the defect is, old, new)
MUTATIONS = [
    ("R1", "coverageStrip is defined, correct, and never called from render()",
     "    coverageStrip(w);\n", '    "";\n'),
    ("R2", "every pinned line of docQual intact, sitting below an early return",
     "function docQual(){\n", 'function docQual(){\n  if(true) return "";\n'),
    ("R2", "the same dead-code attack on itemQual",
     "function itemQual(it){\n", 'function itemQual(it){\n  if(true) return "";\n'),
    ("R2", "the same dead-code attack on the banner half",
     "function coverageStrip(warns){\n",
     'function coverageStrip(warns){\n  if(true) return "";\n'),
    ("R4", "a third render site the literal `conf ${` scan could not see",
     '        <span class="b">${esc(it.method || "—")}</span>',
     '        <span class="b">confidence ${it.confidence ?? "—"}</span>\n'
     '        <span class="b">${esc(it.method || "—")}</span>'),
    ("R3", "the document flag folded back into the item flag's token",
     'const flag = (it.evidence && (it.evidence.warnings || []).length) ? " lo"\n'
     '               : (docQual() ? " docw" : "");',
     'const flag = ((it.evidence && (it.evidence.warnings || []).length)'
     ' || docQual()) ? " lo" : "";'),
    ("R7", "a NON-coverage figure labelled as coverage",
     'id="coverage">unattributed content: ${',
     'id="coverage">document coverage: ${'),
]


def main():
    src = SRC.read_text()
    case = json.loads(CASE.read_text())
    bad = []

    with tempfile.TemporaryDirectory() as td:
        rel = pathlib.Path(td).relative_to(pathlib.Path(td).anchor)
        for n, (fid, what, old, new) in enumerate(MUTATIONS):
            if src.count(old) != 1:
                bad.append(f"{fid}: anchor is no longer unique ({src.count(old)} "
                           f"hits) — the probe cannot build `{what}`")
                continue
            f = pathlib.Path(td) / f"m{n}.html"
            f.write_text(src.replace(old, new))
            c = json.loads(json.dumps(case))
            c["input"]["file"] = str(f)
            r = run_case(c)
            state = "red" if not r["passed"] else "GREEN"
            print(f"[{fid}] {state:5} — {what}")
            for x in r["failures"]:
                print(f"          {' '.join(x.split())[:120]}")
            if r["passed"]:
                bad.append(f"{fid}: `{what}` passes the case — the defect this "
                           f"finding names is invisible again")

    ctl = run_case(json.loads(CASE.read_text()))
    print(f"[ctl] {'green' if ctl['passed'] else 'RED':5} — the shipped index.html, unmodified")
    for x in ctl["failures"]:
        print(f"          {' '.join(x.split())[:120]}")
    if not ctl["passed"]:
        bad.append("control: the shipped file does not pass its own case")

    for b in bad:
        print("FAIL:", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
