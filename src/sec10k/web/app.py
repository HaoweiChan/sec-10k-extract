"""Inspector service for the sec10k extractor (T7).

Three input modes, all converging on extract_items(path) — acquisition lives
here, never in the extractor (task2-problem-definition.md):

  fixture  zero-friction demo path
  upload   the guaranteed path: no network, no SEC dependency, no EDGAR rate
           limit (the free tier's own global limit, D15, applies to all three).
           Evaluators test with their own filings, so this one must never break.
  url      EDGAR fetch, best-effort — EDGAR sometimes blocks datacenter IPs, so
           failures are surfaced loudly rather than silently degraded.

Uploads arrive as the raw request body, not multipart: FastAPI's UploadFile
needs python-multipart, and a dependency is a poor trade for what four lines
of tempfile does. The UI posts the File object straight as the body.

Run: uvicorn src.sec10k.web.app:app --reload
"""
import hashlib
import secrets
import tempfile
import urllib.error
import urllib.request
import os
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from src.sec10k.extract import extract_items
from src.sec10k.web import capabilities as capabilities_mod
from src.sec10k.web import gate
from src.sec10k.web import limiter
from src.sec10k.web.build_id import git_sha
from src.sec10k.web.fixtures import (FIXTURES, ROOT, deployed_fixtures,
                                     fixture_file)
from src.sec10k.web.view import build_view

STATIC = Path(__file__).resolve().parent / "static"
EDGAR_UA = "Haowei Chan hwchan42@gmail.com"   # SEC fair-access: declare a contact
MAX_BYTES = 25 * 1024 * 1024                  # provisional cap, both upload and URL
ALLOWED_SUFFIX = (".htm", ".html", ".txt")

# ---------------------------------------------------------------- ADR-036 §h2
# The deployed inspector is PUBLIC and UNAUTHENTICATED. It escalates BY
# DEFAULT — owner decision, 2026-08-27, "make it default on, remove the
# button": there is no `escalate` flag on any endpoint and no control on the
# page, because a capability the viewer has to find and tick is a capability
# most viewers never see.
#
# Lock 1 is therefore INVERTED, not removed. It used to arm paid work
# (`== "1"`, off until someone opts in); it now DISARMS it, on until the
# operator says stop. An off-switch costs nothing, does not contradict
# "default on", and means a runaway is stopped by an env var on the host
# rather than by a code change and a redeploy.
#
# PR #61 R3: it takes a documented FALSY SET, not the single literal "0".
# `SEC10K_ESCALATION_ENABLED=false` is what an operator actually types into a
# Zeabur variable, and a stop button that silently ignores it is worse than no
# stop button, because someone will believe it. Compared after `.strip()` and
# `.lower()`, so `FALSE`, `Off` and `"0 "` all disarm. UNSET and EMPTY both
# ARM — that is the owner's default-on, and `os.environ.get(VAR, "")` makes
# the two states identical on purpose. Anything not in the set arms.
#
# Lock 2 is UNTOUCHED and now matters more, because it is the only ceiling
# left: one `Budget` for the life of the server process, shared by every
# request, so the bound is on the DEPLOYMENT and not on each document. When it
# is spent the tier refuses like any other `EscalationUnavailable` and says so
# in the routing record. It does not reset on its own; restarting the process
# is the deliberate act that refills it — which also means a redeploy refills
# it. Lock 3 (ADR-036 §h2, `EXTRACT_WINDOW`) lives in `escalate.route` and is
# untouched too.
#
# LOCK 4, THE DOOR — and it is why the paragraph that used to sit here is
# gone rather than edited (PR #61 R10, owner decision "close it at the door").
# That paragraph said any anonymous caller could trigger paid work by UPLOADING
# a collapsing document, and that an upload was the only route. Both halves
# were wrong. PR #61 R1 had already found that two committed fixtures made the
# dropdown a one-click paid button and `?fixture=<name>&run=1` a paid PAGE
# LOAD; R10 then found that excluding those fixtures still did not close the
# money path, because `POST /api/extract/url` extracts ANY
# `https://www.sec.gov/Archives/…` URL — and `intc-2025` is a real Intel EDGAR
# filing whose own Archives URL bills. Excluding fixtures could never fix that:
# extracting arbitrary EDGAR URLs is the feature, and every collapsing filing
# on EDGAR is one.
#
# So the paid path is now closed at the door instead. `web.gate.paid_path_open`
# is consulted ONCE, in `_run`, which is the single point all three input modes
# converge on and the only caller of `extract_items` in this file — so fixture,
# upload and URL are covered by construction rather than by three guards that
# can drift (R13 is that failure: a per-line guard a second endpoint walked
# around). Escalation runs only for a request carrying a valid
# `X-Escalation-Token`; with no `SEC10K_ESCALATION_TOKEN` on the host it runs
# for NOBODY. Unset means closed, never open.
#
# Extraction itself is untouched and stays open, free and unauthenticated —
# that is the product, and an evaluator with no secret still gets every item,
# every span and every pane. What they do not get is a bill, and the envelope
# says which of the two happened (`escalation.reason`, on screen in the routing
# strip) instead of going quiet about it.
#
# The fixture exclusion below stays as the second layer: with the door shut it
# is no longer what makes the spend bounded, but a paid button in a public
# dropdown is worth not shipping even when it is locked.
#
# Neither web lock touches a local run: `python3 -m src.sec10k.escalate`, the
# eval suites and a direct `extract_items(..., escalate=True)` call all bypass
# this module entirely, and `extract_items`' own `escalate=False` default is
# deliberately unchanged — flipping it would put paid calls on every
# `python3 -m evals.run` and in CI, destroying the $0 offline gate.
DISARM_VALUES = ("0", "false", "no", "off")
ESCALATION_ENABLED = (os.environ.get("SEC10K_ESCALATION_ENABLED", "")
                      .strip().lower() not in DISARM_VALUES)
