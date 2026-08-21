"""S3 browser-evidence gate, as a re-runnable script.

The S3 row's Validation gate asked for the three input modes driven in a real
browser with a committed screenshot, plus the font-fallback question answered
rather than asserted. Both stood UNRUN because the branch that built S3 could
not drive a browser. This script is that gate: it drives the modes, writes the
screenshots next to itself, and measures the font behaviour instead of
describing it.

Run:
    pip install playwright && playwright install chromium
    uvicorn src.sec10k.web.app:app --port 8001
    python3 tasks/reviews/s3_browser_walk.py [--base http://localhost:8001]

Writes s3-browser-walk/*.png and prints a JSON record to stdout. Exit code is
non-zero if any mode's rendered banner disagrees with what the row claims, so
this is a check, not just a screenshotter.
"""
import argparse, hashlib, json, pathlib, sys
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
SHOTS = HERE / "s3-browser-walk"
UPLOAD = HERE / "s3-upload-4item.htm"
FONTS = "**fonts.googleapis.com/**"

# What the S3 row claims each mode renders. The walk fails if the page disagrees.
EXPECT = {
    "fixture": ("s-success", "success", "18 extracted"),
    "upload": ("s-ambiguous", "ambiguous", "4 extracted"),
    "url": ("s-failed", "failed", None),
}


def banner(page):
    b = page.query_selector("#banner")
    return {"text": b.inner_text() if b else None,
            "cls": b.get_attribute("class") if b else None}


def shoot(page, name, timeout=30000):
    """Returns the repo-relative path, or a reason string if the capture failed.
    A capture that times out is itself a finding: Playwright waits for webfonts
    to settle before it will shoot, so a hung font host stalls the shot too."""
    SHOTS.mkdir(exist_ok=True)
    try:
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=False,
                        timeout=timeout, animations="disabled")
        return f"s3-browser-walk/{name}.png"
    except Exception as e:
        return f"CAPTURE FAILED: {type(e).__name__}: {str(e).splitlines()[0]}"


def check(mode, bn, out):
    cls, status, frag = EXPECT[mode]
    ok = bn["cls"] == cls and status in (bn["text"] or "")
    if frag:
        ok = ok and frag in (bn["text"] or "")
    out["agrees_with_row"] = ok
    return ok


def first_contentful_paint(page, budget_ms):
    """Poll for FCP. Returns ms, or None if the page never painted in budget."""
    return page.evaluate(
        """(budget) => new Promise(res => {
             const t0 = performance.now();
             const tick = () => {
               const e = performance.getEntriesByType('paint')
                          .find(p => p.name === 'first-contentful-paint');
               if (e) return res(e.startTime);
               if (performance.now() - t0 > budget) return res(null);
               setTimeout(tick, 50);
             };
             tick();
           })""", budget_ms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8001")
    ap.add_argument("--fcp-budget-ms", type=int, default=8000)
    a = ap.parse_args()
    rec = {"base": a.base, "modes": {}, "fonts": {}}
    rec["upload_file"] = {
        "path": "tasks/reviews/s3-upload-4item.htm",
        "sha256": hashlib.sha256(UPLOAD.read_bytes()).hexdigest(),
        "bytes": UPLOAD.stat().st_size}
    failures = []

    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": 1920, "height": 1080})

        # --- mode 1: committed fixture -----------------------------------
        pg.goto(a.base, wait_until="networkidle")
        pg.click("#go-fx")
        pg.wait_for_selector(".it", timeout=30000)
        m = banner(pg)
        m["items_rendered"] = len(pg.query_selector_all(".it"))
        pg.query_selector_all(".it")[0].click()
        pg.wait_for_timeout(300)
        m["shot"] = shoot(pg, "mode1-fixture")
        rec["modes"]["fixture"] = m
        if not check("fixture", m, m):
            failures.append("fixture")

        # --- mode 2: upload, through the real file input ------------------
        pg.set_input_files("#up", str(UPLOAD))
        pg.click("#go-up")
        pg.wait_for_timeout(1500)
        m = banner(pg)
        m["items_rendered"] = len(pg.query_selector_all(".it"))
        m["shot"] = shoot(pg, "mode2-upload")
        rec["modes"]["upload"] = m
        if not check("upload", m, m):
            failures.append("upload")

        # --- mode 3: EDGAR URL that 404s ----------------------------------
        pg.fill("#url", a.base.rstrip("/") + "/no-such-filing.htm")
        pg.click("#go-url")
        pg.wait_for_timeout(1500)
        m = banner(pg)
        m["shot"] = shoot(pg, "mode3-url-failed")
        rec["modes"]["url"] = m
        if not check("url", m, m):
            failures.append("url")

        # --- font behaviour: control / refused / blackholed ---------------
        for name, handler in (
                ("control", None),
                ("refused", lambda r: r.abort("connectionrefused")),
                ("blackholed", "hang")):  # request held open == blackholed origin
            p2 = br.new_page(viewport={"width": 1920, "height": 1080})
            if handler == "hang":
                # Never fulfil: the socket stays open, which is what a
                # blackholing origin looks like (vs. a refusal, above).
                p2.route(FONTS, lambda r: p2.wait_for_timeout(600000))
            elif handler:
                p2.route(FONTS, handler)
            try:
                p2.goto(a.base, wait_until="commit", timeout=15000)
                fcp = first_contentful_paint(p2, a.fcp_budget_ms)
            except Exception as e:
                fcp = None
                rec["fonts"].setdefault("errors", {})[name] = str(e).splitlines()[0]
            rec["fonts"][name] = {
                "first_contentful_paint_ms": fcp,
                "painted_within_budget": fcp is not None,
                "shot": shoot(p2, f"fonts-{name}", timeout=6000)}
            p2.close()
        br.close()

    blocked = rec["fonts"]["blackholed"]["painted_within_budget"] is False
    rec["font_fallback_verdict"] = (
        "RENDER-BLOCKED: a blackholed fonts.googleapis.com stops the page "
        "painting within the budget" if blocked else
        "DEGRADES: the page paints without the webfont")
    rec["mode_failures"] = failures
    out = json.dumps(rec, indent=1)
    (HERE / "s3-browser-walk.json").write_text(out + "\n")
    print(out)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
