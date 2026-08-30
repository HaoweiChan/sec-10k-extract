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
import base64
import hashlib
import json
import re
import secrets
import tempfile
import threading
import urllib.error
import urllib.request
import os
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from src.sec10k.extract import extract_items
from src.sec10k.web import capabilities as capabilities_mod
from src.sec10k.web import gate, limiter
from src.sec10k.web.build_id import git_sha
from src.sec10k.web.fixtures import (FIXTURES, ROOT, deployed_fixtures,
                                     fixture_file)
from src.sec10k.web.edgar_url import canonical_edgar_url
from src.sec10k.web.source_asset import (IMAGE_SUFFIXES, asset_url, release_asset,
                                         reserve_asset)
from src.sec10k.web.view import build_view

STATIC = Path(__file__).resolve().parent / "static"
EDGAR_UA = "Haowei Chan hwchan42@gmail.com"   # SEC fair-access: declare a contact
MAX_BYTES = 25 * 1024 * 1024                  # provisional cap, both upload and URL
ALLOWED_SUFFIX = (".htm", ".html", ".txt")

# The public deterministic extractor stays free. Paid work is allowed only
# after `gate.paid_path_open` verifies the configured escalation key; the one
# process-wide Budget and bounded prompts limit that optional path. `_run` is
# the only extraction entrance, while D27's separate table-verdict endpoint
# reuses the same gate and Budget (ADR-043, ADR-052).
DISARM_VALUES = ("0", "false", "no", "off")
ESCALATION_ENABLED = (os.environ.get("SEC10K_ESCALATION_ENABLED", "")
                      .strip().lower() not in DISARM_VALUES)
SERVER_MAX_CALLS = int(os.environ.get("SEC10K_ESCALATION_MAX_CALLS") or 20)
# ADR-041 raised this from 5.00 to 10.00 on owner instruction when the door
# came off: it is now the ONLY money bound, so it is the demo's whole risk
# appetite rather than a backstop behind a header. It pairs with
# SERVER_MAX_CALLS=20 — an escalation is at most 2 calls (a cheap rung 1 at
# ~$0.004 and a rung 2 at ~$1), so ~10 escalations reach both ceilings at
# about the same point rather than one masking the other.
SERVER_MAX_USD = float(os.environ.get("SEC10K_ESCALATION_MAX_USD") or 10.00)
_SERVER_BUDGET = None


