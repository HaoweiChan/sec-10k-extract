"""Turn known SEC filing URL forms into one safe Archives fetch URL."""
from urllib.parse import parse_qs, unquote, urlsplit, urlunsplit


_HOSTS = {"sec.gov", "www.sec.gov"}
_VIEWERS = {"/ix", "/ixviewer/ix.html"}
_ARCHIVES = "/Archives/"


def canonical_edgar_url(value: str) -> str | None:
    """Return a canonical SEC Archives URL, or ``None`` for unsafe input."""
    if not isinstance(value, str) or any(ord(ch) < 32 for ch in value):
        return None
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError:
        return None
    if (parsed.scheme.lower() != "https" or parsed.hostname not in _HOSTS
            or parsed.username is not None or parsed.password is not None
            or port not in (None, 443)):
        return None

    if parsed.path in _VIEWERS:
        docs = parse_qs(parsed.query, keep_blank_values=True).get("doc", [])
        if len(docs) != 1:
            return None
        path = docs[0]
    else:
        path = unquote(parsed.path)

    # Decode exactly once. Double-encoded separators, absolute URLs,
    # protocol-relative targets and Windows separators consequently fail the
    # same path boundary instead of being interpreted a second time later.
    if (not path.startswith(_ARCHIVES)
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in path)
            or "%" in path or "\\" in path
            or "?" in path or "#" in path
            or any(part in (".", "..") for part in path.split("/"))):
        return None
    return urlunsplit(("https", "www.sec.gov", path, "", ""))


def _demo() -> None:
    canonical = "https://www.sec.gov/Archives/edgar/data/1/a.htm"
    assert canonical_edgar_url(canonical) == canonical
    assert canonical_edgar_url(
        "https://www.sec.gov/ix?doc=%2FArchives%2Fedgar%2Fdata%2F1%2Fa.htm"
    ) == canonical
    assert canonical_edgar_url("https://example.com/Archives/a.htm") is None


if __name__ == "__main__":
    _demo()
