"""S8 regression fixture, server half: every handler forwards the flag and
`_run` accepts it, but `_run` then calls `extract_items(path)` — the last
hop is dropped. The checkbox toggles, the request carries the flag, the
response is byte-identical either way, and nothing else in the repo notices.
Caught by evals/adversarial/ui-boilerplate-exclusion-regression.json
(expect.min_failures/max_failures). Not imported — read as text.
"""


def _run(path, source, raw=None, exclude_boilerplate=False):
    result = extract_items(path)
    return JSONResponse(build_view(result))


@app.post("/api/extract/fixture")
def extract_fixture(body: dict):
    return _run(str(f), {"mode": "fixture"},
                exclude_boilerplate=bool((body or {}).get("exclude_boilerplate")))


@app.post("/api/extract/upload")
async def extract_upload(request: Request):
    return _run(str(p), {"mode": "upload"}, raw=raw,
                exclude_boilerplate=request.query_params.get(
                    "exclude_boilerplate") == "1")


@app.post("/api/extract/url")
def extract_url(body: dict):
    return _run(str(p), {"mode": "url"}, raw=raw,
                exclude_boilerplate=bool((body or {}).get("exclude_boilerplate")))
