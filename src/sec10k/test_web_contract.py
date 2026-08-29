import asyncio
import json

from src.sec10k.web import app


async def _post(path, payload):
    body = json.dumps(payload).encode()
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
                   "http_version": "1.1", "method": "POST", "scheme": "http",
                   "path": path, "raw_path": path.encode(), "query_string": b"",
                   "headers": [(b"content-type", b"application/json")],
                   "client": ("testclient", 0), "server": ("testserver", 80)},
                  receive, send)
    return next(m["status"] for m in messages if m["type"] == "http.response.start"), json.loads(
        b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body"))


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


if __name__ == "__main__": main()
