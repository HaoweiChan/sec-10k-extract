# ADR-003 — Stdlib-only parsing and normalization at B-level

Date: 2026-08-15. Status: accepted.

## Context

The pipeline needs HTML → deterministic plain text across three format eras,
including 1.5 MB iXBRL documents saturated with `ix:*` tags. Candidate
dependencies (lxml, BeautifulSoup, sec-parser) add install weight, platform
variance, and version drift to the most correctness-critical stage — and
ponytail discipline says stdlib first. Determinism is a contract requirement
(offsets into `normalized_text`).

## Decision

B-level normalization is built on stdlib `html.parser` only: block tags emit
newlines, inline tags (including `ix:*`) emit nothing, `script`/`style`
skipped, entities unescaped, whitespace normalized. No third-party parsing
dependencies. Page furniture stays in the text (verbatim provenance beats
cosmetic cleanliness); it is handled at candidate level.

**Revisit clause**: if a real malformed-HTML adversarial case defeats this
normalizer — not hypothetically, but as a red case in `evals/adversarial/` —
a successor ADR may introduce a tolerant parser dependency. A T3 spike
(determinism + word-joining on both committed fixtures) validates the approach
before the pipeline is built on it.

## Consequences

- Zero parsing dependencies at B; the only runtime deps are fastapi + uvicorn
  for the web service.
- Known risk accepted: stdlib parser is less tolerant of malformed markup than
  lxml. The taxonomy (F5) tracks this; failure surfaces as an explicit
  `failed` doc_status, never silent garbage.
