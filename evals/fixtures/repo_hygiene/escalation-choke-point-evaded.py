"""ADR-043 regression fixture — the DOOR and the CHOKE POINT, walked around.

`escalation-locks-*.py` cover the process ceiling's own shape. This one covers
what neither it nor the ceiling can see: the paid path being reachable without
the door's answer. Every name the door needs is present here, the gate is
imported, the verdict is computed — and three edits make it decorative.

  1. `escalate=ESCALATION_ENABLED` at the `extract_items` call site. The door
     is consulted and its answer thrown away, so every request escalates again
     on the old, wider condition. `escalation_locks` cannot see this: the
     argument is still a NAME and still not a literal. `budget=` is left
     correctly conditioned on the VERDICT, so this trips the escalate
     assertion alone and the pinned count of three stays exact.
  2. a fourth endpoint, `/api/extract/paste`, calling `extract_items` directly
     instead of `_run`. PR #61 R13's shape exactly — a second path a guard
     written once in one function does not dominate — and it is why the check
     counts ENTRANCES rather than counting a guard.
  3. `view["escalation"]` is never set, so the envelope goes quiet about a
     decision it took, and a viewer cannot tell "the tier ran and found nothing
     worth doing" from "the tier never ran".

`_run` keeps its `request`, `paid_path_open` is still called exactly once and
its verdict is still bound, so a check that blanket-failed would overshoot the
pinned count rather than reach it. The behavioural halves — the imported door
table and the `llm.Budget` battery — are scoped off when `input.file`
substitutes app.py, for the bound `escalation_locks`' window already learned: a
fixture with no say over another module must not be charged for it.

Three mutations, three failures. Caught by
evals/adversarial/escalation-choke-point-evaded.json. Not imported — read as
text.
"""
from src.sec10k.web import gate

ESCALATION_ENABLED = True
SERVER_MAX_USD = 10.00


def server_budget():
    global _SERVER_BUDGET
    if _SERVER_BUDGET is None:
        _SERVER_BUDGET = Budget(max_calls=SERVER_MAX_CALLS, max_usd=SERVER_MAX_USD)
    return _SERVER_BUDGET


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
