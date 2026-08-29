"""Eval adapter for repo_hygiene — structural checks on the repo's own
artifacts (specs/decisions/, evals/report/ citations, the inspector
stylesheet), not on filing extraction. Case shape:

    "task": "repo_hygiene",
    "input": {"checks": ["adr_headers", "adr_index"]}   # names below, in CHECKS

Each check name maps to a function in CHECKS, so one adapter can back several
distinct invariant cases (ADR-025 added report_citations; S3 added
ui_stylesheet). The ADR and citation checks need no case input — there is one
specs/decisions/ tree and one evals/report/ — while `ui_stylesheet` is
case-declared, because WHICH text sits on WHICH ground is the reviewable part.
"""
import ast
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from . import css_contrast
from src.sec10k.web import anchor as web_anchor
from src.sec10k.web import build_id
from src.sec10k.web import capabilities as web_capabilities
from src.sec10k.web.fixtures import (DEPLOY_EXCLUDED, deployed_fixtures,
                                     fixture_file, list_fixtures)
from evals import oracle as eval_oracle
from src.sec10k.web.view import DISPLAY_MAX, build_view
from src.sec10k.extract import extract_items

UI_STYLESHEET = "src/sec10k/web/static/index.html"
API_FILE = "src/sec10k/web/app.py"
EXTRACT_ENDPOINTS = ("/api/extract/fixture", "/api/extract/upload",
                     "/api/extract/url")
FIXTURES = "evals/fixtures"
ZBPACK = "zbpack.json"
GITIGNORE = ".gitignore"

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
    text = idx.read_text()
    entries = re.findall(r"^- (ADR-\d+)\b", text, re.M)
    bad = []
    for name in adrs:
        num = name.split("-")[1]
        hits = entries.count(f"ADR-{num}")
        if hits != 1:
            bad.append(f"INDEX.md: ADR-{num} has {hits} entries (want 1)")
    bad += _index_h2_money(text)
    return bad


# PR #61 R16. INDEX.md:44 said the effective deployment ceiling was
# `MAX_USD + $1.5675` while ADR-036 §h2 — cited in the same clause — had
# superseded that figure with $2.4697 and recorded that $1.5675 was falsified
# by a real billed call. A summary line that CITES a section and contradicts it
# is worse than one that says nothing, and nothing read the two together. This
# does: every dollar figure INDEX.md attributes to §h2 must occur in §h2, and
# the ceiling it publishes must be the one §h2 derives.
MONEY_RE = re.compile(r"\$([0-9][0-9,]*\.[0-9]{2,4})")
CEILING_RE = re.compile(r"effective deployment ceiling is[^$]*\$([0-9.]+)")
INDEX_CEILING_RE = re.compile(r"effective ceiling MAX_USD \+ \$([0-9.]+)")


def _index_h2_money(text):
    adr = (DECISIONS / "ADR-036-tiered-escalation.md").read_text()
    # the section is spelled `## h2)`; splitting on the wrong header silently
    # widens the haystack to the whole ADR, and $1.5675 IS elsewhere in it
    # (§h5, as the figure that was falsified) — which would make this vacuous
    assert "\n## h2)" in adr, "ADR-036 has no `## h2)` section to bind against"
    h2 = adr.split("\n## h2)")[1].split("\n## ")[0]
    bad = []
    want = CEILING_RE.search(adr)
    got = INDEX_CEILING_RE.search(text)
    if want and got and want.group(1) != got.group(1):
        bad.append(f"INDEX.md publishes an effective ceiling of MAX_USD + "
                   f"${got.group(1)} while ADR-036 derives ${want.group(1)} — "
                   f"the summary contradicts the section it cites, which is "
                   f"how a falsified figure outlives its falsification")
    # per CLAUSE, not per line: an INDEX bullet is one very long line whose
    # semicolon-separated clauses each cite a different section, and §k's own
    # billed-exam figure has no business being checked against §h2
    for line in text.splitlines():
        for clause in line.split(";"):
            if "\u00a7h2" not in clause:
                continue
            for fig in MONEY_RE.findall(clause):
                if f"${fig}" not in h2:
                    bad.append(f"INDEX.md attributes ${fig} to ADR-036 "
                               f"\u00a7h2, which does not contain it")
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


HELDOUT_DIR = ROOT / "evals" / "heldout"
# The three claim shapes held-out provenances actually use for byte-level
# facts. `evals/heldout/README.md` records SIX occasions on which the
# verification instrument, not the pipeline, produced a wrong claim, and the
# rule it settled on is that anything character-level must be read from the
# raw bytes. Nothing enforced that: a provenance is free prose, so a
# miscounted string or an offset off by eight bytes sat in the document of
# record until a human re-derived it (PR #52 R4/R5). These re-derive it every
# run, against the committed fixture, importing nothing from src/sec10k.
# ponytail: pins the three phrasings in use, not prose in general — a claim
# written some other way is simply unpinned, which is the same silence as
# before, not a regression. Widen the patterns when a new phrasing appears.
_Q = "['‘’]"  # ASCII or typographic single quote — PR #52 R11: swapping one
                       # for the other silently disarmed every pin in a file
_PROV_COUNT_RE = re.compile(_Q + r"([^'‘’]{1,120})" + _Q + r" (\d+)x")
_PROV_OFFSET_RE = re.compile(
    _Q + r"([^'‘’]{1,160})" + _Q + r"[^.]{0,40}?(?:\(|at )raw offset ([\d,]+)")
_PROV_HITS_RE = re.compile(
    r"[^.]*\bregex\b[^.]*?\breturns\b[^.]*?\b(\d+|one|two|three|four|five|six|"
    r"seven|eight|nine|ten) hits[^.]*", re.I)
_NUM_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten".split())}
_BACKTICKED_RE = re.compile(r"`([^`]+)`")


def check_heldout_provenance_claims(case=None):
    """Every byte-level claim in a held-out case's provenance must reproduce
    against that case's committed fixture: `'<literal>' <N>x` occurrence
    counts, `'<literal>' at raw offset <N>` positions, and any stated regex
    hit count — which must name the regex in backticks so it can be run.

    FAILS CLOSED (PR #52 R11, on the `evals/bench.check_docs` precedent): the
    first version returned green when it extracted NOTHING, so the coverage it
    advertises could be silently reduced to zero — swapping ASCII apostrophes
    for typographic ones, or rewording `'X' 8x` to `'X' appears eight times`,
    disarmed every pin in a file and left the gate at 123/123. `min_claims`
    in the case commits how many claims each file must yield; a file that
    yields fewer, or that has disappeared, is a failure. A check that can be
    disarmed by a curly apostrophe is worse than none — it launders the
    coverage claim."""
    bad = []
    floors = dict((case or {}).get("input", {}).get("min_claims") or {})
    seen = {}
    for f in sorted(HELDOUT_DIR.glob("*.json")):
        hc = json.loads(f.read_text())
        prov = hc.get("provenance", "")
        where = f"evals/heldout/{f.name}"
        raw = (ROOT / hc["input"]["path"]).read_bytes()
        n_claims = 0
        for lit, n in _PROV_COUNT_RE.findall(prov):
            n_claims += 1
            got = raw.count(lit.encode())
            if got != int(n):
                bad.append(f"{where}: claims {lit!r} {n}x, fixture has {got}x")
        for lit, off in _PROV_OFFSET_RE.findall(prov):
            n_claims += 1
            want = int(off.replace(",", ""))
            b = lit.encode()
            if raw[want:want + len(b)] != b:
                bad.append(f"{where}: claims {lit[:40]!r} at raw offset {want}, "
                           f"actually at {raw.find(b)}")
        for m in _PROV_HITS_RE.finditer(prov):
            n_claims += 1
            want = _NUM_WORDS.get(m.group(1).lower())
            if want is None:
                want = int(m.group(1))
            pats = _BACKTICKED_RE.findall(m.group(0))
            if not pats:
                bad.append(f"{where}: states a regex hit count ({m.group(1)}) "
                           f"without naming the regex in backticks — not reproducible")
                continue
            for pat in pats:
                try:
                    got = len(re.findall(pat.encode(), raw))
                except re.error as e:
                    bad.append(f"{where}: regex {pat!r} does not compile ({e})")
                    continue
                if got != want:
                    bad.append(f"{where}: regex {pat!r} claimed {m.group(1)} hits, "
                               f"produces {got}")
        seen[f.name] = n_claims
    for name, floor in sorted(floors.items()):
        got = seen.get(name)
        if got is None:
            bad.append(f"evals/heldout/{name}: committed for {floor} pinned claims "
                       f"but the case file is gone — coverage cannot silently vanish")
        elif got < floor:
            bad.append(f"evals/heldout/{name}: yields {got} pinned claims, "
                       f"committed floor is {floor} — the check is failing closed "
                       f"rather than laundering the coverage claim")
    return bad


LEDGER_LINE_REF_SHORT = {"ADR-021": "specs/decisions/ADR-021-benchmark-instrument.md"}
# PR #52 R9. A ledger row that cites `<file>:<line>` and QUOTES the sentence it
# means is self-verifying; the line number rots the moment anything is inserted
# above it, and this repo has now done that twice (the pending ADR-019 line-ref
# item is the first). Adjacency is the whole discriminator: a quotation that
# immediately follows the ref is a quotation OF it, while one further along the
# sentence belongs to a different clause — matching loosely produced four false
# positives on the committed tree, matching adjacently produces none.
# ponytail: pins refs that quote, which is the shape that CAN be checked. A
# bare `file.py:126` with nothing quoted beside it is unpinnable by any means
# short of re-reading the author's mind, and `min_refs` below is what stops
# that silence from growing — the fix for a bare ref is to quote it.
LEDGER_LINE_REF_RE = re.compile(
    r"`(?P<path>[A-Za-z0-9_./-]*):(?P<line>\d+)(?:-\d+)?`"
    r"\s*(?:reads|says)?\s*\(?\s*[\"“](?P<frag>[^\"”]{4,200})[\"”]")


