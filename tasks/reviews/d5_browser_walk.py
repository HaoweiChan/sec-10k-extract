"""D5 browser evidence, as a re-runnable script (s3_browser_walk.py pattern).

D5's two `repo_hygiene` cases are STATIC reads — they parse the CSS and the
markup of src/sec10k/web/static/index.html. No test in that harness issues an
HTTP request or lays anything out, so nothing there can see the RENDER. This
script is the part only a browser can answer:

  half 1 (debt row V5) — at each of 1280 / 1024 / 900 / 768, does `#pane` sit
      in the SAME ROW as `#source`, and where they do stack, is the sync-scroll
      control actually disabled and labelled inactive on screen?
  half 2 (the compare-pane note) — is `#bp-note` off screen with exclusion off
      and on screen with it on, and what does it say?

Run:
    pip install playwright && playwright install chromium
    uvicorn src.sec10k.web.app:app --port 8001
    python3 tasks/reviews/d5_browser_walk.py [--base http://localhost:8001] [--out NAME]

Writes NAME/*.png + NAME.json (default d5-browser-walk) and prints the record.
Exit code is non-zero if any width disagrees with what D5 claims, so this is a
check, not a screenshotter: pass a fresh --out to re-measure without
overwriting the record of a defect.
"""
import argparse, json, pathlib, sys
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
SHOTS = HERE / "d5-browser-walk"
FIXTURE = "ge-1994"        # the S8 debt row's own fixture, txt-era edgar_chrome
SIDE_BY_SIDE = 1024        # ui-split-breakpoint's min_side_by_side
STACK_AT = 1000            # index.html's stacking @media, pinned to the JS
ROW_TOLERANCE = 4          # px; same row means same top, not merely closer


def shoot(page, name):
    """Clipped to the note-plus-split region, not the viewport and not the whole
    page. s3_browser_walk shoots the viewport, but below the stacking breakpoint
    `#source` is BELOW the fold by definition and its header is where the
    inactive sync label lives, so a viewport shot would omit the half the shot
    exists for — while a full-page shot of a 3,800px document is mostly footer
    at ~800KB a frame. The clip is exactly what D5 is about."""
    SHOTS.mkdir(exist_ok=True)
    clip = page.evaluate("""() => {
      const els = ["#bp-note", "#sidebar", "#pane", "#source"]
        .map(s => document.querySelector(s))
        .filter(e => e && e.offsetParent !== null)
        .map(e => e.getBoundingClientRect());
      if(!els.length) return null;
      const top = Math.min(...els.map(r => r.top)) + scrollY - 8;
      const bot = Math.max(...els.map(r => r.bottom)) + scrollY + 8;
      return {x: 0, y: Math.max(0, top), width: innerWidth, height: bot - top};
    }""")
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True, clip=clip,
                    animations="disabled")
    return f"{SHOTS.name}/{name}.png"


def measure(page):
    """Geometry and control state as the browser actually resolved them."""
    return page.evaluate("""() => {
      const box = s => { const e = document.querySelector(s);
        if(!e) return null; const r = e.getBoundingClientRect();
        return {top: Math.round(r.top + scrollY), left: Math.round(r.left),
                width: Math.round(r.width), height: Math.round(r.height)}; };
      const c = document.querySelector("#sync-scroll");
      const note = document.querySelector("#bp-note");
      return {
        split_columns: getComputedStyle(document.querySelector(".split"))
                         .gridTemplateColumns,
        pane: box("#pane"), source: box("#source"), sidebar: box("#sidebar"),
        sync: c ? {disabled: c.disabled, checked: c.checked,
                   state_label: (document.querySelector("#sync-state")||{}).textContent}
                : null,
        note: note ? {hidden: note.hidden,
                      // offsetParent===null is how the browser reports "not
                      // rendered", which `hidden` alone would not prove if a
                      // CSS rule overrode it.
                      rendered: note.offsetParent !== null,
                      text: note.textContent.replace(/\\s+/g, " ").trim()}
                   : null,
        viewport: {w: innerWidth, h: innerHeight}};
    }""")


