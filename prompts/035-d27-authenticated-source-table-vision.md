# D27 — authenticated source-table raster verification

Date: 2026-08-30

## Decision

The owner authorized a vision-capable call only after the escalation key is
verified, limited to a bounded PNG and matching text from a public SEC filing.
The implementation uses the already same-origin source iframe: it rasterizes a
substantive selected table's actual DOM cells and text, hashes the text, and
posts it to the existing paid gate. The server verifies token, byte caps, PNG
signature, hash, and an exact cached normalized-table match before the existing
Budget/cache-backed model call; that match supplies the deterministic Markdown
candidate to compare with the raster.

## Outcome

Vision returns a strict confirm/reject/null verdict and cannot create
extraction text, spans, or Markdown. A reject/null is an honest partial result.
This replaced the prior image-reference-only seam, which did not render pages
or tables and therefore could not substantiate Duke table fidelity.
