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
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from src.sec10k.extract import extract_items
from src.sec10k.web.view import build_view

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "evals" / "fixtures"
STATIC = Path(__file__).resolve().parent / "static"
EDGAR_UA = "Haowei Chan hwchan42@gmail.com"   # SEC fair-access: declare a contact
MAX_BYTES = 25 * 1024 * 1024                  # provisional cap, both upload and URL
ALLOWED_SUFFIX = (".htm", ".html", ".txt")

app = FastAPI(title="sec10k-extract inspector")


def _git_sha() -> str:
    """Build identity for the status line. A deployed instance usually has no
    .git directory, so GIT_SHA can be set as an env var instead — a reviewer
    needs to know which build they are looking at, and "unknown" is a bad
    answer on the one instance strangers will actually use."""
    env = os.environ.get("GIT_SHA")
    if env:
        return env.strip()[:12]
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _fixture_file(name: str) -> Path:
    """Resolve a fixture name to its single filing file, refusing traversal."""
    d = (FIXTURES / name).resolve()
    if d.parent != FIXTURES.resolve() or not d.is_dir():
        raise FileNotFoundError(f"unknown fixture: {name!r}")
    files = [f for f in d.iterdir() if f.is_file()]
    if len(files) != 1:
        raise FileNotFoundError(
            f"expected exactly one filing file in {d}, found {len(files)}")
    return files[0]


def _err(status: int, code: str, message: str, doc_status: str = "failed", **extra):
    """Every refusal returns the same envelope the UI already renders, so a
    rejected request and a failed extraction look identical to the frontend."""
    return JSONResponse(status_code=status, content={
        "doc_status": doc_status, "items": [], "counts": {}, "trace": [], "meta": {},
        "warnings": [{"code": code, "item": None, "message": message}], **extra})


def _run(path: str, source: dict):
    """Extract and shape for the UI. Never leaks a traceback to the browser."""
    try:
        result = extract_items(path)
    except Exception as e:                       # refuse loudly, hard rule 4
        return _err(500, "extractor_exception", f"{type(e).__name__}: {e}",
                    source=source)
    view = build_view(result)
    view["source"] = source
    return JSONResponse(view)


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/meta")
def api_meta():
    fixtures = sorted(d.name for d in FIXTURES.iterdir() if d.is_dir())
    return {"git_sha": _git_sha(), "fixtures": fixtures,
            "max_bytes": MAX_BYTES, "allowed_suffix": list(ALLOWED_SUFFIX)}


@app.post("/api/extract/fixture")
def extract_fixture(body: dict):
    name = (body or {}).get("fixture", "")
    try:
        f = _fixture_file(name)
    except FileNotFoundError as e:
        return _err(404, "bad_input", str(e))
    return _run(str(f), {"mode": "fixture", "name": name, "file": f.name})


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
                             "sha256": hashlib.sha256(raw).hexdigest()[:16]})


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
                             "sha256": hashlib.sha256(raw).hexdigest()[:16]})


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
