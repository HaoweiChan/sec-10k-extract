# ADR-004 — Status semantics for pointer-shaped items

Date: 2026-08-15. Status: accepted. Amended by: ADR-017, ADR-031 (in place
2026-08-23: a pointer may sit in a footnote outside the item's body — see the
note under Decision).

**Ruling**: `incorporated_by_reference` is reserved for bodies that are solely a pointer to a *different* document; an internal same-document pointer, or a mixed body with substantive prose, stays `extracted`.
**Because**: the extractor reports what the filing labels, verbatim — resolving internal pointers or judging mixed content is not v1's job.
**Enforced by**: `evals/golden/ibm-1997-shallow.json`, `evals/golden/textron-2001-content.json`, `evals/golden/jpm-2024-content.json`

---

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
- *Amended 2026-08-23 (ADR-031, D4): the shape-1 pointer may also live OUTSIDE
  the item's body — a heading whose line ends in an asterisk run over an EMPTY
  body, resolved by a footnote anywhere in the document that begins with the
  same run, names that item's code and names a different document (ba-2003
  items 11/13: "* Certain information required by Items 5, 10, 11, 13 and 14
  is incorporated herein by reference to the registrant's definitive proxy
  statement"). Same external-document test, same two signals; a marked heading
  over a substantive body stays shape 3 (ba-2003 items 5/10).*
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
