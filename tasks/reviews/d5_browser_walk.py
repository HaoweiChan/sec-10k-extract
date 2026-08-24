"""D5 browser evidence, as a re-runnable script (s3_browser_walk.py pattern).

D5's two `repo_hygiene` cases are STATIC reads — they parse the CSS and the
markup of src/sec10k/web/static/index.html. No test in that harness issues an
HTTP request or lays anything out, so nothing there can see the RENDER. This
script is the part only a browser can answer:

  half 1 (debt row V5) — at each of 1280 / 1024 / 900 / 768, is `#pane`
      VISIBLE, is `#source` VISIBLE, and do the two sit in the SAME ROW; where
      they do stack, is the sync-scroll control disabled and labelled inactive
      on screen? (PR #46 R2: visibility is a separate question from geometry —
      an invisible pane keeps its rect, its size AND its `offsetParent`.)
  half 2 (the compare-pane note) — is `#bp-note` off screen with exclusion off
      and on screen with it on, and what does it say? Plus one control run on a
      fixture where exclusion is HONOURED and finds nothing, where the note
      must stay off screen (PR #46 R1).

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
# PR #46 R2/R1: a fixture where the flag is HONOURED and finds nothing — the
# detector returns [], all 23 items come back byte-identical to the un-flagged
# run, and the note must therefore stay off screen. The walk used only ge-1994,
# which is why the R1 state was never observed in any of D5's own evidence.
NO_CHROME_FIXTURE = "aapl-2025"
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
    """Geometry, VISIBILITY and control state as the browser resolved them.

    PR #46 R2: this used to record rect tops only, and `in_row()` compared
    them — so a tree carrying `@media(max-width:1100px){#source{visibility:
    hidden}}` (the compare pane invisible at 1024, i.e. the exact defect D5
    exists to remove) passed the walk with `failures: []` while the invariant
    suite read 56/56. An invisible element still has a rect, still has non-zero
    width and height, and — the trap in the finding's own suggested fix — still
    has a NON-NULL `offsetParent`; only `display:none` clears that.
    `checkVisibility` is the native API that answers the actual question, and
    it covers `display:none`, `visibility:hidden`, `opacity:0` and
    `content-visibility` in one call. `offsetParent` is recorded beside it so a
    later reader can see where the two disagree instead of trusting the weaker.
    """
    return page.evaluate("""() => {
      const vis = e => e.checkVisibility
        ? e.checkVisibility({visibilityProperty: true, opacityProperty: true,
                             contentVisibilityAuto: true})
        : e.offsetParent !== null;
      const box = s => { const e = document.querySelector(s);
        if(!e) return null; const r = e.getBoundingClientRect();
        return {top: Math.round(r.top + scrollY), left: Math.round(r.left),
                width: Math.round(r.width), height: Math.round(r.height),
                visible: vis(e), has_offset_parent: e.offsetParent !== null}; };
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
                      // same question, same API as the panes above: `hidden`
                      // alone would not prove it if a CSS rule overrode it.
                      rendered: vis(note),
                      text: note.textContent.replace(/\\s+/g, " ").trim()}
                   : null,
        viewport: {w: innerWidth, h: innerHeight}};
    }""")


def extract(page, exclude, fixture=FIXTURE):
    """Drive a real fixture extraction with the exclusion box in `exclude`.

    Reloads first: a second extraction leaves the previous run's `.it` buttons
    in the DOM, so `wait_for_selector` would return stale handles that detach
    mid-click. The reload also re-runs syncStacked() at the current viewport,
    which is the state this walk is here to observe.
    """
    page.reload(wait_until="networkidle")
    page.select_option("#fx", fixture)
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
            # PR #46 R2. Sharing a row is worth nothing if one of the two is
            # not on screen, and "in the same row" was the only thing this
            # walk ever asked. Checked in BOTH exclusion states, because a
            # rule scoped to one of them would otherwise slip through.
            panes_visible = all(m[k] and m[k]["visible"]
                                for m in (off, on) for k in ("pane", "source"))
            row = {"exclusion_off": off, "exclusion_on": on,
                   "panes_visible": panes_visible,
                   "panes_same_row": same_row,
                   "pane_source_top_delta_px":
                       off["source"]["top"] - off["pane"]["top"],
                   "pane_source_top_delta_px_note_on":
                       on["source"]["top"] - on["pane"]["top"]}
            rec["widths"][str(w)] = row

            # --- what D5 claims, checked rather than described -------------
            for state, m in (("exclusion off", off), ("exclusion on", on)):
                for sel in ("#pane", "#source"):
                    b = m[sel.lstrip("#")]
                    if not b:
                        failures.append(f"{w}: {sel} is not in the document ({state})")
                    elif not b["visible"]:
                        failures.append(
                            f"{w}: {sel} is not visible ({state}) — box "
                            f"{b['width']}x{b['height']} at top {b['top']}, "
                            f"offsetParent={b['has_offset_parent']}. A pane that "
                            f"holds its place in the grid without rendering is "
                            f"the D5 defect, not the D5 fix")
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

        # --- PR #46 R1 control: exclusion HONOURED, nothing found ----------
        # Every width above drives ge-1994, where chrome IS detected, so "the
        # box was ticked" and "something was hidden" never came apart in D5's
        # own evidence — which is exactly how R1 survived to review. One run at
        # the widest viewport on a fixture where the detector returns []: the
        # pane text is byte-identical to the un-flagged run, so the note, which
        # ASSERTS the two panes differ, must stay off screen.
        pg = br.new_page(viewport={"width": widths[0], "height": 860})
        pg.goto(a.base, wait_until="networkidle")
        extract(pg, True, NO_CHROME_FIXTURE)
        ctl = measure(pg)
        ctl["shot"] = shoot(pg, f"w{widths[0]}-{NO_CHROME_FIXTURE}-exclusion-on")
        pg.close()
        rec["no_chrome_control"] = {"fixture": NO_CHROME_FIXTURE,
                                    "width": widths[0], "measured": ctl}
        if ctl["note"] is None:
            failures.append(f"{NO_CHROME_FIXTURE}: no exclusion note element at all")
        elif ctl["note"]["rendered"]:
            failures.append(
                f"{NO_CHROME_FIXTURE} at {widths[0]}: exclusion was asked for and "
                f"honoured, the detector found nothing, and the note is on screen "
                f"anyway claiming the two panes will not agree (PR #46 R1)")
        br.close()

    rec["failures"] = failures
    out = json.dumps(rec, indent=1)
    (HERE / f"{a.out}.json").write_text(out + "\n")
    print(out)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
