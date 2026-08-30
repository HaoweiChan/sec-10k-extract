# ADR-059 — index-first cross-reference alignment

Date: 2026-08-31. Status: accepted.

**Ruling**: treat a Form 10-K Cross-Reference Index page range as a coarse locator; within its first printed page prefer the last exact mapped title, otherwise the first item-title match scoring at least 0.70, while preserving LangGraph residual routing and its cache identity.
**Because**: mapped pages can begin with preceding prose, repeated running titles, or legitimate body-caption variants, while the ordinary segmenter threshold would also accept nearby unrelated captions such as `Accounting Changes`.
**Enforced by**: five fixture-free `d38-xref-*` cases plus the existing Intel composite/page-anchor checks; no newly downloaded filing or held-out offsets are committed.

---
