"""T2 deploy spike: minimal FastAPI wrapper around the extractor. Proves
(1) the service shape runs and (2) EDGAR egress works. /extract returns a
real contract-v2 envelope from the full T3-T5 pipeline.
Full inspector UI is T7 — see docs/product/task2-problem-definition.md."""
import subprocess
import urllib.request
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from src.sec10k.extract import extract_items

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "evals" / "fixtures"
EDGAR_UA = "Haowei Chan hwchan42@gmail.com"

app = FastAPI(title="sec10k-extract (T2 spike)")


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _case_count() -> int:
    return sum(len(list((ROOT / "evals" / d).glob("*.json")))
               for d in ("golden", "adversarial"))


@app.get("/", response_class=HTMLResponse)
def status_page():
    return f"""<!doctype html>
<title>sec10k-extract</title>
<h1>sec10k-extract</h1>
<p>git SHA: {_git_sha()}</p>
<p>eval cases (golden + adversarial): {_case_count()}</p>
<p>pipeline status: the full deterministic pipeline is live &mdash; document
selection, normalization, heading candidates, TOC filtering, boundaries,
status classification, the label-free validator battery and confidence
scoring. Extraction returns a contract-v2 envelope with per-item offsets,
status, confidence and method.</p>
<p>Refusals are explicit and are not best-effort parses: unreadable input is
<code>failed</code>, input that is not a 10-K is <code>unsupported</code>.
The inspector UI lands at T7 &mdash; see docs/product/task2-problem-definition.md.</p>
<ul>
<li><a href="/edgar-check">GET /edgar-check</a></li>
<li>POST /extract {{"fixture": "aapl-2025"}}</li>
</ul>"""


@app.post("/extract")
def extract(body: dict):
    name = body["fixture"]
    fixture_dir = (FIXTURES / name).resolve()
    if fixture_dir.parent != FIXTURES.resolve() or not fixture_dir.is_dir():
        return JSONResponse({"doc_status": "failed", "error": f"unknown fixture: {name!r}"})
    try:
        files = [f for f in fixture_dir.iterdir() if f.is_file()]
        if len(files) != 1:
            raise FileNotFoundError(
                f"expected exactly one filing file in {fixture_dir}, found {len(files)}")
        result = extract_items(str(files[0]))
        return result
    except Exception as e:
        return JSONResponse(
            {"doc_status": "failed", "error": f"{type(e).__name__}: {e}"})


@app.get("/edgar-check")
def edgar_check():
    req = urllib.request.Request(
        "https://data.sec.gov/submissions/CIK0000320193.json",
        headers={"User-Agent": EDGAR_UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
            return {"status": resp.status, "bytes": len(body), "ok": resp.status == 200}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "bytes": 0, "ok": False}
    except Exception as e:
        return {"status": None, "bytes": 0, "ok": False, "error": f"{type(e).__name__}: {e}"}