def server_budget():
    """The one process-wide Budget, created on first use.

    Lazily, so importing this module does not import `llm` — and therefore
    does not import `urllib` on any path `repo_hygiene`'s `escalation_seam`
    walks. Keeping the seam uniform costs three lines and removes a footgun.

    ONE instance, memoized: since ADR-041 every request shares this ceiling,
    and a fresh Budget per request would bound one request and leave the
    deployment unbounded. `escalation_choke_point` pins the `global`.
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
SOURCE_BASES: "dict[str, str]" = {}
SOURCE_ASSETS: "dict[tuple[str, str], tuple[str, bytes]]" = {}
SOURCE_ASSET_PENDING: "set[tuple[str, str]]" = set()
SOURCE_ASSET_LOCK = threading.Lock()
SOURCE_VIEWER_ASSET_MAX = 32  # 32 × 512 KiB = at most 16 MiB per cached filing, not Vision's cap of 2.
SOURCE_ASSET_BYTES = 512 * 1024
VISION_TABLE_TEXT_CAP = 12_000
VISION_TABLE_IMAGE_CAP = 512 * 1024
SOURCE_TABLES: "dict[str, list[dict]]" = {}

# D35: the progress channel is a fixed, write-only projection of execution
# state. Jobs may retain the normal response until its separate result request,
# but polling can see only these six names and their bounded statuses.
PROGRESS_STAGES = ("prepare", "classify", "plan", "route", "verify", "decide")
PROGRESS_STATUSES = {"pending", "active", "done", "skipped", "failed"}
PROGRESS_JOBS: "OrderedDict[str, dict]" = OrderedDict()
PROGRESS_LOCK = threading.Lock()
PROGRESS_MAX = 8


def _progress_advance(job_id, stage, status="active"):
    if stage not in PROGRESS_STAGES or status not in PROGRESS_STATUSES:
        return
    with PROGRESS_LOCK:
        job = PROGRESS_JOBS.get(job_id)
        if not job or job["status"] != "running":
            return
        if status == "active":
            for name, prior in job["stages"].items():
                if prior == "active":
                    job["stages"][name] = "done"
        job["stages"][stage] = status


def _start_progress(run):
    job_id = secrets.token_urlsafe(18)
    job = {"status": "running", "stages": dict.fromkeys(PROGRESS_STAGES, "pending")}
    job["stages"]["prepare"] = "active"
    with PROGRESS_LOCK:
        for stale in list(PROGRESS_JOBS):
            if len(PROGRESS_JOBS) < PROGRESS_MAX:
                break
            if PROGRESS_JOBS[stale]["status"] != "running":
                PROGRESS_JOBS.pop(stale)
        if len(PROGRESS_JOBS) >= PROGRESS_MAX:
            return _err(503, "progress_busy",
                        "the shared extraction progress queue is full — try again shortly")
        PROGRESS_JOBS[job_id] = job

    def work():
        try:
            response = run(lambda stage, status="active":
                           _progress_advance(job_id, stage, status))
            payload = json.loads(response.body)
            status_code = response.status_code
        except Exception:
            payload = {"doc_status": "failed", "items": [], "counts": {},
                       "trace": [], "meta": {}, "warnings": [{"code": "extractor_exception",
                       "item": None, "message": "background extraction failed"}]}
            status_code = 500
        with PROGRESS_LOCK:
            current = PROGRESS_JOBS.get(job_id)
            if not current:
                return
            route_stages = ((payload.get("routing") or {}).get("stages") or [])
            if route_stages:
                current["stages"] = {"prepare": "done", **{
                    name: next((s.get("status") for s in route_stages
                                if s.get("stage") == name), "skipped")
                    for name in PROGRESS_STAGES[1:]}}
            else:
                for name, status in current["stages"].items():
                    if status == "active":
                        current["stages"][name] = ("failed" if payload.get("doc_status") == "failed" else "done")
                    elif status == "pending":
                        current["stages"][name] = "skipped"
            current.update(status="complete", result=(status_code, payload))

    threading.Thread(target=work, daemon=True).start()
    return JSONResponse(status_code=202, content={"progress_id": job_id})


@app.get("/api/progress/{job_id}")
def progress_status(job_id: str):
    with PROGRESS_LOCK:
        job = PROGRESS_JOBS.get(job_id)
        if job is None:
            return JSONResponse(status_code=404, content={"error": "progress_not_found"})
        stages = [{"stage": name, "status": status if status in PROGRESS_STATUSES else "failed"}
                  for name, status in job["stages"].items()]
        return {"status": job["status"], "stages": stages,
                "result_url": f"/api/progress/{job_id}/result" if job["status"] == "complete" else None}


@app.get("/api/progress/{job_id}/result")
def progress_result(job_id: str):
    with PROGRESS_LOCK:
        job = PROGRESS_JOBS.get(job_id)
        result = job.get("result") if job else None
    if result is None:
        return JSONResponse(status_code=409 if job else 404,
                            content={"error": "progress_not_complete" if job else "progress_not_found"})
    return JSONResponse(status_code=result[0], content=result[1])


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

    The process `Budget` bounds the PAID path (ADR-041 left it as the only
    bound); this bounds what the free path costs — measured at ~1.1 s CPU and ~138 MB peak RSS for one ~25 MB request
    (`tasks/reviews/pr-d15-red.txt`). Middleware rather than a guard in each
    endpoint, for the same reason escalation is decided in `_run` (R13): every
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


def _cache_source(raw: bytes, suffix: str, normalized: str, tables=(), omit=(), source_url=None) -> str:
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
    if canonical_edgar_url(source_url or ""):
        SOURCE_BASES[token] = source_url
    from src.sec10k.tables import to_markdown
    SOURCE_TABLES[token] = [{"text": re.sub(r"\s+", "", normalized[t["start"]:t["end"]]).lower(),
                             "markdown": to_markdown(normalized, t, omit=omit)} for t in tables]
    SOURCE_CACHE.move_to_end(token)
    while len(SOURCE_CACHE) > SOURCE_CACHE_MAX:
        stale, _ = SOURCE_CACHE.popitem(last=False)
        SOURCE_TABLES.pop(stale, None)
        SOURCE_BASES.pop(stale, None)
        with SOURCE_ASSET_LOCK:
            for key in [key for key in SOURCE_ASSETS if key[0] == stale]:
                SOURCE_ASSETS.pop(key)
            for key in [key for key in SOURCE_ASSET_PENDING if key[0] == stale]:
                SOURCE_ASSET_PENDING.discard(key)
    return token


def _run(path: str, source: dict, raw: bytes = None,
         exclude_boilerplate: bool = False, markdown: bool = False,
         request: Request = None, source_url: str = None, progress=None,
         escalation_token: str = None):
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

    The shared credential gate is evaluated here for every input mode. With no
    valid key the extraction is complete, deterministic, and free; with one,
    the normal trigger and process Budget still decide whether a model runs.
    """
    # The sole extraction call uses the gate verdict for both escalation and
    # Budget, so all input modes have one paid-path decision.
    escalate, why = gate.paid_path_open(
        request.headers.get(gate.HEADER) if request is not None else escalation_token,
        ESCALATION_ENABLED)
    try:
        result = extract_items(path, exclude_boilerplate=exclude_boilerplate,
                               tables=markdown or escalate, blocks=markdown, escalate=escalate,
                               budget=server_budget() if escalate else None,
                               source_url=source_url, progress=progress)
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
        source = dict(source, token=_cache_source(body, Path(path).suffix.lower(), norm,
                                                   result.get("tables") or (), result.get("boilerplate") or (), source_url))
    view["source"] = source
    return JSONResponse(view)


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/meta")
def api_meta():
    return {"git_sha": git_sha(ROOT), "fixtures": deployed_fixtures(),
            "max_bytes": MAX_BYTES, "allowed_suffix": list(ALLOWED_SUFFIX),
            # Publish configuration state, never the credential or shared
            # budget balance.
            "escalation_enabled": ESCALATION_ENABLED,
            # ADR-043. The page shows its key field only when a secret is
            # configured — a field that cannot open anything is worse than
            # none. False means CLOSED TO ALL, not open to all.
            "escalation_token_required": bool(gate.configured_token())}


