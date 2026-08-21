"""Static WCAG contrast + selector checks over a stylesheet's token block.

Exists because S3 restyled src/sec10k/web/static/index.html and shipped two
defects the eval set could not see: (a) light-palette FILL colors reused as
text at 2.40-3.51:1, (b) a bare `button:hover` rule outranking `.it`'s own
selected rule. Both are decidable from the file text with no browser, so they
become a case (hard rule 2) rather than a promise.

ponytail: this does NOT resolve the CSS cascade. What it guards, exactly:

  * token VALUES — every color is resolved live out of the file, so moving
    `--dim` or `--grid` moves the measurement;
  * the ground STACKS and text/ground PAIRS declared in the case JSON;
  * for a pair carrying `fg_from`/`fg_opacity_from`, that one named rule's own
    declared `color:`/`opacity:`, so a rule repointed at a different token
    goes red instead of measuring a color the page no longer paints.

What it is blind to, and these are real holes, not hypotheticals:

  * an element/ground combination nobody added to the pair list;
  * a pair with no `fg_from` — its `fg` is asserted against nothing, so
    repointing that rule passes green (round-2 R13 demonstrated 1.46:1);
  * any OTHER rule that wins the cascade for a pair's element — a later
    `#sidebar span{color:…}`, an `opacity` on an ancestor, an inline style.

Closing the last one means resolving the cascade, which means a browser,
which is the dependency this check exists to avoid. The trade is deliberate;
the claim is narrowed to match it rather than the other way round.
"""
import re

TRANSPARENT = (0.0, 0.0, 0.0, 0.0)


def _strip_comments(s):
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def parse_tokens(css):
    """-> (dark, light) dicts of custom-property name -> raw value string.

    `dark` is the bare `:root{}` block; `light` is that block overlaid with the
    `@media (prefers-color-scheme:light){:root{...}}` overrides.
    """
    css = _strip_comments(css)
    root = re.search(r"(?<!\))\s:root\{(.*?)\}", "\n" + css, re.S)
    if not root:
        raise ValueError("no :root{} block found")
    light_block = re.search(
        r"@media\s*\(prefers-color-scheme:\s*light\)\s*\{\s*:root\{(.*?)\}\}", css, re.S)
    if not light_block:
        raise ValueError("no light-scheme :root override found")

    def decls(block):
        return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;}]+)", block))

    dark = decls(root.group(1))
    light = dict(dark)
    light.update(decls(light_block.group(1)))
    return dark, light


