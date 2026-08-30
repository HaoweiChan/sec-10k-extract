import asyncio
import json
import threading
import time

from src.sec10k.web import app


async def _request(method, path, payload=None, headers=()):
    body = json.dumps(payload).encode() if payload is not None else b""
    sent = False
    messages = []

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    await app.app({"type": "http", "asgi": {"version": "3.0"},
                   "http_version": "1.1", "method": method, "scheme": "http",
                   "path": path, "raw_path": path.encode(), "query_string": b"",
                   "headers": [(b"content-type", b"application/json"), *headers],
                   "client": ("testclient", 0), "server": ("testserver", 80)},
                  receive, send)
    return next(m["status"] for m in messages if m["type"] == "http.response.start"), json.loads(
        b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body"))


async def _post(path, payload, headers=()):
    return await _request("POST", path, payload, headers)


async def _get(path):
    return await _request("GET", path)


def main():
    text = "Item 2. Pointer\nItem 16. Missing\n"
    routing = {"trigger": {"fired": True, "codes": [], "items": [], "message": "", "class": "agentic_repair", "route": "agent_loop", "reason": "test", "target_items": ["2", "16"], "calls_paid": True}, "tiers": [{"tier": "agent_loop", "turn": 1, "model": "openai/gpt-5-mini", "items": ["2", "16"], "offset": 0, "input_chars": 0, "truncated": True, "outcome": "unparseable", "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0}, "actions": [], "observations": []}], "resolved": [], "alternative": [], "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0}, "stages": []}
    result = {"normalized_text": text, "items": [{"item": "2", "part": "I", "title": "Properties", "status": "extracted", "confidence": .8, "method": "heading_strict", "heading_text": "Item 2.", "start": 0, "end": 15, "evidence": {}, "review_required": True}, {"item": "16", "part": "IV", "title": "Summary", "status": "missing", "confidence": 0, "method": "status_keyword", "heading_text": None, "start": None, "end": None, "evidence": {}, "review_required": True}], "warnings": [], "meta": {}, "timings": {}, "trace": [], "cost": routing["cost"], "routing": routing}
    real = app.extract_items
    try:
        app.extract_items = lambda *a, **k: result
        status, body = asyncio.run(_post("/api/extract/fixture", {"fixture": "xom-2021"}))
    finally:
        app.extract_items = real
    assert status == 200
    targets = {i["item"]: i for i in body["items"]}
    assert set(targets) == {"2", "16"}
    assert all(targets[item]["review_required"] for item in {"2", "16"})
    assert body["routing"]["tiers"][0]["actions"] == []
    assert body["routing"]["tiers"][0]["observations"] == []

    status, refused = asyncio.run(_post("/api/extract/url", {"url": "not-an-edgar-url"},
                                         headers=[(b"x-progress", b"1")]))
    assert status == 400 and refused["doc_status"] == "failed" and "progress_id" not in refused

    release = threading.Event()
    entered = threading.Event()
    try:
        def delayed(*args, progress=None, **kwargs):
            progress("prepare")
            entered.set()
            assert release.wait(1)
            progress("classify")
            return result
        app.extract_items = delayed
        status, started = asyncio.run(_post("/api/extract/fixture", {"fixture": "xom-2021"},
                                             headers=[(b"x-progress", b"1")]))
        assert status == 202 and entered.wait(1)
        status, first = asyncio.run(_get(f"/api/progress/{started['progress_id']}"))
        assert status == 200 and first["stages"][0]["status"] == "active"
        release.set()
        for _ in range(100):
            status, next_progress = asyncio.run(_get(f"/api/progress/{started['progress_id']}"))
            if any(s["stage"] == "classify" and s["status"] == "active"
                   for s in next_progress["stages"]):
                break
            time.sleep(.001)
        assert status == 200 and any(s["stage"] == "classify" and s["status"] == "active"
                                     for s in next_progress["stages"])
    finally:
        release.set()
        app.extract_items = real

    routing["stages"] = [{"stage": stage, "status": status} for stage, status in (
        ("classify", "done"), ("plan", "done"), ("route", "done"),
        ("verify", "failed"), ("decide", "done"))]
    try:
        app.extract_items = lambda *a, progress=None, **k: (
            [progress(stage) for stage in ("prepare", "classify", "plan", "route", "verify", "decide")]
            and result)
        status, started = asyncio.run(_post("/api/extract/fixture", {"fixture": "xom-2021"},
                                             headers=[(b"x-progress", b"1")]))
        assert status == 202 and set(started) == {"progress_id"}
        job_id = started["progress_id"]
        for _ in range(100):
            with app.PROGRESS_LOCK:
                complete = app.PROGRESS_JOBS[job_id]["status"] == "complete"
            if complete:
                break
            time.sleep(.001)
        with app.PROGRESS_LOCK:
            assert len(app.PROGRESS_JOBS[job_id]["snapshots"]) <= len(app.PROGRESS_STAGES)
        active = []
        for _ in range(100):
            status, progress = asyncio.run(_get(f"/api/progress/{job_id}"))
            active += [s["stage"] for s in progress["stages"] if s["status"] == "active"]
            if progress["status"] == "complete":
                break
        assert status == 200 and set(progress) == {"status", "stages", "result_url"}
        assert active == ["prepare", "classify", "plan", "route", "verify", "decide"]
        assert {s["stage"]: s["status"] for s in progress["stages"]}["verify"] == "failed"
        status, completed = asyncio.run(_get(progress["result_url"]))
        assert status == 200 and {i["item"] for i in completed["items"]} == {"2", "16"}
        assert completed["routing"]["stages"][3]["status"] == "failed"
    finally:
        app.extract_items = real


if __name__ == "__main__": main()
