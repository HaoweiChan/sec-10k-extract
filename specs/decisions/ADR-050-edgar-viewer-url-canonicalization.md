# ADR-050 — canonicalize SEC viewer URLs before fetch

Date: 2026-08-29. Status: accepted.

**Ruling**: canonicalize direct SEC Archives links plus the confirmed `/ix` and `/ixviewer/ix.html` wrappers to one clean `https://www.sec.gov/Archives/...` fetch URL; accept encoded `doc`, `sec.gov`, host case, default port, fragments, and unrelated viewer parameters, but reject every unconfirmed endpoint or unsafe target before network access.
**Because**: SEC publishes the same filing through multiple iXBRL viewer generations, while blind string replacement or a generic `doc=` rule would either reject normal browser URLs or widen the outbound-fetch boundary.
**Enforced by**: `edgar-viewer-url.json` executes the full accepted/rejected matrix and pins the one call site used before `/api/extract/url` fetches.

---

The accepted input family is deliberately finite:

- direct `https://www.sec.gov/Archives/...` links;
- `https://www.sec.gov/ix?doc=/Archives/...`;
- `https://www.sec.gov/ixviewer/ix.html?doc=/Archives/...`.

`doc` may use literal slashes or normal percent encoding. `sec.gov` and the
HTTPS default port are same-origin variants. Query presentation parameters and
fragments are discarded. The fetched URL and source provenance both use the
rebuilt canonical URL.

The canonicalizer does not guess future viewer routes. In particular,
`/ixviewer/doc/action` is rejected until SEC evidence says it is a filing URL.
Absolute/protocol-relative `doc` values, credentials, non-default ports,
duplicate or missing `doc`, traversal, double encoding, non-Archives paths,
encoded control characters, lookalike hosts, and non-HTTPS schemes are also
rejected.
