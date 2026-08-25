"""D10 browser-evidence walk: the inspector is drivable by a generic
accessibility-first agent.

The 2026-08-24 demo's second failure line was that Task 1's browser agent
could not drive this page (postmortem: browser-agent repo,
`docs/evals/2026-08-24-demo-sec10k-inspector-postmortem.md`). Four page
defects were named there. The `repo_hygiene` cases
(`ui-banner-status-role`, `ui-item-text-region`, `ui-mode-button-names`,
`ui-deep-link`) pin them in the FILE; this script is the other half — it
asks a real browser's ACCESSIBILITY TREE, which is what an agent's observer
actually reads. A `role=` attribute present in the source and a role visible
to `get_by_role` are not the same claim, and only the second one is the one
the postmortem is about.

Every assertion below is made through `get_by_role(role, name=...)`, i.e.
through Playwright's ARIA-role engine, never through a CSS selector on the
attribute we just added — a selector would only re-read the file the eval
cases already read.

What it demonstrates:
  1. `?fixture=<id>&run=1` lands on an ALREADY-RENDERED page — items present
     with no click ever issued, banner reporting a real doc_status.
  2. the banner is exposed as a named `status` element.
  3. the item text is exposed as a named `region` whose name carries the
     item's own code (and the same holds in Markdown mode, the other view of
     the same slot).
  4. the three mode buttons expose three DISTINCT accessible names.
  5. the deep link degrades safely: an unknown fixture, and `run=1` with no
     fixture at all, leave the idle page untouched and throw nothing.

Run:
    pip install playwright && playwright install chromium
    uvicorn src.sec10k.web.app:app --port 8001
    python3 tasks/reviews/d10_agent_walk.py [--base http://localhost:8001] [--out NAME]

Writes NAME/*.png + NAME.json (default d10-agent-walk) next to itself and
prints the record. Exit code is non-zero if any assertion fails, so this is a
check, not just a screenshotter.
"""
import argparse, json, pathlib, sys
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
FIXTURE = "aapl-2025"


def a11y_names(page, role):
    """Accessible names of every element with `role`, read through the ARIA
    engine (not the DOM attribute)."""
    loc = page.get_by_role(role)
    return [" ".join(loc.nth(i).evaluate(
        "el => el.getAttribute('aria-label') || el.textContent").split())[:70]
        for i in range(loc.count())]


