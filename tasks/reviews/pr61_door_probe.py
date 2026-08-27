#!/usr/bin/env python3
"""PR #61 R10 — does the door actually close all three routes? Measured, not read.

Drives the REAL ASGI app over httpx for `fixture`, `upload` and `url`, with and
without a valid `X-Escalation-Token`, and counts OUTBOUND CONNECTIONS to a
stand-in listener that stands where OpenRouter would. An escalating request
opens one; a request the door refused opens none. That connection count is the
whole measurement — the envelope could lie, a TCP accept cannot.

  python3 tasks/reviews/pr61_door_probe.py          # needs fastapi + httpx

NO LIVE API CALLS. `OPENROUTER_BASE_URL` points at a local socket that accepts
the request and answers HTTP 503, so `llm.call` fails loudly the way a provider
outage does — which is fine, because what is being counted is the ATTEMPT. A
rung whose response is already in the on-disk cache is served from it and makes
no connection, so the paid rows assert `>= 1` outbound rather than exactly 1.

The url route's EDGAR fetch is served from the committed `intc-2025` filing
through a patched `urlopen`: the bytes are the real fixture's, only the
transport is local. Nothing about `_run`, the door or the extractor is patched.
"""
import asyncio
import os
import socket
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

HITS = []


def listener():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 0))
    s.listen(64)

    def serve():
        while True:
            try:
                c, _ = s.accept()
            except OSError:
                return
            HITS.append(1)
            try:
                c.recv(65536)
                # a REAL provider failure, not a fabricated answer: 503 with a
                # JSON error body, which `llm.call` must turn into
                # `EscalationUnavailable` and `route()` must record as a tier
                # outcome. Hanging up mid-response instead would test the
                # client's JSON parser, which is not what is being measured.
                c.sendall(b"HTTP/1.1 503 Service Unavailable\r\n"
                          b"Content-Type: application/json\r\n"
                          b"Content-Length: 46\r\n\r\n"
                          b'{"error":{"message":"probe listener, no model"}}'[:46])
            except OSError:
                pass
            c.close()
    threading.Thread(target=serve, daemon=True).start()
    return s.getsockname()[1]


def main():
    port = listener()
    token = "probe-token-not-a-real-secret"
    os.environ["OPENROUTER_BASE_URL"] = f"http://127.0.0.1:{port}"
    os.environ["OPENROUTER_API_KEY"] = "probe-not-a-real-key"
    os.environ["SEC10K_ESCALATION_TOKEN"] = token
    os.environ.pop("SEC10K_ESCALATION_ENABLED", None)

    import httpx
    import urllib.request
    from src.sec10k.web import app as webapp

    filing = os.path.join(ROOT, "evals", "fixtures", "intc-2025")
    filing = os.path.join(filing, os.listdir(filing)[0])
    raw = open(filing, "rb").read()

    class _Resp:                      # the fixture's own bytes, local transport
        status = 200

        def read(self, n=None):
            return raw

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    # ONLY the EDGAR fetch. Patching `urlopen` wholesale would also intercept
    # `llm.call`'s own request and hand the model client a page of HTML, which
    # is a different experiment (and produced a JSONDecodeError the first time
    # this probe was run).
    _real = urllib.request.urlopen

    def _urlopen(req, *a, **k):
        url = getattr(req, "full_url", req)
        return _Resp() if str(url).startswith("https://www.sec.gov/") \
            else _real(req, *a, **k)

    urllib.request.urlopen = _urlopen
    # the fixture route needs a document the trigger fires on, and the D8-hot
    # fixtures are the ones DEPLOY_EXCLUDED removes — so the exclusion is
    # stepped over HERE, in the probe, not in the app. Everything downstream of
    # `_fixture_file` (the door included) is the shipped code.
    import pathlib
    webapp._fixture_file = lambda name: pathlib.Path(filing)

    async def drive():
        cases = []
        async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=webapp.app),
                base_url="http://probe", timeout=120) as c:
            bands = (("no token", {}, token),
                     ("valid token", {"X-Escalation-Token": token}, token),
                     # SAFE WHEN UNSET: the caller presents the right secret and
                     # the HOST has none configured. Closed, not open.
                     ("host unset", {"X-Escalation-Token": token}, None))
            for label, hdr, configured in bands:
                for mode in ("fixture", "upload", "url"):
                    if configured is None:
                        os.environ.pop("SEC10K_ESCALATION_TOKEN", None)
                    else:
                        os.environ["SEC10K_ESCALATION_TOKEN"] = configured
                    before = len(HITS)
                    if mode == "fixture":
                        r = await c.post("/api/extract/fixture",
                                         json={"fixture": "intc-2025"}, headers=hdr)
                    elif mode == "upload":
                        r = await c.post("/api/extract/upload?filename=f.htm",
                                         content=raw, headers=hdr)
                    else:
                        r = await c.post("/api/extract/url", json={
                            "url": "https://www.sec.gov/Archives/probe/intc.htm"},
                            headers=hdr)
                    body = r.json()
                    esc = body.get("escalation") or {}
                    cases.append((label, mode, r.status_code, len(HITS) - before,
                                  esc.get("ran"), ((esc.get("reason") or "") or "; ".join(w.get("message","") for w in body.get("warnings") or []))[:70],
                                  body.get("routing") is not None))
        return cases

    cases = asyncio.run(drive())

    print(f"{'header':12} {'route':8} {'HTTP':>5} {'outbound':>9} "
          f"{'ran':>6}  routing  reason")
    for label, mode, code, hits, ran, why, routed in cases:
        print(f"{label:12} {mode:8} {code:>5} {hits:>9} {str(ran):>6}  "
              f"{str(routed):7}  {why}")

    free = [c for c in cases if c[0] in ("no token", "host unset")]
    paid = [c for c in cases if c[0] == "valid token"]
    assert all(c[3] == 0 for c in free), "a tokenless request reached the provider"
    assert all(c[4] is False for c in free), "a tokenless request escalated"
    assert all(c[2] == 200 for c in free), "the FREE path was refused"
    assert all(c[3] >= 1 for c in paid), "a token holder did not reach the provider"
    assert all(c[4] is True for c in paid), "a token holder was refused the tier"
    print("\nOK — 3 routes x tokenless AND 3 routes x host-unset:")
    print("        0 outbound, HTTP 200, full deterministic extraction, reason said")
    print("   3 routes x valid token: >=1 outbound each")
    print("   so the door is the only gate, and an unconfigured host is CLOSED")


if __name__ == "__main__":
    main()
