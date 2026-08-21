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
import re
from pathlib import Path

from . import css_contrast
from src.sec10k.web import anchor as web_anchor
from src.sec10k.web import capabilities as web_capabilities
from src.sec10k.web.view import build_view
from src.sec10k.extract import extract_items

UI_STYLESHEET = "src/sec10k/web/static/index.html"
FIXTURES = "evals/fixtures"

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


def check_capabilities_parse(case):
    """The committed README must still yield a non-trivial parse through
    capabilities.py — the check that turns a README restructure red instead
    of silently emptying the `/api/capabilities` panel (S4), the INV-S2
    argument applied to docs.

    R1: counting rows/entries alone is blind to a mutation that keeps every
    row and column but empties the CONTENT (every cell replaced with a
    same-length placeholder like "x") — same shape, garbage panel, and the
    old check stayed green. Content is checked two ways: no row/item may be
    all-identical-cells (a placeholder table has one distinct value; a real
    one does not), and every cell/term/detail must clear a minimum length —
    both cheap, neither requires pinning the README's literal text, and both
    are exactly what R1's acceptance offered as options, so a legitimate
    future README edit (not a hollowing-out) does not need this case rewired.
    Written against the V3 shape: `difficult` items are `{term, detail}`
    dicts, not one fused string.
    """
    inp = case.get("input", {})
    readme = ROOT / inp.get("file", "README.md")
    data = web_capabilities.parse_readme(readme)
    min_works = inp.get("min_works_well", 8)
    min_diff = inp.get("min_difficult", 3)
    min_cell_chars = inp.get("min_cell_chars", 8)
    min_term_chars = inp.get("min_term_chars", 6)
    min_detail_chars = inp.get("min_detail_chars", 20)

    works = data["works_well"]
    diff_items = [it for g in data["difficult"] for it in g["items"]]
    bad = []
    if len(works) < min_works:
        bad.append(f"works_well has {len(works)} rows (< {min_works})")
    if len(diff_items) < min_diff:
        bad.append(f"difficult has {len(diff_items)} entries (< {min_diff})")

    for i, row in enumerate(works):
        vals = list(row.values())
        if len(set(vals)) < 2:
            bad.append(f"works_well row {i}: every cell is the identical "
                       f"placeholder {vals[0]!r}")
        short = [v for v in vals if len(v) < min_cell_chars]
        if short:
            bad.append(f"works_well row {i}: cell(s) under {min_cell_chars} "
                       f"chars (placeholder-shaped): {short}")
    # R8: a bare heading-with-inline-content group's one item has no
    # "term" key at all (a spanning descriptive row, not a fake term/detail
    # pair) — only check the term floor when a term is actually present.
    thin = [it for it in diff_items
            if ("term" in it and len(it["term"]) < min_term_chars)
            or len(it["detail"]) < min_detail_chars]
    if thin:
        bad.append(f"{len(thin)} difficult item(s) with a term under "
                   f"{min_term_chars} chars or detail under {min_detail_chars} "
                   f"chars (placeholder-shaped): {thin}")

    return bad, {"works_well_rows": len(works), "difficult_entries": len(diff_items)}


def _fixture_file(d):
    """A fixture dir's single filing file, or None if it doesn't have
    exactly one — mirrors app.py's `_fixture_file`, without the traversal
    guard this read-only check doesn't need."""
    files = [f for f in d.iterdir() if f.is_file()]
    return files[0] if len(files) == 1 else None


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
    bad = []
    checked_items = 0
    for d in sorted(p for p in fixtures_dir.iterdir() if p.is_dir()):
        f = _fixture_file(d)
        if f is None:
            continue  # not a single-file filing fixture (e.g. repo_hygiene/)
        is_html = f.suffix.lower() in (".htm", ".html")
        try:
            result = extract_items(str(f))
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


CHECKS = {
    "adr_headers": lambda case: check_adr_headers(),
    "adr_index": lambda case: check_index(),
    "report_citations": lambda case: check_report_citations(),
    "ui_stylesheet": check_ui_stylesheet,
    "typography_floor": check_typography_floor,
    "layout_centering": check_layout_centering,
    "pane_heights": check_pane_heights,
    "title_legibility": check_title_legibility,
    "capabilities_parse": check_capabilities_parse,
    "anchor_contract": check_anchor_contract,
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