def _ledger_norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[`*_]", "", s)).strip()


def check_ledger_line_refs(case):
    """Every `<file>:<line>` citation in the ledger that quotes its target must
    quote something actually on (or beside) that line. Fails closed on
    `min_refs`: a rewrite that drops the quotations drops the coverage."""
    bad, seen = [], {}
    for rel in case.get("input", {}).get("files", LEDGER_FILES):
        n_refs = 0
        for n, line in enumerate((ROOT / rel).read_text().split("\n"), 1):
            # `last` resets per row: a bare `:893` continuation always follows
            # its full path inside the same row, and carrying it across rows let
            # a deleted ref silently re-point its neighbours at another file
            # (found by mutation-testing this check, PR #52 R9)
            last = None
            for m in LEDGER_LINE_REF_RE.finditer(line):
                path = m.group("path") or last
                path = LEDGER_LINE_REF_SHORT.get(path, path)
                if m.group("path"):
                    last = path
                if not path:
                    continue
                target = ROOT / path
                n_refs += 1
                if not target.is_file():
                    bad.append(f"{rel}:{n}: cites {path} — no such file")
                    continue
                src = target.read_text().split("\n")
                lo = int(m.group("line"))
                # ±2 lines: a quoted sentence legitimately wraps in the source
                window = _ledger_norm(" ".join(src[max(0, lo - 2):lo + 2]))
                for piece in re.split(r"…|\.\.\.", m.group("frag")):
                    piece = _ledger_norm(piece)
                    if len(piece) < 6:
                        continue
                    if piece not in window:
                        bad.append(f"{rel}:{n}: {path}:{lo} does not contain the "
                                   f"quoted {piece[:70]!r}")
        seen[rel] = n_refs
    for rel, floor in sorted((case.get("input", {}).get("min_refs") or {}).items()):
        if seen.get(rel, 0) < floor:
            bad.append(f"{rel}: {seen.get(rel, 0)} verifiable line refs, committed "
                       f"floor is {floor} — failing closed")
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


def check_typography_floor(case):
    """No declared px `font-size` in the inspector stylesheet may sit below
    the floor (S4: 11px) — a human reading the inspector should never hit a
    10px badge. Catches `font-size:Npx` and the `font:Npx[/...]` shorthand's
    leading size token, both of which the file uses. `rem`/`em` are
    explicitly out of scope: nothing in the file declares a font-size in
    those units today, and resolving one into a pixel floor would need a
    root font-size baseline this check has no reason to track otherwise —
    if that ever changes, this check must grow with it rather than staying
    silently blind.
    """
    inp = case.get("input", {})
    floor = inp.get("min_px", 11)
    css = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    # R2: `\d+` cannot see a decimal size (`font-size:10.5px`) at all — a
    # sub-floor decimal shipped invisible to this check. `[\d.]+` catches it;
    # evals/adversarial/ui-typography-floor-decimal.json pins the regression.
    sizes = re.findall(r"font(?:-size)?\s*:\s*([\d.]+)px", css)
    return [f"{n}px < {floor}px floor" for n in sizes if float(n) < floor]


def _margin_centers(body):
    """True iff the rule's `margin`/`margin-inline` shorthand sets BOTH the
    inline-start and inline-end side to `auto` (R3: a substring search for
    "auto" also matched asymmetric forms like `margin-inline:auto 0` or
    `margin:0 auto 0 0`, neither of which centres — only the shared value
    in the 1- or 2-value `margin-inline` forms, or the symmetric left/right
    slots of the 2/3/4-value `margin` shorthand, actually do).
    `margin-inline` wins if both are declared, matching the cascade (it is
    the more specific property and, in this file, always comes second).
    """
    m = re.search(r"margin-inline\s*:\s*([^;]+)", body)
    if m:
        parts = m.group(1).split()
        if len(parts) == 1:
            return parts[0] == "auto"
        if len(parts) == 2:
            return parts[0] == "auto" and parts[1] == "auto"
        return False
    m = re.search(r"(?:^|[;\s])margin\s*:\s*([^;]+)", body)
    if not m:
        return False
    parts = m.group(1).split()
    if len(parts) == 1:
        return parts[0] == "auto"
    if len(parts) in (2, 3):
        return parts[1] == "auto"          # left = right = parts[1]
    if len(parts) == 4:
        return parts[1] == "auto" and parts[3] == "auto"
    return False


def check_layout_centering(case):
    """`header`/`main`/`footer` must each declare a `max-width` and a margin
    shorthand that actually centres (both inline sides `auto`), or the page
    hugs the left edge on a wide viewport (S4)."""
    inp = case.get("input", {})
    css = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    bad = []
    for sel in inp.get("selectors", ["header", "main", "footer"]):
        try:
            body = css_contrast._rule_body(css, sel)
        except ValueError as e:
            bad.append(str(e))
            continue
        if "max-width" not in body:
            bad.append(f"{sel}: no max-width declared")
        if not _margin_centers(body):
            bad.append(f"{sel}: margin does not centre (both inline sides must be auto)")
    return bad


def _flat_rules(css):
    """Yield (selector_list, body) for every rule in css, comments stripped.

    Does not track @media nesting — a rule inside `@media(...){...}` is
    yielded the same as a top-level one, losing the condition it's scoped
    under. That is a real hole (see css_contrast's own module docstring for
    the same trade elsewhere in this file), but nothing this scans (pane
    `height`, `#sidebar` `overflow`, `.it .ttl` `color`/`font-weight`) is
    declared inside a media query in this stylesheet today.
    """
    css = css_contrast._strip_comments(css)
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        yield [s.strip() for s in m.group(1).split(",")], m.group(2)


def _declared_for(css, selector, prop):
    """Last-declared `prop:` value across every rule whose selector list
    contains `selector` verbatim, or None. `last` approximates the cascade
    for same-specificity id/class selectors within one file — not a real
    resolver, same limitation css_contrast documents for its own helpers."""
    val = None
    # (?<![\w-]) stops `height` from matching inside `min-height` — a plain
    # substring search did exactly that and silently read #pane's 230px
    # min-height as if it were the shared height this check exists to pin.
    pat = r"(?<![\w-])" + re.escape(prop) + r"\s*:\s*([^;]+)"
    for sels, body in _flat_rules(css):
        if selector in sels:
            m = re.search(pat, body)
            if m:
                val = m.group(1).strip()
    return val


def check_pane_heights(case):
    """`#sidebar`, `#pane` and `#source` must resolve to the SAME declared
    `height` (S5: `#sidebar` grew with the item count while `#pane`/
    `#source` were capped at 520px inside, leaving the three columns
    ragged — tops shared via the grid's `align-items:start`, but nothing
    made the bottoms match), and the item list must declare its own
    scrolling overflow rather than letting the column grow without bound.
    """
    inp = case.get("input", {})
    css = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    panes = inp.get("panes", ["#sidebar", "#pane", "#source"])
    list_sel = inp.get("scroll_list", "#sidebar")
    bad = []
    heights = {p: _declared_for(css, p, "height") for p in panes}
    for p, h in heights.items():
        if not h:
            bad.append(f"{p}: no height declared")
    distinct = {h for h in heights.values() if h}
    if len(distinct) > 1:
        bad.append(f"panes do not share one height declaration: {heights}")
    overflow = (_declared_for(css, list_sel, "overflow-y")
                or _declared_for(css, list_sel, "overflow"))
    if not overflow or overflow in ("hidden", "visible"):
        bad.append(f"{list_sel}: no scrolling overflow declared for the item list "
                   f"(got {overflow!r})")
    return bad, {"heights": heights, "list_overflow": overflow}


def check_title_legibility(case):
    """`.it .ttl` must resolve to the page's ink token at font-weight >= 600,
    not `--dim` (S5: item titles read as grey noise beside the amber item
    code). Reads the rule's OWN declared `color:`/`font-weight:` — the same
    not-a-cascade-resolver limitation css_contrast documents; the rendered
    ratio itself stays covered by ui-contrast-and-specificity's row-title*
    pairs, which this check does not duplicate.
    """
    inp = case.get("input", {})
    css = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    sel = inp.get("selector", ".it .ttl")
    want_color = inp.get("ink_token", "var(--ink)")
    min_weight = inp.get("min_weight", 600)
    body = css_contrast._rule_body(css, sel)
    color = css_contrast.rule_color(css, sel)
    weight_m = re.search(r"font-weight\s*:\s*(\d+)", body)
    weight = int(weight_m.group(1)) if weight_m else None
    bad = []
    if color != want_color:
        bad.append(f"{sel}: color is {color!r}, want {want_color!r}")
    if weight is None or weight < min_weight:
        bad.append(f"{sel}: font-weight is {weight!r}, want >= {min_weight}")
    return bad, {"color": color, "font_weight": weight}


def _margin_side(body, side):
    """The resolved value of one side of a `margin` shorthand, mirroring the
    CSS 1/2/3/4-value expansion rules (top,right,bottom,left, wrapping)."""
    m = re.search(r"(?:^|[;\s])margin\s*:\s*([^;]+)", body)
    if not m:
        return None
    parts = m.group(1).split()
    order = {1: [0, 0, 0, 0], 2: [0, 1, 0, 1], 3: [0, 1, 2, 1], 4: [0, 1, 2, 3]}.get(len(parts))
    if not order:
        return None
    return parts[order[{"top": 0, "right": 1, "bottom": 2, "left": 3}[side]]]


def check_pane_meta_amendment(case):
    """S5 amendment (5)+(7): the parsed pane's heading/offsets/evidence block
    (`.pane-meta`) must start collapsed on every render, must not sit flush
    against the pane edge, and must be taken OUT of #pane's flex flow —
    the round-3 shape left it in-flow after pre.text, which quietly stole
    ~65px of pre.text's height and broke the content-bottom alignment
    requirement (3)/(7) beside it. `position:absolute` is the mechanical
    proof it can no longer do that; a non-zero `left` is the mechanical
    proof it isn't flush. Separately, pre.text's own bottom margin was the
    OTHER half of that 65px gap (a 14px visual gutter #source-body's iframe
    never had) — it must resolve to 0 so the two content regions' bottoms
    truly coincide, not just get closer.
    """
    inp = case.get("input", {})
    text = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    bad = []
    if re.search(r'<details[^>]*\bclass="pane-meta"[^>]*\bopen\b'
                 r'|<details[^>]*\bopen\b[^>]*\bclass="pane-meta"', text):
        bad.append("pane-meta details renders `open` — must start collapsed")
    # A bare `.pane-meta{}` rule not existing at all (only `.pane-meta[open]`,
    # the round-3 shape) is itself the defect this check exists to catch, not
    # a case for _rule_body's usual "stale pair" exception — report it as a
    # failure like any other, rather than letting the whole run crash.
    try:
        body = css_contrast._rule_body(text, ".pane-meta")
    except ValueError:
        bad.append(".pane-meta: no rule found — not position:absolute, "
                   "not inset from the pane edge")
    else:
        if not re.search(r"(?:^|[;\s])position\s*:\s*absolute", body):
            bad.append(".pane-meta: not position:absolute — back in #pane's "
                       "flex flow, competing with pre.text for height")
        left_m = re.search(r"(?:^|[;\s])left\s*:\s*([^;]+)", body)
        if not left_m or left_m.group(1).strip() in ("0", "0px"):
            bad.append(".pane-meta: no non-zero left inset — sits flush "
                       "against the pane edge")
    try:
        pre_body = css_contrast._rule_body(text, "pre.text")
    except ValueError:
        bad.append("pre.text: no rule found")
    else:
        bottom = _margin_side(pre_body, "bottom")
        if bottom is None or bottom not in ("0", "0px"):
            bad.append(f"pre.text: margin-bottom is {bottom!r}, want 0 — a "
                       "non-zero bottom margin is a gutter #source-body's "
                       "iframe never had, so the content bottoms can't match")
    return bad


def check_bottom_panel_order(case):
    """S5 amendment (6): `capabilities` must lead the panels below the split
    — it's the one worth an interviewer reading — with `pipeline trace` and
    `meta & timings` following, not leading; both mean nothing to the
    interviewer the human is optimizing this page for.
    """
    inp = case.get("input", {})
    text = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    order = inp.get("order", ["cap-box", "trace-box", "meta-box"])
    positions = {}
    bad = []
    for ident in order:
        m = re.search(r'id="' + re.escape(ident) + r'"', text)
        if not m:
            bad.append(f"#{ident}: not found")
            continue
        positions[ident] = m.start()
    for a, b in zip(order, order[1:]):
        if a in positions and b in positions and positions[a] > positions[b]:
            bad.append(f"#{a} appears after #{b} in the file — want order {order}")
    return bad


def check_truncated_notice_in_overlay(case):
    """S5 round 4 finding, live-caught while re-measuring after amendment
    (7): the truncated-text notice ('Showing the first N of M characters')
    used to render as its own in-flow sibling right after pre.text, which
    steals pre.text's flex share on a large truncated item the exact same
    way the round-3 `.pane-meta` did — jpm-2024 item 1A (136k chars, shown
    to 40k) measured a live 24px content-bottom gap from it, even after
    `.pane-meta` itself was already fixed. Any `it.truncated` reference in
    #pane's render template must sit INSIDE the `.pane-meta` block (already
    taken out of flow by amendment (7)), not beside it.
    """
    inp = case.get("input", {})
    text = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    anchor = inp.get("anchor", '$("#pane").innerHTML')
    start = text.find(anchor)
    if start < 0:
        return [f"{anchor!r} not found"]
    end = text.find(inp.get("end_anchor", 'const pre = $("#pane pre.text")'), start)
    template = text[start:end if end > 0 else start + 4000]
    meta_m = re.search(r'<details[^>]*class="pane-meta"', template)
    if not meta_m:
        return [".pane-meta block not found in #pane's render template"]
    meta_start = meta_m.start()
    bad = []
    for m in re.finditer(r"it\.truncated", template):
        if m.start() < meta_start:
            bad.append(f"it.truncated referenced before .pane-meta (offset "
                       f"{m.start()} < {meta_start}) — still an in-flow "
                       "sibling stealing pre.text's flex height")
    return bad


def _check_capability_rows(rows, label, min_count, min_cell_chars, bad):
    """Shared row-count and content-emptiness check for one capabilities.py
    table (`works_well` or `difficult` — both are flat `{header: cell}`
    dicts since the V4 README unified both sections onto one table shape).

    R1: counting rows alone is blind to a mutation that keeps every row and
    column but empties the CONTENT (every cell replaced with a same-length
    placeholder like "x") — same shape, garbage panel, and the old check
    stayed green. So content is checked two ways: no row may be
    all-identical-cells (a placeholder row has one distinct value; a real
    one does not), and every cell must clear a minimum length.
    """
    if len(rows) < min_count:
        bad.append(f"{label} has {len(rows)} rows (< {min_count})")
    for i, row in enumerate(rows):
        vals = list(row.values())
        if len(set(vals)) < 2:
            bad.append(f"{label} row {i}: every cell is the identical "
                       f"placeholder {vals[0]!r}")
        short = [v for v in vals if len(v) < min_cell_chars]
        if short:
            bad.append(f"{label} row {i}: cell(s) under {min_cell_chars} "
                       f"chars (placeholder-shaped): {short}")


def check_capabilities_parse(case):
    """The committed README must still yield a non-trivial parse through
    capabilities.py — the check that turns a README restructure red instead
    of silently emptying the `/api/capabilities` panel (S4), the INV-S2
    argument applied to docs. Written against the V4 shape: `works_well`
    and `difficult` are both flat lists of `{header: cell}` row dicts.
    """
    inp = case.get("input", {})
    readme = ROOT / inp.get("file", "README.md")
    data = web_capabilities.parse_readme(readme)
    min_works = inp.get("min_works_well", 8)
    min_diff = inp.get("min_difficult", 3)
    min_cell_chars = inp.get("min_cell_chars", 8)

    works, diff = data["works_well"], data["difficult"]
    bad = []
    _check_capability_rows(works, "works_well", min_works, min_cell_chars, bad)
    _check_capability_rows(diff, "difficult", min_diff, min_cell_chars, bad)
    return bad, {"works_well_rows": len(works), "difficult_entries": len(diff)}


def check_anchor_contract(case):
    """For every committed filing fixture, every extracted item's own
    `heading_text` must be locatable in that filing's ORIGINAL source text
    by the SAME algorithm the inspector's compare pane uses client-side
    (src/sec10k/web/anchor.py mirrors index.html's normalizeNode/
    buildSourceIndex/findAnchor) — i.e. `find_anchor` must not return None.

    This pins the anchor CONTRACT across the whole fixture set even though
    the DOM half (iframe, TreeWalker, getBoundingClientRect) cannot be
    reached from Python (PR #21 round 2, V1). Watched red against the
    round-1 algorithm (`find_anchor_frac`, kept in anchor.py for exactly
    this): on jpm-2024 it locks onto the front cross-reference table for
    several items, and pinning that mis-selection against body agreement
    scores below AGREEMENT_MIN — the same "confidently wrong" failure the
    live browser walk reproduced. Green against `find_anchor` (body
    agreement), the algorithm actually shipped.
    """
    inp = case.get("input", {})
    fixtures_dir = ROOT / inp.get("fixtures_dir", FIXTURES)
    # S8/PR#27 R1: the anchor oracle is the item's own `text`, so it is only
    # a real contract if it holds with ADR-026's exclusion ON as well. It did
    # not — the stripped body scored below AGREEMENT_MIN on six items — and
    # the case that runs this with the flag set is what says so.
    exclude = bool(inp.get("exclude_boilerplate"))
    bad = []
    checked_items = 0
    for d in sorted(p for p in fixtures_dir.iterdir() if p.is_dir()):
        f = fixture_file(d)  # D1: the one predicate app.py and the oracle use
        if f is None:
            continue  # not a single-file filing fixture (e.g. repo_hygiene/)
        is_html = f.suffix.lower() in (".htm", ".html")
        try:
            result = extract_items(str(f), exclude_boilerplate=exclude)
        except Exception as e:
            bad.append(f"{d.name}: extract_items raised {type(e).__name__}: {e}")
            continue
        view = build_view(result)
        raw = f.read_text(errors="ignore")
        chunks = web_anchor.visible_text_chunks(raw, is_html)
        index_text, _nodes = web_anchor.build_source_index(chunks)
        for it in view["items"]:
            heading = it.get("heading_text")
            if not heading:
                continue  # no heading recorded for this item — nothing to locate
            item_text = it.get("text") or ""
            needle = web_anchor.core_of(heading)
            has_body = bool(web_anchor.core_of(item_text)[len(needle):]) if needle else False
            multi = index_text.count(needle) > 1 if needle else False
            checked_items += 1
            anchor = web_anchor.find_anchor(index_text, heading, item_text)
            if anchor is None and (has_body or not multi):
                # An honest miss is only EXPECTED when the heading repeats
                # (a TOC/cross-reference entry exists to confuse it with)
                # AND the item has no body at all to disambiguate with (e.g.
                # jpm-2024 Item 6 "Reserved" — heading appears twice, body is
                # empty, so no signal distinguishes the two and `find_anchor`
                # correctly refuses to guess). Anything else failing to
                # anchor — a single occurrence that still doesn't match, or
                # a real body that still scores below threshold — is a
                # genuine contract violation.
                bad.append(f"{d.name} item {it.get('item')}: heading_text "
                          f"{heading!r} not anchorable in source")
    return bad, {"fixtures_checked": len(list(sorted(p for p in fixtures_dir.iterdir() if p.is_dir()))),
                "items_checked": checked_items}


def check_boilerplate_exclusion(case):
    """S8. The inspector's extracted-item pane must hide detected chrome when
    the caller asks for it, and be BYTE-IDENTICAL to the un-flagged run when
    it does not. Both directions, per item, on a real fixture.

    The oracle here deliberately does not call `strip_chrome`: it marks the
    characters the envelope's own `boilerplate` spans cover and rebuilds the
    expected string from the mark. A check that re-ran the implementation
    would agree with any window or off-by-one bug the implementation has.

    Pinned, per item:
      both `text` == `normalized_text[start:end][:DISPLAY_MAX]` — verbatim,
           the INV-S2 slice, in BOTH modes. PR #27 R1: `text` is also the
           oracle `findAnchor` matches against the original filing, so it is
           not the pane's to restyle. Pinning it identical across the two
           runs is what makes `ui-anchor-contract-boilerplate` true by
           construction rather than by luck.
      ON   `display_text` == that same slice with exactly the chrome
           characters inside `[start, end)` dropped, and ABSENT when it
           would equal `text`. So a strip that ignores the item window, or
           is off by one, disagrees.
      OFF  no `display_text` at all.
      both `start`, `end`, `chars`, `status`, `method`, `confidence`
           identical between the runs, and `normalized_text` identical too —
           exclusion is display-only (ADR-026 s.d, INV-S2).

    At least one item per fixture must actually come out DIFFERENT under ON,
    or the fixture has stopped exercising the exclusion and the case says so
    rather than passing vacuously.
    """
    inp = case.get("input", {})
    # "text" is in here deliberately (PR #27 R1): the anchor oracle must be
    # the same string with the flag on and off, so the two runs must agree on
    # it, not merely each be self-consistent.
    pinned = ("item", "part", "start", "end", "chars", "status", "method",
              "confidence", "heading_text", "text")
    bad, stripped_items = [], 0
    for rel in inp.get("fixtures", []):
        off = extract_items(str(ROOT / rel))
        on = extract_items(str(ROOT / rel), exclude_boilerplate=True)
        text = on.get("normalized_text") or ""
        spans = on.get("boilerplate")
        if not spans:
            bad.append(f"{rel}: exclude_boilerplate=True reported no chrome — "
                       "this fixture no longer exercises the exclusion")
            continue
        if (off.get("normalized_text") or "") != text:
            bad.append(f"{rel}: normalized_text differs between the runs — "
                       "exclusion is display-only (ADR-026 s.d)")
        hidden = bytearray(len(text))
        for sp in spans:
            hidden[sp["start"]:sp["end"]] = b"\x01" * (sp["end"] - sp["start"])
        v_off, v_on = build_view(off), build_view(on)
        if v_off.get("boilerplate_excluded") is not False:
            bad.append(f"{rel}: view reports boilerplate_excluded="
                       f"{v_off.get('boilerplate_excluded')!r} on an un-flagged run")
        if v_on.get("boilerplate_excluded") is not True:
            bad.append(f"{rel}: view reports boilerplate_excluded="
                       f"{v_on.get('boilerplate_excluded')!r} on an excluded run")
        if len(v_off["items"]) != len(v_on["items"]):
            bad.append(f"{rel}: {len(v_off['items'])} items un-flagged vs "
                       f"{len(v_on['items'])} excluded — zip below would hide it")
        for a, b in zip(v_off["items"], v_on["items"]):
            code = a.get("item")
            for k in pinned:
                if a.get(k) != b.get(k):
                    # truncated: `text` is up to DISPLAY_MAX chars and an
                    # unreadable failure is a failure nobody acts on
                    bad.append(f"{rel} item {code}: {k} moved under exclusion "
                               f"({a.get(k)!r:.90} -> {b.get(k)!r:.90})")
            s, e = a.get("start"), a.get("end")
            if s is None or e is None:
                if a["text"] or b["text"]:
                    bad.append(f"{rel} item {code}: null span but non-empty text")
                continue
            raw = text[s:e]
            for label, got in (("un-flagged", a["text"]), ("excluded", b["text"])):
                if got != raw[:DISPLAY_MAX]:
                    bad.append(f"{rel} item {code}: {label} `text` is no longer "
                               f"the verbatim slice — findAnchor matches this "
                               f"string against the original filing (INV-S2, R1)")
            if "display_text" in a:
                bad.append(f"{rel} item {code}: un-flagged run carries a "
                           f"display_text — nothing is hidden with the flag off")
            want = "".join(c for k, c in enumerate(raw, s) if not hidden[k])
            pane = b.get("display_text", b["text"])
            if pane != want[:DISPLAY_MAX]:
                bad.append(
                    f"{rel} item {code}: excluded pane is identical to the "
                    f"un-flagged one — nothing was stripped"
                    if pane == a["text"] else
                    f"{rel} item {code}: excluded pane != the item slice minus "
                    f"its own chrome runs ({len(pane)} chars shown, "
                    f"expected {len(want[:DISPLAY_MAX])})")
            if want == raw and "display_text" in b:
                bad.append(f"{rel} item {code}: display_text emitted although it "
                           f"is identical to text — dead payload")
            # not redundant with the `chars` pairing above: that one only says
            # the two runs AGREE, and they would agree if both reported the
            # shown length. This says WHICH length is right.
            if b["chars"] != e - s:
                bad.append(f"{rel} item {code}: chars became {b['chars']} — it "
                           f"reports the SPAN length ({e - s}), not the shown length")
            if want != raw:
                stripped_items += 1
    if inp.get("fixtures") and not stripped_items:
        bad.append("no item anywhere had chrome inside its own span — the "
                   "exclusion direction was never exercised")
    return bad, {"items_stripped": stripped_items}


JS_COMMENT_RE = re.compile(r"^[ \t]*//.*$", re.M)
JS_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
PY_COMMENT_RE = re.compile(r"^[ \t]*#.*$", re.M)


def _live(src, lang):
    """`src` with commented-out code removed. A pin has to be satisfied by
    code that RUNS: commenting a call site out and leaving it in the file is
    a realistic way to sever the wire while every pin still finds its text
    (measured — it passed the first version of the allow-list, and so did an
    `<!-- -->`-ed checkbox).

    Per language, deliberately. Only FULL-line `//` goes, so the `https://`
    inside a URL survives; `/* */` goes wherever it appears, since the
    stylesheet's 22 comments are all genuine and nothing in this file opens
    `/*` inside a string; and `#` is stripped ONLY from Python, because the
    inspector's stylesheet is full of id selectors like `#banner{...}` that
    start a line with `#` and are not comments at all.

    The `/* */` form was missing until PR #27 R10, which is worth recording
    because of WHAT it re-admitted: block-commenting a call site while
    leaving the pinned text inside the comment reproduced both of the
    findings this check was rewritten for, with the whole gate green."""
    if lang == "py":
        return PY_COMMENT_RE.sub("", src)
    return JS_COMMENT_RE.sub(
        "", JS_BLOCK_COMMENT_RE.sub("", HTML_COMMENT_RE.sub("", src)))


def _fn_body(src, signature):
    """The `{...}` body of one JS function, by brace matching from `signature`.

    Text pins can say a string is in the file; they cannot say WHICH function
    holds it, and for the escalation header that distinction is the whole
    property — in `call()` it covers all three extract modes, at a call site it
    covers one. Returns None when the signature is absent or unbalanced.
    """
    i = src.find(signature)
    if i < 0:
        return None
    i = src.find("{", i + len(signature) - 1)
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
    return None


def _squash(s):
    """Whitespace-free form. Same argument as `anchor.py`'s `core_of`: how a
    line happens to be wrapped or indented carries no information about what
    it does, so it is not part of what "the same expression" means here."""
    return "".join(s.split())


# Every expression that carries the checkbox's value from the DOM to
# extract_items, pinned WHOLE, plus what each one is for.
#
# PR #27 R5 and R6 are why this is an allow-list. Two rounds of asking each
# hop a QUESTION about itself — does it mention the flag? do the two ends use
# the same key? — left the VALUE unchecked at every hop but one, and `not
# bool(...)`, `!= "1"`, `False and bool(...)`, `return true`, `$("#exclude-bp
# -OLD")` and a deleted `display_text ??` all answered the questions
# correctly while severing the wire. A question can always be answered by a
# broken hop, and a list of FORBIDDEN operators only ever bans the inversions
# somebody already thought of. Pinning the permitted expression makes
# everything else red by default, including the next inversion nobody
# thought of.
#
# ponytail: whitespace-insensitive but token-exact, so reformatting survives
# and a semantic edit does not. A DELIBERATE change to any of these must
# update the pin — the friction is the point, because editing the wire is
# exactly the moment to re-check that it still carries the checkbox.
WIRE_UI = [
    ("the excludeBp() helper reads the checkbox's own .checked",
     'function excludeBp(){ const c = $("#exclude-bp"); return !!(c && c.checked); }'),
    # S9 (ADR-032): the Markdown checkbox rides the same three wires; the
    # fixture/url pins moved with the body literal, deliberately
    # Owner, 2026-08-27: the escalate flag came OFF all three wires with the
    # control that fed it. The server decides now, so a request carrying an
    # `escalate` key would be a client re-acquiring a say it no longer has —
    # `ROUTING_UI_ABSENT` is what forbids that; these two only pin the two
    # display flags that remain.
    ("the fixture mode puts the checkbox value on the wire",
     'JSON.stringify({fixture: $("#fx").value, exclude_boilerplate: excludeBp(), markdown: renderMd()})'),
    ("the url mode puts the checkbox value on the wire",
     'JSON.stringify({url: $("#url").value, exclude_boilerplate: excludeBp(), markdown: renderMd()})'),
    ("the upload mode appends the checkbox value to its query string",
     '(excludeBp() ? "&exclude_boilerplate=1" : "")'),
    ("the pane SAYS it is hiding text — R5's defect was un-stripped text "
     "under this label, and the inverse, a silent strip, is the same lie",
     '(VIEW.boilerplate_excluded ? "boilerplate hidden · " : "")'),
    # D10 moved this pin: the same render now carries role=region + an
    # item-naming aria-label (ui-item-text-region). D14 moved it again:
    # tabindex="0" (ui-item-text-region-focusable). Re-checked per the pin's
    # own failure message — the STRIPPED string is still what is rendered,
    # `display_text ?? text` unmodified, and the new attributes are display
    # metadata that touch neither end of the wire.
    ("the extracted-item pane renders the STRIPPED string",
     '<pre class="text" role="region" tabindex="0" aria-label="Item ${esc(it.item)} extracted text">'
     '${esc(it.display_text ?? it.text)}</pre>'),
    ("the truncation notice counts the STRIPPED string",
     '${(it.display_text ?? it.text).length.toLocaleString()}'),
]

# per handler, sliced out of app.py so each is unique without more context
WIRE_HANDLER = {
    "/api/extract/fixture":
        'exclude_boilerplate=bool((body or {}).get("exclude_boilerplate"))',
    "/api/extract/url":
        'exclude_boilerplate=bool((body or {}).get("exclude_boilerplate"))',
    "/api/extract/upload":
        'exclude_boilerplate=request.query_params.get("exclude_boilerplate") == "1"',
}

# A pin proves its expression is present; it cannot prove nothing SHADOWS it.
# A second `function excludeBp(){ return true; }` after the pinned one leaves
# the pin satisfied and wins at runtime (declarations hoist, last one binds),
# and a second `pre.text` render makes `$("#pane pre.text")` ambiguous. So the
# definition sites themselves must be unique — measured: the shadowing attack
# passed the allow-list until this was added.
UNIQUE_UI = [
    ("nothing may shadow the excludeBp() helper", "function excludeBp"),
    # D10: opening tag only, so the pin survives the ARIA attributes added to
    # it while still counting every `pre.text` `$("#pane pre.text")` could hit
    ("nothing may shadow the extracted-item render", '<pre class="text"'),
]

WIRE_API = [
    # S9 (ADR-032) added the Markdown flag to the same call; the pin moved with
    # it deliberately, and the wire was re-checked (see the ADR). D11 (ADR-036)
    # added the escalate flag the same way.
    #
    # Owner, 2026-08-27 ("make it default on, remove the button"). PR #58 R6
    # pinned TWO expressions here — a request-level `escalate` flag ANDed with
    # the deployment's arming switch, and the call carrying the result. There
    # is no request-level flag any more, so the AND is gone and one pin is
    # left: `_run` escalates on the DEPLOYMENT's own switch and always carries
    # the process-wide budget. The property this pin protects is unchanged and
    # is now carried by a single expression — the two display flags reach
    # `extract_items` unmodified, and escalation reaches it through a decision
    # and never as a constant.
    #
    # PR #61 R10 moved that decision to a token door, ADR-041 removed the door
    # the next day, and ADR-043 restored it WITH the page half it had been
    # missing — so `escalate=` carries the door's verdict again and the budget
    # rides that same name; the call cannot escalate on one condition and bill
    # against another. `escalation_locks` pins the AST half (the argument is a
    # name, never a literal) and `escalation_choke_point` pins where that name
    # comes from; this pins the text.
    ("_run forwards the two display flags unmodified, and escalates and bills "
     "on the same single decision",
     "extract_items(path, exclude_boilerplate=exclude_boilerplate, "
     "blocks=markdown, escalate=escalate, "
     "budget=server_budget() if escalate else None, source_url=source_url)"),
    # PR #61 R4. The page stopped reading this when the control went away, and
    # `routing_provenance`'s pin on the reader went with it — so deleting the
    # key reddened nothing, while ADR-036 §h2 had just started claiming it is
    # what keeps the deployment's arming state inspectable. Either the claim
    # goes or the key is pinned; the key is one line and the claim is true.
    ("/api/meta publishes the deployment's arming state",
     '"escalation_enabled": ESCALATION_ENABLED'),
]

# no trailing `\)`: `@app.post("/api/extract/x", response_model=None)` is
# app.py's own decorator style (see `@app.get("/", response_class=...)`),
# and requiring the paren immediately after the literal let a fourth
# unwired mode through in that spelling (PR #27 R11)
ROUTE_RE = re.compile(r'@app\.post\("(/api/extract/[^"]+)"')


def check_boilerplate_plumbing(case):
    """S8. The ADR-026 flag has to survive the whole trip — checkbox,
    excludeBp(), request, handler, `_run`, `extract_items` — the checkbox has
    to start OFF, and the pane has to render the string the exclusion
    produced. None of that is reachable from the eval harness (no browser,
    and importing app.py would drag fastapi into the dependency-free unit
    job), so it is checked in the two files that carry the wire, the shape
    the ui-* checks have used since S3.

    It works by ALLOW-LIST: `WIRE_UI`, `WIRE_HANDLER` and `WIRE_API` above
    hold every expression on the path, each of which must appear exactly once
    in the file's LIVE text — `//`, `/* */`, `<!-- -->` and Python `#`
    comments stripped, so a call site commented out in any of those four
    forms cannot satisfy its own pin. (Narrowed deliberately: it once said
    "a dead call site cannot satisfy its own pin", and PR #27 R10 was
    precisely the fifth form. Dead code that is not COMMENTED — inside a
    string literal, or behind a condition that is never true — still
    satisfies its pin.) `UNIQUE_UI` additionally forbids a second definition
    shadowing a pinned one; the routes are pinned as a set, so a fourth input
    mode declared with an `@app.post("/api/extract/…"` decorator cannot be
    added without wiring it — any OTHER way of registering a route, such as
    a single-quoted literal or `app.add_api_route`, is not seen; and the
    checkbox may be neither `checked` nor `disabled`. None of those is
    hypothetical: each was written as an attack on the allow-list and passed
    it before it was closed (`ui-boilerplate-wire-values` pins them).

    What it still cannot do is in the debt row: it cannot prove FastAPI
    BINDS any of this. An HTTP case was considered and rejected — see the
    row for the reason and for the correction to what that row first claimed.
    """
    inp = case.get("input", {})
    ui = _live((ROOT / inp.get("ui_file", UI_STYLESHEET)).read_text(), "js")
    api = _live((ROOT / inp.get("api_file", API_FILE)).read_text(), "py")
    bad = []
    boxes = re.findall(r'<input[^>]*id="exclude-bp"[^>]*>', ui)
    if len(boxes) != 1:
        bad.append(f"expected exactly one #exclude-bp checkbox in the UI, "
                   f"found {len(boxes)}")
    for box in boxes:
        if 'type="checkbox"' not in box:
            bad.append(f"#exclude-bp is not a checkbox: {box}")
        if re.search(r"\bchecked\b", box):
            bad.append(f"#exclude-bp defaults to CHECKED — ADR-026 is opt-in "
                       f"and OFF must stay today's behaviour: {box}")
        # a box that cannot be ticked is OFF forever, which passes every
        # other check here and makes the whole feature unreachable
        if re.search(r"\bdisabled\b", box):
            bad.append(f"#exclude-bp is DISABLED — the wire is intact and the "
                       f"capability is still unreachable: {box}")

    def pin(haystack, where, why, expr):
        n = _squash(haystack).count(_squash(expr))
        if n != 1:
            bad.append(f"{where}: {why} — expected exactly one "
                       f"`{expr}`, found {n}. If this expression changed on "
                       f"purpose, update its pin AND re-check that the wire "
                       f"still carries the checkbox's value unmodified.")

    for why, expr in WIRE_UI:
        pin(ui, "index.html", why, expr)
    for why, token in UNIQUE_UI:
        n = _squash(ui).count(_squash(token))
        if n != 1:
            bad.append(f"index.html: {why} — `{token}` occurs {n} times, "
                       f"expected 1")
    for why, expr in WIRE_API:
        pin(api, "app.py", why, expr)

    # Key verification shares the limited /api/extract/ namespace for abuse
    # protection, but it is not a fourth filing-input mode.
    routes = set(ROUTE_RE.findall(api)) - {"/api/extract/verify-key"}
    if routes != set(EXTRACT_ENDPOINTS):
        bad.append(f"app.py's /api/extract routes are {sorted(routes)}, not the "
                   f"{sorted(EXTRACT_ENDPOINTS)} this check knows how to pin — "
                   f"an input mode was added or removed without wiring it")
    for ep in sorted(routes & set(EXTRACT_ENDPOINTS)):
        j = api.index(f'"{ep}"')
        k = api.find("\n@app.", j + 1)
        pin(api[j:k if k > 0 else len(api)], f"app.py {ep}",
            "the handler reads the flag off the request and forwards it "
            "unmodified", WIRE_HANDLER[ep])
    return bad


LINK_RE = re.compile(r"<link\b[^>]*>", re.I)
# quoted OR unquoted values — PR #33 R1: `<link rel=stylesheet href=https://…>`
# is valid HTML and the quoted-only form skipped it as "not a stylesheet"
ATTR_RE = re.compile(r"""([\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""")
NOSCRIPT_RE = re.compile(r"<noscript>.*?</noscript>", re.S | re.I)
EXTERNAL_HREF_RE = re.compile(r"^(?:https?:)?//", re.I)
# media values a screen never matches — a stylesheet scoped to one of these
# does not block first paint. Anything else (unset, `all`, `screen`, any
# `(...)` query) is evaluated against the screen and blocks. `not all` is the
# other standard non-blocking idiom (PR #33 R2); values compare lowercased
# because media types are case-insensitive.
NON_SCREEN_MEDIA = ("print", "speech", "not all")


def check_external_stylesheets_nonblocking(case):
    """S3-FONT (gates-2026-08-22 `S3_browser_evidence.font_fallback_finding`,
    MEDIUM, measured): `<link rel=stylesheet>` to fonts.googleapis.com was
    render-blocking, so an origin that BLACKHOLES the connection (vs. refuses
    it) stopped the inspector painting at all — control FCP 88ms, refused
    28ms, blackholed never painted in an 8s budget. The fix is the one-
    attribute pattern `media="print" onload="this.media='all'"`: the sheet is
    fetched off the critical path and promoted to screen once it arrives.

    The check asserts the PROPERTY, not that literal: every live `<link>`
    whose `rel` contains `stylesheet` and whose `href` names another host
    must carry a `media` type a screen never matches AND an `onload` that
    assigns `media` to a screen-matching value — without the second half a
    `print` sheet simply never applies, which is the other way to get the
    fix wrong. Same-origin sheets are out of scope (the finding is about a
    third-party host you cannot make answer); `@import url(https://…)` inside
    `<style>` is not scanned — the file has none, and one would be the same
    defect — noted so the next reader does not assume coverage.

    `<noscript>` blocks are stripped before scanning, deliberately and
    honestly: the conventional no-JS fallback is a plain blocking link, and it
    IS render-blocking for a JS-off visitor on a blackholing network. That is
    accepted here because the inspector is fetch-driven end to end — with JS
    off the visitor has the static shell and nothing else — so a webfont that
    arrives late costs them nothing the page still offers.
    """
    inp = case.get("input", {})
    text = _live((ROOT / inp.get("file", UI_STYLESHEET)).read_text(), "js")
    text = NOSCRIPT_RE.sub("", text)
    bad = []
    for tag in LINK_RE.findall(text):
        attrs = {k.lower(): (v or w or u) for k, v, w, u in ATTR_RE.findall(tag)}
        if ("stylesheet" not in attrs.get("rel", "").lower().split()
                or not EXTERNAL_HREF_RE.match(attrs.get("href", ""))):
            continue
        href = attrs["href"].split("?")[0]
        media = attrs.get("media", "").strip().lower()
        onload = attrs.get("onload", "")
        if media not in NON_SCREEN_MEDIA:
            bad.append(f"{href}: external stylesheet is render-blocking "
                       f"(media={media or 'unset'!r}) — a blackholed host stops "
                       f"first paint; want media=print + an onload promoting it "
                       f"to all")
        elif not re.search(r"\bmedia\s*=\s*['\"]?(all|screen)\b", onload, re.I):
            bad.append(f"{href}: media={media!r} but no onload promoting it to "
                       f"all/screen — the sheet never applies on screen")
    return bad


# Text a source can hand the resolver that is NOT a build identity, and must
# therefore resolve to `unknown` (ADR-028) — fed through BOTH the file and the
# `GIT_SHA` override, because the ruling is per-value, not per-source. None of
# these is hypothetical: `printf %s "$FOO" > f` with FOO unset writes the empty
# file, a build step whose shell never expands writes the literal, and an
# operator acting on the S2 row's own title ("Set `GIT_SHA` on Zeabur") reaches
# for `latest` or `main` or pastes a `${ZEABUR_GIT_COMMIT_SHA}` reference that
# nothing expands at runtime (PR #31 R1: all four were build labels).
#
# NOT exhaustive, and the list does not claim to be: non-UTF-8 bytes are a
# known gap (PR #31 R8, `## Debt` in tasks/TODO.md) — `build_sha` raises rather
# than resolving on those.
NOT_A_SHA = ["", "\n", "   ", "  \n\n ", "$ZEABUR_GIT_COMMIT_SHA",
             "${ZEABUR_GIT_COMMIT_SHA}", "unknown", "HEAD", "main", "latest",
             "a1b2c3", "0123456789abcdef0123456789abcdef012345678",
             "zzzzzzz", "a1b2c3d4-dirty", "a1b2 c3d4e5f6"]

# (file contents, reported label) — a real sha IS reported, cut to 12 like the
# env-var branch always did, and surrounding whitespace is not a lie.
REAL_SHA = [
    ("0f1e2d3c4b5a", "0f1e2d3c4b5a"),
    ("0f1e2d3c4b5a\n", "0f1e2d3c4b5a"),
    ("  0f1e2d3c4b5a6978  \n", "0f1e2d3c4b5a"),
    ("0f1e2d3c4b5a69788796a5b4c3d2e1f001234567", "0f1e2d3c4b5a"),
    ("abcdef1", "abcdef1"),
]

# Pinned WHOLE, same argument as WIRE_UI: a question about the build command
# ("does it mention the variable?") is answerable by a command that writes the
# wrong thing. `printf %s` and not `echo`: `echo` appends a newline, which is
# harmless here only by accident, and `printf` without a format string cannot
# be handed a sha starting with `-`.
BUILD_COMMAND = 'printf %s "${ZEABUR_GIT_COMMIT_SHA:-}" > BUILD_SHA || true'
META_CALL = '"git_sha": git_sha(ROOT)'

# Location variables exist to point git at a repository OTHER than the one you
# are standing in, which is the opposite of the question this resolver asks.
GIT_LOCATION_VARS = ["GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"]


def _no_git_env():
    """The ambient environment with EVERY `GIT_*` variable removed.

    For BUILDING a fixture repository, where the only safe assumption is that
    we control nothing. Deliberately wider than the resolver's own scrub:
    `GIT_INDEX_FILE` does not redirect `rev-parse`, so the resolver has no
    reason to strip it, but it absolutely redirects `git commit` — and PR #31
    R4 measured what that cost. `git commit -a` sets it, and so does
    committing from a linked worktree (`.git/worktrees/<name>/index`), which
    is how this PR was authored. Under an inherited absolute value the fixture
    commit lands in another repository's index, `_temp_repo` returns None, and
    every source-3 assertion silently disappears — the git-first falsifier
    went from 2 failures to 0 inside exactly the pre-commit gate that is
    supposed to be enforcing it.
    """
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _temp_repo(td):
    """`td` made into a real one-commit checkout; its short HEAD, or None.

    Source 3 is the ONE branch a temp directory cannot exercise by accident,
    and PR #31 R4 measured the cost of not exercising it: a resolver reordered
    to try `git rev-parse` FIRST left this check at 0 failures, so the
    published precedence table was enforced by nothing. Builds in
    `_no_git_env()` rather than in whatever the caller inherited — the caller
    is the thing being tested, so its environment is not a safe place to
    construct the fixture from. A None here is NOT silently tolerated; see
    the call site.
    """
    env = _no_git_env()

    def run(*a):
        return subprocess.run(["git", *a], cwd=td, env=env,
                              capture_output=True, text=True)
    if run("init", "-q").returncode:
        return None
    run("config", "user.email", "eval@example.invalid")
    run("config", "user.name", "eval")
    if run("commit", "--allow-empty", "-q", "-m", "build-identity").returncode:
        return None
    return run("rev-parse", "--short", "HEAD").stdout.strip() or None


def check_build_identity(case):
    """S2/ADR-028. `/api/meta` must report the sha of the build actually
    running, and must say `unknown` rather than anything it cannot stand
    behind. Three parts, because the property has three halves that fail
    independently:

    1. the RESOLVER, exercised for real — `build_id.py` is stdlib-only and
       imports no fastapi, precisely so this case can call it (ADR-003: the
       CI jobs install nothing). Every value a build can plausibly write is
       fed through BOTH sources that carry text — the file and the `GIT_SHA`
       override — and only a hex sha may come back out of either.
    2. the PRECEDENCE, all four steps, and the ordering asserted rather than
       merely observed: source 3 is exercised inside a real `git init`
       checkout so that BUILD_SHA and GIT_SHA are seen to OUTRANK it, not
       just to answer where it cannot (PR #31 R4). An ambient GIT_DIR must
       not let source 3 answer about a different repository, on the explicit
       environ AND on the default one `/api/meta` actually uses (R2).
    3. the DEPLOYMENT plumbing, pinned as text, because nothing here can run
       a Zeabur build: the `build_command` that writes the file, the
       `.gitignore` line that keeps it out of the repo (a committed sha is
       the stale label the S2 row refuses), and `/api/meta` calling the
       shared resolver rather than growing a second copy.
    """
    inp = case.get("input", {})
    bad = []
    # A real PATH so `git` is found, and nothing else. `git rev-parse` honours
    # GIT_DIR from the environment and the pre-commit hook SETS it — which is
    # how this check first went red: the resolver answered with the repo's HEAD
    # while pointed at a temp directory that is not a repository at all. That
    # was a defect in `git_sha`, not in the test, and PR #31 R2 found the first
    # fix half-done — it closed the leak only for callers passing an explicit
    # environ, while `/api/meta` passes none. The resolver now strips the git
    # location variables on every path; `clean` here is belt-and-braces so a
    # failure names the resolver rather than this check's own environment.
    clean = {"PATH": os.environ.get("PATH", "")}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        f = root / build_id.BUILD_SHA_FILE
        if build_id.git_sha(root, clean) != "unknown":
            bad.append("no injected file, no GIT_SHA and no .git must be "
                       f"`unknown`, got {build_id.git_sha(root, clean)!r}")
        for junk in NOT_A_SHA:
            f.write_text(junk)
            got = build_id.git_sha(root, clean)
            if got != "unknown":
                bad.append(f"{build_id.BUILD_SHA_FILE} holding {junk!r} became "
                           f"the build label {got!r} — a build label that is "
                           f"not a sha is worse than `unknown`")
        for text, want in REAL_SHA:
            f.write_text(text)
            got = build_id.git_sha(root, clean)
            if got != want:
                bad.append(f"{build_id.BUILD_SHA_FILE} holding {text!r} must "
                           f"report {want!r}, got {got!r}")
        f.write_text("0f1e2d3c4b5a")
        got = build_id.git_sha(root, dict(clean, GIT_SHA="deadbeefcafe"))
        if got != "0f1e2d3c4b5a":
            bad.append(f"the build-written sha must outrank a hand-set "
                       f"GIT_SHA — only the build knows it is current — "
                       f"got {got!r}")
        f.unlink()
        got = build_id.git_sha(root, dict(clean, GIT_SHA="deadbeefcafe"))
        if got != "deadbeefcafe":
            bad.append("with no injected file the GIT_SHA override must still "
                       f"answer, got {got!r}")
        # PR #31 R1. The ruling is per-VALUE, not per-source: the override is
        # the branch an operator actually reaches for (the row is titled "Set
        # GIT_SHA on Zeabur"), so it is exactly where a placeholder gets typed.
        for junk in NOT_A_SHA:
            got = build_id.git_sha(root, dict(clean, GIT_SHA=junk))
            if got != "unknown":
                bad.append(f"GIT_SHA={junk!r} became the build label {got!r} — "
                           f"the same value is rejected when it arrives in "
                           f"{build_id.BUILD_SHA_FILE}, and where a lie enters "
                           f"from does not make it true")
        # PR #31 R2. `/api/meta` calls `git_sha(ROOT)` with no environ, so the
        # DEFAULT path is the deployed path: an ambient GIT_DIR must not let
        # `git rev-parse` answer about a repository that is not `root`.
        for name in GIT_LOCATION_VARS:
            got = build_id.git_sha(root, dict(clean, **{name: str(ROOT / ".git")}))
            if got != "unknown":
                bad.append(f"{name} in the environment made a non-repository "
                           f"report {got!r} — that is another repo's sha, "
                           f"served as this build's identity")
        saved = {k: os.environ.get(k) for k in GIT_LOCATION_VARS}
        try:
            os.environ["GIT_DIR"] = str(ROOT / ".git")
            got = build_id.git_sha(root)          # exactly app.py's call shape
            if got != "unknown":
                bad.append(f"on the DEFAULT environ — the one /api/meta uses — "
                           f"an ambient GIT_DIR made a non-repository report "
                           f"{got!r}. The deployed path is the one that has to "
                           f"be closed, not just the one the eval passes.")
        finally:
            for k, v in saved.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    # PR #31 R4. Source 3, and the only place it can be exercised: a real
    # checkout, so that BUILD_SHA and GIT_SHA are seen to OUTRANK it rather
    # than merely to answer where it cannot.
    clean_full = _no_git_env()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        head = _temp_repo(td)
        if not head:
            # PR #31 R4: the previous version skipped here in silence, so a
            # broken fixture and a passing precedence table were the same
            # observation. An assertion that cannot run has not passed.
            bad.append("could not build a temp git checkout, so the source-3 "
                       "precedence assertions did not run — this check reports "
                       "nothing about precedence until that is fixed")
        else:
            got = build_id.git_sha(root, clean_full)
            if got != head:
                bad.append(f"source 3: a real checkout must report its own "
                           f"short sha {head!r}, got {got!r}")
            got = build_id.git_sha(root, dict(clean_full, GIT_SHA="deadbeefcafe"))
            if got != "deadbeefcafe":
                bad.append(f"precedence: GIT_SHA must outrank `git rev-parse` "
                           f"in a real checkout, got {got!r} (HEAD is {head!r})")
            (root / build_id.BUILD_SHA_FILE).write_text("0f1e2d3c4b5a")
            got = build_id.git_sha(root, dict(clean_full, GIT_SHA="deadbeefcafe"))
            if got != "0f1e2d3c4b5a":
                bad.append(f"precedence: the build-injected sha must outrank "
                           f"BOTH GIT_SHA and `git rev-parse` in a real "
                           f"checkout, got {got!r} (HEAD is {head!r})")

    # local dev: a working checkout still reports its own short sha. The real
    # ambient environment here, with only the override cleared — this is the
    # branch that is SUPPOSED to find a repository. Skipped only where git
    # cannot answer at all; a real BUILD_SHA sitting in the tree is the
    # file-first case above, already pinned.
    # PR #31 R10: the oracle must measure HEAD in the SAME environment the
    # resolver resolves in. Once the resolver started stripping the location
    # vars and this subprocess did not, an ambient GIT_DIR made the two
    # disagree and turned correct code red — a false failure in precisely the
    # pre-commit-hook condition this check's own history is about.
    head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
        env={k: v for k, v in os.environ.items() if k not in GIT_LOCATION_VARS},
        capture_output=True, text=True).stdout.strip()
    if head and not build_id.build_sha(ROOT):
        got = build_id.git_sha(ROOT, dict(os.environ, GIT_SHA=""))
        if got != head:
            bad.append(f"a checkout with a .git must report its own short sha "
                       f"{head!r}, got {got!r}")

    zb = json.loads((ROOT / inp.get("zbpack_file", ZBPACK)).read_text())
    if _squash(zb.get("build_command", "")) != _squash(BUILD_COMMAND):
        bad.append(f"{ZBPACK}: build_command is "
                   f"{zb.get('build_command')!r}, not the pinned "
                   f"`{BUILD_COMMAND}` — this is the ONLY thing that puts a "
                   f"real sha in the image, and Zeabur exposes "
                   f"ZEABUR_GIT_COMMIT_SHA in the build phase only")
    ignored = [l.strip() for l in (ROOT / GITIGNORE).read_text().splitlines()]
    if build_id.BUILD_SHA_FILE not in ignored:
        bad.append(f"{GITIGNORE} does not ignore {build_id.BUILD_SHA_FILE} — a "
                   f"committed build sha is stale the moment it is committed")
    tracked = subprocess.run(["git", "ls-files", "--", build_id.BUILD_SHA_FILE],
                             cwd=ROOT, capture_output=True, text=True).stdout
    if tracked.strip():
        bad.append(f"{build_id.BUILD_SHA_FILE} is TRACKED: {tracked.strip()}")

    api = _live((ROOT / inp.get("api_file", API_FILE)).read_text(), "py")
    n = _squash(api).count(_squash(META_CALL))
    if n != 1:
        bad.append(f"app.py: /api/meta must report the shared resolver's "
                   f"answer — expected exactly one `{META_CALL}`, found {n}")
    if re.search(r"def\s+_?git_sha\b", api):
        bad.append("app.py defines its own git_sha — build identity has one "
                   "implementation, in build_id.py, or the eval set is "
                   "exercising a copy nobody serves")
    return bad


def _single_file_dirs(root):
    """{name: file} for every directory under `root` holding exactly one file
    — the fixture rule, spelled out here INDEPENDENTLY of
    `src/sec10k/web/fixtures.py` so a wrong predicate cannot certify itself."""
    out = {}
    for d in sorted(root.iterdir()):
        if d.is_dir():
            files = [f for f in d.iterdir() if f.is_file()]
            if len(files) == 1:
                out[d.name] = files[0]
    return out


# both of app.py's readers of evals/fixtures/ must ask the shared rule
META_FIXTURES = '"fixtures": deployed_fixtures()'  # the listing /api/meta serves
RESOLVE_CALL = "f = fixture_file(d)"               # _fixture_file, request time
# PR #61 R1: and request-time resolution must be the LISTING, not merely the
# same predicate as it — an exclusion that only shrinks the menu is cosmetic
# while the deep link and a hand-written POST still name a fixture directly.
#
# PR #61 R13 removed the single-line text pin that used to live here
# (`DEPLOY_GUARD = "if name not in deployed_fixtures():"`, counted once in one
# function) and replaced it with the DOMINANCE property below. Counting a
# literal proves the guard is written somewhere; it says nothing about a SECOND
# function that resolves a fixture without it, which is a new endpoint away and
# leaves every existing assertion green. The names a resolver cannot use
# without going through `_fixture_file`:
FIXTURE_PRIMITIVES = ("FIXTURES", "fixture_file")
FIXTURE_RESOLVER = "_fixture_file"


def check_fixture_discovery(case):
    """D1. A fixture directory is one holding exactly one file (the filing),
    and every reader of `evals/fixtures/` must agree on that set: the list
    `/api/meta` serves (`list_fixtures`, hence the inspector dropdown) and
    the (name, path) pairs `evals.oracle.iter_fixtures()` yields (hence
    `evals/bench.py`'s timed population and `oracle.run_all`). Before D1
    the first listed every directory, the second yielded the largest non-.md
    file of every directory, and only the request-time `_fixture_file`
    applied the rule — so `repo_hygiene/` (14 regression stubs) was a dead
    dropdown entry and a would-be dev fixture.

    app.py cannot be imported here (fastapi; ADR-003's no-install CI jobs),
    so `list_fixtures` is called from the stdlib module app.py imports it
    from, and app.py's two uses of the rule — `/api/meta`'s listing and
    `_fixture_file`'s resolution — are pinned as live text, the way
    `build_identity` pins `git_sha(ROOT)` (`META_FIXTURES`, `RESOLVE_CALL`).

    `input.fixtures_dirs` lists the roots to check; the default is the real
    tree plus the committed regression tree under repo_hygiene/, whose
    `two-files/` directory is the shape the three readers disagreed on.

    RE-PINNED 2026-08-27 (PR #61 R1), and read this before assuming the
    invariant weakened. D1's property was a three-way EQUALITY: single-file set
    == list_fixtures == iter_fixtures. The deployment now refuses to serve two
    fixtures that fire D8's trigger, so the web listing is deliberately SMALLER
    than the eval corpus — which is exactly what D1 forbade, and is why it is
    re-pinned rather than relaxed. The relationship asserted now:

        single-file set  ==  list_fixtures  ==  iter_fixtures      (unchanged:
            the EVAL corpus is untouched, and both excluded fixtures are still
            eval fixtures the oracle and the bench see)
        deployed_fixtures  ==  single-file set  -  DEPLOY_EXCLUDED (new)
        DEPLOY_EXCLUDED    is a subset of the single-file set       (new)

    The last one matters: an exclusion naming a fixture that does not exist is
    a typo that silently protects nothing, and it is the failure this shape
    invites. There is still ONE predicate (`fixture_file`) and now one named
    subtraction on top of it, in one place — never a second predicate. The
    money half — that the named set actually contains the two hot fixtures, and
    that RESOLUTION consults it and not just the listing — is
    `check_deployed_exclusion`.
    """
    inp = case.get("input", {})
    roots = inp.get("fixtures_dirs") or [FIXTURES,
                                         f"{FIXTURES}/repo_hygiene/fixture-discovery"]
    bad, info = [], {}
    for rel in roots:
        root = ROOT / rel
        want = _single_file_dirs(root)
        listed = list_fixtures(root)
        yielded = dict(eval_oracle.iter_fixtures(root))
        for name in sorted(set(listed) - set(want)):
            bad.append(f"{rel}: /api/meta lists {name!r}, which does not hold "
                       f"exactly one file")
        for name in sorted(set(want) - set(listed)):
            bad.append(f"{rel}: /api/meta omits fixture {name!r}")
        for name in sorted(set(yielded) - set(want)):
            bad.append(f"{rel}: iter_fixtures yields {name!r} -> "
                       f"{yielded[name].name}, a directory that does not hold "
                       f"exactly one file")
        for name in sorted(set(want) - set(yielded)):
            bad.append(f"{rel}: iter_fixtures omits fixture {name!r}")
        # PR #61 R1. The deployed listing is the eval corpus MINUS the named
        # exclusions — not "roughly", exactly, in both directions.
        served, want_served = set(deployed_fixtures(root)), set(want) - DEPLOY_EXCLUDED
        for name in sorted(served - want_served):
            bad.append(f"{rel}: /api/meta serves {name!r}, which is either not "
                       f"a fixture or is in DEPLOY_EXCLUDED — the deployment "
                       f"escalates by default, so its menu is a spend surface")
        for name in sorted(want_served - served):
            bad.append(f"{rel}: /api/meta omits {name!r}, which is a fixture and "
                       f"is NOT in DEPLOY_EXCLUDED — the exclusion is wider "
                       f"than the set that names it")
        for name, path in yielded.items():
            if name in want and path != want[name]:
                bad.append(f"{rel}: iter_fixtures yields {name!r} -> {path.name}, "
                           f"not its filing {want[name].name}")
        info[rel] = {"dirs": sum(1 for d in root.iterdir() if d.is_dir()),
                     "single_file_dirs": len(want), "api_meta_listed": len(listed),
                     "iter_fixtures_yielded": len(yielded)}
    stray = sorted(DEPLOY_EXCLUDED - set(_single_file_dirs(ROOT / FIXTURES)))
    if stray:
        bad.append(f"DEPLOY_EXCLUDED names {stray}, which are not fixtures at "
                   f"all — an exclusion nobody can trip protects nothing, and "
                   f"reads as if it did")
    api = _live((ROOT / inp.get("api_file", API_FILE)).read_text(), "py")
    n = _squash(api).count(_squash(META_FIXTURES))
    if n != 1:
        bad.append(f"app.py: /api/meta must serve the shared listing — expected "
                   f"exactly one `{META_FIXTURES}`, found {n}")
    n = _squash(api).count(_squash(RESOLVE_CALL))
    if n != 1:
        bad.append(f"app.py: _fixture_file must resolve through the shared rule — "
                   f"expected exactly one `{RESOLVE_CALL}`, found {n}")
    if re.search(r"def\s+(_?list_fixtures|deployed_fixtures|fixture_file)\b", api):
        bad.append("app.py defines its own fixture listing/predicate — there is "
                   "one rule, in src/sec10k/web/fixtures.py")
    return bad, info


FIXTURES_MODULE = "src/sec10k/web/fixtures.py"


def check_deployed_exclusion(case):
    """ADR-036 §h2 / PR #61 R1. The money half of the fixture exclusion.

    `fixture_discovery` pins the RELATIONSHIP (deployed = eval corpus minus
    DEPLOY_EXCLUDED) and would stay green with an empty exclusion set. This
    pins the three things that make the relationship worth anything:

    1. the named set really contains the fixtures that fire the trigger. The
       names come from the CASE (`input.must_exclude`), not from a second copy
       in this file — the eval set is the spec. Deleting a name from
       `DEPLOY_EXCLUDED` puts a one-click paid button back in the dropdown and
       must not be a green edit.
    2. RESOLUTION consults the listing, not merely the same predicate. This is
       the finding's sharp edge: `?fixture=intc-2025&run=1` bills on page load
       with no click and no upload, and `POST /api/extract/fixture` names a
       fixture directly, so an exclusion that only shrank the menu would be
       cosmetic. Pinned as the guard's live text in `_fixture_file`.
    3. the set is named in ONE place. An excluded name appearing as a literal
       in `app.py` too is a second copy that will drift, and the copy that
       drifts is the one nobody reads.

    What it does NOT prove: that the excluded fixtures are the only ones that
    fire (that is `tasks/reviews/d11_trigger_scan.py`, re-run by hand — TD-160
    carries deriving the set from the trigger instead of maintaining it), that
    fastapi binds the route, or that an UPLOAD of the same document is refused.
    It is not: upload is the deliberate act the exposure notes name, and this
    exclusion is about what the deployment hands a passer-by.
    """
    inp = case.get("input", {})
    bad = []
    for name in inp.get("must_exclude", []):
        if name not in DEPLOY_EXCLUDED:
            bad.append(f"{name!r} is not in DEPLOY_EXCLUDED — it fires D8's "
                       f"trigger, so the deployment would offer it in the "
                       f"dropdown and bill on `?fixture={name}&run=1`")

    api = _live((ROOT / inp.get("api_file", API_FILE)).read_text(), "py")
    # PR #61 R13. THE PROPERTY, not the line. Two halves, and the first is what
    # the old single-literal count could not see: every path in app.py that
    # touches the fixture primitives goes through `_fixture_file`, so a second
    # endpoint cannot resolve a fixture at all — let alone resolve one around
    # the guard. The second half is that `_fixture_file` really is guarded.
    tree = ast.parse(api)
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    resolver = inp.get("resolver", FIXTURE_RESOLVER)
    prims = set(inp.get("primitives", FIXTURE_PRIMITIVES))
    inner = {id(n) for f in fns for n in ast.walk(f)}
    for fn in fns:
        used = sorted({n.id for n in ast.walk(fn)
                       if isinstance(n, ast.Name) and n.id in prims})
        if used and fn.name != resolver:
            bad.append(f"app.py: `{fn.name}` touches {used} — only "
                       f"`{resolver}` may, because it is the one function the "
                       f"membership guard dominates. A second resolver walks "
                       f"around the exclusion with every other pin green.")
    loose = sorted({n.id for n in ast.walk(tree)
                    if isinstance(n, ast.Name) and n.id in prims
                    and id(n) not in inner})
    if loose:
        bad.append(f"app.py: {loose} used at module scope, outside "
                   f"`{resolver}` — same defect, one indent level out")
    fnode = next((f for f in fns if f.name == resolver), None)
    if fnode is None:
        bad.append(f"app.py has no `def {resolver}` — request-time resolution "
                   f"has no single home to guard")
    elif not any(
            isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
            and any(isinstance(o, ast.NotIn) for o in n.test.ops)
            and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                    and c.func.id == "deployed_fixtures"
                    for c in n.test.comparators)
            and any(isinstance(r, ast.Raise) for r in ast.walk(n))
            for n in ast.walk(fnode)):
        bad.append(f"app.py: `{resolver}` does not refuse a name outside "
                   f"`deployed_fixtures()` — resolution must consult the "
                   f"LISTING, not merely share its predicate, because the deep "
                   f"link and a hand-written POST both name a fixture directly")
    for name in sorted(DEPLOY_EXCLUDED):
        if name in api:
            bad.append(f"app.py names the excluded fixture {name!r} itself — "
                       f"the set belongs in one place ({FIXTURES_MODULE})")

    mod = (ROOT / inp.get("fixtures_module", FIXTURES_MODULE)).read_text()
    assigns = [n for n in ast.parse(mod).body
               if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "DEPLOY_EXCLUDED"
                       for t in n.targets)]
    if len(assigns) != 1:
        bad.append(f"{FIXTURES_MODULE}: expected exactly one module-level "
                   f"`DEPLOY_EXCLUDED = ...`, found {len(assigns)}")
    for node in assigns:
        v = node.value
        if not (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                and v.func.id == "frozenset" and len(v.args) == 1
                and isinstance(v.args[0], ast.Set)
                and all(isinstance(e, ast.Constant) and isinstance(e.value, str)
                        for e in v.args[0].elts)):
            bad.append("`DEPLOY_EXCLUDED` is not a frozenset of string literals "
                       "— a computed or mutable set is one an import-time "
                       "failure can silently empty")
    return bad


# PR #61 R21. Where the trigger census is PUBLISHED, and the shape it is
# published in. `src/repo_hygiene/eval_adapter.py` is deliberately absent: its
# one "18 of 43 dev documents" is a different statistic (rung 1's window
# offset, PR #58 R17) that this sweep does not re-derive, and pinning a
# denominator whose numerator nothing here can check would be the vacuity this
# whole PR is about. Recorded rather than silently skipped.
CENSUS_FILES = ["src/sec10k/extract.py", "src/sec10k/escalate.py", "README.md",
                "docs/architecture/overview.md",
                "specs/decisions/ADR-036-tiered-escalation.md"]
# `\s+`, not " ": the sentence these figures live in wraps, and the first
# revision of this pin missed `"42 of 43\n    dev fixtures"` — the exact
# line R21 found — because a newline sat where it wanted a space.
CENSUS_RE = re.compile(r"(\d+)\s+of\s+(?:the\s+)?(\d+)\s+(dev|real)\b")
TRIGGER_SCAN = "tasks/reviews/d11_trigger_scan.py"


def check_deployed_exclusion_derived(case):
    """PR #61 R15 / TD-160. `DEPLOY_EXCLUDED` must EQUAL the set of fixtures
    that actually fire the trigger — re-derived here, not maintained by hand.

    The rejection this replaces was costed against the wrong option. TD-160
    argued that recomputing the trigger "means a full `extract_items` sweep of
    44 filings at process start (seconds of CPU, and a hard dependency on the
    extractor from the LISTING path, which today is pure stdlib directory
    reading)" — all true, and all about deriving it at IMPORT time in the web
    layer. Deriving it at EVAL time was never considered and costs 4.6s
    (measured, `tasks/reviews/pr61-r2-red.txt`) against a 44s suite, with no
    new import on any request path. So the sweep runs here instead: the
    deployment still reads a frozenset, and the gate is what keeps that
    frozenset honest.

    Equality in BOTH directions, deliberately:

    * a fixture that fires and is not excluded is the R1 hole re-opening —
      before the door (TD-158) it was a one-click paid button, and after the
      door it is still a paid button for anyone holding the token;
    * a fixture that is excluded and does NOT fire is a demo entry deleted for
      no reason, which nothing else would ever catch.

    Deliberately NOT in the `invariant` suite. The PostToolUse hook runs that
    one on every edit and 4.6s per keystroke-batch is a real tax; the
    pre-commit gate runs `fast`, so the property is enforced at every commit,
    which is the last moment a hand-maintained set can drift. `input.trigger`
    names the warning code so this check cannot silently follow a rename of
    `escalate.TRIGGER_CODES`.
    """
    inp = case.get("input", {})
    root = ROOT / inp.get("fixtures_dir", FIXTURES)
    code = inp.get("trigger", "low_item_coverage")
    # ADR-042 §e: read the ROUTER'S OWN SENSOR, not the raw warning code. The
    # two agreed until the cross-reference resolver landed, and the property
    # this check exists for — "could an anonymous click reach a PAID rung" —
    # is the sensor's, not the code's: `intc-2025` still publishes
    # `low_item_coverage` (its spans really are index entries) and no longer
    # escalates, because the deterministic layer answered it. Keeping the raw
    # code here would withhold from the demo the one filing this repo now
    # handles best, for a cost that is no longer incurred. `input.trigger` is
    # still the rename-pin it was, asserted against TRIGGER_CODES below.
    from src.sec10k.escalate import TRIGGER_CODES, trigger
    if code not in TRIGGER_CODES:
        return {"passed": False, "failures": [
            f"input.trigger {code!r} is not in escalate.TRIGGER_CODES "
            f"{list(TRIGGER_CODES)} — the pin followed a rename it should have caught"]}
    fires, names = set(), []
    for name, path in sorted(_single_file_dirs(root).items()):
        names.append(name)
        r = extract_items(str(path))
        if trigger(r.get("warnings", []))["fired"]:
            fires.add(name)
    scanned = len(names)
    bad = []
    if scanned < inp.get("min_scanned", 40):
        bad.append(f"only {scanned} fixtures scanned — a sweep that sees "
                   f"nothing agrees with any exclusion set")
    for name in sorted(fires - set(DEPLOY_EXCLUDED)):
        bad.append(f"{name!r} fires {code} and is NOT in DEPLOY_EXCLUDED — the "
                   f"deployment would offer it in the dropdown and bill on "
                   f"`?fixture={name}&run=1`. Nobody had to edit the set for "
                   f"this to happen, which is exactly the drift TD-160 names.")
    for name in sorted(set(DEPLOY_EXCLUDED) - fires):
        bad.append(f"{name!r} is in DEPLOY_EXCLUDED but does not fire {code} — "
                   f"a demo entry withheld for no reason, and an exclusion "
                   f"nobody can trip protects nothing while reading as if it did")

    # PR #61 R21. The same defect class as R16, on the census instead of a
    # dollar figure: `extract.py`'s public docstring still said the trigger
    # stays quiet on "42 of 43 dev fixtures, every real EDGAR filing in the
    # set" after the corpus grew to 44 and the real-filing rate stopped being
    # zero — eight lines below a header the SAME commit corrected. Restating a
    # measurement in six files makes five of them free to rot.
    #
    # This sweep already knows the true denominators, so binding them costs a
    # regex. The SYNTHETIC roster comes from `d11_trigger_scan.py`, which is
    # the source of record for the dev/real split (`evals/fixtures/README.md`
    # is its provenance) — importing it beats a second copy that can disagree.
    # ponytail: DENOMINATORS only. The numerators are claims about different
    # statistics per site (fires, stays quiet, refuses before any item) and
    # pinning each would mean re-deriving each; the corpus size is the part
    # that goes stale for everyone at once, which is what happened.
    spec = importlib.util.spec_from_file_location(
        "d11_scan", ROOT / inp.get("scan_script", TRIGGER_SCAN))
    scan_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scan_mod)
    want = {"dev": scanned,
            "real": sum(1 for n in names if n not in scan_mod.SYNTHETIC)}
    for rel in inp.get("census_files", CENSUS_FILES):
        for m in CENSUS_RE.finditer((ROOT / rel).read_text()):
            n, denom, kind = int(m.group(1)), int(m.group(2)), m.group(3)
            if denom != want[kind]:
                bad.append(f"{rel}: publishes '{m.group(0)}' — the {kind} "
                           f"corpus is {want[kind]}, not {denom}. A census "
                           f"restated in {len(CENSUS_FILES)} files rots in "
                           f"{len(CENSUS_FILES) - 1} of them.")
            elif n > denom:
                bad.append(f"{rel}: publishes '{m.group(0)}', a count larger "
                           f"than the corpus it is out of")
    return bad, {"deployed_exclusion_scanned": scanned,
                 "deployed_exclusion_fires": sorted(fires),
                 "census_corpus": want}


LEDGER_FILES = ["tasks/TODO.md", "evals/fixtures/README.md"]
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")


def check_ledger_table_shape(case):
    """L1. Every row of every Markdown table in the ledger files has exactly
    its header's cell count, and no code span in a table row carries a `|`.

    Cells are counted on EVERY `|` in the row (one leading and one trailing
    pipe dropped), escaped or not, inside a code span or not. That is
    deliberately the naive rule, because it is the one every reader of these
    tables actually applies: `src/sec10k/web/capabilities.py` splits README
    rows with `line.strip("|").split("|")`, the PR #30 R1 repro was
    `awk '{print gsub(/\\|/,"|")-1}'`, and the orchestrator's row inventory
    counted the same way. GFM honours `\\|` as a literal pipe (rows 79/84/91/
    113 of `tasks/TODO.md` at 1efc457 render as 3 cells on GitHub) but strips
    the backslash inside a code span — so `grep 'a\\|b'` in a table cell
    renders as `grep 'a|b'`, a different command — and an UNescaped pipe in a
    code span splits the row on GitHub too (PR #30 R1/R8). The only shape on
    which the naive counter, a span-aware counter and GFM all agree is: no
    pipe anywhere in a row except the cell delimiters. A table ends at the
    first line that does not start with `|`; strikethrough rows count like
    any other. Pipes in fenced code blocks are out of scope (none of the
    ledger tables sit inside one).
    """
    inp = case.get("input", {})
    bad = []
    for rel in inp.get("files", LEDGER_FILES):
        width = None
        for n, line in enumerate((ROOT / rel).read_text().split("\n"), 1):
            s = line.strip()
            if not s.startswith("|"):
                width = None
                continue
            body = s[1:-1] if s.endswith("|") and len(s) > 1 else s[1:]
            cells = body.count("|") + 1
            if width is None:
                width = cells
            elif cells != width:
                bad.append(f"{rel}:{n}: {cells} cells, header has {width}")
            for span in CODE_SPAN_RE.findall(s):
                if "|" in span:
                    bad.append(f"{rel}:{n}: code span {span} carries a pipe")
    return bad


# --- D5: inspector layout + exclusion honesty -------------------------------
#
# BOTH checks below are STATIC reads of the committed source — CSS text and JS
# text. Nothing in this harness issues an HTTP request and nothing lays
# anything out, so neither check observes the RENDER; they pin the source that
# produces it, and the existing pin mechanism's documented holes apply (a
# pinned element can be `hidden` and still satisfy its pin). The rendered
# geometry is evidence only a browser can give: it lives in
# tasks/reviews/d5-browser-walk.json, measured at 1280 / 1024 / 900 / 768.

# D5 half 1. What carries "the panes are stacked" into the sync-scroll
# control, pinned WHOLE for the reason WIRE_UI above is an allow-list: asking
# each hop a question about itself ("does it mention disabled?") is a question
# a broken hop can also answer correctly. A deliberate change here must update
# the pin — that friction is the point.
STACK_WIRE = [
    ("syncOn() refuses to sync through a disabled control",
     'function syncOn(){ const c = $("#sync-scroll"); return !!(c && c.checked && !c.disabled); }'),
    ("the stacked state disables the control AND says so in words",
     'function syncStacked(){\n'
     '  const c = $("#sync-scroll"); if(!c) return;\n'
     '  c.disabled = STACKED.matches;\n'
     '  $("#sync-state").textContent = STACKED.matches ? " — inactive: panes stacked" : "";\n'
     '}'),
    ("crossing the breakpoint re-evaluates it, so a resize cannot leave a "
     "live-looking control sitting over stacked panes",
     'STACKED.addEventListener("change", syncStacked);'),
]


def _media_blocks(css):
    """Yield (condition, body) for every `@media` block, braces MATCHED rather
    than regexed — _flat_rules' own `([^{}]+)\\{([^{}]*)\\}` cannot see inside
    one at all (it documents that hole), and a plain regex would end the block
    at the first nested `}`."""
    css = css_contrast._strip_comments(css)
    for m in re.finditer(r"@media([^{]*)\{", css):
        i, depth = m.end(), 1
        while i < len(css) and depth:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        yield m.group(1).strip(), css[m.end():i - 1]


def _without_media(css):
    """`css` with every `@media` block removed, so `_declared_for` (which is
    media-BLIND — it documents that hole) can be asked about the unconditional
    cascade. Without this, `.split`'s base `grid-template-columns` reads as
    the LAST one declared in the file, which is the narrowest breakpoint's."""
    css = css_contrast._strip_comments(css)
    out, last = [], 0
    for m in re.finditer(r"@media[^{]*\{", css):
        if m.start() < last:
            continue
        i, depth = m.end(), 1
        while i < len(css) and depth:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        out.append(css[last:m.start()])
        last = i
    out.append(css[last:])
    return "".join(out)


def _tracks(value):
    """Track count of a `grid-template-columns` value. Enough for the literal
    values this stylesheet declares; a repeat()/minmax() form would need a
    real parser and none is used here."""
    return len(value.split())


def check_split_breakpoint(case):
    """D5 half 1 (debt row V5). The compare pane (`#source`) and the item pane
    (`#pane`) must stay in ONE grid row down to `min_side_by_side` px — below
    the old 1100px breakpoint `#source` dropped to `grid-column:1/-1` and
    stacked BELOW `#pane`, so the two were never on screen together and
    sync-scroll had nothing to demonstrate itself against (measured live at
    1024x860 on c13aa5c: `#pane` top 507, `#source` top 1157). Wherever the
    layout DOES still stack, the sync-scroll control must be disabled and
    labelled inactive rather than left looking live.

    Mechanically: `.split`'s own rule declares three tracks; every `@media`
    block that stacks (drops `.split` below three tracks, or gives `#source` a
    `grid-column` span) must trigger strictly below `min_side_by_side`; the JS
    must watch a media query at EXACTLY the widest stacking breakpoint, so
    re-raising the CSS `max-width` without moving the JS one goes red twice;
    and the three expressions carrying "stacked" into the control are pinned
    whole.

    Text, not layout — see the block comment above this function.
    """
    inp = case.get("input", {})
    text = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    live = _live(text, "js")   # strips /* */, // and <!-- -->; CSS + JS in one file
    js = _squash(live)
    split = inp.get("split", ".split")
    stack_sel = inp.get("stack_selector", "#source")
    floor = inp.get("min_side_by_side", 1024)
    bad = []

    base = _declared_for(_without_media(live), split, "grid-template-columns")
    if not base or _tracks(base) < 3:
        bad.append(f"{split}: base rule declares {base!r} — want three tracks "
                   f"(sidebar + both compare panes) at full width")

    stack_widths = []
    for cond, body in _media_blocks(live):
        cols = _declared_for(body, split, "grid-template-columns")
        stacks = (cols is not None and _tracks(cols) < 3) or bool(
            _declared_for(body, stack_sel, "grid-column"))
        if not stacks:
            continue
        w = re.search(r"max-width\s*:\s*(\d+)px", cond)
        if not w:
            bad.append(f"@media{cond}: stacks the panes under a condition with "
                       f"no max-width — nothing says where the stacking starts")
            continue
        w = int(w.group(1))
        stack_widths.append(w)
        if w >= floor:
            bad.append(f"@media{cond}: stacks the panes at widths up to {w}px, "
                       f"so {stack_sel} and #pane are not on screen together at "
                       f"{floor}px (want a stacking breakpoint < {floor})")

    if not stack_widths:
        bad.append("no stacking @media block found at all — this check would "
                   "pass vacuously, and the control's inactive state has no "
                   "breakpoint to key on")
    else:
        want = f'matchMedia("(max-width:{max(stack_widths)}px)")'
        if _squash(want) not in js:
            bad.append(f"the JS does not watch {want} — the width the CSS "
                       f"stacks at and the width the control calls itself "
                       f"inactive at must be the same number")

    for why, expr in STACK_WIRE:
        if _squash(expr) not in js:
            bad.append(f"missing pinned expression ({why}): {expr}")

    label = inp.get("state_label", "sync-state")
    if not re.search(r'id="' + re.escape(label) + r'"', live):
        bad.append(f'#{label}: no element carrying the "inactive" wording — a '
                   f"silently disabled checkbox still looks like a live control")
    return bad, {"stack_widths": stack_widths, "split_columns": base}


def check_exclusion_note(case):
    """D5 half 2 (debt row: the compare pane still shows chrome while the
    extracted pane hides it). With the box ticked the two panes visibly
    disagree — the left drops the detected runs, the right still serves every
    `<PAGE>` and running head — because `boilerplate` offsets index the
    DERIVED `normalized_text` while the compare pane serves the RAW filing,
    and no raw<->normalized offset map exists anywhere in this pipeline.
    Building one stays ruled out as post-freeze scope creep (ADR-026 s.a);
    this note is an honest statement of the limit, NOT a fix for it.

    Pinned: the element exists; it ships `hidden`, so it cannot fire with
    exclusion off; its visibility is assigned from the response's own
    `boilerplate_excluded` (the same read-at-request-time field the pane
    header labels itself from); and its wording says what IS true (raw vs
    normalized, the panes will not agree) and none of what is not (that the
    map exists, or that the panes match).

    Text, not render — see the block comment above check_split_breakpoint.
    """
    inp = case.get("input", {})
    text = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    live = _live(text, "js")
    ident = inp.get("note_id", "bp-note")
    bad = []
    m = re.search(r'<div[^>]*\bid="' + re.escape(ident) + r'"([^>]*)>(.*?)</div>',
                  live, re.S)
    if not m:
        return ([f'#{ident}: no note element in the markup — under exclusion '
                 f"the two panes disagree with nothing on screen saying why"],
                {"note_text": None})
    attrs = m.group(1)
    # tags out, whitespace collapsed: how the note happens to be wrapped in
    # the file says nothing about what it tells the reader (_squash's argument,
    # kept at single spaces here because the pinned wording is prose).
    body = " ".join(re.sub(r"<[^>]+>", "", m.group(2)).split())
    if not re.search(r"(?:^|\s)hidden(?:[=\s]|$)", attrs):
        bad.append(f"#{ident}: does not ship `hidden` — the note would stand on "
                   f"screen with exclusion off, where it is simply false")
    for expr in inp.get("wire", []):
        if _squash(expr) not in _squash(live):
            bad.append(f"missing pinned expression (the note follows the "
                       f"response's own exclusion state): {expr}")
    for want in inp.get("must_say", []):
        if want not in body:
            bad.append(f"#{ident}: does not say {want!r}")
    for nope in inp.get("must_not_say", []):
        if nope in body:
            bad.append(f"#{ident}: says {nope!r} — the panes do NOT agree and "
                       f"no offset map exists; the note may not imply either")
    return bad, {"note_text": body}


def _chrome_inside_items(env):
    """ADR-026 s.d recomputed from the envelope alone: does any detected
    chrome run intersect any item's own span? This is the oracle for
    "exclusion removed something the reader would see", and it deliberately
    does NOT call `strip_chrome` — that is what `build_view` itself uses, and
    a check that re-runs the implementation agrees with any window bug the
    implementation has (`check_boilerplate_exclusion` says the same about its
    own oracle). Independent of which view mode rendered the payload, which
    is the whole point after S9."""
    spans = env.get("boilerplate") or []
    return any(sp["start"] < i["end"] and sp["end"] > i["start"]
               for sp in spans
               for i in env.get("items", [])
               if i.get("start") is not None and i.get("end") is not None)


def check_exclusion_note_trigger(case):
    """D5 PR #46 R1. The note asserts a DISAGREEMENT between the two panes.
    That assertion is true only when exclusion actually removed something
    from the extracted pane — and `boilerplate_excluded` does not say that.
    `view.build_view` sets it from `spans is not None`, i.e. from the flag
    having been ASKED FOR, so it is True on aapl-2025 (detector returns [],
    23 items, 0 with `display_text`, pane text byte-identical to the
    un-flagged run) and True on aapl-2026-10q (`unsupported`, 0 items), where
    the note would sit above an empty pane claiming a difference nobody can
    see.

    So the trigger is a SECOND field, `boilerplate_applied` — asked-for vs
    applied — and this check is the one that runs the real pipeline rather
    than reading text. Per fixture, in EVERY view mode the case names, with
    the flag ON:
      * the field exists;
      * it equals `_chrome_inside_items` — ADR-026 s.d recomputed here from
        the envelope's own spans, independently of `build_view`;
      * it equals the hand-labeled expectation in the case, so a fixture
        that stops exercising its side of the distinction says so rather
        than quietly re-labelling itself;
      * with the flag OFF it is False.
    Globally it refuses to pass vacuously: at least one run must come out
    True, at least one False, at least one must be the R1 shape itself
    (`boilerplate_excluded` True while `boilerplate_applied` is False), and
    at least one must be in `blocks` mode.

    PR #46 R10 — WHY THE MODES. The first version of this check used
    `any("display_text" in item)` as its oracle, because before S9 that WAS
    "the pane on screen differs from the verbatim slice": exclusion was the
    only producer of `display_text`. S9 (ADR-032) gave it a second one — in
    `blocks` mode `display_text` is the derived Markdown — so that equality
    holds in PLAIN MODE ONLY, and a check asserting it in `blocks` mode would
    report the CORRECT field as wrong. Measured at the merge: over 84 runs
    (42 fixtures x 2 modes) the old expression disagrees with the envelope on
    14, every one of them in `blocks` mode. The oracle is therefore computed
    from the spans, and the divergence is reported in `info` as a measurement
    rather than asserted, since how far Markdown departs from the raw slice
    is S9's business, not this case's.

    Deliberately NOT `strip_chrome(...) != raw` either: that is the
    expression `build_view` itself now uses, and a check that re-runs the
    implementation agrees with any window bug the implementation has —
    `check_boilerplate_exclusion` makes the same argument about its own
    oracle, for the same reason.

    `boilerplate_excluded` keeps its meaning for every existing consumer —
    the S8 pane header and `ui-boilerplate-exclusion`'s pins read it and are
    untouched. This adds a field; it does not redefine one.
    """
    inp = case.get("input", {})
    field = inp.get("trigger_field", "boilerplate_applied")
    modes = inp.get("blocks_modes", [False, True])
    live = _live((ROOT / inp.get("file", UI_STYLESHEET)).read_text(), "js")
    bad, seen, old_expr, r1_shape = [], {}, {}, 0
    for rel, want in inp.get("fixtures", {}).items():
        for md in modes:
            key = f"{rel} blocks={md}"
            env = extract_items(str(ROOT / rel), exclude_boilerplate=True, blocks=md)
            on = build_view(env)
            off = build_view(extract_items(str(ROOT / rel), blocks=md))
            if field not in on:
                bad.append(f"{key}: the view payload carries no {field!r} — the "
                           f"note has nothing to key on but `boilerplate_excluded`, "
                           f"which is True whenever the flag was merely asked for")
                continue
            got = on[field]
            oracle = _chrome_inside_items(env)
            seen[key] = got
            # reported, never asserted: the pre-S9 expression, kept visible so
            # the mode where it diverges stays on the record, not in prose
            old_expr[key] = any("display_text" in i for i in on.get("items", []))
            if got is not oracle:
                bad.append(f"{key}: {field}={got!r} but the envelope's own "
                           f"boilerplate spans "
                           f"{'do' if oracle else 'do NOT'} fall inside an item "
                           f"span — the field does not mean 'exclusion removed "
                           f"something the reader would see'")
            if got is not want:
                bad.append(f"{key}: {field}={got!r}, case expects {want!r}")
            if off.get(field) is not False:
                bad.append(f"{key}: {field}={off.get(field)!r} on an UN-flagged "
                           f"run — nothing was excluded, so nothing was applied")
            if on.get("boilerplate_excluded") is True and got is False:
                r1_shape += 1
    if inp.get("fixtures"):
        if not any(seen.values()):
            bad.append("no run came out True — the note could never fire "
                       "and this case would pass vacuously")
        if all(seen.values()) and seen:
            bad.append("no run came out False — the R1 distinction between "
                       "'exclusion asked for' and 'exclusion applied' is not "
                       "exercised by any fixture in this case")
        if not r1_shape:
            bad.append("no run reproduces the R1 shape (boilerplate_excluded "
                       "True while nothing was applied) — the case has stopped "
                       "covering the defect it exists for")
    # OUTSIDE the `fixtures` gate above, deliberately: those three guards are
    # only reached when the case still HAS fixtures, which is the hole PR #46
    # R8 carries as debt. R8 is not fixed here — an empty `fixtures` map still
    # defangs them — but a guard added in the same repair that was told about
    # the hole does not get to sit behind it.
    if True not in modes:
        bad.append("no run drives S9's `blocks` mode — that is the mode where "
                   "`display_text` has a second producer, i.e. the only mode "
                   "where the pre-S9 oracle was wrong (PR #46 R10)")
    for expr in inp.get("wire", []):
        if _squash(expr) not in _squash(live):
            bad.append(f"missing pinned expression (the note keys off {field}, "
                       f"not off the asked-for flag): {expr}")
    return bad, {"applied_by_run": seen, "r1_shape_runs": r1_shape,
                 "pre_s9_expression_by_run": old_expr,
                 "runs_where_pre_s9_expression_diverges":
                     sorted(k for k in seen if seen[k] is not old_expr[k])}


# D12 — the offset REPRODUCTION contract. Verbatim in exactly two places, and
# this tuple is the third: README.md (the human's copy) and app.py's
# `/api/normalized/{token}` docstring, which FastAPI serves as the endpoint's
# own OpenAPI description, so a consumer with no access to this repo reads it
# at /docs. Pinned line by line rather than as one blob because the two copies
# wrap differently (markdown list vs. Python docstring) and how a sentence is
# wrapped carries no information — `_squash`, same argument as everywhere else
# in this file.
RECIPE = (
    "1. Extract: POST the filing to /api/extract/fixture (or /upload, or /url) and keep "
    "three things from the response: source.token, norm_sha256, and each item's start and end.",
    "2. Download: GET /api/normalized/{token} — the exact normalized_text those offsets "
    "index, served as UTF-8 text.",
    "3. Verify: sha256 of the downloaded bytes must equal norm_sha256 from step 1. If it "
    "does not, the download is not that run and the offsets do not apply to it.",
    "4. Slice: item_text = normalized_text[start:end], where normalized_text is the DECODED "
    "string — start and end are character offsets into that string, never byte offsets into a file.",
    "WARNING: these offsets do not index the raw filing. Slicing the raw HTML — what "
    "/api/source/{token} serves, or the file you uploaded — by the same start and end yields "
    "different bytes, because normalization rewrites the document. There is deliberately no "
    "raw-to-normalized offset map (ADR-026 §a).",
)

RECIPE_DOCS = ("README.md", "src/sec10k/web/app.py")

# PR #54 R2. README's worked snippet is the recipe as a consumer will actually
# run it, and its step-4 line first shipped as a bare `==`, which is false for
# any item over DISPLAY_MAX — aapl-2025 item 1A is 68,162 chars against a
# 40,000-char display copy, so the published snippet raised AssertionError on
# the fixture printed one line above it. The prose underneath said "compare
# prefixes"; the code did not.
#
# This is a TEXT PIN and nothing more, stated plainly because the first version
# of this comment claimed the line was also "executed below ... so the pin is
# not just a spelling check" (PR #54 R5). It was not: the comparison added for
# that claim was `slice_[:len(it["text"])] != it["text"]`, which `build_view`
# makes identical to the `slice_[:DISPLAY_MAX] != it["text"]` line already in
# the loop, so it could never fail alone and the truncated-item guard built on
# top of it guarded nothing. Both were deleted rather than reworded. What this
# pin catches is an edit to README.md; what it cannot catch is someone editing
# README.md and this constant together, which is the same ceiling every
# allow-list pin in this file has.
SNIPPET_ASSERT = 'assert text[item["start"]:item["end"]][:len(item["text"])] == item["text"]'

NORMALIZED_ROUTE_RE = re.compile(r'@app\.get\("(/api/normalized/[^"]+)"')

# The three hops the eval harness cannot walk, because importing app.py would
# drag fastapi into the dependency-free unit job (see check_boilerplate_plumbing
# for the full argument). Allow-list, whole expressions, same reasons as WIRE_API.
WIRE_NORMALIZED = [
    ("_run puts THIS RUN's normalized_text in the cache, under the same token "
     "that serves the raw source — a token that served some other run's text "
     "would fail the sha in step 3 rather than lie, but it would fail it for "
     "the wrong reason",
     'source = dict(source, token=_cache_source(body, Path(path).suffix.lower(), norm))'),
    ("the cache stores the normalized bytes beside the raw bytes",
     'SOURCE_CACHE[token] = (content_type, raw, normalized.encode("utf-8"))'),
    ("the endpoint serves the NORMALIZED bytes, not the raw ones — serving "
     "`raw` here is the whole defect this contract exists to make impossible",
     'return Response(content=norm, media_type="text/plain; charset=utf-8", headers={'),
    ("...citing the sha step 3 verifies against",
     '"X-Normalized-SHA256": hashlib.sha256(norm).hexdigest(),'),
    # PR #54 R1. The two pins above name `norm` and stop there, so they were
    # satisfied by `norm = hit[1]` — the endpoint serving the RAW filing under
    # a matching sha header, i.e. exactly the defect the comment above calls
    # impossible, green. Measured, not imagined: the reviewer ran that mutation
    # and so did this repair. Pinning where the value COMES FROM is the other
    # half, and it is the half that carries the meaning.
    ("the endpoint's bytes come from the NORMALIZED slot of the cache entry — "
     "`hit[1]` is the raw filing and satisfies every other pin here",
     "norm = hit[2]"),
    ("...and what goes into that slot is the WHOLE normalized_text of this "
     "run, not a prefix of it — a truncated cache entry fails step 3 for "
     "every consumer on every run",
     'norm = result.get("normalized_text") or ""'),
]

# A pin proves its expression is present; it cannot prove nothing REBINDS the
# name afterwards — UNIQUE_UI's argument, in Python. `norm = hit[2]` followed
# by `norm = hit[1]` satisfies both pins and serves the raw filing, so the two
# functions that bind `norm` must bind it exactly once each.
#
# Counted with `ast`, not a regex, and PR #54 R4 is why. The first version was
# `^\s*norm\s*=[^=]` over a text window, which counts only a rebind that starts
# its own physical line: `norm = hit[2]; norm = hit[1]` and
# `norm, _unused = hit[1], 0` both left the whole gate green while the endpoint
# served the raw filing. Two more spellings would have needed two more regex
# patches, which is the shape of a guard that is always one spelling behind.
# `Name(id="norm", ctx=Store)` inside the function node is the property itself:
# every binding form Python has — assignment, augmented, walrus, tuple unpack,
# for-target — is one Store node, and the ast also makes the text-window scan
# (and the decorator-keying defect that version carried in-session, caught
# and fixed inside round 1 and never committed) unnecessary.
NORM_BINDERS = {"api_normalized": 1, "_run": 1}


def _binds(src, func, name):
    """How many times `func` in `src` binds `name`. None if there is no such
    function — a rename must be loud, not a silent zero."""
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == func):
            return sum(1 for n in ast.walk(node) if isinstance(n, ast.Name)
                       and n.id == name and isinstance(n.ctx, ast.Store))
    return None


def check_offset_reproduction_contract(case):
    """D12. A consumer with no access to this repo must be able to reproduce
    any item's text from the published offsets, and must be told, in the same
    breath, that those offsets do NOT index the raw filing.

    ADR-026 §a refuses a raw-to-normalized offset map, so reproducibility
    ships as a CONTRACT: serve the exact `normalized_text` the offsets index,
    pin the recipe that slices it, and pin the sha that binds the download to
    the run. Three halves, because each can rot on its own:

    LIVE (the recipe is TRUE) — per fixture, `extract_items` + `build_view`,
        no HTTP: the view's `norm_sha256` is the sha256 of the UTF-8
        `normalized_text` (so step 3 can be performed at all), and for every
        item with a span `normalized_text[start:end]` is byte-for-byte the
        `text` the API serves (step 4). This is INV-S2 restated at the API
        boundary, and it is what makes the recipe a fact rather than a claim.
    LIVE (the WARNING is true) — the same offsets applied to the RAW filing
        bytes must produce something DIFFERENT, on every span-carrying item of
        every fixture here. A warning nobody can falsify is decoration; if
        normalization ever became the identity, this half goes red and the
        docs get to stop shouting.
    WIRE + DOCS — the endpoint exists exactly once, and every expression on
        the path from this run's `normalized_text` to the response body is
        pinned WHOLE: what goes into the cache, which slot comes back out, the
        response, and the sha header — plus a guard that neither function
        binds `norm` more than once, counted with `ast` (PR #54 R1: the first
        version pinned only the two expressions that MENTION `norm`, and `norm
        = hit[1]` served the raw filing straight through it; R4: the guard that
        closed R1 was a line-anchored regex, and a same-line or tuple-unpack
        rebind walked through THAT). The recipe appears
        verbatim in both `RECIPE_DOCS`, warning included. What none of this can
        do is issue a request — importing app.py drags fastapi into the
        dependency-free unit job — so FastAPI BINDING the route stays unpinned
        and carries its own debt row. Pinned text is not a served response, and
        the difference is written down rather than glossed.
    """
    inp = case.get("input", {})
    bad, info = [], {}
    api = _live((ROOT / inp.get("api_file", API_FILE)).read_text(), "py")

    routes = NORMALIZED_ROUTE_RE.findall(api)
    if routes != ["/api/normalized/{token}"]:
        bad.append(f"app.py declares {routes!r} for the normalized-text download, "
                   f"not exactly one `/api/normalized/{{token}}` GET route — the "
                   f"recipe's step 2 names that path and nothing else serves it")
    for why, expr in WIRE_NORMALIZED:
        n = _squash(api).count(_squash(expr))
        if n != 1:
            bad.append(f"app.py: {why} — expected exactly one `{expr}`, found {n}")
    for func, want in NORM_BINDERS.items():
        n = _binds(api, func, "norm")
        if n != want:
            bad.append(f"app.py `{func}()`: binds `norm` {n} times, expected "
                       f"{want} — a second binding after the pinned one wins at "
                       f"runtime and leaves every pin above satisfied "
                       f"(None means the function is gone or renamed)")

    for rel in RECIPE_DOCS:
        text = _squash((ROOT / rel).read_text())
        for line in RECIPE:
            n = text.count(_squash(line))
            if n != 1:
                bad.append(f"{rel}: the reproduction recipe is not carried "
                           f"verbatim — `{line[:60]}…` occurs {n} times, expected 1")
    n = _squash((ROOT / "README.md").read_text()).count(_squash(SNIPPET_ASSERT))
    if n != 1:
        bad.append(f"README.md: the worked snippet's step-4 line is not "
                   f"`{SNIPPET_ASSERT}` (found {n}) — any other comparison is "
                   f"false for an item longer than DISPLAY_MAX, i.e. the "
                   f"published recipe raises on the reader's first long item")

    for rel in inp.get("fixtures", []):
        r = extract_items(str(ROOT / rel))
        text = r.get("normalized_text") or ""
        v = build_view(r)
        want_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if v.get("norm_sha256") != want_sha:
            bad.append(f"{rel}: the run publishes norm_sha256="
                       f"{v.get('norm_sha256')!r}, not the sha256 of its own "
                       f"UTF-8 normalized_text ({want_sha}) — step 3 of the "
                       f"recipe cannot be performed")
        raw = (ROOT / rel).read_bytes().decode("utf-8", "replace")
        spanned = raw_same = 0
        for it in v["items"]:
            s, e = it.get("start"), it.get("end")
            if s is None or e is None:
                continue
            spanned += 1
            slice_ = text[s:e]
            if slice_[:DISPLAY_MAX] != it["text"]:
                bad.append(f"{rel} item {it.get('item')}: the recipe's slice "
                           f"normalized_text[{s}:{e}] is not the text the API "
                           f"serves for that item (INV-S2 at the API boundary)")
            if len(slice_) != it.get("chars"):
                bad.append(f"{rel} item {it.get('item')}: chars={it.get('chars')} "
                           f"disagrees with len(normalized_text[{s}:{e}])={len(slice_)}")
            if raw[s:e] == slice_:
                raw_same += 1
        if not spanned:
            bad.append(f"{rel}: no item carries a span — this fixture pins nothing")
        if raw_same:
            bad.append(f"{rel}: {raw_same} of {spanned} spanned items slice the "
                       f"RAW bytes to the same string as the normalized text — "
                       f"the documented WARNING is not true of this fixture")
        info[f"{Path(rel).parent.name}_spanned_items"] = spanned
    return bad, info
def _js_block(live, opener):
    """Text between the braces of the block `opener` opens, braces MATCHED.

    Same argument as `_media_blocks`: a plain regex ends the block at the
    first nested `}`, and every function here is mostly template literal, so
    `${...}` alone would defeat one. Template `${}` pairs balance, so simple
    depth counting is enough; a brace inside a STRING would defeat it, and
    none of the blocks this is pointed at contains one.
    """
    i = live.find(opener)
    if i < 0:
        return None
    i = live.index("{", i) + 1
    depth, start = 1, i
    while i < len(live) and depth:
        if live[i] == "{":
            depth += 1
        elif live[i] == "}":
            depth -= 1
        i += 1
    return live[start:i - 1]


def check_confidence_honesty(case):
    """D7. The 2026-08-24 demo's trust amplifier, both halves.

    PANEL. `doc_status` and the warnings list live in the top banner; the
    side panel a viewer actually reads showed a per-item `conf 0.95` with no
    visual link back to a document the banner had already called
    `success_with_warning` or `ambiguous` (postmortem §2, "The UI amplified
    both"). Pinned as an ADJACENCY, not as a question: every live
    interpolation of `it.confidence` must sit where the pinned
    `conf_marker` would start and must be followed IMMEDIATELY by the
    pinned `qualifier`. A question about the file ("does it mention
    doc_status somewhere?") is answerable by a file that still prints a
    bare number two lines later — the `boilerplate_plumbing` allow-list
    records two rounds of exactly that. `min_conf_sites` keeps it from
    passing vacuously by deleting the render sites; the `bodies` pins keep
    a producer from being neutered in place or shadowed by a second
    declaration; the banner pin carries its assignment target. What that
    adds up to, and what it does not, is the next paragraph.

    WHAT THIS CHECK IS, WRITTEN SO IT CANNOT BE READ AS MORE. Rewritten
    twice — PR #53 round 1 and again at round 2. Each earlier version
    asserted a property of the PROGRAM ("a bare confidence is
    unrepresentable", then "no live interpolation of `it.confidence`
    renders without the pinned qualifier"), and each was falsified inside
    one review by an edit a working developer might plausibly make. So the
    claim is now stated as what the code actually does.

    This is a TEXT PIN over one file. A green run asserts that
    src/sec10k/web/static/index.html contains, verbatim modulo whitespace:

      * every mention of `it.confidence` sitting inside an interpolation
        whose whole `${...}` is the pinned `conf_marker`, immediately
        followed by the pinned `qualifier`;
      * exactly one declaration of each pinned helper, each with a body
        byte-equal to its pin;
      * the pinned banner assignment, assignment target included;
      * the pinned wording in the coverage strip and none of the forbidden
        wording.

    It does NOT assert that the page renders a qualified confidence, and no
    static read of one file could: these pins constrain the text a program
    is written in, not the program. Out of reach today, concretely — a
    number rendered without mentioning `it.confidence` (copied into a local
    first, or read off a re-shaped object); markup injected by another
    script or served from another file; anything hidden by CSS or simply
    never reached at runtime for a reason the text does not show. THAT LIST
    IS ILLUSTRATIVE, NOT EXHAUSTIVE, and this is the sentence that matters:
    a text pin cannot enumerate the programs it fails to constrain. Read a
    green run as "the pinned text is present and unique", never as "the
    defect is impossible". What the screen actually showed is the browser
    walk, tasks/reviews/d7-browser-walk.json; the falsification attempts
    that have been run against these pins are
    tasks/reviews/pr53_mutation_probe.py.

    The qualifier reads `it.evidence.warnings`, which IS `score()`'s own
    `hits` list — the codes that carried this item's code and each cost it
    `WARN_PENALTY`. So the panel names exactly the warnings that moved the
    number, and inherits ADR-018's exclusion of `expected_item_missing`
    (which only restates the `missing` status the status badge already
    shows) rather than re-deriving a second definition here.

    BANNER. `unattributed_content` already computes a document-coverage
    figure and buries it in a warning row below the banner (postmortem §8
    gap 1). This pins that the banner surfaces it AND states the caveat
    `validate.py` states in its own comment — interior gaps are not counted,
    so the figure can understate true non-coverage by up to 9.7 points
    (ibm-1997, ADR-019 §d). `must_not_say` forbids the inversion that caveat
    exists to prevent: `100 - outside` is NOT the attributed share, and a
    banner that publishes it would overstate coverage by exactly the
    uncounted interior gaps.

    Text, not render — see the block comment above check_split_breakpoint.
    CEILING: this is a STATIC READ of the markup of
    src/sec10k/web/static/index.html. No test in this harness issues an HTTP
    request, so nothing here observes the render: it cannot see the
    qualifier appear beside a real 0.95, and a CSS rule could hide the
    coverage strip with every pin below green. That is browser evidence, in
    tasks/reviews/d7-browser-walk.json.
    """
    inp = case.get("input", {})
    text = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    live = _live(text, "js")
    bad = []

    marker, qual = inp["conf_marker"], inp["qualifier"]
    # PR #53 R1/R2/R4 all exploited the same weakness from different sides:
    # this check asked about TEXT THAT IS PRESENT and never about text that
    # is REACHED or COMPLETE. Site discovery used to be a literal search for
    # `conf ${`, so a third render site spelled `confidence ${it.confidence
    # ?? "—"}` printed a bare number and was invisible to the scan while
    # `min_conf_sites` stayed satisfied by the two qualified sites. The scan
    # now finds every interpolation OF THE FIELD and steps back to where the
    # pinned marker would have to start, so a differently-spelled site is
    # reported as unpinned rather than skipped.
    lead = marker.index("${")           # `conf ` — what precedes the field
    # PR #53 R4, second pass. Round 1 matched `${\s*it.confidence`, i.e. only
    # interpolations the field STARTS. `conf ${esc(it.confidence)}` names the
    # field, renders a bare number, and started nothing — and it is the
    # PLAUSIBLE next edit, not an exotic one, because every sibling badge in
    # that same template literal is already `${esc(...)}`. So every mention of
    # the field is now traced back to the `${` that encloses it and the whole
    # enclosing interpolation must be the pinned marker: wrapped, parenthesised
    # or reordered spellings are reported as unpinned rather than skipped.
    # `rfind` alone is not enough: the nearest preceding `${` may belong to an
    # interpolation that already CLOSED, in which case the mention is not being
    # rendered at all and attaching it to that interpolation reports the wrong
    # offset — and fires on correct code (`if (it.confidence == null)` would be
    # flagged). So the candidate must actually enclose the mention. A mention
    # outside every interpolation is not a render site and is skipped, which is
    # the "copied into a local first" hole the ceiling names out loud.
    sites = set()
    for m in re.finditer(r"it\.confidence", live):
        opened = live.rfind("${", 0, m.start())
        if opened < 0:
            continue
        i, depth = opened + 2, 1
        while i < len(live) and depth:
            if live[i] == "{":
                depth += 1
            elif live[i] == "}":
                depth -= 1
            i += 1
        if i <= m.start():          # that interpolation closed before the mention
            continue
        sites.add(max(0, opened - lead))
    sites = sorted(sites)
    floor = inp.get("min_conf_sites", 1)
    if len(sites) < floor:
        bad.append(f"only {len(sites)} live confidence render site(s), expected "
                   f"at least {floor} — the side panel's badge and the pane "
                   f"header each print one, and deleting a site is not a way "
                   f"to qualify it")
    for i in sites:
        rest = live[i:]
        head = " ".join(rest[:90].split())
        if not rest.startswith(marker):
            bad.append(f"confidence rendered by an unpinned expression: {head!r}")
        elif not _squash(rest[len(marker):]).startswith(_squash(qual)):
            bad.append(f"bare confidence, no qualifier beside it: {head!r} — a "
                       f"number a viewer reads with no link back to doc_status "
                       f"or to the warnings that moved it is the demo defect")

    for expr in inp.get("wire", []):
        if _squash(expr) not in _squash(live):
            bad.append(f"missing pinned expression (the qualifier reads the "
                       f"response's own doc_status and the item's own "
                       f"evidence.warnings): {expr}")

    # PR #53 R2. Substring existence proves a line is in the file, never that
    # it RUNS: `if(true) return "";` as the first statement of docQual and
    # itemQual left every pinned line intact below it as dead code, restored
    # the bare `conf 0.95` on every cvx-2015 badge, and passed. Same attack
    # class `_live` was added for in PR #27 R10, one level deeper — there the
    # pinned text survived inside a comment, here it survives below a return.
    # So the helpers whose whole job is the qualifier are pinned WHOLE:
    # anything added, removed or reordered inside them is a difference,
    # including a line that merely precedes the pinned one.
    for fn_name, want_body in (inp.get("bodies") or {}).items():
        # PR #53 R2, second pass. `_js_block` reads the FIRST declaration; JS
        # runs the LAST. `function docQual(){ return ""; }` inserted above
        # `render()` therefore left the pinned body byte-equal, won at runtime,
        # and restored the bare `conf 0.95` on all 20 cvx-2015 badges with the
        # whole gate green. Pinning a body says nothing about which body runs
        # unless the name is declared exactly once, so that is checked first.
        seen = live.count(f"function {fn_name}(")
        if seen != 1:
            bad.append(f"{fn_name}(): declared {seen} times in the live markup, "
                       f"expected exactly 1 — a second declaration shadows the "
                       f"pinned one at runtime (JS runs the LAST), so the body "
                       f"pin below would be checking a function nothing calls")
            continue
        got_body = _js_block(live, f"function {fn_name}(")
        if got_body is None:
            bad.append(f"{fn_name}(): no such function in the live markup — "
                       f"the qualifier has no producer")
        elif _squash(got_body) != _squash(want_body):
            got_s, want_s = _squash(got_body), _squash(want_body)
            at = next((k for k in range(min(len(got_s), len(want_s)))
                       if got_s[k] != want_s[k]), min(len(got_s), len(want_s)))
            bad.append(f"{fn_name}(): body differs from the pinned one at "
                       f"char {at} — pinned {want_s[at:at + 60]!r}, found "
                       f"{got_s[at:at + 60]!r}. The body is pinned whole "
                       f"because a pinned LINE can sit unreachable below an "
                       f"early return (PR #53 R2)")

    fn = inp.get("coverage_fn", "coverageStrip")
    body = _js_block(live, f"function {fn}(")
    if body is None:
        bad.append(f"{fn}(): the banner has no coverage strip — the "
                   f"document-coverage figure `unattributed_content` already "
                   f"computes stays buried in a warning row below it")
        return bad, {"conf_sites": len(sites), "coverage_text": None}
    say = " ".join(re.sub(r"<[^>]+>", "", body).split())
    for want in inp.get("must_say", []):
        if want not in say:
            bad.append(f"{fn}(): does not say {want!r}")
    for nope in inp.get("must_not_say", []):
        if nope in say:
            bad.append(f"{fn}(): says {nope!r} — the banner may neither publish "
                       f"the complement of this figure as an attributed share "
                       f"(interior gaps are not counted, so it is not one) nor "
                       f"label the figure itself as coverage when what it "
                       f"measures is NON-coverage (PR #53 R7)")
    return bad, {"conf_sites": len(sites), "coverage_text": say}
# --- D10: agent-legibility (correct ARIA + a deep link) --------------------
# All four read the file's TEXT, not a render, for the same reason
# check_split_breakpoint documents: there is no browser in the eval harness.
# The behavioural half — that the deep link actually lands on a rendered page
# and that these names reach the accessibility tree — is the browser walk
# (tasks/reviews/d10_agent_walk.py), which is evidence, not a gate.


def _attrs(tag):
    """{name: value} of the double-quoted attributes in one start tag."""
    return dict(re.findall(r'([-a-zA-Z]+)\s*=\s*"([^"]*)"', tag))


def _named(attrs, live):
    """The accessible name an element carries in its own start tag, or "" if
    it has none.

    PR #55 R2: an `aria-labelledby` is a name only if its IDREFs RESOLVE. The
    first version returned the raw attribute value, so
    `aria-labelledby="no-such-id"` — whose computed name is EMPTY, and which
    `get_by_role(role, name=...)` matches nothing by — read as named, i.e. the
    anonymous-`generic` defect these checks exist to catch passed them. Every
    token must therefore name an `id="…"` present in the same live file.

    Ceiling, deliberate: the name of a resolving reference is the referenced
    element's TEXT, which is not statically reachable here (that element may
    itself be built by JS). So what this returns for the labelledby form is
    the token list — enough to answer "is it named", not "what does it say".
    The page uses `aria-label` everywhere, so nothing rides on the difference
    today; a real labelledby would want the browser walk to assert its text.
    """
    if attrs.get("aria-label"):
        return attrs["aria-label"].strip()
    ids = (attrs.get("aria-labelledby") or "").split()
    if ids and all(re.search(r'\bid="' + re.escape(t) + r'"', live) for t in ids):
        return " ".join(ids)
    return ""


def _why_unnamed(attrs):
    """Why `_named` came back empty — a dangling IDREF and a missing attribute
    are different defects and the diagnostic has to tell them apart."""
    lb = attrs.get("aria-labelledby")
    if lb:
        return (f"aria-labelledby={lb!r} resolves to no id present in this "
                f"file, so the computed name is empty")
    return "it carries neither aria-label nor aria-labelledby"


def check_banner_status_role(case):
    """D10 (2): `#banner` is the page's live status region — it is the only
    element that reports `doc_status`, and JS rewrites it asynchronously after
    every extraction. As a bare `<div>` its role is `generic`, which the
    browser-agent postmortem (S2) records as dropped from the observation
    entirely, so the one answer the page exists to give had no element to be
    the name of. `role="status"` is the correct role for exactly this element
    (it IS a polite live region), and an `aria-label` makes it a *named*
    element rather than an anonymous one.
    """
    inp = case.get("input", {})
    text = _live((ROOT / inp.get("file", UI_STYLESHEET)).read_text(), "js")
    ident = inp.get("banner_id", "banner")
    m = re.search(r'<div([^>]*\bid="' + re.escape(ident) + r'"[^>]*)>', text)
    if not m:
        return [f"#{ident}: no banner element in the live markup"], {"banner_attrs": None}
    attrs = _attrs(m.group(1))
    want_role = inp.get("role", "status")
    bad = []
    if attrs.get("role") != want_role:
        bad.append(f'#{ident}: role is {attrs.get("role")!r}, want {want_role!r} '
                   f"— a bare div is `generic` and carries no name for doc_status")
    if not _named(attrs, text):
        bad.append(f"#{ident}: no accessible name — {_why_unnamed(attrs)}. "
                   f"role=status alone leaves the region anonymous")
    return bad, {"banner_attrs": attrs}


def check_item_text_region(case):
    """D10 (3): the extracted item's text container (`pre.text`, and the
    `div.text.md` the same slot renders in Markdown mode) must be a named
    region. Same S2 shape as the banner: a bare `<pre>` is `generic`, so the
    pane holding the actual answer was invisible to an accessibility-first
    reader. `role="region"` plus an `aria-label` that interpolates the item's
    own code is what makes "Item 1A" addressable; a static label would name
    every item identically and is therefore rejected here.
    """
    inp = case.get("input", {})
    text = _live((ROOT / inp.get("file", UI_STYLESHEET)).read_text(), "js")
    want_expr = inp.get("label_must_interpolate", "${esc(it.item)}")
    want_role = inp.get("role", "region")
    want_tab = inp.get("tabindex")  # D14: ARIA APG scrollable-region pattern
    found, bad = {}, []
    for tag in re.findall(r'<(?:pre|div)[^>]*\bclass="text[^"]*"[^>]*>', text):
        attrs = _attrs(tag)
        key = attrs.get("class")
        found[key] = attrs
        if attrs.get("role") != want_role:
            bad.append(f'class="{key}": role is {attrs.get("role")!r}, '
                       f"want {want_role!r}")
        if want_tab is not None and attrs.get("tabindex") != want_tab:
            bad.append(f'class="{key}": tabindex is {attrs.get("tabindex")!r}, '
                       f"want {want_tab!r} — a named scrollable region without "
                       f"it is unreachable by keyboard on engines lacking "
                       f"auto-focusable scroll containers")
        name = _named(attrs, text)
        if not name:
            bad.append(f'class="{key}": no accessible name naming the item — '
                       f"{_why_unnamed(attrs)}")
        elif want_expr not in name:
            bad.append(f'class="{key}": aria-label {name!r} does not interpolate '
                       f"{want_expr} — every item would carry the same name")
    for key in inp.get("containers", ["text", "text md"]):
        if key not in found:
            bad.append(f'class="{key}": no such item-text container in the live markup')
    return bad, {"item_text_containers": found}


def check_mode_button_names(case):
    """D10 (4): the three input modes each render a button whose accessible
    name was exactly "Extract" — the postmortem's S3 ambiguity shape, where a
    plan targeting the button resolves to 3 matches. Each needs a DISTINCT
    accessible name; the visible label stays "Extract" because that is what
    the button does in every mode, so the distinction rides `aria-label`.

    PR #55 R3 — distinct is not enough, and was the whole check. Swapping
    #go-fx to "Upload" and #go-up to "Fixture" keeps three distinct non-empty
    names and passed: an accessibility-first reader picking by name then
    reaches the file-upload mode when it asked for the fixture, which is worse
    than the ambiguity this row set out to remove. So each name must ALSO
    carry the substring naming its own mode, and must contain the button's own
    VISIBLE text — WCAG 2.5.3 Label in Name, the rule that keeps a speech-input
    user's "click Extract" working once an aria-label is in play. The second
    clause is why the row's evidence can say "screen-reader correctness, not
    agent special-casing": nothing in the eval set backed that before.
    """
    inp = case.get("input", {})
    text = _live((ROOT / inp.get("file", UI_STYLESHEET)).read_text(), "js")
    # {id: substring the name must carry}; a bare list means "no per-mode pin"
    want = inp.get("buttons", ["go-fx", "go-up", "go-url"])
    if not isinstance(want, dict):
        want = dict.fromkeys(want, "")
    names, labels, bad = {}, {}, []
    for ident, mode in want.items():
        m = re.search(r'<button([^>]*\bid="' + re.escape(ident) + r'"[^>]*)>(.*?)</button>',
                      text, re.S)
        if not m:
            bad.append(f"#{ident}: no such button in the live markup")
            continue
        attrs = _attrs(m.group(1))
        names[ident] = _named(attrs, text)
        labels[ident] = " ".join(re.sub(r"<[^>]+>", "", m.group(2)).split())
        if not names[ident]:
            bad.append(f"#{ident}: no accessible name of its own — all three "
                       f'modes read "Extract", which is the 3-match ambiguity '
                       f"({_why_unnamed(attrs)})")
            continue
        if mode and mode.lower() not in names[ident].lower():
            bad.append(f"#{ident}: accessible name {names[ident]!r} does not "
                       f"name its own mode ({mode!r}) — distinct names that "
                       f"point at the wrong mode are worse than no names")
        if labels[ident] and labels[ident].lower() not in names[ident].lower():
            bad.append(f"#{ident}: accessible name {names[ident]!r} does not "
                       f"contain its visible label {labels[ident]!r} "
                       f"(WCAG 2.5.3 Label in Name — speech input targets the "
                       f"word the user can see)")
    seen = [n for n in names.values() if n]
    dupes = sorted({n for n in seen if seen.count(n) > 1})
    if dupes:
        bad.append(f"mode buttons share accessible name(s) {dupes} — the names "
                   f"must tell the three modes apart")
    return bad, {"mode_button_names": names, "mode_button_labels": labels}


def check_deep_link(case):
    """D10 (1), the highest-leverage one: `?fixture=<id>&run=1` must preload
    the fixture select and extract on load, so an agent (or a shared link)
    lands on an already-rendered page instead of the fetch-then-render SPA the
    postmortem's S1/S4 shapes are about.

    Pinned as WHOLE expressions, for the reason WIRE_UI states: asking each
    hop a question about itself is answerable by a broken hop. The pins carry
    the safe-degrade contract too — the membership guard returns before
    anything is assigned, so an unknown or absent `fixture` is a no-op and
    `run=1` on its own extracts nothing.

    WHERE `deepLink()` IS CALLED FROM is the other half, and two rounds got it
    wrong before this shape. The call must sit on `boot()`'s straight-line
    tail, after `#fx` has been filled from `/api/meta`: the option list is the
    very thing the membership guard tests against, so a call that runs earlier
    — or only on the error path — finds an empty `<select>`, returns every
    time, and leaves the deep link a permanent silent no-op.

    PR #55 R1 pinned that as guard-before-run, which is inert: that order is
    fixed by `deepLink()`'s own function text and cannot move. PR #55 R9 then
    measured both failure directions of the replacement, a `flat.find()`
    ordering chain — FALSE GREEN on `deepLink()` moved into the `catch` arm
    (runs only when /api/meta fails, i.e. never on the happy path; `[PASS]
    ui-deep-link`, invariant 63/63 = 1.000) and FALSE RED on hoisting the
    whole `function deepLink(){…}` declaration above `boot()` (behaviour
    identical, declarations hoist). Both follow from the same mistake: the
    guard and run pins live INSIDE the function body, whose textual position
    says nothing about when it runs.

    So there is no ordering machinery here at all any more. The call site is
    pinned by CONTAINMENT — one contiguous span running from the options
    assignment, through the `catch` arm, to `deepLink();` — and any relocation
    out of that straight-line tail is simply a missing pin. What is asserted
    is exactly what is checked: these expressions, and that shape around the
    call. Nothing claims the guard's or the run trigger's position means
    anything, because it does not.
    """
    inp = case.get("input", {})
    text = _live((ROOT / inp.get("file", UI_STYLESHEET)).read_text(), "js")
    flat, bad = _squash(text), []
    for expr in inp.get("wire", []):
        if _squash(expr) not in flat:
            bad.append(f"missing pinned expression (the deep link's wire): {expr}")
    return bad, {"deep_link_pins": len(inp.get("wire", []))}



# ---------------------------------------------------------------- D11 (ADR-036)

# Module names whose presence in `sys.modules` means a network stack was
# loaded. `ssl` and `socket` are there because a client that reached for them
# directly would satisfy a check that only knew about `urllib`.
NET_MODULES = ("urllib.request", "urllib.error", "http.client", "socket", "ssl",
               "requests", "httpx", "anthropic", "openai")
# The gate's own entry points. Importing any of these must not pull a network
# module in — that is the seam ADR-036 §h rules on.
SEAM_IMPORTS = ("src.sec10k.extract", "src.sec10k.eval_adapter",
                "src.sec10k.escalate", "evals.run")
LLM_MODULE = "src/sec10k/llm.py"


def check_escalation_seam(case):
    """ADR-036 §h. The paid path must be UNREACHABLE from a gate run.

    Not a text pin — a DYNAMIC one, because the property is about what an
    import actually loads and a static read of `import` statements cannot see
    a transitive one. A subprocess imports the gate's entry points and reports
    `sys.modules`; any network module in that set fails the check and names
    itself. `evals/bench.py` already self-checks the same property for its own
    AST; this extends it to the modules the eval harness runs.

    Two vacuity guards, because a check that passes on a repo with no client
    at all would be worthless the day someone deletes the seam:

    * `src/sec10k/llm.py` must exist and must itself import `urllib.request` —
      the network code has to be real and has to live there;
    * `llm` must not be imported at MODULE scope anywhere under `src/` or
      `evals/`. `escalate.route` imports it inside the function, which is what
      makes the first property hold; hoisting that import to the top of
      `escalate.py` would break the seam while every other check stayed green.

    What this does NOT prove: that no call is made at runtime. A module can be
    imported lazily inside a function this check never calls, which is
    precisely what `route()` does — deliberately. The property here is "a gate
    run loads no network stack", not "this program cannot reach the network".
    """
    inp = case.get("input", {})
    bad = []
    mods = list(inp.get("imports", SEAM_IMPORTS))
    probe = (
        "import sys; sys.path.insert(0, %r)\n" % str(ROOT)
        + "".join(f"import {m}\n" for m in mods)
        + "import json; print(json.dumps(sorted(sys.modules)))"
    )
    got = subprocess.run([sys.executable, "-c", probe], cwd=str(ROOT),
                         capture_output=True, text=True, timeout=120)
    if got.returncode != 0:
        return [f"importing {mods} failed: {got.stderr.strip().splitlines()[-1:]}"]
    loaded = set(json.loads(got.stdout))
    hit = sorted(set(NET_MODULES) & loaded)
    if hit:
        bad.append(f"importing {mods} loaded network modules {hit} — the gate "
                   "must stay offline and $0 (ADR-036 §h)")

    llm = ROOT / inp.get("llm_file", LLM_MODULE)
    if not llm.exists():
        bad.append(f"{llm.name} does not exist — this check would pass "
                   "vacuously on a repo with no client at all")
    elif "import urllib.request" not in _live(llm.read_text(), "py"):
        bad.append(f"{llm.name} does not import urllib.request — the seam is "
                   "only meaningful if the network code really lives there")

    hoisted = []
    for d in ("src", "evals"):
        for f in sorted((ROOT / d).rglob("*.py")):
            if f.name == "llm.py" or "__pycache__" in f.parts:
                continue
            for node in ast.walk(ast.parse(f.read_text())):
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module or ""])
                if not any(n.endswith("sec10k.llm") or n == "llm" for n in names):
                    continue
                if node.col_offset == 0:   # module scope
                    hoisted.append(f"{f.relative_to(ROOT)}:{node.lineno}")
    if hoisted:
        bad.append(f"`llm` is imported at module scope in {hoisted} — that "
                   "hoists the network stack onto the gate's import graph")
    return bad, {"escalation_seam_modules_loaded": len(loaded)}


# The routing display, pinned the way `confidence_honesty` pins the qualifier:
# as TEXT that must be present and unique in one file. Read the long warning in
# `check_confidence_honesty` — it applies here word for word. A green run says
# the pinned expressions are in `index.html`; it does not say a browser renders
# them, and no static read of one file could.
ROUTING_UI = [
    ("the doc-level routing strip is declared", "function routingStrip(r)"),
    ("...and the banner calls it", "routingStrip(v.routing)"),
    ("the strip distinguishes a quiet trigger from an absent record",
     'if(!r) return "";'),
    ("the strip prints the money, not just the outcome",
     '`$${Number(c.usd || 0).toFixed(4)}'),
    ("the strip names each tier's outcome", "<b>${esc(t.outcome)}</b>"),
    # PR #58 R17/R19. The strip's truncation clause was unpinned, so deleting
    # it left the gate green — and while it existed it said "the first N chars"
    # about a rung 1 window that starts at an arbitrary offset (18 of 43 dev
    # documents). Both halves are pinned: the clause exists, and it renders the
    # RANGE from the record's own `offset`, which is what makes it true.
    ("the strip says what each rung actually saw when its input was clipped",
     "t.truncated ? ` · saw chars ${Number(t.offset).toLocaleString()}"),
    ("agent-loop compact outlines are not described as empty filing windows",
     't.tier === "agent_loop" ? ` · compact outline${t.input_chars ?'),
    ("...and the item pane shows what the deterministic path had said",
     "it.evidence && it.evidence.deterministic"),
    ("...naming the tier that replaced it", "<b>${esc(it.method)}</b>"),
    ("the five-stage flow visibly identifies vision provenance", "v.source || \"skipped\""),
    ("...and its bounded image count and measured cost", "images ${Number((v.images || []).length)}"),
]

# The mirror of ROUTING_UI: expressions that must NOT be in the page at all.
#
# Owner decision, 2026-08-27 — "make it default on, remove the button". The
# escalate checkbox, the helper that read it, the arming round-trip that
# disabled it and the refusal note it printed are all gone, and the three
# request paths no longer carry an `escalate` flag: the SERVER decides, on its
# own off-switch (`SEC10K_ESCALATION_ENABLED=0`), and the page's only remaining
# job is to report what the response says happened.
#
# Pinned as ABSENCE rather than deleted outright, because deleting them would
# leave the property unbound in the direction it can actually rot: a control
# creeping back — the whole assembly at once, or just a stray `&escalate=1` on
# one wire — hands the client a say in whether the deployment spends money,
# which is exactly what the owner removed. `escalation_disarmed` is here for
# the same reason in the other direction: the server no longer emits it, so a
# page still rendering it is a dead honesty note that can never fire.
ROUTING_UI_ABSENT = [
    ("no escalate control is offered — the server decides",
     'id="escalate"'),
    ("...so nothing reads a checkbox at request time", "escalateOn("),
    ("...the fixture and url wires carry no escalate flag", "escalate:"),
    ("...nor does the upload query string", "escalate=1"),
    ("...the page does not ask the server whether it is armed",
     "setEscalationArmed("),
    ("...and renders no disarmed-refusal note the server cannot send",
     "escalation_disarmed"),
]


def check_routing_provenance(case):
    """D11 (ADR-036 §i). Routing is user-visible or it is not routing.

    Both halves the ledger row names, in one check:

    * the DOC-level record — trigger fired or not, each tier attempted with
      its outcome and its cost — rendered in the banner strip;
    * the PER-ITEM tier, which rides the existing `method` field the sidebar
      and pane header already print as `via ...`, plus the pane's evidence row
      naming what the $0 path had said before a tier replaced it.

    Plus the property that replaced this check's original third half. It used
    to pin that the escalate checkbox shipped UNCHECKED and not `disabled` —
    unchecked because a paid tier must never be the default, not disabled
    because a wire nobody can reach is not a shipped capability. The owner
    removed the control on 2026-08-27 ("make it default on, remove the
    button"), so there is no box to be unchecked and the deployment escalates
    on its own switch. What is pinned instead is `ROUTING_UI_ABSENT`: no
    control, no helper reading one, no `escalate` flag on any of the three
    wires, no arming round-trip and no disarmed-refusal note. Same direction
    of protection, inverted — before, the page had to offer the capability
    honestly; now it must not re-acquire a say in whether the server spends.

    Removing those pins rather than inverting them was the option NOT taken:
    a deleted pin binds nothing, and a stray `&escalate=1` creeping back onto
    one wire is exactly the shape that would go unnoticed.
    """
    inp = case.get("input", {})
    src = (ROOT / inp.get("file", UI_STYLESHEET)).read_text()
    live = _live(src, "js")
    bad = []
    for label, expr in ROUTING_UI:
        n = _squash(live).count(_squash(expr))
        if n != 1:
            bad.append(f"index.html: {label} — expected exactly one "
                       f"`{expr}`, found {n}")
    for label, expr in ROUTING_UI_ABSENT:
        n = _squash(live).count(_squash(expr))
        if n:
            bad.append(f"index.html: {label} — `{expr}` occurs {n} times, "
                       f"expected 0. The server decides whether to escalate "
                       f"(ADR-036 §h2, owner 2026-08-27); a page that carries "
                       f"this is taking that decision back.")
    return bad


def check_d26_routing_ui(case):
    """D26 keeps index-row counts, xref counts, and routing decisions visible."""
    ui = (ROOT / "src/sec10k/web/static/index.html").read_text()
    view = (ROOT / "src/sec10k/web/view.py").read_text()
    pins = [
        ("API publishes separately measured primary characters", '"primary_chars"'),
        ("API publishes index-row provenance characters", '"index_entry_chars"'),
        ("API publishes separately measured cross-reference characters", '"cross_reference_chars"'),
        ("cards label primary character counts", "primary ${it.primary_chars.toLocaleString()} ch"),
        ("cards label verified xref character counts", "verified xref ${it.cross_reference_chars.toLocaleString()} ch"),
        ("null primary xref header is safe", "no primary span"),
        ("suppression is not called quiet", 'route === "suppressed"'),
        ("suppression prints backend reason", "r.trigger.reason || \"\""),
        ("flow retains reason and skipped detail", "s.skipped ? `; skipped:"),
        ("fired routing shows exact routing evidence", "resolved xref ${esc((r.trigger.resolved_codes"),
        ("Pipeline trace serializes routing", "routing: v.routing"),
        ("problem routing opens Pipeline trace", "$(\"#trace-box\").open"),
    ]
    bad = [f"D26 UI missing {label}" for label, pin in pins if pin not in ui and pin not in view]
    if "reason || s.skipped" in ui:
        bad.append("D26 UI hides skipped detail behind reason")
    return bad


def check_d26_partial_disposition_ui(case):
    """D26's partial batch names terminal decisions and unfinished targets."""
    ui = (ROOT / "src/sec10k/web/static/index.html").read_text()
    pins = [
        ("routing reads accepted terminal dispositions", "const dispositions = r.dispositions || [];"),
        ("routing counts accepted alternative evidence", "...(r.alternative || [])"),
        ("routing labels the accepted terminal result", "verified terminal disposition"),
        ("routing lists remaining targets", "unresolved targets"),
    ]
    return [f"D26 partial UI missing {label}" for label, pin in pins if pin not in ui]



def _assign(tree, name):
    """The value node of the last module-level `name = ...`, or None."""
    got = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            got = node.value
    return got


def _env_get(node):
    """`os.environ.get("X" ...)` -> "X", else None. Accepts a surrounding
    `int(...)` / `float(...)` coercion, which is how the two numeric knobs
    are written, and any chain of no-argument method calls (`.strip().lower()`),
    which is how the arming variable is normalised (PR #61 R3)."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in ("int", "float") and node.args:
        node = node.args[0]
    while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
            and not node.args and not node.keywords:
        node = node.func.value
    if isinstance(node, ast.BoolOp):          # `os.environ.get(...) or default`
        node = node.values[0]
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    if not (isinstance(f, ast.Attribute) and f.attr == "get"
            and isinstance(f.value, ast.Attribute) and f.value.attr == "environ"):
        return None
    return node.args[0].value if node.args and isinstance(
        node.args[0], ast.Constant) else None


# The largest DEFAULT each ceiling may carry. Not the value the operator must
# choose — that is theirs — but the bound on what an unset variable means.
# Sized at ADR-036 §h2's published defaults (20 calls, $5.00) with headroom, so
# raising a default is possible and unbounding it is not.
DEFAULT_CEILINGS = {"SERVER_MAX_CALLS": 100, "SERVER_MAX_USD": 25.0}

# PR #61 R3. The spellings an operator plausibly types to mean "stop". Not the
# whole set the code may accept — the floor of what it MUST accept.
DISARM_REQUIRED = {"0", "false", "no", "off"}

# PR #61 R5. `escalate.EXTRACT_WINDOW` had a floor ("must not truncate any dev
# filing", the largest committed filing at 1,213,284 chars) and no ceiling. The
# ceiling is what stops one rung-2 call's price from being multiplied silently;
# raising the cap past it means re-deriving ADR-036 §h2's published figure, and
# that is exactly the friction wanted here.
ESCALATE_MODULE = "src/sec10k/escalate.py"
EXTRACT_WINDOW_BOUNDS = (1_213_284, 1_500_000)


def _default_of(node):
    """The literal in `os.environ.get(...) or <literal>`, or None.

    The mirror of `_env_get`, which steps OVER this operand — which is exactly
    how an unbounded default slipped past the name check (PR #58 R18).
    """
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in ("int", "float") and node.args:
        node = node.args[0]
    if not (isinstance(node, ast.BoolOp) and len(node.values) == 2):
        return None
    tail = node.values[1]
    return tail.value if isinstance(tail, ast.Constant) and isinstance(
        tail.value, (int, float)) and not isinstance(tail.value, bool) else None


class _patched_env:
    """`os.environ` with some names set and others removed, restored after.

    Stdlib-only stand-in for the one thing these money checks could never do:
    RUN the shipped expression. `None` as a value means "unset this variable".
    """

    def __init__(self, **values):
        self.values, self.old = values, {}

    def __enter__(self):
        for k, v in self.values.items():
            self.old[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *exc):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return False


def _module_ns(tree, names, env):
    """Exec the module-level assignments and defs called `names`, in source
    order, under `env`, and return the namespace.

    Nodes are picked rather than the file imported because `app.py` imports
    fastapi at module scope and the no-install CI jobs (ADR-003) cannot load
    it — which is the whole reason every money pin over that file has been an
    AST SHAPE read, and shapes are what PR #58 R18, PR #61 R2 and PR #61 R11
    each walked past while satisfying every assertion. Imports are deliberately
    NOT executed; `os` is injected instead, and `server_budget`'s own
    function-scope `from src.sec10k.llm import Budget` runs when it is called.
    """
    body = [n for n in tree.body
            if (isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id in names
                        for t in n.targets))
            or (isinstance(n, ast.FunctionDef) and n.name in names)]
    ns = {"os": os}
    with _patched_env(**env):
        exec(compile(ast.Module(body=body, type_ignores=[]),   # noqa
                     "<money-pin>", "exec"), ns)
    return ns


# PR #61 R11. The spellings the SHIPPED expression must actually refuse, and
# the ones it must let through. `.strip().lower()` was asserted nowhere —
# `_env_get` steps over the method chain by design — so deleting it re-armed
# `FALSE`, `Off` and `"0 "` with the whole gate green. Evaluated, not read:
# `None` means the variable is unset.
DISARM_SPELLINGS = ("0", "false", "no", "off", "FALSE", "Off", "0 ", "  no")
ARM_SPELLINGS = (None, "", "1", "yes", "true", "banana")


def check_escalation_locks(case):
    """ADR-036 §h2. The two locks on the PUBLIC deployment's money, bound by a
    runnable check instead of by prose.

    PR #58 R9, and it is PR #58 R3 reappearing on the code that guards the
    credential: the locks WORK — the reviewer exercised them — but nothing in
    the gate stopped them being removed. Setting `ESCALATION_ENABLED = True`
    and building the process `Budget` with an effectively infinite ceiling left
    invariant 76/76, fast 139/139 and BOTH module self-checks green
    (`tasks/reviews/pr58-r2-red.txt`). `app.py` imports fastapi so it cannot
    carry a CI self-check the dependency-free unit job would run, and the only
    checks over it were two `WIRE_API` source-text pins that read neither
    the constant's definition nor the budget's construction.

    RE-PINNED 2026-08-27 on the owner's "make it default on, remove the
    button". Lock 1 is INVERTED, not removed: it used to ARM paid work
    (`== "1"`) and now DISARMS it (`!= "0"`), so the deployment escalates
    unless the operator says stop. What this check protects is unchanged and
    is the reason the inversion is safe to make — **the money brakes must not
    be removable by a one-token edit** — so every assertion below is re-derived
    for the new shape rather than dropped. The direction the semantics guard
    moved with it: under `== "1"` the danger was an expression that read True
    with the variable UNSET; under `!= "0"` unset means ON by design, and the
    danger is an expression the documented off value cannot switch off.

    It reads the SHAPE, with `ast`, not the text:

    1. `ESCALATION_ENABLED` is a comparison of `os.environ.get(<off-switch
       var>)` against a constant — never a bare `True`. A constant here is an
       off-switch the operator does not have.
    2. ...and the comparison is exactly `!= <off value>`, so setting
       `SEC10K_ESCALATION_ENABLED=0` on the host really does stop the spending.
       Any other operator or comparand leaves a switch that is documented and
       does not work.
    3. `SEC10K_ESCALATION_MAX_CALLS` and `SEC10K_ESCALATION_MAX_USD` are each
       read from the environment into their own module constant, with a bounded
       numeric default.
    4. the process `Budget(...)` is constructed from those two NAMES, not from
       literals — which is the mutation that made the ceiling infinite.
    5. `_run` passes that budget into `extract_items`, so the ceiling is
       actually reached (`WIRE_API` pins the call's text; this pins that the
       budget argument is the process one and not a fresh instance).
    6. ...and that call's `escalate=` names `ESCALATION_ENABLED` rather than a
       literal. New in this pass, and it is what makes the inversion honest:
       with no request flag left to AND against, `escalate=True` at the call
       site would hard-wire paid work and leave `ESCALATION_ENABLED` sitting in
       the file looking authoritative while nothing read it.

    What it does NOT prove: that fastapi binds the routes, that the deployment
    sets any variable, or that the ceiling is the right size. It proves the
    brakes are still WIRED, which is exactly the property that silently
    disappeared under mutation.
    """
    inp = case.get("input", {})
    src = (ROOT / inp.get("file", API_FILE)).read_text()
    bad = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [f"{inp.get('file', API_FILE)} does not parse: {e}"]

    arm_var = inp.get("arming_var", "SEC10K_ESCALATION_ENABLED")
    armed = _assign(tree, "ESCALATION_ENABLED")
    if armed is None:
        bad.append("no module-level `ESCALATION_ENABLED = ...` — the "
                   "off-switch is gone entirely")
    elif not isinstance(armed, ast.Compare):
        bad.append(f"`ESCALATION_ENABLED` is {ast.dump(armed)[:60]}, not a "
                   f"comparison against {arm_var} — a constant here is an "
                   "off-switch the operator does not have, on a public, "
                   "unauthenticated deployment that now escalates by default")
    elif _env_get(armed.left) != arm_var:
        bad.append(f"`ESCALATION_ENABLED` does not compare "
                   f"os.environ.get({arm_var!r}); left is "
                   f"{_env_get(armed.left)!r}")
    else:
        # PR #58 R18: the SHAPE was pinned and the SEMANTICS were not, so a
        # one-token operator edit defeated the lock while satisfying every
        # other assertion here. That lesson survives the 2026-08-27 inversion
        # unchanged; only the target moved. The property now is that the
        # DOCUMENTED off value actually disarms — `!= "0"` — so any other
        # operator or comparand ships a stop button wired to nothing.
        if len(armed.ops) != 1 or not isinstance(armed.ops[0], ast.NotIn):
            bad.append(f"`ESCALATION_ENABLED` compares {arm_var} with "
                       f"{[type(o).__name__ for o in armed.ops]}, not NotIn — "
                       "escalation is on by default, so this expression is the "
                       "OFF switch and any other operator breaks it")
        rhs = armed.comparators[0] if len(armed.comparators) == 1 else None
        if not (isinstance(rhs, ast.Name) and rhs.id == "DISARM_VALUES"):
            bad.append("`ESCALATION_ENABLED` is not tested against the named "
                       "`DISARM_VALUES` — an inline literal is a stop button "
                       "whose accepted spellings nobody can read or document")
        else:
            # PR #61 R3: the SET is the property. `!= "0"` alone left `false`,
            # `off` and `FALSE` all ARMED, and those are what an operator types
            # into a Zeabur variable. A stop button wired to a comparand nobody
            # documents is worse than none — this repo's own
            # `escalation-locks-evaded.py` makes that argument.
            vals = _assign(tree, "DISARM_VALUES")
            got = ([e.value for e in vals.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                   if isinstance(vals, (ast.Tuple, ast.List, ast.Set)) else None)
            want = set(inp.get("disarm_values", DISARM_REQUIRED))
            if got is None:
                bad.append("`DISARM_VALUES` is not a module-level literal "
                           "tuple/list/set of strings")
            elif not want <= set(got):
                bad.append(f"`DISARM_VALUES` is {sorted(got)}, missing "
                           f"{sorted(want - set(got))} — an operator typing one "
                           f"of those into the host variable would believe they "
                           f"had stopped the spending, and would be wrong")
            elif any(v != v.strip().lower() for v in got):
                bad.append(f"`DISARM_VALUES` has a member that is not already "
                           f"stripped and lowercase ({sorted(got)}) — the "
                           f"comparison normalises the input, so such a member "
                           f"can never match")

    # PR #61 R11 — and it is the whole defect class this round is about. Every
    # assertion above reads the expression's SHAPE, and `.strip().lower()` is
    # not part of any of them: `_env_get` steps over the method chain on
    # purpose, so deleting the chain leaves `FALSE`, `Off` and `"0 "` ARMED
    # with all of the above green. This one RUNS the shipped expression, once
    # per spelling, and asserts the property directly. Normalisation is
    # therefore bound by what it DOES, not by the two method names that happen
    # to do it today.
    if armed is not None:
        try:
            ns = {v: _module_ns(tree, {"DISARM_VALUES", "ESCALATION_ENABLED"},
                                {arm_var: v})["ESCALATION_ENABLED"]
                  for v in DISARM_SPELLINGS + ARM_SPELLINGS}
        except Exception as e:                    # a shape too broken to run
            bad.append(f"`ESCALATION_ENABLED` cannot be evaluated in isolation "
                       f"({type(e).__name__}: {e}) — the off-switch must be a "
                       f"self-contained expression over the environment")
        else:
            wrong = [v for v in DISARM_SPELLINGS if ns[v]]
            if wrong:
                bad.append(f"`{arm_var}` set to {wrong} leaves escalation ARMED "
                           f"— those are what an operator types into a Zeabur "
                           f"variable, and a stop button that ignores them is "
                           f"worse than none")
            wrong = [v for v in ARM_SPELLINGS if not ns[v]]
            if wrong:
                bad.append(f"`{arm_var}` set to {wrong} DISARMS escalation — "
                           f"unset and empty are the owner's default-on, and a "
                           f"switch that trips on an unrelated value is a "
                           f"deployment nobody can arm")

    knobs = {"SERVER_MAX_CALLS": inp.get("calls_var", "SEC10K_ESCALATION_MAX_CALLS"),
             "SERVER_MAX_USD": inp.get("usd_var", "SEC10K_ESCALATION_MAX_USD")}
    for const, envvar in knobs.items():
        got = _assign(tree, const)
        if got is None:
            bad.append(f"no module-level `{const} = ...`")
        elif _env_get(got) != envvar:
            bad.append(f"`{const}` is not read from os.environ[{envvar!r}] "
                       f"(got {_env_get(got)!r}) — a literal here is a ceiling "
                       "the operator cannot lower")
        else:
            # PR #58 R18: `_env_get` deliberately steps over the `or <default>`
            # operand, so an unbounded DEFAULT passed the name check. A ceiling
            # whose fallback is 10**9 is not a ceiling on a host where the
            # variable is unset — which is every host that has not been told
            # about it.
            dflt = _default_of(got)
            cap = inp.get("max_default", {}).get(const, DEFAULT_CEILINGS[const])
            if dflt is None:
                # says which of the two it is, because "no fallback" and
                # "a fallback this check cannot evaluate, e.g. `10 ** 9`" are
                # different defects and the message must not conflate them
                bad.append(f"`{const}`'s `or <default>` fallback is absent or "
                           "is not a plain numeric literal (a computed default "
                           "like `10 ** 9` reads as a ceiling and is not one) — "
                           "an unset variable must not mean 'no ceiling'")
            elif not 0 < dflt <= cap:
                bad.append(f"`{const}`'s default is {dflt}, outside (0, {cap}] — "
                           "an unbounded default is an unbounded deployment")

    budgets = [n for n in ast.walk(tree)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id == "Budget"]
    if len(budgets) != 1:
        bad.append(f"expected exactly one `Budget(...)` construction in "
                   f"{API_FILE}, found {len(budgets)} — a second one is a "
                   "second ceiling, which is no ceiling")
    for b in budgets:
        kw = {k.arg: k.value for k in b.keywords}
        if sorted(kw) != ["max_calls", "max_usd"]:
            bad.append(f"`Budget(...)` keywords {sorted(kw)} != "
                       "['max_calls', 'max_usd'] — a positional or missing "
                       "ceiling falls back to llm.Budget's per-document default")
        for arg, want in (("max_calls", "SERVER_MAX_CALLS"),
                          ("max_usd", "SERVER_MAX_USD")):
            v = kw.get(arg)
            if not (isinstance(v, ast.Name) and v.id == want):
                bad.append(f"`Budget({arg}=...)` is not the constant {want} — "
                           "a literal here is the mutation that made the "
                           "process ceiling infinite (PR #58 R9)")
    if budgets and not any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "server_budget"
            for n in ast.walk(tree)):
        bad.append("nothing calls `server_budget()` — the process budget is "
                   "constructed and never passed, so nothing is bounded")

    # PR #61 R2. `server_budget()`'s MEMO is the only thing that makes the
    # budget process-wide, and nothing read it: deleting three lines gave every
    # request its own $5 / 20-call ceiling with invariant and fast byte-
    # identical. This check's own docstring already claimed to pin "the process
    # one and not a fresh instance"; now it does. Two assertions, because
    # either alone is evadable — the function must declare the module memo
    # `global`, and it must RETURN that name rather than a fresh construction.
    memo = inp.get("memo_var", "_SERVER_BUDGET")
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef)
               and n.name == "server_budget"), None)
    if fn is None:
        bad.append("no module-level `def server_budget(...)` — there is no "
                   "process budget to be process-wide")
    else:
        if not any(isinstance(n, ast.Global) and memo in n.names
                   for n in ast.walk(fn)):
            bad.append(f"`server_budget()` does not declare `global {memo}` — "
                       f"without the memo every request builds its own Budget "
                       f"and the ceiling is per-REQUEST, not per-deployment")
        rets = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
        if not rets or not all(isinstance(r.value, ast.Name) and r.value.id == memo
                               for r in rets):
            bad.append(f"`server_budget()` returns something other than the "
                       f"module-level `{memo}` — a fresh `Budget(...)` here is "
                       f"the mutation that leaves invariant and fast green "
                       f"while the deployment loses its only aggregate ceiling")
        if not any(isinstance(n, ast.Assign) and n.targets and any(
                isinstance(t, ast.Name) and t.id == memo for t in n.targets)
                for n in ast.walk(fn)):
            bad.append(f"nothing assigns `{memo}` inside `server_budget()` — "
                       f"the memo is never filled")

        # PR #61 R12. The three assertions above prove the OBJECT is shared and
        # say nothing about its COUNTERS, and the counters are the ceiling. A
        # three-line self-reset inside `server_budget()` satisfies all three
        # and gives every request a fresh allowance: measured, six uploads
        # produced 6 outbound calls against the shipped tree's 1. So run it —
        # spend one call through the first handle, ask for the budget again,
        # and require the spend to still be there. `take()` is used rather than
        # a drain because a mutated ceiling can be 10**9 and draining it would
        # hang the suite.
        try:
            ns = _module_ns(tree, {"SERVER_MAX_CALLS", "SERVER_MAX_USD",
                                   memo, "server_budget"},
                            {envvar: None for envvar in knobs.values()})
            first = ns["server_budget"]()
            first.take()
            again = ns["server_budget"]()
            spent = getattr(again, "calls", None)
        except Exception as e:
            bad.append(f"`server_budget()` cannot be exercised "
                       f"({type(e).__name__}: {e}) — the process ceiling must "
                       f"be runnable to be a ceiling")
        else:
            if again is not first or spent != 1:
                bad.append(f"`server_budget()` hands back a budget whose spend "
                           f"has been reset (calls={spent!r} after one take, "
                           f"same object: {again is first}) — the OBJECT being "
                           f"shared is not the property; the COUNTERS are, and "
                           f"a per-request allowance bounds nothing when the "
                           f"caller is anonymous and unlimited")

    # PR #61 R5. Lock 3's cap had a FLOOR and no ceiling, so raising it to
    # 25,000,000 left the gate and the module self-check green while one rung-2
    # call's price rose ~20x and §h2's published figure silently stopped being
    # true. Read from escalate.py, because that is where the cap lives and a
    # money brake belongs to whichever file holds it.
    #
    # REAL TREE ONLY. The known-bad fixtures substitute app.py and have no say
    # over escalate.py, so asserting a second file against them adds a failure
    # they cannot cause and breaks their exact counts — measured: the first
    # revision of this reddened all three lock cases on one window mutation
    # instead of the one whose file it is.
    win_file = inp.get("window_file", None if "file" in inp else ESCALATE_MODULE)
    lo, hi = inp.get("window_bounds", EXTRACT_WINDOW_BOUNDS)
    win = (_assign(ast.parse((ROOT / win_file).read_text()), "EXTRACT_WINDOW")
           if win_file else None)
    if win_file is None:
        pass
    elif not (isinstance(win, ast.Constant) and isinstance(win.value, int)
            and not isinstance(win.value, bool)):
        bad.append(f"{win_file}: `EXTRACT_WINDOW` is not a plain integer "
                   f"literal — the published per-call ceiling is derived from "
                   f"it and must be readable here")
    elif not lo <= win.value <= hi:
        bad.append(f"{win_file}: `EXTRACT_WINDOW` is {win.value:,}, outside "
                   f"[{lo:,}, {hi:,}] — below the floor it truncates a dev "
                   f"filing, above the ceiling it multiplies one call's price "
                   f"and voids ADR-036 §h2's published MAX_USD + one call")

    # Owner, 2026-08-27. With no request-level flag left to AND against, the
    # call site is where the switch is either honoured or quietly orphaned:
    # `escalate=True` here hard-wires paid work and leaves the switch above it
    # looking authoritative with nothing reading it.
    #
    # PR #61 R10 briefly widened what "the switch" means — `escalate=` named a
    # token door's verdict rather than `ESCALATION_ENABLED` — and ADR-041
    # removed the door the next day, so it names the off-switch again. This
    # assertion keeps the half that belongs to it, that the argument is a NAME
    # and never a literal, and `escalation_choke_point` owns the other half:
    # WHICH name, and that the budget rides it. Neither check can be satisfied
    # by the other's evasion.
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "extract_items"]
    for c in calls:
        v = {k.arg: k.value for k in c.keywords}.get("escalate")
        if v is None:
            bad.append("the `extract_items(...)` call passes no `escalate=` "
                       "keyword — the deployment's own switch reaches nothing")
        elif not isinstance(v, ast.Name):
            bad.append(f"`extract_items(escalate=...)` is "
                       f"{ast.dump(v)[:40]}, not a name bound from the door's "
                       f"decision — a literal here hard-wires paid work and "
                       f"orphans every switch above it")
    return bad



GATE_MODULE = "src.sec10k.web.gate"
# ADR-043's whole reason for existing. The door of ADR-036 §h2 lock 4 was
# correct server-side and shipped with NO WAY FOR THE PAGE TO OPEN IT: four
# `fetch()` calls, two headers, both `Content-Type`, and no field. It was shut
# to every human visitor including the owner, and ADR-041 deleted it. These
# pins are the half nothing checked. `SENDS_TOKEN_UI` is not decoration — a
# door whose client cannot present a credential is not a door, it is an outage.
SENDS_TOKEN_UI = [
    ("the page has a field to type the key into", 'id="esc-key"'),
    ("...and a button to verify it before extraction", 'id="verify-key"'),
    ("...and a visible verification status", 'id="key-status"'),
    ("...and injects it in the ONE helper all three modes go through",
     "async function call(url, opts)"),
    # A CROSS-REPO CONTRACT, which is why it is pinned rather than left as an
    # implementation detail. D10's deep link (`?fixture=…&run=1`) extracts
    # during boot, BEFORE any agent can type into `#esc-key` — so the only way
    # a browser agent escalates on that path is to seed this exact key into
    # localStorage before navigating. Rename it and the agent silently drops to
    # the free tier with everything green on both sides (ADR-043 §d).
    ("...under the storage key the browser agent seeds",
     'const KEY_STORE = "sec10k.escalation-key"'),
    ("...and extraction reads only the verified value",
     "const k = verifiedKey()"),
]
ESCALATION_UI = [
    ("the page declares the strip", "function escalationStrip(e)"),
    ("...and the banner calls it", "escalationStrip(v.escalation)"),
    ("...printing the SERVER's reason, not one the page invented",
     'esc(e.reason || "")'),
    ("...and saying plainly that the tier did not run",
     "model tier: <b>did not run</b>"),
]


def check_escalation_choke_point(case):
    """ADR-041. The paid tier is open to every request, so the process Budget
    is the ONLY money bound — and nothing may escalate outside it.

    This replaces `escalation_door` (TD-158 / PR #61 R10), which pinned a
    `X-Escalation-Token` header that the owner removed on 2026-08-28: the
    deployment exists to be opened by an interviewer who configures nothing,
    and a door only the operator can walk through closed the demo along with
    the billing. ADR-041 records that reversal and what it costs.

    **What is GONE with the door, said plainly**: an anonymous caller can now
    reach the paid tier through `POST /api/extract/url` on any EDGAR Archives
    URL. That is deliberate. It is also why the assertions below are stricter
    about the budget than the door's ever were — with the header gone, the
    ceiling is not the second line of defence, it is the only one.

    Four properties, and the first three are the ones a mutation walks around:

    1. **One entrance.** Exactly one `extract_items(...)` in `app.py`, inside
       `_run`. PR #61 R13 is the failure this exists for: a guard written once
       in one function that a second endpoint simply did not call.
    2. **Escalating and billing are the SAME name.** `escalate=` must be the
       module off-switch (`ESCALATION_ENABLED`) and `budget=` must be
       conditioned on that same name. A literal `True` at `escalate=` defeats
       the operator's runaway stop while `/api/meta` goes on publishing it;
       two different conditions let a request escalate on one and bill against
       another, which is the process ceiling bypassed in one token.
    3. **The envelope publishes the decision**, built from that same name, and
       the page prints the server's own sentence. `routing: null` alone cannot
       distinguish "the tier ran and stayed quiet" from "the tier never ran".
    4. **The ceiling is real and finite.** `llm.Budget` is RUN — it must
       actually refuse on both its call and its dollar limit — and
       `SERVER_MAX_USD` must fall back to a positive finite number when the
       host variable is unset. A ceiling nobody runs is a number in a
       docstring.

    What it does NOT prove: that fastapi binds the routes (the standing
    `app.py` limitation, TD-38), that the ceiling is set LOW enough — that is
    the operator's judgement and `SEC10K_ESCALATION_MAX_USD` is the knob — or
    that the budget survives a redeploy. It does not: a restart refills it,
    which ADR-041 states as an accepted, recurring cost rather than a bound.
    Rate limiting is `check_free_tier_limit`'s (D15, ADR-040), not this one's.

    One half IS a shape read and is marked as such at the site: `app.py`
    imports fastapi, which the eval environment does not have, so
    `server_budget()`'s memoization is pinned by its `global` statement rather
    than by calling it twice. Everything about the ceiling's BEHAVIOUR runs for
    real out of `llm.py`.
    """
    inp = case.get("input", {})
    api_file = inp.get("file", API_FILE)
    off_const = inp.get("off_switch", "ESCALATION_ENABLED")
    bad = []
    try:
        tree = ast.parse((ROOT / api_file).read_text())
    except SyntaxError as e:
        return [f"{api_file} does not parse: {e}"]

    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    runner = inp.get("runner", "_run")
    run_fn = next((f for f in fns if f.name == runner), None)
    inside = {id(n) for n in ast.walk(run_fn)} if run_fn else set()

    # ---- 1: one entrance.
    ex = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
          and isinstance(n.func, ast.Name) and n.func.id == "extract_items"]
    stray = [c for c in ex if id(c) not in inside]
    if len(ex) != 1 or stray:
        bad.append(f"{api_file}: {len(ex)} `extract_items(...)` call(s), "
                   f"{len(stray)} of them outside `{runner}` — with the tier "
                   f"open to everyone, a second entrance is an UNBUDGETED "
                   f"entrance (PR #61 R13)")
    if run_fn is None:
        bad.append(f"{api_file}: no `def {runner}` — nothing converges")

    # A cheap credential check must still sit behind the existing global
    # limiter; otherwise it becomes an unbounded password oracle.
    verify_fn = next((f for f in fns if f.name == "verify_escalation_key"), None)
    if "file" not in inp and verify_fn is None:
        bad.append(f"{api_file}: no `verify_escalation_key` endpoint — the "
                   "page cannot confirm a key before extraction")
    elif "file" not in inp:
        source = ast.unparse(verify_fn)
        if "gate.paid_path_open" not in source or "gate.HEADER" not in source:
            bad.append(f"{api_file}: `verify_escalation_key` does not ask the "
                       "shared gate with its shared header — verification can "
                       "disagree with extraction")
        routes = [ast.literal_eval(a.args[0]) for a in verify_fn.decorator_list
                  if isinstance(a, ast.Call) and a.args
                  and isinstance(a.args[0], ast.Constant)]
        if "/api/extract/verify-key" not in routes:
            bad.append(f"{api_file}: key verification is not under "
                       "`/api/extract/verify-key` — the existing request "
                       "limiter does not cover the credential oracle")

    # ---- 2: escalating and billing carry the DOOR's verdict, and the same one.
    # ADR-043 restored the door, so `escalate=` names the verdict again rather
    # than the bare off-switch (which the door folds in). The budget must ride
    # that SAME name: escalating on one condition and billing against another
    # is the process ceiling bypassed in one token (PR #61 R19).
    verdict = None
    for n in (ast.walk(run_fn) if run_fn else []):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) \
                and isinstance(n.value.func, ast.Attribute) \
                and n.value.func.attr == "paid_path_open" \
                and isinstance(n.targets[0], ast.Tuple):
            first = n.targets[0].elts[0]
            verdict = first.id if isinstance(first, ast.Name) else None
    if run_fn is not None and verdict is None:
        bad.append(f"{api_file}: `{runner}` does not bind the door's verdict to "
                   f"a name — `(may, why) = gate.paid_path_open(...)`; a "
                   f"verdict nothing holds is a verdict nothing can honour")
    for c in [c for c in ex if id(c) in inside]:
        kw = {k.arg: k.value for k in c.keywords}
        v = kw.get("escalate")
        if verdict is None or not (isinstance(v, ast.Name) and v.id == verdict):
            bad.append(f"{api_file}: `extract_items(escalate=...)` is "
                       f"{ast.dump(v)[:40] if v is not None else 'absent'}, not "
                       f"the door's verdict — a literal or the raw off-switch "
                       f"here means the decision is taken and then discarded, "
                       f"which is the shape PR #61 R13 found and R10 paid for")
        b = kw.get("budget")
        names = {n.id for n in ast.walk(b) if isinstance(n, ast.Name)} if b else set()
        if verdict is not None and verdict not in names:
            bad.append(f"{api_file}: `extract_items(budget=...)` is not "
                       f"conditioned on `{verdict}` — escalating on one "
                       f"condition and billing against another is how the "
                       f"process ceiling gets bypassed")

    # ---- 3: the envelope says what was decided, and the page prints it.
    published = [n for n in (ast.walk(run_fn) if run_fn else [])
                 if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Subscript)
                         and isinstance(t.slice, ast.Constant)
                         and t.slice.value == "escalation" for t in n.targets)]
    if run_fn is not None and not published:
        bad.append(f"{api_file}: `{runner}` never sets `view['escalation']` — "
                   f"an envelope that says nothing lets a viewer believe the "
                   f"paid path ran and found nothing worth doing")
    elif verdict is not None and not all(
            verdict in {n.id for n in ast.walk(p.value) if isinstance(n, ast.Name)}
            for p in published):
        bad.append(f"{api_file}: `view['escalation']` is not built from "
                   f"`{verdict}` — the envelope would be free to disagree "
                   f"with what actually ran")

    ui = inp.get("ui_file", None if "file" in inp else UI_STYLESHEET)
    if ui:
        live = _live((ROOT / ui).read_text(), "js")

        if _squash(live).count(_squash('"X-Escalation-Token"')) != 2:
            bad.append("index.html: the shared escalation header must appear "
                       "once for verification and once for extraction")

        # ---- 5: THE PAGE CAN ACTUALLY OPEN THE DOOR. The assertion whose
        # absence cost ADR-041. Each pin must occur exactly once: zero means
        # the door is shut to every human (the original defect), and more than
        # one means a second, drifting copy.
        for label, expr in SENDS_TOKEN_UI:
            n = _squash(live).count(_squash(expr))
            if n != 1:
                bad.append(f"index.html: {label} — expected exactly one "
                           f"`{expr}`, found {n}. A door the client cannot "
                           f"present a credential to is not a door, it is an "
                           f"outage (ADR-041 deleted the last one for this)")
        # ...and it must be injected in the SHARED helper, not at one of the
        # three call sites. A count of 1 alone cannot tell those apart, and the
        # per-call-site version silently leaves two of three modes unable to
        # escalate — the same class of defect, one third as visible.
        body = _fn_body(live, "async function call(url, opts)")
        if body is None:
            bad.append("index.html: no `async function call(url, opts)` body "
                       "to read — the frontend choke point is gone, so each "
                       "mode is free to forget the header")
        elif "X-Escalation-Token" not in body:
            bad.append("index.html: the `X-Escalation-Token` header is set "
                       "OUTSIDE `call()` — every extract mode funnels through "
                       "that helper, and a header attached at one call site "
                       "leaves the other two modes unable to escalate")

        verify_body = _fn_body(live, "async function verifyKey()")
        if verify_body is None:
            bad.append("index.html: no `verifyKey()` — the green state has no "
                       "credential check behind it")
        else:
            for expr in ('fetch("/api/extract/verify-key"',
                         "VERIFIED_KEY = k", "rememberKey(k)"):
                if expr not in verify_body:
                    bad.append(f"index.html: `verifyKey()` is missing `{expr}` "
                               "— only a server-approved key may be enabled "
                               "and remembered")

        for label, expr in ESCALATION_UI:
            n = _squash(live).count(_squash(expr))
            if n != 1:
                bad.append(f"index.html: {label} — expected exactly one "
                           f"`{expr}`, found {n}")

    # ---- 4: the ceiling is real, and it REFUSES. Run it, never read it.
    # Scoped off when a known-bad app.py fixture stands in: that fixture has no
    # say over llm.py, and charging it for a module it cannot influence is the
    # bound `escalation_locks` already learned the hard way.
    if "file" not in inp:
        # ---- 6: RUN the door's decision table. Not a shape read: `gate.py` is
        # stdlib-only and imports no fastapi precisely so this can import it
        # and exercise every row. PR #58 R18, PR #61 R2 and PR #61 R11 were
        # three separate evasions that each satisfied a shape and broke the
        # property; a table that is EXECUTED cannot be satisfied that way.
        gate = importlib.import_module(inp.get("gate_module", GATE_MODULE))
        floor = inp.get("min_token_chars", 10)
        if gate.MIN_TOKEN_CHARS < floor:
            bad.append(f"gate.MIN_TOKEN_CHARS is {gate.MIN_TOKEN_CHARS}, under "
                       f"{floor} — a secret short enough to guess is a door "
                       f"that is closed only in the docs")
        good = "k" * max(gate.MIN_TOKEN_CHARS, floor)
        for (presented, armed, configured), want in [
                ((good, True, ""), False),          # UNSET IS CLOSED
                ((None, True, ""), False),
                ((good, True, good[:gate.MIN_TOKEN_CHARS - 1]), False),
                # a SHORT secret the caller gets exactly right: without this row
                # the MIN_TOKEN_CHARS floor is unbound, because a mismatched
                # token fails the compare anyway (PR #61 R2 mutation N3)
                (("abc", True, "abc"), False),
                ((None, True, good), False),        # no header
                (("", True, good), False),          # empty header
                (("w" * len(good), True, good), False),                # wrong
                ((good, False, good), False),       # operator's off-switch wins
                ((good, True, good), True)]:        # the one case that opens
            try:
                got, why = gate.paid_path_open(presented, armed, token=configured)
            except Exception as e:
                bad.append(f"gate.paid_path_open raised {type(e).__name__}: {e} "
                           f"— a door that throws is a door whose behaviour "
                           f"nobody knows")
                continue
            if bool(got) is not want:
                bad.append(
                    f"gate.paid_path_open(header="
                    f"{'set' if presented else presented!r}, armed={armed}, "
                    f"secret={len(configured)} chars) is {got!r}, want {want!r}"
                    + (" — an unconfigured or misconfigured deployment must be "
                       "CLOSED to everyone, not open to everyone"
                       if not configured or len(configured) < gate.MIN_TOKEN_CHARS
                       else ""))
            elif not got and (not why or len(why) < 30):
                bad.append(f"a refusal with no usable reason ({why!r}) — the "
                           f"envelope publishes this string and a viewer who "
                           f"is told nothing assumes the tier ran")
            elif not got and configured and configured in (why or ""):
                bad.append("the refusal reason contains the secret itself")

        # PR #61 R18. Every row above passes `token=`, and NOTHING in production
        # does — `app.py` calls `paid_path_open(header, ESCALATION_ENABLED)`, so
        # the `token is None` branch was the only one a request ever took and
        # was exercised by no row. These call it exactly as `_run` does.
        for env_secret, presented, want in ((None, good, False),
                                            (None, None, False),
                                            ("", good, False),
                                            (good, None, False),
                                            (good, good, True)):
            with _patched_env(**{gate.TOKEN_VAR: env_secret}):
                try:
                    got, _ = gate.paid_path_open(presented, True)
                except Exception as e:
                    bad.append(f"the PRODUCTION call gate.paid_path_open("
                               f"presented, armed) raised {type(e).__name__}: {e}")
                    continue
            if bool(got) is not want:
                bad.append(
                    f"the PRODUCTION call with {gate.TOKEN_VAR}={env_secret!r} "
                    f"and header={'set' if presented else presented!r} is "
                    f"{got!r}, want {want!r}"
                    + ("" if env_secret else " — an UNCONFIGURED deployment "
                       "must be closed to everyone; this is the one branch "
                       "app.py takes and no `token=` row reaches"))
        with _patched_env(**{gate.TOKEN_VAR: "  " + good + "  "}):
            if gate.configured_token() != good:
                bad.append(f"gate.configured_token() does not read "
                           f"{gate.TOKEN_VAR} out of the environment (stripped) "
                           f"— the secret must be host configuration, never a "
                           f"literal in the tree")

        # `app.py` imports fastapi, which is NOT a dependency of the eval
        # environment — that is why every money pin in this file reads it with
        # `ast`. So the ceiling's VALUE is read from the tree and the ceiling's
        # BEHAVIOUR is run out of `llm.py`, which is stdlib only.
        ceiling = None
        for n in tree.body:
            if isinstance(n, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "SERVER_MAX_USD"
                    for t in n.targets):
                ceiling = n.value
        lits = [x.value for x in ast.walk(ceiling) if isinstance(x, ast.Constant)
                and isinstance(x.value, (int, float))
                and not isinstance(x.value, bool)] if ceiling else []
        if not lits or not all(0 < v < float("inf") for v in lits):
            bad.append(f"{api_file}: SERVER_MAX_USD's fallback is {lits!r} — "
                       f"the only money bound since ADR-041 must fall back to "
                       f"a positive finite number of dollars when the host "
                       f"variable is unset or garbage")

        from src.sec10k.llm import Budget, BudgetExceeded
        spent = Budget(max_calls=5, max_usd=0.01)
        spent.charge(0.02, 100)
        try:
            spent.take()
            bad.append("llm.Budget did not refuse a call after its DOLLAR "
                       "ceiling was passed — the deployment's only bound does "
                       "not bind")
        except BudgetExceeded:
            pass
        try:
            Budget(max_calls=0, max_usd=100.0).take()
            bad.append("llm.Budget did not refuse a call at max_calls=0 — the "
                       "hard offline mode a zero budget is supposed to be")
        except BudgetExceeded:
            pass

        # ...and the deployment must build ONE, shared. A per-request Budget is
        # a ceiling per request, which on an open endpoint is no ceiling at
        # all. This half IS a shape read (see the docstring's negative space):
        # `server_budget` cannot be called here without fastapi.
        sb = next((f for f in fns if f.name == "server_budget"), None)
        if sb is None:
            bad.append(f"{api_file}: no `server_budget()` — the process-wide "
                       f"ceiling every request must share")
        elif not any(isinstance(n, ast.Global) for n in ast.walk(sb)):
            bad.append(f"{api_file}: `server_budget()` memoizes nothing "
                       f"(no `global`) — a fresh Budget per request bounds one "
                       f"request and leaves the deployment unbounded")
    return bad


def check_escalation_key_ui_behavior(case):
    """Run the escalation credential state machine from the shipped page."""
    ui = ROOT / case.get("input", {}).get("ui_file", UI_STYLESHEET)
    probe = ROOT / "evals/probes/escalation_key_ui_behavior.js"
    got = subprocess.run(["node", str(probe), str(ui)], cwd=ROOT,
                         capture_output=True, text=True, timeout=10)
    if got.returncode:
        detail = (got.stderr or got.stdout).strip().splitlines()
        return ["index.html escalation-key behavior: " +
                (detail[-1] if detail else f"node exited {got.returncode}")]
    return []


def check_ui_cover_navigation(case):
    """Run the cover projection and shipped source-navigation behavior."""
    from src.sec10k.web.view import build_view

    text = "FORM 10-K\nACME\nItem 1. Business\nbody"
    start = text.index("Item 1.")
    view = build_view({"normalized_text": text, "items": [
        {"item": "1", "status": "extracted", "start": start,
         "end": len(text), "heading_text": "Item 1. Business"}]}, display_max=12)
    front = view.get("front_matter") or {}
    bad = []
    if front.get("text") != text[:start][:12]:
        bad.append("view.front_matter is not the normalized slice before Item 1")
    if front.get("chars") != start or front.get("truncated") is not (start > 12):
        bad.append("view.front_matter does not report its full size/truncation")

    ui = ROOT / case.get("input", {}).get("ui_file", UI_STYLESHEET)
    probe = ROOT / "evals/probes/ui_cover_navigation.js"
    got = subprocess.run(["node", str(probe), str(ui)], cwd=ROOT,
                         capture_output=True, text=True, timeout=10)
    if got.returncode:
        detail = (got.stderr or got.stdout).strip().splitlines()
        bad.append("index.html cover/navigation behavior: " +
                   (detail[-1] if detail else f"node exited {got.returncode}"))
    return bad


def check_edgar_viewer_url(case):
    """Accept SEC's documented URL variants without widening the fetch boundary."""
    try:
        from src.sec10k.web.edgar_url import canonical_edgar_url
    except ImportError:
        return ["src.sec10k.web.edgar_url canonicalizer is missing"]

    canonical = ("https://www.sec.gov/Archives/edgar/data/17797/"
                 "000132616025000072/duk-20241231.htm")
    bad = []
    accepted = [
        canonical,
        canonical + "?output=1#part-ii",
        canonical.replace("www.sec.gov", "sec.gov"),
        canonical.replace("www.sec.gov", "WWW.SEC.GOV:443"),
        ("https://www.sec.gov/ix?doc=/Archives/edgar/data/17797/"
         "000132616025000072/duk-20241231.htm"),
        ("https://www.sec.gov/ix?doc=%2FArchives%2Fedgar%2Fdata%2F17797%2F"
         "000132616025000072%2Fduk-20241231.htm"),
        ("https://www.sec.gov/ix?theme=dark&doc=/Archives/edgar/data/17797/"
         "000132616025000072/duk-20241231.htm#facts"),
        ("https://www.sec.gov/ixviewer/ix.html?doc=%2FArchives%2Fedgar%2Fdata%2F"
         "17797%2F000132616025000072%2Fduk-20241231.htm"),
    ]
    for url in accepted:
        if canonical_edgar_url(url) != canonical:
            bad.append(f"valid SEC document variant was not canonicalized: {url}")
    rejected = [
        "http://www.sec.gov/Archives/edgar/data/1/a.htm",
        "https://www.sec.gov.example/Archives/edgar/data/1/a.htm",
        "https://user@www.sec.gov/Archives/edgar/data/1/a.htm",
        "https://www.sec.gov:444/Archives/edgar/data/1/a.htm",
        "https://www.sec.gov/ix",
        "https://www.sec.gov/ix?doc=https://example.com/a.htm",
        "https://www.sec.gov/ix?doc=/Archives/a.htm&doc=/Archives/b.htm",
        "https://www.sec.gov/ix?doc=/not-archives/a.htm",
        "https://www.sec.gov/ix?doc=/Archives/../etc/passwd",
        "https://www.sec.gov/ix?doc=%252FArchives%252Fedgar%252Fdata%252F1%252Fa.htm",
        "https://www.sec.gov/ix?doc=/Archives/a.htm%00evil",
        "https://www.sec.gov/ix?doc=/Archives/a.htm%0Aevil",
        "https://www.sec.gov/Archives/a.htm%0Devil",
        "https://www.sec.gov/ix?doc=/Archives/a.htm%7Fevil",
        "https://www.sec.gov/ixviewer/doc/action?doc=/Archives/edgar/data/1/a.htm",
    ]
    for url in rejected:
        if canonical_edgar_url(url) is not None:
            bad.append(f"unsafe/non-document URL was accepted: {url}")
    app = (ROOT / "src/sec10k/web/app.py").read_text()
    if "url = canonical_edgar_url(" not in app or "if url is None:" not in app:
        bad.append("/api/extract/url does not use the canonicalizer before fetch")
    return bad


LIMITER_MODULE = "src.sec10k.web.limiter"


def check_free_tier_limit(case):
    """TD-162 / D15. The FREE deterministic tier has a bound, and the bound
    binds.

    The door (TD-158) closed the PAID path and deliberately left extraction
    open — which left everything the free path costs unbounded: no rate limit,
    no request cap, no concurrency bound on the three `/api/extract/*` routes,
    only `MAX_BYTES` per document. A caller could post 25 MB filings in a loop,
    and `/api/extract/url` spent an attributable outbound EDGAR fetch each
    time. This check binds the fix the same way `escalation_choke_point` binds
    the paid path's single budgeted entrance, because the recurring defect
    class in this repo is a safety mechanism nobody bound.

    Two halves, and only the registration line is a shape read:

    1. **The limiter is RUN, not read.** `src/sec10k/web/limiter.py` is stdlib
       only and imports no fastapi precisely so this check can import it and
       exercise the real decision path with an injected clock: the burst
       admits, the burst+1th refuses with a positive retry-after and a usable
       reason, elapsed time refills at the configured rate and never past the
       burst, `reset()` restores service, and the env-var config is BOUNDED —
       garbage parses to the default and any value clamps into [1, max], so
       there is no spelling of the variables that means "no limit". PR #58
       R18, PR #61 R2 and PR #61 R11 are why executing beats shape-reading.
    2. **`app.py`'s middleware is EXECUTED, not pattern-matched.** The one
       `@app.middleware("http")` function that consults `.allow()` is compiled
       out of the real tree (`_module_ns`'s argument: fastapi is not
       importable here, but the function body does not need it) and CALLED
       with a controlled `limiter.LIMITER`: under the limit it must reach
       `call_next`; over the limit it must return the 429 envelope with a
       `Retry-After` header and must NOT call `call_next` — on ALL THREE
       extract paths, so a narrowed prefix reds regardless of how it is
       spelled — and a non-extract path (`/api/meta`) must pass through
       without consuming a token, so the limit never touches the pages and
       metadata a viewer loads around a run. An inverted test, an ignored
       verdict and a deleted middleware all red here functionally, not
       textually.

    What it does NOT prove: that fastapi binds the middleware into the ASGI
    stack (the standing `app.py` limitation, TD-38 — the decorator is pinned
    by AST and the live uvicorn measurement in `tasks/reviews/pr-d15-red.txt`
    is the end-to-end evidence), that the limit is per-caller (it is global
    per process, deliberately — Zeabur's proxy makes forwarded-for headers
    untestable offline, TD-158's reasoning), or that a request under the limit
    is cheap — the cost of one 25 MB request is a measured figure in the same
    record, not an assertion here.
    """
    import asyncio
    import types

    inp = case.get("input", {})
    api_file = inp.get("file", API_FILE)
    bad = []
    try:
        tree = ast.parse((ROOT / api_file).read_text())
    except SyntaxError as e:
        return [f"{api_file} does not parse: {e}"]

    try:
        lim_mod = importlib.import_module(
            inp.get("limiter_module", LIMITER_MODULE))
    except ImportError as e:
        bad.append(f"cannot import {LIMITER_MODULE} ({e}) — there is no "
                   f"limiter for the free tier to consult")
        lim_mod = None

    # ---- 1: run the limiter's own decision path. Real module only: a
    # known-bad app.py fixture substitutes THIS file and has no say over
    # limiter.py (the escalation_choke_point precedent).
    if lim_mod is not None and "file" not in inp:
        floor_burst = inp.get("min_default_burst", 5)
        floor_rate = inp.get("min_default_per_minute", 10)
        ceiling = inp.get("max_config", 10_000)
        for name in ("DEFAULT_BURST", "DEFAULT_PER_MINUTE", "MAX_BURST",
                     "MAX_PER_MINUTE", "LIMITED_PREFIX", "BURST_VAR",
                     "RATE_VAR"):
            if not hasattr(lim_mod, name):
                bad.append(f"limiter has no {name} — the config surface the "
                           f"docs and this check name does not exist")
        if bad:
            return bad
        if not (floor_burst <= lim_mod.DEFAULT_BURST <= lim_mod.MAX_BURST
                <= ceiling):
            bad.append(f"DEFAULT_BURST {lim_mod.DEFAULT_BURST} / MAX_BURST "
                       f"{lim_mod.MAX_BURST} outside [{floor_burst}, "
                       f"{ceiling}] — a burst a demo viewer notices, or a "
                       f"cap that is no cap")
        if not (floor_rate <= lim_mod.DEFAULT_PER_MINUTE
                <= lim_mod.MAX_PER_MINUTE <= ceiling):
            bad.append(f"DEFAULT_PER_MINUTE {lim_mod.DEFAULT_PER_MINUTE} / "
                       f"MAX_PER_MINUTE {lim_mod.MAX_PER_MINUTE} outside "
                       f"[{floor_rate}, {ceiling}]")
        for route in ("fixture", "upload", "url"):
            if not f"/api/extract/{route}".startswith(lim_mod.LIMITED_PREFIX):
                bad.append(f"LIMITED_PREFIX {lim_mod.LIMITED_PREFIX!r} does "
                           f"not cover /api/extract/{route} — a limit on two "
                           f"of three routes is the R13 defect again")

        frozen = [0.0]
        lim = lim_mod.Limiter(burst=3, per_minute=60, clock=lambda: frozen[0])
        verdicts = [lim.allow() for _ in range(4)]
        if not all(v[0] for v in verdicts[:3]):
            bad.append("a fresh limiter refuses inside its own burst — the "
                       "demo viewer this limit must never touch is throttled")
        ok, wait, why = verdicts[3]
        if ok:
            bad.append("the burst+1th request on a frozen clock is ALLOWED — "
                       "the cap does not bind (deleted or inverted)")
        else:
            if not wait > 0:
                bad.append(f"an over-limit refusal advertises retry-after "
                           f"{wait!r}, want > 0 — a refusal with no horizon "
                           f"reads as an outage")
            if not why or len(why) < 30:
                bad.append(f"a refusal with no usable reason ({why!r}) — the "
                           f"envelope publishes this string and a viewer told "
                           f"nothing assumes the service is broken")
        frozen[0] += 1.0            # 60/min == 1 token per second
        if not lim.allow()[0]:
            bad.append("one second at 60/min refills nothing — a rate limit "
                       "that never recovers is a one-shot lockout")
        if lim.allow()[0]:
            bad.append("refill exceeds elapsed-time x rate — the sustained "
                       "rate does not bind")
        frozen[0] += 10_000.0       # a long idle must not bank requests
        admitted = sum(1 for _ in range(6) if lim.allow()[0])
        if admitted != 3:
            bad.append(f"after a long idle the bucket admits {admitted}, want "
                       f"the burst of 3 — an unbounded accumulator is an "
                       f"unbounded burst")
        lim.reset()
        if not lim.allow()[0]:
            bad.append("reset() does not restore a full burst — the "
                       "documented test seam is broken")

        # bounded config: no spelling of the env vars means "no limit"
        env_rows = [
            ({lim_mod.BURST_VAR: None, lim_mod.RATE_VAR: None},
             lim_mod.DEFAULT_BURST, lim_mod.DEFAULT_PER_MINUTE, "unset"),
            ({lim_mod.BURST_VAR: "banana", lim_mod.RATE_VAR: ""},
             lim_mod.DEFAULT_BURST, lim_mod.DEFAULT_PER_MINUTE, "garbage"),
            ({lim_mod.BURST_VAR: "999999999", lim_mod.RATE_VAR: "999999999"},
             lim_mod.MAX_BURST, lim_mod.MAX_PER_MINUTE, "huge"),
            ({lim_mod.BURST_VAR: "0", lim_mod.RATE_VAR: "-7"},
             1, 1, "zero-or-negative"),
        ]
        for env, want_burst, want_rate, label in env_rows:
            with _patched_env(**env):
                try:
                    probe = lim_mod.Limiter(clock=lambda: 0.0)
                except Exception as e:
                    bad.append(f"Limiter() under {label} env raised "
                               f"{type(e).__name__}: {e} — a limiter that "
                               f"crashes on config is a limiter the operator "
                               f"turns off")
                    continue
            if (probe.burst, probe.per_minute) != (want_burst, want_rate):
                bad.append(f"Limiter() under {label} env is burst="
                           f"{probe.burst}, per_minute={probe.per_minute}, "
                           f"want ({want_burst}, {want_rate}) — env parsing "
                           f"must clamp toward a working limit, never toward "
                           f"infinity or zero")
        # PR #65 R1. The singleton is pinned by BEHAVIOR, not by type alone:
        # `isinstance` accepted an always-allow subclass assigned to LIMITER
        # (measured: production admitted 1000/1000 while the gate stayed
        # green), because every other row here exercises fresh Limiter(...)
        # instances and part 2 swaps its own in — the one object production
        # consults was exempt. So: exact type, then drain the REAL singleton
        # to refusal through its documented reset() seam and restore it.
        sing = getattr(lim_mod, "LIMITER", None)
        if type(sing) is not lim_mod.Limiter:
            bad.append(f"limiter.LIMITER is {type(sing).__name__}, not exactly "
                       f"Limiter — a subclass here is how an always-allow "
                       f"override ships while every Limiter(...) row stays "
                       f"green (PR #65 R1)")
        elif not (sing.burst <= lim_mod.MAX_BURST
                  and sing.per_minute <= lim_mod.MAX_PER_MINUTE):
            # PR #65 R3: the drain below is bounded by sing.burst ITSELF, so
            # without this row an inflated attribute (bypassing _bounded_int,
            # which pins only construction) makes the drain confirm whatever
            # the mutation chose — measured green at burst = 10**6
            bad.append(f"the PRODUCTION singleton is configured burst="
                       f"{sing.burst}, per_minute={sing.per_minute}, over the "
                       f"module's own MAX_BURST {lim_mod.MAX_BURST} / "
                       f"MAX_PER_MINUTE {lim_mod.MAX_PER_MINUTE} — a "
                       f"self-referential drain would happily confirm an "
                       f"inflated limit (PR #65 R3)")
        else:
            try:
                sing.reset()
                # +1 slack: the real monotonic clock refills ~microtokens
                # during the loop; it cannot legitimately admit more than that
                admitted = sum(1 for _ in range(sing.burst + 3)
                               if sing.allow()[0])
                if admitted > sing.burst + 1:
                    bad.append(f"the PRODUCTION singleton limiter.LIMITER "
                               f"admitted {admitted} of {sing.burst + 3} rapid "
                               f"requests (burst {sing.burst}) and never "
                               f"refused — the object the middleware actually "
                               f"consults enforces nothing (PR #65 R1)")
            finally:
                sing.reset()

    # ---- 2: execute app.py's middleware out of the real tree.
    mws = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.AsyncFunctionDef):
            continue
        decorated = any(
            isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
            and d.func.attr == "middleware" and d.args
            and isinstance(d.args[0], ast.Constant) and d.args[0].value == "http"
            for d in n.decorator_list)
        consults = any(
            isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
            and c.func.attr == "allow" for c in ast.walk(n))
        if decorated and consults:
            mws.append(n)
    if len(mws) != 1:
        bad.append(f"{api_file}: {len(mws)} `@app.middleware(\"http\")` "
                   f"function(s) consulting a limiter `.allow()`, want exactly "
                   f"1 — the free tier must be limited at one choke point that "
                   f"runs before every /api/extract/* route, or the next "
                   f"endpoint walks around it (PR #61 R13)")
        return bad
    if lim_mod is None:
        return bad
    node = mws[0]
    node.decorator_list = []        # references `app`, which needs fastapi
    for a in node.args.args:        # `Request` annotation, same reason
        a.annotation = None
    node.returns = None

    made = []

    def _fake_err(status, code, message, doc_status="failed", **extra):
        r = types.SimpleNamespace(status_code=status, code=code,
                                  message=message, headers={})
        made.append(r)
        return r

    ns = {"limiter": lim_mod, "_err": _fake_err}
    try:
        exec(compile(ast.Module(body=[node], type_ignores=[]),  # noqa: S102
                     "<free-tier-pin>", "exec"), ns)
    except Exception as e:
        return bad + [f"{api_file}: the limiter middleware does not compile "
                      f"standalone ({type(e).__name__}: {e})"]
    mw = ns[node.name]

    passed_through = object()

    async def call_next(request):
        call_next.calls += 1
        return passed_through
    call_next.calls = 0

    def req(path):
        return types.SimpleNamespace(url=types.SimpleNamespace(path=path))

    real = lim_mod.LIMITER
    frozen = [0.0]
    try:
        lim_mod.LIMITER = lim_mod.Limiter(burst=2, per_minute=60,
                                          clock=lambda: frozen[0])
        got = asyncio.run(mw(req("/api/extract/fixture"), call_next))
        if got is not passed_through:
            bad.append(f"{api_file}: an under-limit extract request does not "
                       f"reach call_next — the limiter throttles the demo "
                       f"viewer it exists to protect")
        asyncio.run(mw(req("/api/extract/fixture"), call_next))  # spend burst
        for route in ("fixture", "upload", "url"):
            before = call_next.calls
            got = asyncio.run(mw(req(f"/api/extract/{route}"), call_next))
            if call_next.calls != before:
                bad.append(f"{api_file}: an OVER-limit /api/extract/{route} "
                           f"request still reaches call_next — the verdict is "
                           f"consulted and ignored, so the route (and for "
                           f"/url the outbound EDGAR fetch) runs anyway")
            if getattr(got, "status_code", None) != 429:
                bad.append(f"{api_file}: over-limit /api/extract/{route} "
                           f"returns {getattr(got, 'status_code', got)!r}, "
                           f"want the 429 envelope via _err — an inverted or "
                           f"absent refusal branch")
                continue
            # PR #65 R2: the envelope code is the contract ADR-040 §d names
            # and the UI renders; an unpinned string is a contract in prose
            if got.code != "rate_limited":
                bad.append(f"{api_file}: the 429's envelope code is "
                           f"{got.code!r}, want 'rate_limited' — ADR-040 §d's "
                           f"refusal contract, rendered by the UI without a "
                           f"special case (PR #65 R2)")
            retry = got.headers.get("Retry-After")
            if not (retry and str(retry).isdigit() and int(retry) >= 1):
                bad.append(f"{api_file}: the 429 carries Retry-After="
                           f"{retry!r}, want an integer >= 1 — a refusal with "
                           f"no horizon reads as an outage")
            if not got.message or len(got.message) < 30:
                bad.append(f"{api_file}: the 429 reason is {got.message!r} — "
                           f"the envelope publishes this string")
        tokens_before = lim_mod.LIMITER._tokens
        before = call_next.calls
        got = asyncio.run(mw(req("/api/meta"), call_next))
        if got is not passed_through or call_next.calls != before + 1:
            bad.append(f"{api_file}: /api/meta does not pass through the "
                       f"middleware — the limit must bound extraction, not "
                       f"the page and metadata around it")
        if lim_mod.LIMITER._tokens != tokens_before:
            bad.append(f"{api_file}: a non-extract request consumes a token — "
                       f"page loads would spend the budget extraction needs")
        frozen[0] += 120.0
        got = asyncio.run(mw(req("/api/extract/fixture"), call_next))
        if got is not passed_through:
            bad.append(f"{api_file}: service does not recover after the "
                       f"window elapses — the middleware holds its own state "
                       f"instead of asking the limiter")
    except Exception as e:
        bad.append(f"{api_file}: executing the limiter middleware raised "
                   f"{type(e).__name__}: {e} — a refusal path that throws is "
                   f"a 500, not a 429")
    finally:
        lim_mod.LIMITER = real
    return bad


TOKEN_RATIO_FILE = "tasks/reviews/2026-08-27-token-ratio.json"
SWEEP_SCRIPT = "tasks/reviews/d11_sweep_cost.py"


def check_token_proxy_bound(case):
    """The published chars-per-token proxy must not sit ABOVE the measured
    minimum for any model, because every cost figure in ADR-036 is derived
    through it.

    Why this exists, and why the direction matters. More chars per token means
    FEWER tokens for the same text, so a proxy above the measured ratio
    UNDERSTATES the token count and therefore understates the price. That is
    the failure the two held-out exam runs exposed: a retyped `4` for both
    rungs, against a measured 2.74 for `anthropic/claude-opus-5` — so §h2
    published a worst-case single call of $1.5675 while a real call on a
    LARGER input had already cost $2.12163.

    The check binds the SWEEP SCRIPT's own published value (not a copy of it)
    against the committed measurement record, so a hand-edited artifact or a
    reintroduced constant both go red. It also refuses to pass vacuously: every
    rung's model must carry at least one sample.

    What it does NOT establish: that the bound is right for any other corpus.
    Two samples per model, both SEC filings in HTML-derived normalized text.
    The record says so in its own `honesty` field.
    """
    inp = case.get("input", {})
    bad = []
    rec = json.loads((ROOT / inp.get("ratio_file", TOKEN_RATIO_FILE)).read_text())
    spec = importlib.util.spec_from_file_location(
        "_sweep", ROOT / inp.get("script", SWEEP_SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        return [f"{SWEEP_SCRIPT} does not import: {type(e).__name__}: {e}"]

    observed = {}
    for smp in rec.get("samples", []):
        observed.setdefault(smp["model"], []).append(smp["chars_per_token"])
    if not observed:
        return [f"{TOKEN_RATIO_FILE} carries no samples — the bound would be vacuous"]

    from src.sec10k.escalate import RUNGS
    for _rung, model, _think in RUNGS:
        if model not in observed:
            bad.append(f"no measured chars-per-token sample for {model} — a rung "
                       "whose price nothing measured is a guessed price")
            continue
        try:
            published = mod.chars_per_token(model)
        except Exception as e:
            bad.append(f"{SWEEP_SCRIPT} cannot publish a ratio for {model} "
                       f"({type(e).__name__}: {e})")
            continue
        low = min(observed[model])
        if published > low:
            bad.append(
                f"{model}: published chars/token {published} > measured minimum "
                f"{low} — a proxy above the measured ratio UNDERSTATES tokens and "
                f"therefore understates every cost figure derived from it "
                f"(samples: {sorted(observed[model])})")
    return bad, {"token_proxy_samples": {m: len(v) for m, v in observed.items()}}


CHECKS = {
    "adr_headers": lambda case: check_adr_headers(),
    "adr_index": lambda case: check_index(),
    "report_citations": lambda case: check_report_citations(),
    "heldout_provenance_claims": check_heldout_provenance_claims,
    "ledger_line_refs": check_ledger_line_refs,
    "ui_stylesheet": check_ui_stylesheet,
    "typography_floor": check_typography_floor,
    "layout_centering": check_layout_centering,
    "pane_heights": check_pane_heights,
    "title_legibility": check_title_legibility,
    "pane_meta_amendment": check_pane_meta_amendment,
    "bottom_panel_order": check_bottom_panel_order,
    "truncated_notice_in_overlay": check_truncated_notice_in_overlay,
    "capabilities_parse": check_capabilities_parse,
    "anchor_contract": check_anchor_contract,
    "boilerplate_exclusion": check_boilerplate_exclusion,
    "boilerplate_plumbing": check_boilerplate_plumbing,
    "external_stylesheets_nonblocking": check_external_stylesheets_nonblocking,
    "build_identity": check_build_identity,
    "ledger_table_shape": check_ledger_table_shape,
    "fixture_discovery": check_fixture_discovery,
    "deployed_exclusion": check_deployed_exclusion,
    "deployed_exclusion_derived": check_deployed_exclusion_derived,
    "split_breakpoint": check_split_breakpoint,
    "exclusion_note": check_exclusion_note,
    "exclusion_note_trigger": check_exclusion_note_trigger,
    "offset_reproduction_contract": check_offset_reproduction_contract,
    "confidence_honesty": check_confidence_honesty,
    "banner_status_role": check_banner_status_role,
    "item_text_region": check_item_text_region,
    "mode_button_names": check_mode_button_names,
    "deep_link": check_deep_link,
    "escalation_seam": check_escalation_seam,
    "routing_provenance": check_routing_provenance,
    "d26_routing_ui": check_d26_routing_ui,
    "d26_partial_disposition_ui": check_d26_partial_disposition_ui,
    "escalation_locks": check_escalation_locks,
    "escalation_choke_point": check_escalation_choke_point,
    "escalation_key_ui_behavior": check_escalation_key_ui_behavior,
    "ui_cover_navigation": check_ui_cover_navigation,
    "edgar_viewer_url": check_edgar_viewer_url,
    "free_tier_limit": check_free_tier_limit,
    "token_proxy_bound": check_token_proxy_bound,
}


def run_case(case):
    # PR #52 R14: this used to DEFAULT to ["adr_headers", "adr_index"] when a
    # case named no checks, so `ledger-line-refs.json` — which declares
    # `files`/`min_refs` and no `checks` — ran two unrelated ADR checks against
    # a clean tree and reported PASS while its own check was red. A case that
    # cannot fail is worse than no case: the suite count moved 60 -> 61 on it.
    # Every repo_hygiene case in the repo declares `checks` explicitly, so the
    # default was dead behaviour whose only effect was to swallow a
    # misconfiguration. Deleted rather than guarded — the failure is now loud,
    # and a case naming check parameters but no check goes red on sight.
    names = case.get("input", {}).get("checks")
    if not names:
        return {"passed": False, "failures": [
            f"case {case.get('id', case.get('_file'))!r} names no `input.checks` — "
            f"a repo_hygiene case that declares no check cannot fail and must not "
            f"report green (PR #52 R14)"]}
    failures, info = [], {}
    for name in names:
        got = CHECKS[name](case)
        if isinstance(got, tuple):  # check also reports measurements
            got, extra = got
            info.update(extra)
        failures += got
    # A case normally asserts the file is CLEAN (passed = no failures). A
    # regression case asserts the opposite: that a known-bad mutation fixture
    # is actually CAUGHT (PR #21 R1/R2/R3 — a check that once missed a
    # decimal font-size / an asymmetric margin / an emptied table needs a
    # fixture proving the miss is fixed, not just a fixture proving the real
    # file is clean, which a regressed check would also pass vacuously).
    # `expect.min_failures`/`max_failures` invert scoring for that one case.
    # min_failures ALONE is a floor, not an exact count (PR #21 round-2 R5):
    # a regressed check that ALSO over-fires on something it must not flag
    # (e.g. `main`, which genuinely centres, in the layout-centering-
    # asymmetric fixture) still clears the floor and reports green, hiding
    # exactly the false positive the fixture's own triage note promises is
    # excluded. Pairing it with max_failures pins an EXACT count, so both a
    # regressed miss (too few) and a regressed over-fire (too many) go red.
    expect = case.get("expect", {})
    min_failures, max_failures = expect.get("min_failures"), expect.get("max_failures")
    if min_failures is not None or max_failures is not None:
        passed = ((min_failures is None or len(failures) >= min_failures) and
                  (max_failures is None or len(failures) <= max_failures))
    else:
        passed = not failures
    return {"passed": passed, "failures": failures, **info}
