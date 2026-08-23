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

## INV-S1: Span-carrying item ranges are non-overlapping and in document order
- Scope: every status that carries offsets — `extracted` **and**
  `incorporated_by_reference` (ADR-011). `missing`/`omitted` have no span.
- Rationale: overlap means double-attribution of text; disorder means the
  splitter matched a TOC entry or a stray reference instead of a real heading.
  Restricting this to `extracted` left IBR spans unchecked by anything, which
  is how `ibr-pointer-first` disowned 4,805 chars in silence.
- Enforced by: evals/golden/aapl-2025-structure.json,
  evals/adversarial/ibr-pointer-first.json,
  src/sec10k/test_eval_adapter.py::test_ibr_spans_are_checked

## INV-S2: Every extracted item's text is a verbatim slice of normalized_text
- Rationale: no paraphrase, no LLM rewriting, no dropped characters — offsets
  must reproduce the item exactly, or provenance is lost. Optional boilerplate
  exclusion (ADR-026) does not weaken this: it reports chrome as spans and
  never edits the text, so the offsets are the same bytes with the flag on and
  off. That equality is asserted, not assumed. Optional table annotation
  (ADR-029) is held to the same rule: tables are offset records into the
  text, never an edit of it, and a cell's text is a slice, not a field.
  Optional block-structure annotation (ADR-031) likewise: blocks are offset
  records, the Markdown is derived from them, and `normalized_text` is never
  rewritten as Markdown (ADR-031 §f2 measured what that would move).
- Enforced by: evals/golden/aapl-2025-structure.json,
  evals/adversarial/boilerplate-offsets-invariant.json (exclusion on vs off),
  evals/adversarial/tables-offsets-invariant.json (tables on vs off),
  evals/adversarial/blocks-offsets-invariant.json and
  evals/adversarial/blocks-wrapped-invariant.json (blocks on vs off)

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

## INV-S5: normalized_text is the readable filing, not machine metadata
- Rationale: offsets are the unit of provenance, so anything in
  `normalized_text` that a human reading the filing would never see displaces
  every offset after it and poisons every ratio measured against document
  length (coverage, gap analysis, numeric density). iXBRL context headers are
  the concrete case: 15.4% of JPM 2024's normalized text, ahead of the first
  readable word. Stated positively so it cannot be satisfied by deleting
  content — readable text must survive intact.
- Enforced by: evals/adversarial/ixbrl-hidden-metadata.json (ADR-006)
