# D24 — same-accession external evidence

## Material prompt

Extend the existing maximum-three-turn agent loop into a same-accession SEC
filing-package navigator. Preserve the primary pointer span and primary coverage;
publish attachment identity, hashes, document-scoped offsets and verifier
decisions. Route only independently evidenced external Annual Report pointers
with an available same-accession candidate, keep clean/internal/absent/xref paths
bounded, and burn MRK FY1995 and PGR FY2023 if their outcomes influence code.

## Outcome

ADR-048 keeps one agent loop and adds document listing, bounded attachment
search/read and multi-item external proposals. Acquisition is restricted to
embedded SGML EX-13/ARS blocks or the validated SEC Archives accession's capped
full submission. Evidence is annotation-only under `external_regions`; primary
item offsets, methods and coverage never move. The two influenced cases and
fixtures moved from held-out, with two replacements tracked as TD-167.

## Assumption → Eval contradiction → Correction

- Assumed: committing PGR's EX-13 beside its primary fixture was the simplest
  offline package representation.
- Eval said: the repository's fixture discovery contract accepts exactly one
  primary file per directory; a second file made PGR disappear from the corpus.
- Corrected: package attachments live under `evals/package-fixtures/`, outside
  default fixture discovery, with independent provenance and hashes.

## PR83 round 1 correction

Fresh review showed that a nearby title was not enough section proof, decoded
SGML could not support a raw-byte hash claim, and exact `EX-13` omitted SEC's
numbered exhibit variants. The repair reuses the canonical item-title taxonomy
plus a proved end boundary, slices SGML attachment bodies before decoding, and
admits only numeric `EX-13.<digits>` variants. PGR wrong-section/end, CP1252, and
real KO 1997 EX-13.1 cases were each red before the shared-boundary fixes.
