---
name: sec10k-domain
description: 10-K filing anatomy — item taxonomy by era, format variants, and known extraction traps. Use when writing or debugging the sec10k extraction pipeline, authoring eval cases, or judging whether an extraction result is plausible.
---

# 10-K filing anatomy

## Canonical item taxonomy (modern, post-2005)

| Part | Items |
|---|---|
| I | 1 Business · 1A Risk Factors · 1B Unresolved Staff Comments · 1C Cybersecurity (2023+) · 2 Properties · 3 Legal Proceedings · 4 Mine Safety Disclosures |
| II | 5 Market for Common Equity · 6 [Reserved] (2021+; was Selected Financial Data) · 7 MD&A · 7A Market Risk · 8 Financial Statements · 9 Changes/Disagreements with Accountants · 9A Controls and Procedures · 9B Other Information · 9C Foreign Jurisdictions that Prevent Inspections (2021+) |
| III | 10 Directors/Officers/Governance · 11 Executive Compensation · 12 Security Ownership · 13 Related Transactions · 14 Accountant Fees |
| IV | 15 Exhibits and Financial Statement Schedules · 16 Form 10-K Summary (2016+, optional) |

## Taxonomy by era — expected-item sets differ

- **pre-2003** (e.g. GE 1994): Items 1–14 only. No 1A/1B/1C, no 7A (added
  1997), no 9A/9B (SOX, 2003). Item 14 = Exhibits (today's 15). Part III
  items 10–13 routinely `incorporated_by_reference` to the proxy statement.
- **2005+**: 1A Risk Factors mandatory. **2010+**: smaller reporting companies
  may omit 7A. **2021+**: Item 6 becomes "[Reserved]". **2023+**: 1C exists.
- An extractor emitting "1A" for a 1994 filing has hallucinated (INV-S3).

## Format eras

- **1993–2001**: plain-text full submissions (`.txt`), ALL documents in one
  file wrapped in `<DOCUMENT>...</DOCUMENT>` blocks (the 10-K body is one of
  several — exhibits follow). Fixed-width layout, page headers/footers inline.
- **2001–2019**: HTML primary document, separately downloadable.
- **2019+**: inline XBRL (iXBRL) — HTML saturated with `<ix:*>` tags
  (AAPL 2025 fixture). Text extraction must strip tags without joining or
  splitting words.

## Known traps (each one is or becomes an adversarial case)

1. **TOC trap** — every item heading appears ≥2× (table of contents + body).
   AAPL 2025: all headings have exactly 2 hits. Matching the first hit
   truncates every item at the TOC.
2. **Regulation references** — "Item 405 of Regulation S-K", "Item 601"
   appear as prose (GE 1994 lines 124, 6275). Any `Item \d+` regex without a
   canonical-code filter emits garbage items.
3. **Cross-references** — "see Item 8", "as discussed in Item 1A" inside item
   bodies must not terminate/open items.
4. **Incorporation by reference** — Part III often contains only a pointer to
   the proxy statement. That is `incorporated_by_reference`, not `missing`,
   and not a tiny "extracted" item.
5. **Multi-document .txt submissions** — find the 10-K `<DOCUMENT>` block
   first; exhibits repeat item-like headings.
6. **Page furniture** — repeated page headers ("PART II", company name) and
   page numbers inside old fixed-width filings.
7. **Item 8 boundary** — financial statements + notes are the largest span
   and full of things that look like headings; F-pages sometimes live outside
   the item sequence entirely.

## Fixture provenance

See `evals/fixtures/README.md`. All fixtures are public EDGAR documents
fetched with a declared User-Agent per SEC fair-access policy.
