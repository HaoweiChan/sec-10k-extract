---
id: DRAFT-89
title: The image FETCH half of S10 is not built
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-106
  - >-
    `specs/decisions/ADR-033-image-reference-annotation.md` §c and §e row 1;
    `evals/golden/*-images.json` (the references the fetch would resolve)
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The image FETCH half of S10 is not built** (added 2026-08-23, Origin: S10) — ADR-033 §c rules it out: `extract_items(path, images=True)` reports every `<img>` as `{offset, src, alt, width, height}` but never resolves `src`, never downloads, never caches, and the inspector shows nothing where an image sits. All 53 images in the committed corpus are external references to sibling documents in their EDGAR accession (0 inline `data:` URIs), so the bytes are not in any fixture and cannot be. What shipping it would cost, measured in ADR-033 §c: a live-fetch case that goes red whenever EDGAR is slow or rate-limits (hard rule 4 forbids the mock), a second cache beside the inspector's process-local one, and — because cost-discipline rule 4 says a `full`-suite case commits its cached response, and an image's cached response IS the image — roughly 3 MB of binary joining a text-only benchmark corpus, which moves ADR-021 §b8's populations and every figure derived from them. The resolution rule is written down in ADR-033 §c so a consumer can do it themselves.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
