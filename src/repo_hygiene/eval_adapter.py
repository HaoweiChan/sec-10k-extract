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
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from . import css_contrast
from src.sec10k.web import anchor as web_anchor
from src.sec10k.web import build_id
from src.sec10k.web import capabilities as web_capabilities
from src.sec10k.web.fixtures import fixture_file, list_fixtures
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
    ("the fixture mode puts the checkbox value on the wire",
     'JSON.stringify({fixture: $("#fx").value, exclude_boilerplate: excludeBp(), markdown: renderMd()})'),
    ("the url mode puts the checkbox value on the wire",
     'JSON.stringify({url: $("#url").value, exclude_boilerplate: excludeBp(), markdown: renderMd()})'),
    ("the upload mode appends the checkbox value to its query string",
     '(excludeBp() ? "&exclude_boilerplate=1" : "")'),
    ("the pane SAYS it is hiding text — R5's defect was un-stripped text "
     "under this label, and the inverse, a silent strip, is the same lie",
     '(VIEW.boilerplate_excluded ? "boilerplate hidden · " : "")'),
    ("the extracted-item pane renders the STRIPPED string",
     '<pre class="text">${esc(it.display_text ?? it.text)}</pre>'),
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
    ("nothing may shadow the extracted-item render", '<pre class="text">'),
]

WIRE_API = [
    # S9 (ADR-032) added the Markdown flag to the same call; the pin moved
    # with it deliberately, and the wire was re-checked (see the ADR)
    ("_run forwards the flag into extract_items unmodified",
     "extract_items(path, exclude_boilerplate=exclude_boilerplate, blocks=markdown)"),
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

    routes = set(ROUTE_RE.findall(api))
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
META_FIXTURES = '"fixtures": list_fixtures()'      # the listing /api/meta serves
RESOLVE_CALL = "f = fixture_file(d)"               # _fixture_file, request time


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
        for name, path in yielded.items():
            if name in want and path != want[name]:
                bad.append(f"{rel}: iter_fixtures yields {name!r} -> {path.name}, "
                           f"not its filing {want[name].name}")
        info[rel] = {"dirs": sum(1 for d in root.iterdir() if d.is_dir()),
                     "single_file_dirs": len(want), "api_meta_listed": len(listed),
                     "iter_fixtures_yielded": len(yielded)}
    api = _live((ROOT / inp.get("api_file", API_FILE)).read_text(), "py")
    n = _squash(api).count(_squash(META_FIXTURES))
    if n != 1:
        bad.append(f"app.py: /api/meta must serve the shared listing — expected "
                   f"exactly one `{META_FIXTURES}`, found {n}")
    n = _squash(api).count(_squash(RESOLVE_CALL))
    if n != 1:
        bad.append(f"app.py: _fixture_file must resolve through the shared rule — "
                   f"expected exactly one `{RESOLVE_CALL}`, found {n}")
    if re.search(r"def\s+(_?list_fixtures|fixture_file)\b", api):
        bad.append("app.py defines its own fixture listing/predicate — there is "
                   "one rule, in src/sec10k/web/fixtures.py")
    return bad, info


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
    passing vacuously by deleting the render sites, and the `bodies` pins
    below keep the qualifier's producers from being neutered in place.

    WHAT THIS DOES AND DOES NOT GUARANTEE (corrected at PR #53 R2/R4; the
    first version of this docstring said a bare confidence was made
    "unrepresentable", and three of the round's six findings were attacks
    that walked straight through that word). Guaranteed: no live
    interpolation of `it.confidence` renders without the pinned qualifier
    concatenated onto it; the qualifier's three producers are byte-equal to
    the pinned bodies, so a pinned line cannot sit unreachable below an
    early return; the banner's call to the coverage strip is pinned in the
    assignment that makes it. NOT guaranteed: a render site that never
    names `it.confidence` — one that copies the number into a local first,
    or reads it off a re-shaped object — is outside the scan, and no static
    read can see whether any of it reaches a screen.

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
    sites = []
    for m in re.finditer(r"\$\{\s*it\.confidence", live):
        sites.append(max(0, m.start() - lead))
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


CHECKS = {
    "adr_headers": lambda case: check_adr_headers(),
    "adr_index": lambda case: check_index(),
    "report_citations": lambda case: check_report_citations(),
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
    "split_breakpoint": check_split_breakpoint,
    "exclusion_note": check_exclusion_note,
    "exclusion_note_trigger": check_exclusion_note_trigger,
    "confidence_honesty": check_confidence_honesty,
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