@app.post("/api/extract/verify-key")
def verify_escalation_key(request: Request):
    """Confirm paid-tier access without running an extraction."""
    valid, _ = gate.paid_path_open(request.headers.get(gate.HEADER),
                                   ESCALATION_ENABLED)
    return {"valid": valid}


@app.post("/api/extract/vision-table")
async def verify_source_table_raster(request: Request):
    """Check one bounded public-filing table raster after the shared paid gate.

    The browser sends only a source-table PNG and matching DOM text/hash: no
    key, browser state, or unrelated filing content. The verdict never edits
    extraction output; reject/null leaves the deterministic render partial.
    """
    may_call, reason = gate.paid_path_open(request.headers.get(gate.HEADER),
                                           ESCALATION_ENABLED)
    zero = {"llm_calls": 0, "tokens": 0, "usd": 0.0}
    if not may_call:
        return {"status": "skipped", "reason": reason, "images": 0, "cost": zero}
    try:
        too_large = int(request.headers.get("content-length", "0")) > (
            VISION_TABLE_IMAGE_CAP * 2 + VISION_TABLE_TEXT_CAP + 4096)
    except ValueError:
        too_large = True
    if too_large:
        return JSONResponse(status_code=413, content={"status": "failed", "reason": "table request exceeds cap", "images": 0, "cost": zero})
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse(status_code=400, content={"status": "failed", "reason": "invalid JSON", "images": 0, "cost": zero})
    token = body.get("token") if isinstance(body, dict) else None
    image = body.get("image") if isinstance(body, dict) else None
    table_text = body.get("table_text") if isinstance(body, dict) else None
    table_hash = body.get("table_sha256") if isinstance(body, dict) else None
    hit = SOURCE_CACHE.get(token) if isinstance(token, str) else None
    if hit is None or not isinstance(table_text, str) or not isinstance(table_hash, str):
        return JSONResponse(status_code=400, content={"status": "failed", "reason": "source token or table proof is invalid", "images": 0, "cost": zero})
    if len(table_text) > VISION_TABLE_TEXT_CAP or hashlib.sha256(table_text.encode()).hexdigest() != table_hash:
        return JSONResponse(status_code=400, content={"status": "failed", "reason": "table text hash is invalid", "images": 0, "cost": zero})
    proof = re.sub(r"\s+", "", table_text).lower()
    candidate = next((t for t in SOURCE_TABLES.get(token, ()) if proof == t["text"]), None)
    if len(proof) < 16 or candidate is None:
        return JSONResponse(status_code=400, content={"status": "failed", "reason": "table text is not bound to cached source", "images": 0, "cost": zero})
    prefix = "data:image/png;base64,"
    if not isinstance(image, str) or not image.startswith(prefix) or len(image) > VISION_TABLE_IMAGE_CAP * 2:
        return JSONResponse(status_code=400, content={"status": "failed", "reason": "table raster is invalid", "images": 0, "cost": zero})
    try:
        png = base64.b64decode(image[len(prefix):], validate=True)
    except (ValueError, TypeError):
        png = b""
    if len(png) > VISION_TABLE_IMAGE_CAP or not png.startswith(b"\x89PNG\r\n\x1a\n"):
        return JSONResponse(status_code=400, content={"status": "failed", "reason": "table raster is invalid", "images": 0, "cost": zero})
    from src.sec10k.escalate import vision_table_verify
    verdict = vision_table_verify(image, table_text, candidate["markdown"], server_budget())
    return {**verdict, "verifier": {"source_token": True, "table_sha256": True,
                                      "source_text": True}}


