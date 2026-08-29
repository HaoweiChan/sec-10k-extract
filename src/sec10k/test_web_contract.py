import json
from fastapi import Request
from src.sec10k.web import app

def main():
    text = "Item 2. Pointer\nItem 16. Missing\n"
    routing = {"trigger": {"fired": True, "codes": [], "items": [], "message": "", "class": "agentic_repair", "route": "agent_loop", "reason": "test", "target_items": ["2", "16"], "calls_paid": True}, "tiers": [{"tier": "agent_loop", "turn": 1, "model": "openai/gpt-5-mini", "items": ["2", "16"], "offset": 0, "input_chars": 0, "truncated": True, "outcome": "unparseable", "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0}, "actions": [], "observations": []}], "resolved": [], "alternative": [], "cost": {"llm_calls": 0, "tokens": 0, "usd": 0.0}, "stages": []}
    result = {"normalized_text": text, "items": [{"item": "2", "part": "I", "title": "Properties", "status": "extracted", "confidence": .8, "method": "heading_strict", "heading_text": "Item 2.", "start": 0, "end": 15, "evidence": {}, "review_required": True}, {"item": "16", "part": "IV", "title": "Summary", "status": "missing", "confidence": 0, "method": "status_keyword", "heading_text": None, "start": None, "end": None, "evidence": {}, "review_required": True}], "warnings": [], "meta": {}, "timings": {}, "trace": [], "cost": routing["cost"], "routing": routing}
    request = Request({"type": "http", "method": "POST", "path": "/api/extract/fixture", "headers": []})
    real = app.extract_items
    try:
        app.extract_items = lambda *a, **k: result
        response = app.extract_fixture({"fixture": "xom-2021"}, request)
    finally:
        app.extract_items = real
    body = json.loads(response.body)
    assert all(i["review_required"] for i in body["items"] if i["item"] in {"2", "16"})
    assert body["routing"]["tiers"][0]["actions"] == []
    assert body["routing"]["tiers"][0]["observations"] == []

if __name__ == "__main__": main()
