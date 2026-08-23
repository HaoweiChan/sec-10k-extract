"""S9 browser-evidence walk: the inspector renders the derived Markdown.

Drives the fixture mode with the `render as Markdown` box ticked, selects an
item on three fixtures (modern iXBRL with tables, legacy HTML, txt era),
screenshots the pane, and records what the DOM actually holds — real <h2>,
<p>, <table> elements inside #pane .text.md, the raw slice still on the
compare pane — plus the S3 modes with the box ticked, so the S3/S5 walk's
banner contract still holds in Markdown mode. Exit code is non-zero if any
assertion disagrees, so this is a check, not just a screenshotter.

Run:
    uvicorn src.sec10k.web.app:app --port 8001
    python3 tasks/reviews/s9_markdown_walk.py [--base http://localhost:8001] [--out NAME]

Writes NAME/*.png + NAME.json (default s9-markdown-walk) next to itself.
"""
import argparse, json, pathlib, sys
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
# fixture -> (item code, expectations on the rendered pane)
CASES = {
    "aapl-2025": ("7", {"min_tables": 3, "h2": 1, "kind": "iXBRL, tables interleaved with prose"}),
    "msft-2013": ("1", {"min_tables": 8, "h2": 1, "kind": "legacy HTML, bullet tables"}),
    "ge-1994": ("1", {"min_tables": 0, "h2": 0, "pre": 1, "kind": "txt era, one fenced pre block"}),
}


def run(base, out):
    shots = HERE / out
    shots.mkdir(exist_ok=True)
    record = {"base": base, "fixtures": {}, "failures": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        for fx, (code, want) in CASES.items():
            page.goto(base + "/", wait_until="networkidle")
            page.check("#render-md")
            page.select_option("#fx", fx)
            page.click("#go-fx")
            page.wait_for_selector(".it", timeout=60000)
            page.wait_for_function("document.querySelector('#banner').innerText.startsWith('doc_status')")
            page.evaluate(
                "code => [...document.querySelectorAll('.it')]"
                ".find(b => b.querySelector('.code').textContent.trim() === code).click()", code)
            page.wait_for_selector("#pane .text.md", timeout=10000)
            got = page.evaluate("""() => {
                const pane = document.querySelector('#pane .text.md');
                const hdr = document.querySelector('#pane .src-hdr').innerText;
                return {tables: pane.querySelectorAll('table').length,
                        h2: pane.querySelectorAll('h2').length,
                        p: pane.querySelectorAll('p').length,
                        pre: pane.querySelectorAll('pre').length,
                        b: pane.querySelectorAll('b').length,
                        raw_pre_present: !!document.querySelector('#pane pre.text'),
                        header: hdr, first_text: pane.innerText.slice(0, 160),
                        banner: document.querySelector('#banner').innerText.split('\\n')[0],
                        source_iframe: !!document.querySelector('#src-frame')};
            }""")
            # scroll the pane to its first table (or a bit down) so the shot shows structure
            page.evaluate("""() => { const pane = document.querySelector('#pane .text.md');
                const t = pane.querySelector('table'); if (t) pane.scrollTop = Math.max(0, t.offsetTop - 80); }""")
            shot = shots / f"{fx}-item{code}-markdown.png"
            page.screenshot(path=str(shot), full_page=False, animations="disabled")
            got["shot"] = f"{out}/{shot.name}"
            ok = (got["tables"] >= want["min_tables"] and got["h2"] == want["h2"]
                  and got["pre"] == want.get("pre", 0) and not got["raw_pre_present"]
                  and "markdown" in got["header"].lower())
            got["agrees"] = ok
            if not ok:
                record["failures"].append(f"{fx} item {code}: {got}")
            record["fixtures"][fx] = {"item": code, "expect": want, **got}
        # the S3 contract in Markdown mode: fixture banner unchanged by the checkbox
        page.goto(base + "/", wait_until="networkidle")
        page.check("#render-md")
        page.select_option("#fx", "aapl-2025")
        page.click("#go-fx")
        page.wait_for_function("document.querySelector('#banner').innerText.startsWith('doc_status')")
        bn = page.evaluate("() => ({text: document.querySelector('#banner').innerText,"
                           " cls: document.querySelector('#banner').className})")
        record["s3_fixture_banner_in_markdown_mode"] = bn
        if not (bn["cls"] == "s-success" and "18 extracted" in bn["text"]):
            record["failures"].append(f"S3 fixture banner in markdown mode: {bn}")
        # and with the box UNTICKED the pane is the plain <pre> — the default did not move
        page.goto(base + "/", wait_until="networkidle")
        page.select_option("#fx", "aapl-2025")
        page.click("#go-fx")
        page.wait_for_selector(".it", timeout=60000)
        page.evaluate("() => [...document.querySelectorAll('.it')].find(b => b.querySelector('.code').textContent.trim() === '7').click()")
        page.wait_for_selector("#pane pre.text", timeout=10000)
        plain = page.evaluate("() => ({pre: !!document.querySelector('#pane pre.text'), md: !!document.querySelector('#pane .text.md'),"
                              " header: document.querySelector('#pane .src-hdr').innerText})")
        shot = shots / "aapl-2025-item7-plain.png"
        page.screenshot(path=str(shot), full_page=False, animations="disabled")
        plain["shot"] = f"{out}/{shot.name}"
        record["default_unticked"] = plain
        if not (plain["pre"] and not plain["md"] and "markdown" not in plain["header"].lower()):
            record["failures"].append(f"default (unticked) pane: {plain}")
        browser.close()
    (HERE / f"{out}.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))
    return 1 if record["failures"] else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8001")
    ap.add_argument("--out", default="s9-markdown-walk")
    a = ap.parse_args()
    sys.exit(run(a.base, a.out))