SERVER_MAX_CALLS = int(os.environ.get("SEC10K_ESCALATION_MAX_CALLS") or 20)
SERVER_MAX_USD = float(os.environ.get("SEC10K_ESCALATION_MAX_USD") or 5.00)
_SERVER_BUDGET = None


def server_budget():
    """The one process-wide Budget, created on first use.

    Lazily, so importing this module does not import `llm` — and therefore
    does not import `urllib` on any path `repo_hygiene`'s `escalation_seam`
    walks. `app.py` is not on the gate's import graph, but keeping the seam
    uniform costs three lines and removes a footgun.
    """
    global _SERVER_BUDGET
    if _SERVER_BUDGET is None:
        from src.sec10k.llm import Budget
        _SERVER_BUDGET = Budget(max_calls=SERVER_MAX_CALLS, max_usd=SERVER_MAX_USD)
    return _SERVER_BUDGET

app = FastAPI(title="sec10k-extract inspector")

# Original-filing bytes for the S4 compare pane and (D12) the run's own
# normalized text, keyed by one opaque token handed to the browser:
# {token: (content_type, raw_bytes, normalized_utf8_bytes)}. Bounded at 3
# documents: this is a browse aid for the run just performed, not a document
# store, so an LRU cap is enough and needs no eviction policy fancier than
# OrderedDict gives for free.
# ponytail: process-local and in-memory, so a restart or a second worker
# process empties it — fine for a single-instance inspector, revisit if this
# ever runs behind more than one uvicorn worker. D12 roughly doubles what an
# entry costs (normalized text is the same order as the filing); the ceiling
# is 3 x 2 x MAX_BYTES, and the upgrade path if that ever bites is a disk
# spill, not a smaller cap.
SOURCE_CACHE: "OrderedDict[str, tuple[str, bytes, bytes]]" = OrderedDict()
SOURCE_CACHE_MAX = 3


