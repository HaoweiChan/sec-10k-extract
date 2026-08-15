# ADR-004 — Status semantics for pointer-shaped items

Date: 2026-08-15. Status: accepted.

## Context

T2 case authoring found three pointer shapes in real filings that the contract
did not disambiguate:

1. **Pure external pointer** — the item's whole body points to a *different
   document*: GE FY1993 Items 11–13 ("Incorporated by reference to ... the
   definitive proxy statement") and Item 7 ("Reported on pages 32-43 ... of
   the Annual Report to Share Owners" — a separately printed exhibit).
2. **Internal same-document pointer** — the labeled item is a short pointer to
   pages *of the same filed document*: JPMorgan FY2024 Items 7 and 8 are ~400
   raw chars each ("appears on pages 52-167"), while the actual MD&A and
   financial statements (~70% of the document) sit unlabeled later in the same
   file. (Textron FY2001 is NOT this shape — its pointers name the separately
   filed 2001 Annual Report to Shareholders exhibit, i.e. shape 1; the T2
   dual-pass audit corrected this ADR's original misclassification.)
3. **Mixed** — substantial real content plus a closing IBR sentence: GE FY1993
   Item 10 (full officers table, then "The remaining information ... is
   incorporated by reference").

## Decision

- `incorporated_by_reference` is reserved for shape 1: the labeled content is
  (only) a pointer to a **different document** — proxy statement, printed
  annual report, exhibit filed separately.
- Shape 2 is `extracted`: the extractor reports what the filing *labels* as
  the item, verbatim — the pointer paragraph — and does **not** resolve
  internal pointers at v1. The unlabeled content region is surfaced honestly
  by the layer-8 validators (coverage ratio, gap analysis) as warnings, so
  such filings land in `success_with_warning`, never a silent clean success.
  Resolving internal pointers to capture the real content is a candidate
  A-level enhancement requiring its own ADR.
- Shape 3 is `extracted` (the pointer sentence rides along inside the span).
- **Pointer-only mixed bodies** (audit follow-up): an item whose body consists
  solely of pointers with no substantive standalone content takes IBR if any
  pointer names a different document (Textron Item 10: one proxy-IBR sentence
  + one internal page pointer → IBR); internal-only pointers remain shape 2 →
  `extracted`. An item with substantive standalone content before its
  pointer(s) is shape 3 → `extracted` (Textron Item 5: exchange listings +
  holder count → `extracted`, correcting its original IBR pin).

## Consequences

- Case assertions encode this ruling: GE item 7 → IBR; GE item 10 → extracted;
  JPM internal-pointer items → extracted; Textron Part II pointer items → IBR
  (shape 1), Textron Item 5 → extracted (shape 3), Textron Item 10 → IBR
  (pointer-only mixed). The deliberately-unpinned Item 10 statuses in
  nike-2006 / ibm-1997 shallow cases can be pinned in a later pass using this
  rule.
- Financial-sector filings with the internal-pointer layout become the
  strongest test of the gap-analysis validator — JPM's unlabeled mega-section
  is exactly what it must flag.
- The fallback-stage ADR previously informally referred to as "ADR-004" in
  planning docs is renumbered to "a dedicated ADR (when residual-failure data
  exists)" — references updated.
