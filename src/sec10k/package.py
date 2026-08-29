"""Bounded same-accession attachment acquisition (ADR-048)."""
import hashlib
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from src.sec10k.normalize import format_era, normalize

ARCHIVES = "https://www.sec.gov/Archives/"
PACKAGE_MAX_BYTES = 25 * 1024 * 1024
EDGAR_UA = "Haowei Chan hwchan42@gmail.com"
_ACCESSION = re.compile(r"^/Archives/edgar/data/(\d+)/(\d{18})/[^/]+$")
_DOCUMENT = re.compile(br"<DOCUMENT>(.*?)(?:</DOCUMENT>|\Z)", re.S | re.I)
_TEXT = re.compile(br"<TEXT>(.*?)(?:</TEXT>|\Z)", re.S | re.I)
_TYPE = re.compile(br"^<TYPE>(\S+)", re.M | re.I)
_SEQUENCE = re.compile(br"^<SEQUENCE>(\S+)", re.M | re.I)
_FILENAME = re.compile(br"^<FILENAME>(\S+)", re.M | re.I)
_ANNUAL_REPORT_TYPE = re.compile(r"^(?:EX-13(?:\.\d+)?|ARS)$")
_FETCH_CACHE = {}
_BLOBS = {}


def accession_base(source_url):
    """Validated SEC accession directory, or None."""
    u = urlsplit(source_url or "")
    m = _ACCESSION.fullmatch(u.path)
    if u.scheme != "https" or u.netloc != "www.sec.gov" or not m:
        return None
    return f"{ARCHIVES}edgar/data/{m.group(1)}/{m.group(2)}/"


def _submission_url(source_url):
    base = accession_base(source_url)
    if not base:
        return None
    digits = base.rstrip("/").rsplit("/", 1)[-1]
    accession = f"{digits[:10]}-{digits[10:12]}-{digits[12:]}"
    return base + accession + ".txt"


def _decode(raw):
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def document(raw, type_, sequence, filename, *, url=None, sgml_block=None):
    """Create one immutable, document-scoped normalized attachment record."""
    raw = bytes(raw)
    body = _decode(raw)
    text = normalize(body, format_era(body))[0]
    raw_hash = hashlib.sha256(raw).hexdigest()
    norm_hash = hashlib.sha256(text.encode()).hexdigest()
    identity = {
        "id": f"{('url' if url else 'sgml')}:{sequence}:{filename or type_}:{raw_hash[:12]}",
        "type": type_, "sequence": str(sequence), "filename": filename,
        "url": url, "sgml_block": sgml_block,
        "raw_sha256": raw_hash, "normalized_sha256": norm_hash,
    }
    _BLOBS[raw_hash] = raw
    return {"document": identity, "text": text}


def embedded_documents(raw):
    """EX-13 variants/ARS already present in an uploaded full submission."""
    out = []
    for n, match in enumerate(_DOCUMENT.finditer(raw)):
        block = match.group(1)
        field = lambda rx: _decode(rx.search(block).group(1)) if rx.search(block) else ""  # noqa: E731
        type_ = field(_TYPE).upper()
        if not _ANNUAL_REPORT_TYPE.fullmatch(type_):
            continue
        inner = _TEXT.search(block)
        body = inner.group(1) if inner else block
        out.append(document(body, type_, field(_SEQUENCE), field(_FILENAME),
                            sgml_block=f"DOCUMENT[{n}]"))
    return out


def _fetch(url, opener=urllib.request.urlopen):
    """Fetch once; cache the content-addressed bytes and reject redirects."""
    if url in _FETCH_CACHE:
        return _FETCH_CACHE[url], {"calls": 0, "bytes": len(_FETCH_CACHE[url]),
                                   "latency_ms": 0.0, "cached": True}
    started = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": EDGAR_UA})
    try:
        with opener(req, timeout=30) as resp:
            final = resp.geturl()
            if final != url:
                raise ValueError("SEC response redirected outside the requested accession identity")
            raw = resp.read(PACKAGE_MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise RuntimeError(f"same-accession acquisition unavailable: {e}") from None
    if len(raw) > PACKAGE_MAX_BYTES:
        raise RuntimeError(f"same-accession submission exceeds {PACKAGE_MAX_BYTES} bytes")
    _FETCH_CACHE[url] = raw
    _BLOBS[hashlib.sha256(raw).hexdigest()] = raw
    return raw, {"calls": 1, "bytes": len(raw),
                 "latency_ms": round((time.monotonic() - started) * 1000, 3),
                 "cached": False}


def acquire(raw, source_url=None, opener=urllib.request.urlopen):
    """Enumerate only local SGML blocks or the source accession submission."""
    docs = embedded_documents(raw)
    if docs:
        return docs, {"status": "available", "source": "sgml", "calls": 0,
                      "bytes": len(raw), "latency_ms": 0.0, "cap": PACKAGE_MAX_BYTES}
    url = _submission_url(source_url)
    if not url:
        return [], {"status": "absent", "source": None, "calls": 0, "bytes": 0,
                    "latency_ms": 0.0, "cap": PACKAGE_MAX_BYTES}
    try:
        submission, measured = _fetch(url, opener)
    except RuntimeError as e:
        return [], {"status": "unavailable", "source": url, "calls": 0, "bytes": 0,
                    "latency_ms": 0.0, "cap": PACKAGE_MAX_BYTES, "error": str(e)}
    docs = embedded_documents(submission)
    # A source accession is also the allowlist for every published URL.
    base = accession_base(source_url)
    for got in docs:
        got["document"]["url"] = base + got["document"]["filename"]
        got["document"]["sgml_block"] = None
        got["document"]["id"] = got["document"]["id"].replace("sgml:", "url:", 1)
    return docs, {"status": "available" if docs else "absent", "source": url,
                  "cap": PACKAGE_MAX_BYTES, **measured}


def summaries(documents):
    """No attachment text in the persistent prompt until a bounded read."""
    return [{**d["document"], "chars": len(d["text"])} for d in documents]
