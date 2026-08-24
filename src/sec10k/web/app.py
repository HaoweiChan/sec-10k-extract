"""Inspector service for the sec10k extractor (T7).

Three input modes, all converging on extract_items(path) — acquisition lives
here, never in the extractor (task2-problem-definition.md):

  fixture  zero-friction demo path
  upload   the guaranteed path: no network, no SEC dependency, no rate limit.
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
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from src.sec10k.extract import extract_items
from src.sec10k.web import capabilities as capabilities_mod
from src.sec10k.web.build_id import git_sha
from src.sec10k.web.fixtures import FIXTURES, ROOT, fixture_file, list_fixtures
from src.sec10k.web.view import build_view

STATIC = Path(__file__).resolve().parent / "static"
EDGAR_UA = "Haowei Chan hwchan42@gmail.com"   # SEC fair-access: declare a contact
MAX_BYTES = 25 * 1024 * 1024                  # provisional cap, both upload and URL
ALLOWED_SUFFIX = (".htm", ".html", ".txt")

app = FastAPI(title="sec10k-extract inspector")

# Original-filing bytes for the S4 compare pane, keyed by an opaque token
# handed to the browser. Bounded at 3 documents: this is a browse aid for
# the run just performed, not a document store, so an LRU cap is enough and
# needs no eviction policy fancier than OrderedDict gives for free.
# ponytail: process-local and in-memory, so a restart or a second worker
# process empties it — fine for a single-instance inspector, revisit if this
# ever runs behind more than one uvicorn worker.
SOURCE_CACHE: "OrderedDict[str, tuple[str, bytes]]" = OrderedDict()
SOURCE_CACHE_MAX = 3


def _fixture_file(name: str) -> Path:
    """Resolve a fixture name to its single filing file, refusing traversal.
    Same predicate as the /api/meta listing (fixtures.py), so a name the
    dropdown offers always resolves here."""
    d = (FIXTURES / name).resolve()
    if d.parent != FIXTURES.resolve() or not d.is_dir():
        raise FileNotFoundError(f"unknown fixture: {name!r}")
    f = fixture_file(d)
    if f is None:
        raise FileNotFoundError(
            f"expected exactly one filing file in {d}, found "
            f"{sum(1 for p in d.iterdir() if p.is_file())}")
    return f


def _err(status: int, code: str, message: str, doc_status: str = "failed", **extra):
    """Every refusal returns the same envelope the UI already renders, so a
    rejected request and a failed extraction look identical to the frontend."""
    return JSONResponse(status_code=status, content={
        "doc_status": doc_status, "items": [], "counts": {}, "trace": [], "meta": {},
        "warnings": [{"code": code, "item": None, "message": message}], **extra})


def _cache_source(raw: bytes, suffix: str) -> str:
    """Store the original filing bytes under a fresh opaque token, evicting
    the oldest entry once the LRU is over its 3-document cap."""
    content_type = ("text/plain; charset=utf-8" if suffix == ".txt"
                     else "text/html; charset=utf-8")
    token = secrets.token_urlsafe(16)
    SOURCE_CACHE[token] = (content_type, raw)
    SOURCE_CACHE.move_to_end(token)
    while len(SOURCE_CACHE) > SOURCE_CACHE_MAX:
        SOURCE_CACHE.popitem(last=False)
    return token


def _run(path: str, source: dict, raw: bytes = None,
         exclude_boilerplate: bool = False, markdown: bool = False):
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
    """
    try:
        result = extract_items(path, exclude_boilerplate=exclude_boilerplate, blocks=markdown)
    except Exception as e:                       # refuse loudly, hard rule 4
        return _err(500, "extractor_exception", f"{type(e).__name__}: {e}",
                    source=source)
    view = build_view(result)
    body = raw
    if body is None:
        try:
            body = Path(path).read_bytes()
        except OSError:
            body = None
    if body is not None:
        source = dict(source, token=_cache_source(body, Path(path).suffix.lower()))
    view["source"] = source
    return JSONResponse(view)


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/meta")
def api_meta():
    return {"git_sha": git_sha(ROOT), "fixtures": list_fixtures(),
            "max_bytes": MAX_BYTES, "allowed_suffix": list(ALLOWED_SUFFIX)}


@app.post("/api/extract/fixture")
def extract_fixture(body: dict):
    name = (body or {}).get("fixture", "")
    try:
        f = _fixture_file(name)
    except FileNotFoundError as e:
        return _err(404, "bad_input", str(e))
    return _run(str(f), {"mode": "fixture", "name": name, "file": f.name},
                exclude_boilerplate=bool((body or {}).get("exclude_boilerplate")),
                markdown=bool((body or {}).get("markdown")))


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
                    markdown=request.query_params.get("markdown") == "1")


@app.post("/api/extract/url")
def extract_url(body: dict):
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
                    markdown=bool((body or {}).get("markdown")))


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
    content_type, raw = hit
    return Response(content=raw, media_type=content_type, headers={
        "Content-Security-Policy": "sandbox allow-same-origin",
        "X-Content-Type-Options": "nosniff",
    })


@app.get("/api/capabilities")
def api_capabilities():
    """README.md's works-well table and difficult-section entries, parsed at
    request time so the UI never carries a hand-copied second list (INV-S2's
    argument applied to docs — see src/sec10k/web/capabilities.py)."""
    return capabilities_mod.parse_readme()


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