def _fixture_file(name: str) -> Path:
    """Resolve a fixture name to its single filing file, refusing traversal.

    Resolution is the LISTING, not merely the same predicate as it (PR #61 R1):
    a name `/api/meta` does not offer is refused here in the same words an
    unknown name is, because the deep link and a hand-written POST both name a
    fixture directly and an exclusion that only shrank the menu would be
    cosmetic. `deployed_fixtures()` is the one place the exclusion is named.
    """
    if name not in deployed_fixtures():
        raise FileNotFoundError(f"unknown fixture: {name!r}")
    # kept below the membership guard rather than deleted: it is the check that
    # still holds if these two are ever reordered, and it costs one comparison
    d = (FIXTURES / name).resolve()
    if d.parent != FIXTURES.resolve() or not d.is_dir():
        raise FileNotFoundError(f"unknown fixture: {name!r}")
    f = fixture_file(d)
    if f is None:
        raise FileNotFoundError(
            f"expected exactly one filing file in {d}, found "
            f"{sum(1 for p in d.iterdir() if p.is_file())}")
    return f


DECISIONS = ROOT / "specs" / "decisions"


def _decision_file(name: str) -> Path:
    """Resolve an ADR filename to its file in specs/decisions/, refusing
    traversal — same guard shape as _fixture_file. Only names capabilities.py
    itself produced from README.md ever reach this, but the guard holds
    regardless of caller."""
    f = (DECISIONS / name).resolve()
    if f.parent != DECISIONS.resolve() or not f.is_file():
        raise FileNotFoundError(f"unknown decision doc: {name!r}")
    return f


def _err(status: int, code: str, message: str, doc_status: str = "failed", **extra):
    """Every refusal returns the same envelope the UI already renders, so a
    rejected request and a failed extraction look identical to the frontend."""
    return JSONResponse(status_code=status, content={
        "doc_status": doc_status, "items": [], "counts": {}, "trace": [], "meta": {},
        "warnings": [{"code": code, "item": None, "message": message}], **extra})


@app.middleware("http")
async def free_tier_limit(request: Request, call_next):
    """TD-162 / D15: the FREE tier's global request limit, at one choke point.

    The door (`gate.py`) bounds the PAID path; this bounds what the free path
    costs — measured at ~1.1 s CPU and ~138 MB peak RSS for one ~25 MB request
    (`tasks/reviews/pr-d15-red.txt`). Middleware rather than a guard in each
    endpoint, for the same reason the door lives in `_run` (PR #61 R13): every
    current and future `/api/extract/*` route is covered by construction, and
    the refusal happens BEFORE the endpoint body — before the upload is read,
    before any outbound EDGAR fetch, before `extract_items`. Non-extract
    paths (the page, `/api/meta`, source/normalized downloads) pass through
    untouched and consume nothing.

    The refusal is loud and honest: 429 in the same `_err` envelope every
    other refusal uses, `Retry-After` in whole seconds, and a reason that
    names the shared global limit rather than implying a per-caller fairness
    the deployment does not have (`limiter.py` on why global-not-per-IP).
    """
    if request.url.path.startswith(limiter.LIMITED_PREFIX):
        ok, wait, why = limiter.LIMITER.allow()
        if not ok:
            resp = _err(429, "rate_limited", why)
            resp.headers["Retry-After"] = str(int(wait) + 1)
            return resp
    return await call_next(request)


def _cache_source(raw: bytes, suffix: str, normalized: str) -> str:
    """Store the original filing bytes AND the run's normalized text under a
    fresh opaque token, evicting the oldest entry once the LRU is over its
    3-document cap.

    D12: one token, two representations, deliberately. The compare pane wants
    the raw filing; a consumer reproducing an item's offsets wants the exact
    `normalized_text` those offsets index. Keying both off the same token is
    what makes them provably the same run — a second cache could hand out a
    normalized text from a different extraction and nothing would notice.
    """
    content_type = ("text/plain; charset=utf-8" if suffix == ".txt"
                     else "text/html; charset=utf-8")
    token = secrets.token_urlsafe(16)
    SOURCE_CACHE[token] = (content_type, raw, normalized.encode("utf-8"))
    SOURCE_CACHE.move_to_end(token)
    while len(SOURCE_CACHE) > SOURCE_CACHE_MAX:
        SOURCE_CACHE.popitem(last=False)
    return token


