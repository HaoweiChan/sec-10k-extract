"""S8 regression fixture, server half of pair B: the flag's VALUE is wrong at
every handler while every NAME on the wire is correct, plus a fourth input
mode nobody wired. These are the shapes PR #27 R6 found passing the
name-binding check — the point of each is that it reads the right key off the
right request and then forwards something else.

  M1 the fixture handler inverts it (`not bool(...)`), so the dropdown mode
     excludes when the box is UNTICKED — default-OFF becomes always-exclude.
  M2 the upload handler compares `!= "1"` — a one-character typo. With the
     box unticked the query parameter is absent, `None != "1"` is True, so
     every upload excludes, and upload is the no-network path an evaluator
     uses.
  M3 the url handler forwards a constant (`False and bool(...)`), so that
     mode never excludes whatever the box says.
  F  a fourth `/api/extract/paste` mode exists and never passes the flag —
     the check pins the ROUTE SET, so a mode cannot be added without
     wiring. Its decorator carries a keyword argument, which is app.py's
     own style and the spelling that defeated the route pin (PR #27 R11).

`_run` is correct here on purpose: pair A is where that hop is broken.
Caught by evals/adversarial/ui-boilerplate-wire-values.json. Not imported.
"""


def _run(path, source, raw=None, exclude_boilerplate=False, markdown=False,
         escalate=False):
    result = extract_items(path, exclude_boilerplate=exclude_boilerplate,
                           blocks=markdown, escalate=escalate)
    return JSONResponse(build_view(result))


@app.post("/api/extract/fixture")
def extract_fixture(body: dict):
    return _run(str(f), {"mode": "fixture"},
                exclude_boilerplate=not bool((body or {}).get("exclude_boilerplate")))


@app.post("/api/extract/upload")
async def extract_upload(request: Request):
    return _run(str(p), {"mode": "upload"}, raw=raw,
                exclude_boilerplate=request.query_params.get(
                    "exclude_boilerplate") != "1")


@app.post("/api/extract/url")
def extract_url(body: dict):
    return _run(str(p), {"mode": "url"}, raw=raw,
                exclude_boilerplate=False and bool((body or {}).get("exclude_boilerplate")))


@app.post("/api/extract/paste", response_model=None)
def extract_paste(body: dict):
    return _run(str(p), {"mode": "paste"})
