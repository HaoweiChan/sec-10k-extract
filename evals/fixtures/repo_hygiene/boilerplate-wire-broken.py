"""S8 regression fixture, server half. Three ways the "exclude boilerplate"
wire breaks while every hop still MENTIONS the flag — the shapes PR #27 R2
found passing the first version of `check_boilerplate_plumbing`:

  a. the url handler reads `excludeBoilerplate` while index.html sends
     `exclude_boilerplate`, so that mode silently never excludes.
  c. the upload handler compares `== "true"` while the JS appends
     `&exclude_boilerplate=1`, so that mode silently never excludes — and
     upload is the guaranteed, no-network path an evaluator actually uses.
  d. `_run` forwards `not exclude_boilerplate`, inverting the checkbox for
     all three modes at once. Every name along the way is correct; only the
     value is wrong. This branch also covers the older `extract_items(path)`
     shape, which fails the same assertion.

The fixture handler below is correctly wired, because its own UI site is the
mutated end in boilerplate-checkbox-default-on.html — between the two files
each end is wrong exactly once, so a check that blanket-failed would exceed
the pinned count rather than reach it. Caught by
evals/adversarial/ui-boilerplate-exclusion-regression.json
(expect.min_failures/max_failures). Not imported — read as text.
"""


def _run(path, source, raw=None, exclude_boilerplate=False):
    result = extract_items(path, exclude_boilerplate=not exclude_boilerplate)
    return JSONResponse(build_view(result))


@app.post("/api/extract/fixture")
def extract_fixture(body: dict):
    return _run(str(f), {"mode": "fixture"},
                exclude_boilerplate=bool((body or {}).get("exclude_boilerplate")))


@app.post("/api/extract/upload")
async def extract_upload(request: Request):
    return _run(str(p), {"mode": "upload"}, raw=raw,
                exclude_boilerplate=request.query_params.get(
                    "exclude_boilerplate") == "true")


@app.post("/api/extract/url")
def extract_url(body: dict):
    return _run(str(p), {"mode": "url"}, raw=raw,
                exclude_boilerplate=bool((body or {}).get("excludeBoilerplate")))