def _run(path: str, source: dict, raw: bytes = None,
         exclude_boilerplate: bool = False, markdown: bool = False,
         request: Request = None):
    """Extract and shape for the UI. Never leaks a traceback to the browser.

    `raw` is the original bytes already in hand for upload/URL; the fixture
    path has none yet, so it is read from disk here instead. Caching is
    best-effort: a read failure loses the compare pane, never the extraction
    itself, so `source.token` is simply absent and the UI says so honestly.

    `exclude_boilerplate` is ADR-026's opt-in flag, and this is the one place
    all three input modes converge, so it is the one place it is passed on.
    It changes nothing in the envelope except adding the `boilerplate` spans;
    build_view is what turns those into a stripped PANE (S8). `markdown` is
    ADR-032's, the same way: `blocks=True` adds the `blocks` (+ `tables`)
    annotation and build_view renders the pane from it (S9).

    Escalation is NOT a request flag any more (owner, 2026-08-27) and it is
    not automatic either (owner, PR #61 R10). It is one decision taken HERE,
    for all three input modes, by `gate.paid_path_open`: the deployment must be
    armed, a secret must be configured, and this request must carry it. It then
    still does nothing unless the D8 trigger fires, and with no
    `OPENROUTER_API_KEY` on the server it produces a routing record whose tier
    outcome is `unavailable`, never a fabricated item.

    `request` defaults to None on purpose. A future endpoint that forgets to
    pass it gets the FREE path, not a free-for-all — the fail-safe direction,
    and the reason the choke point is structural rather than a convention every
    call site has to remember.
    """
    # ADR-036 §h2 + TD-158. The ONE place the paid path can be entered, and the
    # only `extract_items` call in this file. The process-wide budget rides
    # along whenever it does open — it is the ceiling BEHIND the door, not
    # instead of it.
    escalate, why = gate.paid_path_open(
        request.headers.get(gate.HEADER) if request is not None else None,
        ESCALATION_ENABLED)
    try:
        result = extract_items(path, exclude_boilerplate=exclude_boilerplate,
                               blocks=markdown, escalate=escalate,
                               budget=server_budget() if escalate else None)
    except Exception as e:                       # refuse loudly, hard rule 4
        return _err(500, "extractor_exception", f"{type(e).__name__}: {e}",
                    source=source)
    view = build_view(result)
    # Said, not implied. `routing: null` alone cannot distinguish "the paid
    # tier was never offered to you" from "it ran and stayed quiet", and a
    # viewer who is told nothing assumes the second.
    view["escalation"] = {"ran": escalate, "reason": why}
    body = raw
    if body is None:
        try:
            body = Path(path).read_bytes()
        except OSError:
            body = None
    if body is not None:
        norm = result.get("normalized_text") or ""
        source = dict(source, token=_cache_source(body, Path(path).suffix.lower(), norm))
    view["source"] = source
    return JSONResponse(view)


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/meta")
def api_meta():
    return {"git_sha": git_sha(ROOT), "fixtures": deployed_fixtures(),
            "max_bytes": MAX_BYTES, "allowed_suffix": list(ALLOWED_SUFFIX),
            # ADR-036 §h2 — the deployment's behaviour stays inspectable
            # without a control on the page. TWO facts, because since PR #61
            # R10 one no longer implies the other:
            #
            # `escalation_enabled` is the operator's off-switch only. It reads
            # false where SEC10K_ESCALATION_ENABLED is set to any member of
            # DISARM_VALUES — `0`, `false`, `no`, `off`, compared after
            # `.strip().lower()`, so `FALSE`, `Off` and `"0 "` all disarm.
            # PR #61 R17: this comment used to describe a single-literal `0`,
            # which stopped being true in R3 and would have sent an operator
            # looking for a switch that had already widened.
            #
            # `escalation_token_required` is the DOOR (TD-158). True whenever
            # a secret is configured — which is to say, whenever any request
            # can reach the paid tier at all. Note the polarity: false does not
            # mean "open to all", it means "closed to all", because an
            # unconfigured secret disables escalation rather than waiving it.
            #
            # Neither publishes the secret, and neither publishes the budget's
            # remaining balance — that is a fact about other people's requests.
            "escalation_enabled": ESCALATION_ENABLED,
            "escalation_token_required": bool(gate.configured_token())}