@app.post("/api/extract/fixture")
def extract_fixture(body: dict, request: Request):
    name = (body or {}).get("fixture", "")
    try:
        f = _fixture_file(name)
    except FileNotFoundError as e:
        return _err(404, "bad_input", str(e))
    def run(progress=None):
        return _run(str(f), {"mode": "fixture", "name": name, "file": f.name},
                    exclude_boilerplate=bool((body or {}).get("exclude_boilerplate")),
                    markdown=bool((body or {}).get("markdown")),
                    request=request if progress is None else None, progress=progress,
                    escalation_token=request.headers.get(gate.HEADER))
    return _start_progress(run) if request.headers.get("X-Progress") == "1" else run()


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
    def run(progress=None):
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
                        request=request if progress is None else None, progress=progress,
                        escalation_token=request.headers.get(gate.HEADER))
    return _start_progress(run) if request.headers.get("X-Progress") == "1" else run()


@app.post("/api/extract/url")
def extract_url(body: dict, request: Request):
    url = canonical_edgar_url((body or {}).get("url") or "")
    if url is None:
        return _err(400, "bad_input",
                    "Enter an SEC Archives document or Inline XBRL viewer URL")
    suffix = Path(url).suffix.lower() or ".htm"
    if suffix not in ALLOWED_SUFFIX:
        suffix = ".htm"
    def run(progress=None):
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
                        markdown=bool((body or {}).get("markdown")),
                        request=request if progress is None else None, progress=progress,
                        escalation_token=request.headers.get(gate.HEADER), source_url=url)
    return _start_progress(run) if request.headers.get("X-Progress") == "1" else run()


@app.get("/api/source/{token}")
@app.get("/api/source/{token}/")
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
        "Content-Security-Policy": "sandbox allow-same-origin; img-src 'self'",
        "X-Content-Type-Options": "nosniff",
    })


@app.get("/api/source/{token}/{asset:path}")
def api_source_asset(token: str, asset: str):
    """Serve bounded same-accession SEC images for a cached source frame."""
    hit, base = SOURCE_CACHE.get(token), SOURCE_BASES.get(token)
    key = (token, asset)
    if hit is None or base is None or not asset or "/" == asset[:1] or ".." in asset.split("/"):
        return JSONResponse(status_code=404, content={"error": "source_asset_unavailable"})
    if Path(asset).suffix.lower() not in IMAGE_SUFFIXES:
        return JSONResponse(status_code=415, content={"error": "source_asset_not_image"})
    url = asset_url(base, asset)
    if url is None:
        return JSONResponse(status_code=404, content={"error": "source_asset_unavailable"})
    slot = reserve_asset(SOURCE_ASSETS, SOURCE_ASSET_PENDING, token, key,
                         SOURCE_VIEWER_ASSET_MAX, SOURCE_ASSET_LOCK)
    if slot is None:
        return JSONResponse(status_code=429, content={"error": "source_asset_cap"})
    if slot == "cached":
        return Response(content=SOURCE_ASSETS[key][1], media_type=SOURCE_ASSETS[key][0],
                        headers={"X-Content-Type-Options": "nosniff"})
    try:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": EDGAR_UA}), timeout=15) as response:
                raw = response.read(SOURCE_ASSET_BYTES + 1)
                media_type = response.headers.get_content_type()
                final_url = response.geturl()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            return JSONResponse(status_code=502, content={"error": "source_asset_fetch_failed"})
        if (asset_url(base, asset, final_url) is None or len(raw) > SOURCE_ASSET_BYTES
                or not media_type.startswith("image/")):
            return JSONResponse(status_code=415, content={"error": "source_asset_not_image"})
        with SOURCE_ASSET_LOCK:
            cached = SOURCE_ASSETS.setdefault(key, (media_type, raw))
        return Response(content=cached[1], media_type=cached[0], headers={"X-Content-Type-Options": "nosniff"})
    finally:
        release_asset(SOURCE_ASSET_PENDING, key, SOURCE_ASSET_LOCK)


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
