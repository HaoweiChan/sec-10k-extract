"""Pure same-accession source-asset boundary, usable without FastAPI."""
from pathlib import Path
from threading import Lock
from urllib.parse import urljoin

from src.sec10k.web.edgar_url import canonical_edgar_url

IMAGE_SUFFIXES = {".gif", ".jpg", ".jpeg", ".png", ".webp"}


def asset_url(base, asset, final_url=None):
    if isinstance(asset, str) and asset.startswith("_sec_root/"):
        asset = "/" + asset[len("_sec_root/"):]
    directory = (canonical_edgar_url(base or "") or "").rsplit("/", 1)[0] + "/"
    if not directory or not isinstance(asset, str) or not asset or asset.startswith("//") or ".." in asset.split("/"):
        return None
    if Path(asset).suffix.lower() not in IMAGE_SUFFIXES:
        return None
    candidate = canonical_edgar_url(urljoin(directory, asset))
    final = canonical_edgar_url(final_url or candidate or "")
    return candidate if candidate and final and candidate.startswith(directory) and final.startswith(directory) else None


def reserve_asset(cached, pending, token, key, cap, lock):
    """Atomically reserve one viewer asset slot; callers own fetch/release."""
    with lock:
        if key in cached:
            return "cached"
        if sum(k[0] == token for k in cached) + sum(k[0] == token for k in pending) >= cap:
            return None
        pending.add(key)
        return "reserved"


def release_asset(pending, key, lock):
    with lock:
        pending.discard(key)


def _demo():
    base = "https://www.sec.gov/Archives/edgar/data/1/a.htm"
    assert asset_url(base, "x.jpg") == "https://www.sec.gov/Archives/edgar/data/1/x.jpg"
    assert asset_url(base, "x.jpg", "https://evil.example/x.jpg") is None
    assert asset_url(base, "../x.jpg") is None
    cached, pending, lock = {}, set(), Lock()
    assert reserve_asset(cached, pending, "t", ("t", "x.jpg"), 1, lock) == "reserved"
    assert reserve_asset(cached, pending, "t", ("t", "y.jpg"), 1, lock) is None
    release_asset(pending, ("t", "x.jpg"), lock)


if __name__ == "__main__":
    _demo()