@app.post("/api/extract/fixture")
def extract_fixture(body: dict, request: Request):
    name = (body or {}).get("fixture", "")
    try:
        f = _fixture_file(name)
    except FileNotFoundError as e:
        return _err(404, "bad_input", str(e))
    return _run(str(f), {"mode": "fixture", "name": name, "file": f.name},
                exclude_boilerplate=bool((body or {}).get("exclude_boilerplate")),
                markdown=bool((body or {}).get("markdown")), request=request)


@app.post("/api/extract/upload")
async def extract_upload(request: Request):
    """Raw body upload. ?filename= carries the original name — the suffix picks
    the txt vs HTML path in the normalizer, so it is load-bearing, not cosmetic."""
    name = request.query_params.get("filename", "upload.htm")
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SUFFIX:
        return _err(415, "bad_input", f"suffix {suffix!r} not one of {ALLOWED_SUFFIX}",
                    doc_status="unsupported")
    raw = await request.body()
    if not raw:
        return _err(400, "bad_input", "empty upload")
    if len(raw) > MAX_BYTES:
        return _err(413, "too_large",
                    f"{len(raw):,} bytes exceeds the {MAX_BYTES:,} cap")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / f"upload{suffix}"
        p.write_bytes(raw)
        return _run(str(p), {"mode": "upload", "name": name, "bytes": len(raw),
                             "sha256": hashlib.sha256(raw).hexdigest()[:16]}, raw=raw,
                    # a query STRING here, not a JSON bool: this mode's body
                    # is the filing itself, so the flag has nowhere else to ride
                    exclude_boilerplate=request.query_params.get(
                        "exclude_boilerplate") == "1",
                    markdown=request.query_params.get("markdown") == "1",
                    request=request)


