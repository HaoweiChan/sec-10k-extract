# Failure taxonomy — how 10-K item extraction goes wrong

Seven categories. Each lists its concrete failure modes, then: **detection**
(what signal exposes it), **mitigation** (which pipeline layer answers it,
per `docs/architecture/overview.md`), **eval** (which check types represent it
in cases), **policy** (recover / lower confidence / explicit fail). Built
before the pipeline so the pipeline answers the taxonomy, not vice versa.
New failure modes discovered later are added here *and* become adversarial
cases (CLAUDE.md hard rule 2); the `sec10k-domain` skill carries the
domain background for each trap.

## F1 — False-positive headings

Modes: TOC entries matched as headings; "Item 405 of Regulation S-K" /
"Item 601" prose; cross-references ("see Item 8", "as discussed in Item 1A");
headings repeated in exhibit documents; page-furniture "PART II" repeats in
fixed-width filings.

- Detection: candidate-density cluster near document start (TOC); canonical +
  era code filter; context features (mid-sentence position, "of Regulation"
  suffix, "see/in/under" prefix); document selection excludes exhibits.
- Mitigation: document selection + candidate filtering layers.
- Eval: `known_items_only`, `item_absent`, `text_not_contains`, `min_chars`
  (TOC-truncated stubs).
- Policy: recover via filtering; lower confidence when the filter margin is thin.

## F2 — Heading variance

Modes: capitalization ("Item"/"ITEM"/"item"); punctuation ("Item 1." /
"ITEM 1 —" / "Item 1:"); nbsp and whitespace variants; headings inside table
cells; inline headings mid-paragraph; headings split across iXBRL tags; HTML
nesting differences.

- Detection: tiered pattern matching — strict line-anchored with title match
  first, lenient consulted only for expected items strict matching missed;
  tier recorded per item.
- Mitigation: normalization + candidate detection.
- Eval: `item_present` + `text_contains` anchors on per-era golden fixtures.
- Policy: recover; lenient-tier matches carry lower confidence by construction.

## F3 — Absence and status ambiguity

Modes: genuinely missing items; "Not applicable"/"None" omissions; Part III
incorporated-by-reference to the proxy statement; Item 6 "[Reserved]" (2021+);
era-nonexistent items (no 1A before 2005, no 9A before 2003 — emitting one is
hallucination).

- Detection: expected-set diff for the filing's taxonomy era; short-body
  keyword classification ("incorporated by reference", "not applicable",
  "none", "[reserved]").
- Mitigation: status classification stage.
- Eval: `item_present` with `status:` assertions, `item_absent`.
- Policy: explicit status always (INV-S4); confidence attaches to the status
  judgment itself.

## F4 — Boundary and ordering errors

Modes: Item 8 / F-pages boundary (largest span, full of heading-like lines);
1 vs 1A vs 1B vs 1C and 7 vs 7A longest-match ambiguity; content bleeding
across items; duplicate content; unexpected item ordering; overlapping spans.

- Detection: sequence consistency vs the era's taxonomy order; overlap check;
  per-item length priors.
- Mitigation: boundary resolution + structural validation.
- Eval: `no_overlap_ordered`, `min_chars`, `max_chars` (new, T2),
  end-of-item `text_contains` anchors, cross-item `text_not_contains`
  (the existing "Item 1 must not contain 'Risk Factors'" pattern).
- Policy: recover when ordered assignment resolves it; `doc_status: ambiguous`
  when competing candidate sets cannot be separated; lower confidence.

## F5 — Format and parse hazards

Modes: malformed HTML; iXBRL tag stripping that joins or splits words;
encoding weirdness; fixed-width page furniture in pre-2001 filings; very
large filings (10 MB+).

- Detection: normalization statistics (tag ratio, replacement characters,
  output-length sanity); deterministic re-run equality.
- Mitigation: normalization layer (tolerant stdlib parser, ADR-003).
- Eval: `verbatim` + era-specific anchors; a hand-degraded malformed-HTML
  adversarial case (self-created material — allowed).
- Policy: recover where the tolerant parser copes; `failed` when normalization
  output collapses — caught by coverage validation, not by hoping.

## F6 — Wrong-document selection

Modes: multi-`<DOCUMENT>` submissions where exhibits repeat item-like
headings; wrong file submitted (a 10-Q, a lone exhibit, a 20-F).

- Detection: `<TYPE>` tags; cover-page "FORM 10-K" sniff; expected-heading
  population sanity.
- Mitigation: document selection layer.
- Eval: `ge-1994-oldformat` covers exhibits; new adversarial case: 10-Q input
  expecting `doc_status: unsupported` (needs the `doc_status` check, T2).
- Policy: explicit `unsupported`/`failed` — never a best-effort parse of the
  wrong document.

## F7 — False success (the meta-category)

Any failure above escaping detection while the output reports success. This is
the #1 graded failure mode and the reason INV-0 exists.

- Detection: structural-validation battery (coverage ratio, length priors,
  sequence completeness) + the eval set + auditor sampling.
- Policy: validation failures always downgrade `doc_status` and emit warnings —
  the pipeline never silently recovers.

### Named silent-failure shapes → the check that catches each

| Silent-failure shape | Caught by |
|---|---|
| Every item truncated at its TOC entry | `min_chars` + body anchors (`aapl-2025-content`) |
| "Item 405" prose emitted as an item | `known_items_only` (INV-S3) |
| Item 1A hallucinated in a 1994 filing | `item_absent` (INV-S3) |
| Expected item silently absent from output | expected-set rule + `item_present{status}` (INV-S4) |
| Item 7 swallowing 7A | `item_present 7A` + cross-item `text_not_contains` |
| Near-empty output reported as success | `no_empty_success` (INV-0) + coverage validation |
| Offsets drifted from text | `verbatim` (INV-S2) |
| Exhibit/wrong document parsed confidently | `doc_status` check (T2) + anchor checks |
| Confident wrongness in general | calibration metric + auditor output sampling |

The table maps each shape to its *designed* catch. Which catches are already
backed by committed cases vs pending T2 (the 7A checks, `doc_status`,
`max_chars`, status assertions, the determinism check) is tracked by the
methodology audits in `docs/evals/audits/`.

### Known residual gap (named honestly)

Anchor checks test *containment*, not exact boundaries — a span can bleed far
past its true end while first-paragraph anchors still pass. Guards: length
bands, cross-item exclusion anchors, the boundary-tightness proxy metric, and
auditor sampling against the source. See `evaluation-strategy.md`.