def run(base, out):
    shots = HERE / out
    shots.mkdir(exist_ok=True)
    rec = {"base": base, "fixture": FIXTURE, "steps": {}, "failures": []}

    def fail(msg):
        rec["failures"].append(msg)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        # Two buckets, deliberately. `errors` is UNCAUGHT JS — "the deep link
        # must not break the page or throw" is a claim about exactly this, and
        # it is what the walk fails on. `console_errors` is recorded but not
        # graded: the compare pane's iframe serves the raw filing, whose
        # `<img>` tags point at binaries the fixture does not commit, so every
        # extraction logs subresource 404s. That is pre-existing and outside
        # D10 (logged as debt); grading it here would make an unrelated
        # fixture-packaging gap look like an agent-legibility failure.
        errors, console_errors = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: m.type == "error" and console_errors.append(m.text))

        # --- 1. the deep link lands on an already-rendered page -----------
        # No click is issued anywhere in this block. That is the point: an
        # agent's first observation of this URL already contains the answer.
        page.goto(f"{base}/?fixture={FIXTURE}&run=1", wait_until="domcontentloaded")
        page.wait_for_selector(".it", timeout=60000)
        banner = page.get_by_role("status")
        step = {"url": page.url, "clicks_issued": 0,
                "items_rendered": page.locator(".it").count(),
                "selected_fixture": page.locator("#fx").input_value(),
                "banner_role_status_count": banner.count(),
                "banner_name": banner.first.get_attribute("aria-label"),
                "banner_text": banner.first.inner_text().split("\n")[0],
                "uncaught_js_errors": list(errors),
                "console_errors_ungraded": sorted(set(console_errors))}
        page.screenshot(path=str(shots / "1-deep-link-rendered.png"))
        step["shot"] = f"{out}/1-deep-link-rendered.png"
        rec["steps"]["deep_link"] = step
        if step["items_rendered"] < 1:
            fail("deep link: no items rendered — the page did not auto-extract")
        if step["selected_fixture"] != FIXTURE:
            fail(f"deep link: select holds {step['selected_fixture']!r}, not {FIXTURE!r}")
        if step["banner_role_status_count"] != 1:
            fail(f"banner: {step['banner_role_status_count']} elements expose role=status, want 1")
        if not step["banner_name"]:
            fail("banner: role=status element has no accessible name")
        if not step["banner_text"].startswith("doc_status"):
            fail(f"banner: reports {step['banner_text']!r}, not a doc_status line")
        if errors:
            fail(f"deep link: uncaught JS {errors}")

        # the named status element is reachable BY NAME, which is the form an
        # accessibility-first planner addresses it in
        by_name = page.get_by_role("status", name=step["banner_name"])
        rec["steps"]["deep_link"]["reachable_by_name"] = by_name.count()
        if by_name.count() != 1:
            fail("banner: not reachable as get_by_role('status', name=...)")

        # --- 2. the three mode buttons expose distinct names ---------------
        names = {i: page.locator(f"#{i}").get_attribute("aria-label")
                 for i in ("go-fx", "go-up", "go-url")}
        resolved = {i: page.get_by_role("button", name=n).count() if n else 0
                    for i, n in names.items()}
        rec["steps"]["mode_buttons"] = {"names": names,
                                        "matches_per_name": resolved,
                                        "all_button_names": a11y_names(page, "button")}
        if len(set(names.values())) != 3 or not all(names.values()):
            fail(f"mode buttons: names are not three distinct values: {names}")
        for i, n in resolved.items():
            if n != 1:
                fail(f"mode button #{i}: its accessible name resolves to {n} "
                     f"elements, want exactly 1 (the S3 ambiguity shape)")

        # --- 3. the item text is a named region ---------------------------
        page.locator(".it").first.click()
        page.wait_for_selector("#pane pre.text", timeout=15000)
        code = page.locator(".it").first.locator(".code").inner_text().strip()
        region = page.get_by_role("region", name=f"Item {code} extracted text")
        pre = page.locator("#pane pre.text")
        rec["steps"]["item_region"] = {
            "item_code": code,
            "region_matches_by_name": region.count(),
            "tag": pre.evaluate("el => el.tagName.toLowerCase()"),
            "role_attr": pre.get_attribute("role"),
            "aria_label": pre.get_attribute("aria-label"),
            "first_chars": pre.inner_text()[:80]}
        page.screenshot(path=str(shots / "2-item-region.png"))
        rec["steps"]["item_region"]["shot"] = f"{out}/2-item-region.png"
        if region.count() != 1:
            fail(f"item text: get_by_role('region', name='Item {code} extracted "
                 f"text') matched {region.count()}, want 1")

        # the same slot in Markdown mode (ADR-032) must carry the same name —
        # naming only the <pre> would let the other view regress the fix
        page.goto(f"{base}/?fixture={FIXTURE}&run=1", wait_until="domcontentloaded")
        page.wait_for_selector(".it", timeout=60000)
        page.check("#render-md")
        page.click("#go-fx")
        page.wait_for_selector(".it", timeout=60000)
        page.locator(".it").first.click()
        page.wait_for_selector("#pane .text.md", timeout=15000)
        md_code = page.locator(".it").first.locator(".code").inner_text().strip()
        md_region = page.get_by_role("region", name=f"Item {md_code} extracted text")
        rec["steps"]["item_region_markdown"] = {
            "item_code": md_code, "region_matches_by_name": md_region.count()}
        if md_region.count() != 1:
            fail(f"markdown view: named region matched {md_region.count()}, want 1")

        # --- 4. the deep link degrades safely -----------------------------
        rec["steps"]["degrade"] = {}
        for label, qs in (("unknown-fixture", "?fixture=no-such-fixture-xyz&run=1"),
                          ("run-without-fixture", "?run=1"),
                          ("no-params", "")):
            errors.clear()
            console_errors.clear()
            page.goto(base + "/" + qs, wait_until="networkidle")
            page.wait_for_timeout(500)
            d = {"url": page.url,
                 "items_rendered": page.locator(".it").count(),
                 "banner_text": page.get_by_role("status").first.inner_text(),
                 "selected_fixture": page.locator("#fx").input_value(),
                 "uncaught_js_errors": list(errors),
                 "console_errors_ungraded": sorted(set(console_errors))}
            rec["steps"]["degrade"][label] = d
            if d["items_rendered"]:
                fail(f"degrade {label}: {d['items_rendered']} items rendered — "
                     f"an invalid deep link must be a no-op")
            if d["banner_text"] != "No filing extracted yet.":
                fail(f"degrade {label}: banner reads {d['banner_text']!r}, "
                     f"want the untouched idle text")
            if d["uncaught_js_errors"]:
                fail(f"degrade {label}: uncaught JS {d['uncaught_js_errors']}")
        page.screenshot(path=str(shots / "3-degrade-no-params.png"))
        rec["steps"]["degrade"]["shot"] = f"{out}/3-degrade-no-params.png"

        # a recorded ARIA snapshot of the rendered page, as the artifact an
        # agent's observer would have seen — the thing that was empty of
        # answers before D10
        page.goto(f"{base}/?fixture={FIXTURE}&run=1", wait_until="domcontentloaded")
        page.wait_for_selector(".it", timeout=60000)
        page.locator(".it").first.click()
        page.wait_for_selector("#pane pre.text", timeout=15000)
        snap = page.locator("main").aria_snapshot()
        rec["aria_snapshot_excerpt"] = [
            l[:200] for l in snap.splitlines()
            if "status" in l or "region" in l or 'button "Extract' in l][:20]
        browser.close()

    rec["verdict"] = ("DRIVABLE: deep link renders on load, banner is a named "
                      "status, item text is a named region, the three mode "
                      "buttons are distinguishable"
                      if not rec["failures"] else "FAILED")
    (HERE / f"{out}.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))
    return 1 if rec["failures"] else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8001")
    ap.add_argument("--out", default="d10-agent-walk",
                    help="basename for <out>.json and <out>/*.png")
    a = ap.parse_args()
    return run(a.base.rstrip("/"), a.out)


if __name__ == "__main__":
    sys.exit(main())
