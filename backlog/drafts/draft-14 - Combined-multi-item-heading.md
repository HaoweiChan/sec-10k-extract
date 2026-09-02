---
id: DRAFT-14
title: Combined multi-item heading
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-14
  - '`evals/adversarial/axp-2008-combined-part-iii.json` (`debt` suite'
  - permanently red
  - >-
    asserting all four items `extracted` against the four-way partition — which
    is also what stops a partial fan-out from satisfying its promote-to-green
    contract); ADR-020 §c row 7
  - §g and §h
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Combined multi-item heading** (added 2026-08-19, T12) — `axp-2008` addresses Part III under ONE heading naming four item codes at once: raw bytes offset 1225493, `<B>ITEMS&nbsp;10,&nbsp;11,&nbsp;12&nbsp;and&nbsp;13.</B>` plus the four-item title, immediately followed by an explicit proxy incorporation by reference. Every heading path in `src/sec10k/segment.py` matches exactly one code per heading, so items 10–13 all report `missing` at confidence 0.40 (`expected_item_missing` fired, `doc_status` `success_with_warning`) where the correct status for each is `extracted` — `segment.classify` returns `extracted` on all four bodies of the four-way partition, and for item 10 that is ADR-004 shape 3 rather than IBR because its body is not pointer-only (~1,139 chars of Reg S-K Item 406 code-of-ethics prose follow the proxy pointers, against ADR-007's 300-char remainder threshold). All four are contract-reachable: the caption regions are disjoint and in document order and `no_overlap_ordered` accepts them. What the interleaved bullet order costs is item-10 *coverage* under that partition (item 10 keeps 956 of the block's 3,263 chars; the cost is 2,307 — read backwards here until L1, PR #11 R25), not the other three items' spans. This filer also writes its contents-page entries as bare `10.`/`11.`/`12.`/`13.` with no `Item` prefix, which is why `toc_manifest` comes back empty on a filing that has a complete TOC. An honest miss, not a silent failure — but the **only real-filing item-recall gap in either eval set**, which is why ADR-020 weighs it. The held-out case that carried this fixture was burned and moved here in the same milestone, and its four wrong `missing` labels were dropped in the move

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
