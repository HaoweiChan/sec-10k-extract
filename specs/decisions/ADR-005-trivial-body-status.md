# ADR-005 — Status semantics: trivial bodies and absent headings

Date: 2026-08-15. Status: accepted.

## Context

T2 case authoring pinned "[Reserved]" / "Not applicable" / "None." bodies as
`extracted` (AAPL Item 6, NVDA 6/9C/16, MSFT 9B, IBM 9, Textron 9, Premier
Pacific 7A), while `docs/architecture/overview.md` layer 7 said short body +
those keywords → `omitted`. The T2 dual-pass audit flagged the contradiction:
as documented, layer 7 would fail six golden cases, and the `omitted` status
was unreachable under the cases' convention — a contract status with no eval
representation is decorative.

## Decision

Extending ADR-004's principle (the extractor reports what the filing labels):

1. **Heading present in the 10-K body → `extracted`**, span = the labeled
   content verbatim, no matter how trivial ("[Reserved]", "None.", "Not
   applicable"). Triviality is signaled by span length and validator evidence,
   never by status.
2. **Heading absent, era/filer rules permit the absence** (optional Item 16;
   smaller-reporting-company 7A relief; era-valid omissions) → `omitted`.
3. **Heading absent, era expects it** → `missing`.
4. `incorporated_by_reference` exactly per ADR-004 (external-document
   pointers only).

## Consequences

- The T2 case pins stand as authored. JPM FY2024 (Item 16 genuinely absent,
  optional) is the canonical `omitted` example.
- Architecture layer 7 is corrected: the keyword scan reclassifies only to
  `incorporated_by_reference`; "[Reserved]"-type bodies stay `extracted` and
  are flagged by length/validators instead.
- `omitted` and `missing` become cleanly distinguishable: both mean "no
  heading", and era rules decide which — exactly the distinction INV-S4's
  consumer needs.
- The premier-pacific stratum is relabeled "SRC 7A-relief" (its 7A heading
  exists with not-required text → `extracted`); an SRC filing that omits the
  7A heading entirely is the `omitted` test case to add later.
