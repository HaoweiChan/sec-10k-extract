"""TD-158 / PR #61 R10 regression fixture — the DOOR, walked around.

`escalation-locks-*.py` cover the operator's off-switch and the process
ceiling. This one covers the thing R10 found neither of them could: the paid
path being reachable at all. Every name the door needs is present here, the
gate is imported, the verdict is computed — and three edits make it decorative.

  1. `escalate=ESCALATION_ENABLED` at the `extract_items` call site. The door
     is consulted and its answer thrown away, so every request escalates again
     on the old, wider condition. `escalation_locks` cannot see this: the
     argument is still a NAME and still not a literal.
  2. a fourth endpoint, `/api/extract/paste`, calling `extract_items` directly
     instead of `_run`. This is R13's shape exactly — a second path that a
     guard written once in one function does not dominate — and it is why the
     check counts entrances rather than counting a guard.
  3. `view["escalation"]` is never set, so the envelope goes quiet about a
     decision it took. With the tier behind a token `routing: null` is the
     common case, and a viewer told nothing concludes the tier ran and found
     nothing worth doing.

`budget=` is left correctly conditioned on the verdict, `_run` keeps its
`request` parameter, and `paid_path_open` is still called exactly once, so a
check that blanket-failed would overshoot the pinned count rather than reach
it.

Three mutations, three failures. Caught by
evals/adversarial/escalation-door-open.json. Not imported — read as text.
"""
from src.sec10k.web import gate

ESCALATION_ENABLED = True


def _run(path, source, raw=None, exclude_boilerplate=False, markdown=False,
         request=None):
    escalate, why = gate.paid_path_open(
        request.headers.get(gate.HEADER) if request is not None else None,
        ESCALATION_ENABLED)
    result = extract_items(path, exclude_boilerplate=exclude_boilerplate,
                           blocks=markdown, escalate=ESCALATION_ENABLED,
                           budget=server_budget() if escalate else None)
    view = build_view(result)
    view["source"] = source
    return JSONResponse(view)


@app.post("/api/extract/fixture")
def extract_fixture(body: dict, request: Request):
    return _run(str(f), {"mode": "fixture"}, request=request)


@app.post("/api/extract/upload")
async def extract_upload(request: Request):
    return _run(str(p), {"mode": "upload"}, raw=raw, request=request)


@app.post("/api/extract/url")
def extract_url(body: dict, request: Request):
    return _run(str(p), {"mode": "url"}, raw=raw, request=request)


@app.post("/api/extract/paste", response_model=None)
def extract_paste(body: dict):
    # the second entrance: no _run, no door, no budget
    return JSONResponse(build_view(extract_items(str(p), escalate=True)))
