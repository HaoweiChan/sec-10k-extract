# ADR-006 — Normalization rulings from the T3 spike

Date: 2026-08-15. Status: accepted. Extends ADR-003 (stdlib-only parsing),
whose revisit clause required exactly this spike before the pipeline was built
on the stdlib normalizer.

## Context

ADR-003 committed to `html.parser` and named a T3 spike — determinism plus
word-joining on the committed fixtures — as its precondition. The spike ran
against all 13 fixtures (throwaway script, not committed; every number below
is reproducible from the fixtures). Two of the three questions came back
clean:

- **Determinism**: identical output across repeat runs on all 13 fixtures.
- **Speed**: 12.8 MB JPM normalizes in 0.43 s; 2.3 s for all 13 fixtures
  (~24 MB). The stdlib parser is not a throughput problem at B.
- **Word integrity**: 33 of the 34 `text_contains` anchors in the eval set
  survived normalization. The one dead anchor, plus two defects the anchors
  were never positioned to catch, are what this ADR rules on.

The anchor set was used deliberately as the canary: anchors are authored
against the ADR-003 canon by an independent SOP, so they fail loudly when the
normalizer and the canon disagree.

## Ruling 1 — iXBRL context metadata is not document text

`<ix:header>` (and the `<ix:hidden>` block inside it) carries the filing's
XBRL context definitions. Their *character data* — `<xbrldi:explicitMember>`
values and friends — is emitted as text by any tag-stripping normalizer, so a
naive pass produces a run of concatenated machine identifiers ahead of the
cover page: 12.9 K chars on AAPL 2025, and 221 K chars on JPM 2024 — 15.4% of
that document's normalized text before the first readable word.

**Decision**: `ix:header` and `ix:hidden` subtrees are skipped entirely,
exactly as `script`/`style` already are. Skipping is by element, not by
`style="display:none"` — the iXBRL spec names these containers, whereas a
style-attribute sniff is a heuristic that a filer's stylesheet can defeat in
either direction (AAPL 2025 alone has 33 `display:none` occurrences, most of
them legitimate presentational hiding of real content).

Enforced by INV-S5 / `ixbrl-hidden-metadata`. That case pins the cut with
three positive anchors as well as three negative ones, because "delete
everything before the cover page" would satisfy the negatives while destroying
the document.

## Ruling 2 — a newline means opposite things in the two format eras

The same character, decided by format era:

- **HTML/iXBRL era**: a newline inside a text node is source formatting with
  no rendered meaning (filers hard-wrap at ~80 columns). It **collapses to a
  space**. Structural newlines are emitted only by block tags. Implementation
  consequence: whitespace inside each text chunk collapses *at parse time*,
  before chunks are joined — after joining, a source newline and a block
  boundary are indistinguishable. Scope: 858 mid-sentence breaks in MSFT 2013
  and 669 in NIKE 2006 survived the naive pass; every other HTML fixture had
  zero, so this is a filing-agent style confined to the mid-era HTML stratum.
- **Plain-text era (1993–2001)**: newlines **are** the document — fixed-width
  layout, line-anchored headings, page furniture that stays in the text per
  ADR-003. Passthrough, as `docs/architecture/overview.md` layer 3 already
  said. GE 1994 (2,178), IBM 1997 (1,798) and Textron 2001 (353) show the same
  mid-sentence-newline signature and must keep every one of them.

Enforced by `html-source-wrap` (HTML side) and by the existing txt-era anchor
cases, which pass line-locally either way.

## Ruling 3 — the txt path does not decode entities

The HTML path decodes entities via the parser (ADR-003 canon). The txt path
does not: none of the three committed txt fixtures contains a single HTML
entity (verified by pattern scan), and `html.unescape` on undecoded text is
not risk-free — it rewrites `&amp` without a semicolon, so a literal ampersand
in 1990s prose could be corrupted to buy nothing.

**Known gap, accepted**: a held-out txt filing that does carry entities would
normalize with them intact. Recorded as honest debt rather than pre-solved —
if a held-out or adversarial txt case ever exhibits it, that case is the
trigger to revisit, per the same discipline ADR-003 used.

## Consequences

- Normalization is `src/sec10k/normalize.py`, ~2 KB, still zero parsing
  dependencies; ADR-003's revisit clause stays unfired (no malformed-input
  case has defeated the stdlib parser — `malformed-html` normalizes cleanly).
- Two new adapter check types (`norm_contains` / `norm_not_contains`) judge
  `normalized_text` directly. Before them, no check in the eval set asserted
  anything about the normalizer's own output, so normalization defects were
  only observable once segmentation existed to carry them into an item span —
  a whole layer was untested by construction.
- A third instance of the dead-anchor bug class (ADR-003 records two). All
  three had the same shape: the canon and the normalizer disagreed, and the
  anchors were the only thing that noticed. The spike is now the standing
  cheap check — re-run it whenever normalization changes.