# ---------------------------------------------------------------- color model
def _hsl(h, s, l, a):
    s, l = s / 100.0, l / 100.0
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = l - c / 2
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][
        int(h // 60) % 6]
    return ((r + m) * 255, (g + m) * 255, (b + m) * 255, a)


def _split_args(s):
    """Split a CSS function's argument list on top-level commas."""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def _fn_body(expr, name):
    i = expr.index("(", expr.index(name))
    depth, j = 0, i
    while j < len(expr):
        if expr[j] == "(":
            depth += 1
        elif expr[j] == ")":
            depth -= 1
            if depth == 0:
                return expr[i + 1:j]
        j += 1
    raise ValueError(f"unbalanced {name}() in {expr!r}")


def resolve(expr, tokens, depth=0):
    """CSS color expression -> (r, g, b, a). Handles hsl(), var(), color-mix()."""
    if depth > 12:
        raise ValueError(f"var() cycle at {expr!r}")
    expr = _strip_comments(expr).strip().rstrip(";").strip()
    if expr == "transparent":
        return TRANSPARENT
    if expr.startswith("var("):
        name = _fn_body(expr, "var").split(",")[0].strip()
        if name not in tokens:
            raise ValueError(f"unknown token {name}")
        return resolve(tokens[name], tokens, depth + 1)
    if expr.startswith("hsl"):
        parts = re.split(r"[\s/]+", _fn_body(expr, "hsl").replace(",", " ").strip())
        parts = [p for p in parts if p]
        h = float(parts[0])
        s = float(parts[1].rstrip("%"))
        l = float(parts[2].rstrip("%"))
        a = float(parts[3].rstrip("%")) / (100 if parts[3].endswith("%") else 1) \
            if len(parts) > 3 else 1.0
        return _hsl(h, s, l, a)
    if expr.startswith("#"):
        h = expr[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    if expr.startswith("color-mix("):
        args = _split_args(_fn_body(expr, "color-mix"))
        if not args[0].replace(" ", "").startswith("insrgb"):
            raise ValueError(f"only `in srgb` color-mix is modelled: {expr!r}")
        c1, p1 = _pct(args[1])
        c2, p2 = _pct(args[2])
        if p1 is None and p2 is None:
            p1 = p2 = 0.5
        elif p1 is None:
            p1 = 1 - p2
        elif p2 is None:
            p2 = 1 - p1
        a1, a2 = resolve(c1, tokens, depth + 1), resolve(c2, tokens, depth + 1)
        # CSS color-mix interpolates with PREMULTIPLIED alpha
        a = a1[3] * p1 + a2[3] * p2
        if a == 0:
            return TRANSPARENT
        return tuple(
            [(a1[i] * a1[3] * p1 + a2[i] * a2[3] * p2) / a for i in range(3)] + [a])
    raise ValueError(f"unsupported color expression {expr!r}")


def _pct(arg):
    m = re.search(r"(-?[\d.]+)%\s*$", arg)
    if not m:
        return arg.strip(), None
    return arg[:m.start()].strip(), float(m.group(1)) / 100.0


def over(fg, bg):
    """source-over composite. `bg` must end up opaque for a contrast figure."""
    a = fg[3] + bg[3] * (1 - fg[3])
    if a == 0:
        return TRANSPARENT
    return tuple(
        [(fg[i] * fg[3] + bg[i] * bg[3] * (1 - fg[3])) / a for i in range(3)] + [a])


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (_lin(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    l1, l2 = luminance(fg), luminance(bg)
    lo, hi = sorted((l1, l2))
    return (hi + 0.05) / (lo + 0.05)


def _rule_body(css, selector):
    """The declaration block of `selector`'s own rule.

    Anchored at a rule boundary so a short selector (`a`, `.b`) cannot match
    the tail of a longer one. Raises if absent — a pair naming a rule that no
    longer exists is a stale pair, and staying silent about it is how the
    round-1 version of this check ended up guarding less than it claimed.
    """
    m = re.search(r"(?:^|[}{;\n])\s*" + re.escape(selector) + r"\s*\{([^{}]*)\}",
                  _strip_comments(css), re.M)
    if not m:
        raise ValueError(f"selector {selector!r} not found — pair is stale")
    return m.group(1)


def rule_opacity(css, selector):
    """The `opacity:` declared on `selector`'s OWN rule, else 1.0.

    Only that one rule. An `opacity` arriving from any other selector that
    also matches the element is invisible here — see the module docstring.
    """
    o = re.search(r"opacity\s*:\s*([\d.]+)", _rule_body(css, selector))
    return float(o.group(1)) if o else 1.0


def rule_color(css, selector):
    """The `color:` value declared on `selector`'s OWN rule, else None.

    Lets a pair assert that the rule it claims to model still paints the token
    the pair measures. Text comparison, not cascade resolution.
    """
    c = re.search(r"(?:^|[;\s])color\s*:\s*([^;]+)", _rule_body(css, selector))
    return c.group(1).strip() if c else None


def measure(pair, tokens):
    """pair: {"id","fg","on":[base,...tints],"fg_opacity"?} -> (ratio, ground)."""
    ground = None
    for layer in pair["on"]:
        c = resolve(layer, tokens)
        ground = c if ground is None else over(c, ground)
    if ground is None or ground[3] < 0.999:
        raise ValueError(f"pair {pair['id']!r} has no opaque ground")
    fg = resolve(pair["fg"], tokens)
    if pair.get("fg_opacity") is not None:
        fg = (fg[0], fg[1], fg[2], fg[3] * float(pair["fg_opacity"]))
    return round(contrast(over(fg, ground), ground), 2), ground


# ------------------------------------------------------------------- checks
def check_contrast(css, pairs, minimum=4.5):
    """Every declared text/ground pair clears `minimum` in BOTH schemes."""
    dark, light = parse_tokens(css)
    pairs = [dict(p, fg_opacity=rule_opacity(css, p["fg_opacity_from"]))
             if "fg_opacity_from" in p else p for p in pairs]
    failures, measured = [], {}
    for pair in pairs:  # a pair must still paint the token it claims to measure
        if "fg_from" in pair:
            got = rule_color(css, pair["fg_from"])
            if got != pair["fg"]:
                failures.append(f"{pair['id']}: rule {pair['fg_from']!r} paints "
                                f"{got!r}, but the pair measures {pair['fg']!r}")
    for scheme, tokens in (("dark", dark), ("light", light)):
        for pair in pairs:
            # a ground may differ by scheme (body paints a different overlay
            # stack in light than in dark), declared as {"dark":[…],"light":[…]}
            if isinstance(pair["on"], dict):
                pair = dict(pair, on=pair["on"][scheme])
            ratio, _ = measure(pair, tokens)
            measured[f"{scheme}/{pair['id']}"] = ratio
            if ratio < minimum:
                failures.append(
                    f"{scheme}: {pair['id']} = {ratio}:1 < {minimum}:1")
    return failures, measured


def check_button_specificity(css):
    """No bare-`button` hover rule may outrank `.it`'s own state rules.

    The item rows ARE buttons, so `button:hover:not(:disabled)` (0,2,1) beats
    `.it[aria-current=true]` (0,2,0) and paints the selected row solid amber
    over its own text. Scoping the rule `button:not(.it)` is the fix; this
    asserts it stays scoped.
    """
    css = _strip_comments(css)
    bad = []
    for sel in re.findall(r"([^{}]+)\{[^{}]*\}", css):
        for one in sel.split(","):
            one = one.strip()
            if re.match(r"^button(?![\w-])", one) and ":hover" in one \
                    and ":not(.it)" not in one:
                bad.append(f"unscoped hover rule {one!r} outranks .it state rules")
    return bad


def _demo():
    """Self-check: `python3 -m src.repo_hygiene.css_contrast`."""
    W, B = (255, 255, 255, 1.0), (0, 0, 0, 1.0)
    assert round(contrast(W, B), 2) == 21.0
    assert resolve("hsl(0 0% 100%)", {})[:3] == (255.0, 255.0, 255.0)
    assert resolve("#fff", {}) == (255, 255, 255, 1.0)
    # var() chains through, color-mix() is premultiplied: 10% of an opaque
    # color against `transparent` is that color at alpha .10, not a grey.
    t = {"--a": "hsl(0 100% 50%)", "--b": "var(--a)"}
    assert resolve("var(--b)", t) == resolve("hsl(0 100% 50%)", t)
    tint = resolve("color-mix(in srgb,var(--a) 10%,transparent)", t)
    assert round(tint[3], 3) == 0.1 and round(tint[0]) == 255
    assert [round(c) for c in over(tint, W)[:3]] == [255, 230, 230]
    # 50/50 opaque mix, and an alpha-carrying token
    assert [round(c) for c in resolve("color-mix(in srgb,#fff 50%,#000)", {})[:3]] == [128] * 3
    assert resolve("hsl(0 0% 0% / .5)", {})[3] == 0.5

    # regression pin: the exact figure round-1 review reproduced independently
    # for .it:hover — --dim hsl(215 14% 40%) on --muted hsl(214 13% 86%).
    pre = {"--dim": "hsl(215 14% 40%)", "--muted": "hsl(214 13% 86%)"}
    assert measure({"id": "x", "fg": "var(--dim)", "on": ["var(--muted)"]}, pre)[0] == 4.33

    # `color-scheme` is a real property living in the same two blocks the token
    # scan reads. It must not be picked up as if it were a custom property —
    # a decoy declaration cannot be allowed to break the thing guarding the numbers.
    css = (":root{color-scheme:dark;--ink:hsl(0 0% 0%);--bg:hsl(0 0% 100%)}"
           "@media (prefers-color-scheme:light){:root{color-scheme:light;"
           "--ink:hsl(0 0% 60%)}}"
           "button:not(.it):hover{color:red}#banner .src{opacity:.85}")
    dark, light = parse_tokens(css)
    assert set(dark) == set(light) == {"--ink", "--bg"}, "non-token declaration leaked"
    assert dark["--ink"] == "hsl(0 0% 0%)" and light["--ink"] == "hsl(0 0% 60%)"
    assert light["--bg"] == "hsl(0 0% 100%)", "light inherits what it does not override"
    assert rule_opacity(css, "#banner .src") == 0.85
    assert rule_opacity(css, "button:not(.it):hover") == 1.0
    pairs = [{"id": "ink", "fg": "var(--ink)", "on": ["var(--bg)"]}]
    fails, measured = check_contrast(css, pairs)
    assert measured["dark/ink"] == 21.0 and fails == ["light: ink = 2.85:1 < 4.5:1"]

    # _rule_body anchors at a rule boundary: a one-character selector must not
    # match the tail of a longer one (`a{}` is not `#banner .src{}`).
    two = "a{color:var(--x)}\n.data{color:var(--y)}"
    assert rule_color(two, "a") == "var(--x)" and rule_color(two, ".data") == "var(--y)"
    assert rule_color("p{font-size:1px}", "p") is None
    try:
        _rule_body(two, ".nope")
    except ValueError:
        pass
    else:
        raise AssertionError("a stale pair must fail loudly, not silently")

    # fg_from binds a pair to the rule it claims to model. Round-2 R13:
    # repointing `.it .ttl` at another token measured 1.46:1 while staying green.
    bound = css + ".ttl{color:var(--bg)}"
    fails, _ = check_contrast(bound, [
        {"id": "t", "fg": "var(--ink)", "on": ["var(--bg)"], "fg_from": ".ttl"}])
    assert any("paints 'var(--bg)'" in f and "measures 'var(--ink)'" in f
               for f in fails), fails

    # a ground may differ by scheme — body paints a different overlay stack in
    # light than in dark, so `on` accepts {"dark": [...], "light": [...]}
    _, per = check_contrast(css, [{"id": "g", "fg": "var(--ink)",
                                   "on": {"dark": ["var(--bg)"],
                                          "light": ["var(--ink)"]}}])
    assert per["dark/g"] == 21.0 and per["light/g"] == 1.0
    assert not check_button_specificity(css)
    assert check_button_specificity(css.replace("button:not(.it):hover", "button:hover"))
    print("css_contrast self-check ok")


if __name__ == "__main__":
    _demo()