def extract(page, exclude):
    """Drive a real fixture extraction with the exclusion box in `exclude`.

    Reloads first: a second extraction leaves the previous run's `.it` buttons
    in the DOM, so `wait_for_selector` would return stale handles that detach
    mid-click. The reload also re-runs syncStacked() at the current viewport,
    which is the state this walk is here to observe.
    """
    page.reload(wait_until="networkidle")
    page.select_option("#fx", FIXTURE)
    page.set_checked("#exclude-bp", exclude)
    page.click("#go-fx")
    page.wait_for_selector(".it", timeout=30000)
    page.query_selector_all(".it")[0].click()
    page.wait_for_timeout(300)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8001")
    ap.add_argument("--out", default="d5-browser-walk")
    ap.add_argument("--widths", default="1280,1024,900,768")
    a = ap.parse_args()
    global SHOTS
    SHOTS = HERE / a.out
    widths = [int(w) for w in a.widths.split(",")]
    rec = {"base": a.base, "fixture": FIXTURE, "side_by_side_floor": SIDE_BY_SIDE,
           "stack_breakpoint": STACK_AT, "widths": {}}
    failures = []

    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for w in widths:
            pg = br.new_page(viewport={"width": w, "height": 860})
            pg.goto(a.base, wait_until="networkidle")

            extract(pg, False)
            off = measure(pg)
            off["shot"] = shoot(pg, f"w{w}-exclusion-off")

            extract(pg, True)
            on = measure(pg)
            on["shot"] = shoot(pg, f"w{w}-exclusion-on")
            pg.close()

            def label_of(m):
                # None when the element does not exist at all (the c13aa5c
                # shape) — not an empty label, but the same absence to a reader.
                return ((m["sync"] or {}).get("state_label") or "")

            def in_row(m):
                return bool(m["pane"] and m["source"] and
                            abs(m["pane"]["top"] - m["source"]["top"]) <= ROW_TOLERANCE)
            # measured with the note BOTH off and on: the note sits above the
            # split and pushes both panes down, so a layout that only survives
            # without it is not a layout that survives.
            same_row = in_row(off) and in_row(on)
            row = {"exclusion_off": off, "exclusion_on": on,
                   "panes_same_row": same_row,
                   "pane_source_top_delta_px":
                       off["source"]["top"] - off["pane"]["top"],
                   "pane_source_top_delta_px_note_on":
                       on["source"]["top"] - on["pane"]["top"]}
            rec["widths"][str(w)] = row

            # --- what D5 claims, checked rather than described -------------
            if w >= SIDE_BY_SIDE and not same_row:
                failures.append(f"{w}: #pane and #source are not in the same row "
                                f"(top delta {row['pane_source_top_delta_px']}px)")
            if w <= STACK_AT:
                if same_row:
                    failures.append(f"{w}: expected the panes to stack below "
                                    f"{STACK_AT}px, but they share a row")
                if not off["sync"] or not off["sync"]["disabled"]:
                    failures.append(f"{w}: panes stacked but the sync-scroll "
                                    f"control is not disabled")
                if not label_of(off).strip():
                    failures.append(f"{w}: panes stacked but nothing on screen "
                                    f"says the sync control is inactive")
            else:
                if off["sync"] and off["sync"]["disabled"]:
                    failures.append(f"{w}: panes side by side but the sync "
                                    f"control is disabled")
                if label_of(off).strip():
                    failures.append(f"{w}: panes side by side but the control "
                                    f"still carries an inactive label")
            # absent and wrongly-shown are different defects and read as
            # different failures — the c13aa5c run has the first, and a note
            # that fires with the box unticked would have the second.
            if off["note"] is None:
                failures.append(f"{w}: there is no exclusion note in the page "
                                f"at all — the panes disagree unexplained")
            elif off["note"]["rendered"]:
                failures.append(f"{w}: the exclusion note is on screen with "
                                f"exclusion OFF, where it is false")
            elif not on["note"]["rendered"]:
                failures.append(f"{w}: the exclusion note stays off screen with "
                                f"exclusion ON")
        br.close()

    rec["failures"] = failures
    out = json.dumps(rec, indent=1)
    (HERE / f"{a.out}.json").write_text(out + "\n")
    print(out)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
