"""D14 browser-evidence walk: the item-text regions are keyboard-focusable
and keyboard-SCROLLABLE.

TD-145 (PR #55 R7) is a claim about a keyboard-only user: D10 named the two
scrollable item-text containers (`pre.text`, `div.text.md`) as regions, but
without `tabindex="0"` the page advertises regions such a user cannot reach
or scroll on engines lacking auto-focusable scroll containers. The static
half is pinned by `ui-item-text-region-focusable` (the attribute is in the
file); this walk is the other half — a real browser, the region reached by
the ARIA engine, focused, and sent keyboard scroll keys, with `scrollTop`
asserted to actually move. That movement IS the claim TD-145 makes.

For each of the two view modes (plain `pre.text`, Markdown `div.text.md`):
  1. deep-link `?fixture=aapl-2025&run=1`, open Item 1A (long text — the
     R7 evidence names its 68,162 characters).
  2. the region named for the item is found via `get_by_role("region",
     name=...)` — the ARIA engine, never a CSS selector on the attribute.
  3. `tabindex` is "0" in the LIVE DOM, and pressing Tab from the focus
     stop before the pane (the LAST sidebar item button — `#pane` follows
     `#sidebar` in DOM order, and the pane header holds no focusables)
     lands `document.activeElement` on the region.
  4. ArrowDown then PageDown are sent to the focused region and its
     `scrollTop` must strictly increase after each.

Run:
    pip install playwright && playwright install chromium
    uvicorn src.sec10k.web.app:app --port 8014
    python3 tasks/reviews/d14_keyboard_walk.py [--base http://localhost:8014] [--out NAME]

Writes NAME/*.png + NAME.json (default d14-keyboard-walk) next to itself and
prints the record. Exit code is non-zero if any assertion fails.
"""
import argparse, json, pathlib, sys
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
FIXTURE = "aapl-2025"
ITEM = "1A"


def probe(page, markdown, shots, out, fail):
    """Open Item 1A in one view mode; return the step record."""
    mode = "markdown" if markdown else "plain"
    sel = "#pane .text.md" if markdown else "#pane pre.text"
    page.goto(f"{page.ctx_base}/?fixture={FIXTURE}&run=1", wait_until="domcontentloaded")
    page.wait_for_selector(".it", timeout=60000)
    if markdown:
        page.check("#render-md")
        page.click("#go-fx")
        page.wait_for_selector(".it", timeout=60000)
    item = page.locator(f'.it:has(.code:text-is("{ITEM}"))').first
    item.click()
    page.wait_for_selector(sel, timeout=15000)

    region = page.get_by_role("region", name=f"Item {ITEM} extracted text")
    el = page.locator(sel)
    step = {"mode": mode,
            "region_matches_by_name": region.count(),
            "tabindex_live_dom": el.get_attribute("tabindex"),
            "text_chars": el.evaluate("el => el.textContent.length"),
            "scrollable": el.evaluate("el => el.scrollHeight > el.clientHeight")}
    if step["region_matches_by_name"] != 1:
        fail(f"{mode}: get_by_role('region', name='Item {ITEM} extracted text') "
             f"matched {step['region_matches_by_name']}, want 1")
    if step["tabindex_live_dom"] != "0":
        fail(f"{mode}: live-DOM tabindex is {step['tabindex_live_dom']!r}, want '0'")
    if not step["scrollable"]:
        fail(f"{mode}: container does not overflow — the scroll assertion "
             f"below would be vacuous")

    # Tab reaches it: the focus stop right before the pane is the LAST
    # sidebar item button (#pane follows #sidebar in DOM order and the pane
    # header renders only spans), so one Tab from there must land on the
    # region — the new focus stop this task adds to the tab order.
    page.locator(".it").last.focus()
    page.keyboard.press("Tab")
    step["active_after_tab"] = page.evaluate(
        "() => { const a = document.activeElement; "
        "return {cls: a.className, aria: a.getAttribute('aria-label')}; }")
    step["tab_landed_on_region"] = el.evaluate(
        "el => el === document.activeElement")
    if not step["tab_landed_on_region"]:
        fail(f"{mode}: Tab from the last sidebar button did not land on the "
             f"region — activeElement is {step['active_after_tab']}")

    # Keyboard scroll: scrollTop must strictly increase, key by key.
    tops = [el.evaluate("el => el.scrollTop")]
    for key in ("ArrowDown", "PageDown"):
        page.keyboard.press(key)
        page.wait_for_timeout(200)
        tops.append(el.evaluate("el => el.scrollTop"))
    step["scroll_tops"] = {"start": tops[0], "after_ArrowDown": tops[1],
                           "after_PageDown": tops[2]}
    if not (tops[1] > tops[0]):
        fail(f"{mode}: ArrowDown did not scroll — scrollTop {tops[0]} -> {tops[1]}")
    if not (tops[2] > tops[1]):
        fail(f"{mode}: PageDown did not scroll — scrollTop {tops[1]} -> {tops[2]}")
    shot = f"{out}/{'2-markdown' if markdown else '1-plain'}-region-scrolled.png"
    page.screenshot(path=str(shots.parent / shot))
    step["shot"] = shot
    return step


def run(base, out):
    shots = HERE / out
    shots.mkdir(exist_ok=True)
    rec = {"base": base, "fixture": FIXTURE, "item": ITEM, "steps": {},
           "failures": []}
    fail = rec["failures"].append
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.ctx_base = base
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        rec["steps"]["plain"] = probe(page, False, shots, out, fail)
        rec["steps"]["markdown"] = probe(page, True, shots, out, fail)
        if errors:
            fail(f"uncaught JS during the walk: {errors}")
        browser.close()
    rec["verdict"] = ("KEYBOARD-SCROLLABLE: both named regions carry "
                      "tabindex=0 in the live DOM, are reached by Tab, and "
                      "ArrowDown/PageDown move scrollTop in both view modes"
                      if not rec["failures"] else "FAILED")
    (HERE / f"{out}.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))
    return 1 if rec["failures"] else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8014")
    ap.add_argument("--out", default="d14-keyboard-walk",
                    help="basename for <out>.json and <out>/*.png")
    a = ap.parse_args()
    return run(a.base.rstrip("/"), a.out)


if __name__ == "__main__":
    sys.exit(main())
