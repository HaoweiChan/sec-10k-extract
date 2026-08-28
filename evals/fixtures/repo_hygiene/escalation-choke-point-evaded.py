"""ADR-041 regression fixture — the CHOKE POINT, walked around.

`escalation-locks-*.py` cover the process ceiling's own shape. This one covers
what is left after ADR-041 removed the `X-Escalation-Token` door: the paid tier
is open to every request, so the only things still standing are that there is
exactly ONE budgeted entrance, that the operator's stop is honoured, and that
the envelope admits what was decided. Every name those need is present here —
and three edits make them decorative.

  1. `escalate=True` at the `extract_items` call site. The operator's
     `SEC10K_ESCALATION_ENABLED` runaway stop is defeated by a literal, while
     `/api/meta` goes on publishing `escalation_enabled: false` as if honoured.
     `escalation_locks` cannot see this — it is a constant, not a name it
     tracks — and `budget=` is left correctly conditioned on
     `ESCALATION_ENABLED`, so this trips the off-switch assertion ALONE and the
     pinned count of three stays exact.
  2. a fourth endpoint, `/api/extract/paste`, calling `extract_items` directly
     instead of `_run`. PR #61 R13's shape exactly — a second path a guard
     written once in one function does not dominate. Before ADR-041 this was a
     door walked around; now there is no door, so it is plainly an entrance
     that bills against no budget at all.
  3. `view["escalation"]` is never set, so the envelope goes quiet about a
     decision it took, and a viewer cannot tell "the tier ran and found nothing
     worth doing" from "the tier never ran".

Three mutations, three failures. Caught by
evals/adversarial/escalation-choke-point-evaded.json. Not imported — read as
text.
"""
ESCALATION_ENABLED = True
SERVER_MAX_USD = 5.00


def server_budget():
    global _SERVER_BUDGET
    if _SERVER_BUDGET is None:
        _SERVER_BUDGET = Budget(max_calls=SERVER_MAX_CALLS, max_usd=SERVER_MAX_USD)
    return _SERVER_BUDGET


def _run(path, source, raw=None, exclude_boilerplate=False, markdown=False):
    why = ("the model tier is open to every request on this deployment"
           if ESCALATION_ENABLED else "the operator disarmed this deployment")
    result = extract_items(path, exclude_boilerplate=exclude_boilerplate,
                           blocks=markdown, escalate=True,
                           budget=server_budget() if ESCALATION_ENABLED else None)
    view = build_view(result)
    view["source"] = source
    return JSONResponse(view)


@app.post("/api/extract/fixture")
def extract_fixture(body: dict):
    return _run(str(f), {"mode": "fixture"})


@app.post("/api/extract/upload")
async def extract_upload(request: Request):
    return _run(str(p), {"mode": "upload"}, raw=raw)


@app.post("/api/extract/url")
def extract_url(body: dict):
    return _run(str(p), {"mode": "url"}, raw=raw)


@app.post("/api/extract/paste", response_model=None)
def extract_paste(body: dict):
    # the second entrance: no _run, no budget, nothing shared
    return JSONResponse(build_view(extract_items(str(p), escalate=True)))
