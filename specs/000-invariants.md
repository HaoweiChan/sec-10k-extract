# 000 — Invariants

Properties that must ALWAYS hold, across every task in this repo.
**An invariant listed here without a backing eval case (tagged
`"suites": ["invariant"]`) is decorative and counts as drift** — the
`spec-drift` agent flags it.

Format per invariant:

```
## INV-<n>: <one-line property>
- Rationale: why this must never break
- Enforced by: evals/<...>.json (case id)
```

## INV-0: The pipeline never reports success with empty output
- Rationale: silent failure is the #1 graded failure mode; an empty result
  must surface as an explicit failure/low-confidence signal, never a green run.
- Enforced by: evals/golden/aapl-2025-structure.json (`no_empty_success` check)

---

## sec10k

## INV-S1: Extracted item ranges are non-overlapping and in document order
- Rationale: overlap means double-attribution of text; disorder means the
  splitter matched a TOC entry or a stray reference instead of a real heading.
- Enforced by: evals/golden/aapl-2025-structure.json

## INV-S2: Every extracted item's text is a verbatim slice of normalized_text
- Rationale: no paraphrase, no LLM rewriting, no dropped characters — offsets
  must reproduce the item exactly, or provenance is lost.
- Enforced by: evals/golden/aapl-2025-structure.json

## INV-S3: Only canonical item codes, valid for the filing's taxonomy era
- Rationale: "Item 405 of Regulation S-K" and "Item 601" appear as prose in
  real filings (GE 1994) and must never surface as items; pre-2003 filings
  have no Item 1A/9A, so emitting one there means the splitter hallucinated.
- Enforced by: evals/adversarial/ge-1994-oldformat.json

## INV-S4: Expected items are never silently absent
- Rationale: every item in the era's expected set appears in the output with
  an explicit status (extracted / missing / incorporated_by_reference /
  omitted) — a consumer must be able to distinguish "not in filing" from
  "extractor missed it".
- Enforced by: evals/adversarial/ge-1994-oldformat.json