@app.post("/api/extract/url")
def extract_url(body: dict, request: Request):
    url = ((body or {}).get("url") or "").strip()
    if not url.startswith("https://www.sec.gov/Archives/"):
        return _err(400, "bad_input",
                    "URL must start with https://www.sec.gov/Archives/")
    suffix = Path(url.split("?")[0]).suffix.lower() or ".htm"
    if suffix not in ALLOWED_SUFFIX:
        suffix = ".htm"
    req = urllib.request.Request(url, headers={"User-Agent": EDGAR_UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        return _err(502, "edgar_fetch_failed",
                    f"EDGAR returned HTTP {e.code}. EDGAR sometimes blocks "
                    "datacenter IPs — the upload path does not depend on it.")
    except Exception as e:
        return _err(502, "edgar_fetch_failed",
                    f"{type(e).__name__}: {e}. Use the upload path instead.")
    if len(raw) > MAX_BYTES:
        return _err(413, "too_large",
                    f"document exceeds the {MAX_BYTES:,} byte cap")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / f"edgar{suffix}"
        p.write_bytes(raw)
        return _run(str(p), {"mode": "url", "name": url, "bytes": len(raw),
                             "sha256": hashlib.sha256(raw).hexdigest()[:16]}, raw=raw,
                    exclude_boilerplate=bool((body or {}).get("exclude_boilerplate")),
                    markdown=bool((body or {}).get("markdown")), request=request)


@app.get("/api/source/{token}")
def api_source(token: str):
    """Original filing bytes for the compare pane. A miss — bad token, or
    evicted from the 3-document LRU — is a plain refusal, never a 500 and
    never a re-fetch (hard rule 4: no guessing a replacement document).

    The response headers are the actual security boundary for the untrusted
    markup this serves: `sandbox` forbids script execution and most other
    active content regardless of what the frame attribute says, and nosniff
    stops the browser from re-interpreting a .txt filing as HTML.
    """
    hit = SOURCE_CACHE.get(token)
    if hit is None:
        return JSONResponse(status_code=404, content={
            "error": "source_not_cached",
            "message": "original source is no longer cached — re-run the extraction"})
    content_type, raw, _ = hit
    return Response(content=raw, media_type=content_type, headers={
        "Content-Security-Policy": "sandbox allow-same-origin",
        "X-Content-Type-Options": "nosniff",
    })


@app.get("/api/normalized/{token}")
def api_normalized(token: str):
    """Download the exact `normalized_text` this run's item offsets index.

    Item offsets are character offsets into `normalized_text`, never into the
    raw filing, and ADR-026 §a refuses a raw-to-normalized offset map. So
    reproducibility ships as a contract instead: this endpoint serves the one
    string the offsets are true of, and the recipe below is how a consumer
    with no access to this repo checks any published span for itself.

    1. Extract: POST the filing to /api/extract/fixture (or /upload, or /url)
       and keep three things from the response: source.token, norm_sha256, and
       each item's start and end.
    2. Download: GET /api/normalized/{token} — the exact normalized_text those
       offsets index, served as UTF-8 text.
    3. Verify: sha256 of the downloaded bytes must equal norm_sha256 from step
       1. If it does not, the download is not that run and the offsets do not
       apply to it.
    4. Slice: item_text = normalized_text[start:end], where normalized_text is
       the DECODED string — start and end are character offsets into that
       string, never byte offsets into a file.

    WARNING: these offsets do not index the raw filing. Slicing the raw HTML —
    what /api/source/{token} serves, or the file you uploaded — by the same
    start and end yields different bytes, because normalization rewrites the
    document. There is deliberately no raw-to-normalized offset map
    (ADR-026 §a).

    A miss is the same plain refusal /api/source gives — the 3-document LRU
    dropped it, and re-running the extraction is the only honest answer
    (hard rule 4: never guess a replacement document).
    """
    hit = SOURCE_CACHE.get(token)
    if hit is None:
        return JSONResponse(status_code=404, content={
            "error": "source_not_cached",
            "message": "normalized text is no longer cached — re-run the extraction"})
    norm = hit[2]
    return Response(content=norm, media_type="text/plain; charset=utf-8", headers={
        "X-Normalized-SHA256": hashlib.sha256(norm).hexdigest(),
        "Content-Disposition": 'attachment; filename="normalized_text.txt"',
        "X-Content-Type-Options": "nosniff",
    })


@app.get("/api/capabilities")
def api_capabilities():
    """README.md's works-well table, difficult-section entries, and the
    difficult section's collapsed ADR decision log, all parsed at request
    time so the UI never carries a hand-copied second list (INV-S2's
    argument applied to docs — see src/sec10k/web/capabilities.py)."""
    return capabilities_mod.parse_readme()


@app.get("/api/decisions/{name}")
def api_decision(name: str):
    """Serves one ADR file straight from specs/decisions/, so the
    capabilities panel's decision-log links resolve wherever this is
    deployed — README.md's own links work because GitHub renders relative
    paths against the repo tree; the panel has none, so it needs the file."""
    try:
        f = _decision_file(name)
    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={
            "error": "not_found", "message": str(e)})
    return FileResponse(f, media_type="text/markdown; charset=utf-8")


@app.get("/edgar-check")
def edgar_check():
    """Kept from the T2 deploy spike: proves EDGAR egress from wherever this
    is deployed, independently of any filing."""
    req = urllib.request.Request(
        "https://data.sec.gov/submissions/CIK0000320193.json",
        headers={"User-Agent": EDGAR_UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": resp.status, "bytes": len(resp.read()),
                    "ok": resp.status == 200}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "bytes": 0, "ok": False}
    except Exception as e:
        return {"status": None, "bytes": 0, "ok": False,
                "error": f"{type(e).__name__}: {e}"}
