---
id: DRAFT-44
title: >-
  Three input classes disable most of the validator battery — class 1 CLOSED by
  D3 / ADR-030 (2026-08-23), classes 2 and 3 remain
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-55
  - >-
    ADR-027 §e; the standing 'A non-last span dominating the document' row above
    (class 1 is its interior-gap half); ADR-019 §f (class 2 is the deliberate
    EXEC_OFFICERS_RE exclusion
  - measured there on 7 fixtures)
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Three input classes disable most of the validator battery — class 1 CLOSED by D3 / ADR-030 (2026-08-23), classes 2 and 3 remain** (added 2026-08-22, Origin: gates-2026-08-22 T5-5, MEDIUM; re-filed Origin: D3 for the remainder) — class 1 ('a 4-5-of-21 missing filing sits under MISSING_MAX with an interior span swallowing the rest') is now `item_dominates` → `ambiguous`, proved on `evals/adversarial/interior-span-dominates.json` (4 of 20 missing, item 1 at 0.6387); class 2 (the EO clip's interior gap) is a span getting SMALLER, not a dominance, and ADR-019 §d's accounting stands; class 3 (no contents page) is the absence of a signal — the D3 fixture happens to have none and still escalates through the new route, which is not a cure. Verbatim from the reviewer: *Three whole input classes disable most of the battery: a 4-5-of-21 missing filing sits under MISSING_MAX with an interior span swallowing the rest; an EXEC_OFFICERS_RE clip on a comma-terminated wrap truncates item 1 into an interior gap no validator measures; a pre-2005 txt filing with no dense contents page disables toc_manifest_mismatch, numeric_density_inversion and boundary_hygiene at once.* Implementer note, checked not assumed: class 3 is partly mis-stated — `boundary_hygiene` runs over every span regardless of a contents page (it needs no manifest), and `numeric_density_inversion` is gated by both items being substantive, not by the TOC; only `toc_manifest_mismatch` is disabled by a missing manifest

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
