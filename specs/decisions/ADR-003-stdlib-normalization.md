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

## Normalization canon (added 2026-08-15, T2 dual-pass audit)

Anchors and every offset-bearing eval artifact are authored against this
canon, and the normalizer must produce it:

- Entities decode via `html.unescape` to real Unicode and STAY Unicode — no
  ASCII transliteration (`&#8217;` → ’ U+2019, `&#8211;` → – U+2013; cp1252 C1
  refs like `&#146;` decode per the WHATWG mapping html.unescape implements).
- Whitespace runs inside text — including raw newlines in HTML source — 
  collapse to a single space; block-tag boundaries emit newlines; 3+ newlines
  collapse.
- U+00A0 (from `&nbsp;`/`&#160;`) is whitespace: it maps to space and
  participates in collapse, which therefore must run (also) *after* entity
  decoding — T2 re-verification caught NBSPs surviving a pre-decode-only
  collapse (second instance of the dead-anchor bug class).

The audit found five early T2 anchors written in ASCII against
entity-encoded fixtures (dead under this canon); they were rewritten to
canon-decoded form.

## Consequences

- Zero parsing dependencies at B; the only runtime deps are fastapi + uvicorn
  for the web service.
- Known risk accepted: stdlib parser is less tolerant of malformed markup than
  lxml. The taxonomy (F5) tracks this; failure surfaces as an explicit
  `failed` doc_status, never silent garbage.
