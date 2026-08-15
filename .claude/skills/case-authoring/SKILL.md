---
name: case-authoring
description: SOP for hand-authoring golden eval cases from a 10-K fixture — anchor selection, verification, provenance. Use whenever adding a golden case (deep or shallow tier) or promoting a held-out/adversarial finding into the eval set.
---

# Case authoring

Ground truth here is anchor-based because offsets can't be pre-labeled
(`normalized_text` is extractor-owned — see docs/evals/evaluation-strategy.md).
A golden case is only as good as its anchors; author them mechanically.

## Deep-tier case (full anchor work)

1. **Fetch + commit the fixture** with the declared User-Agent pattern from
   `evals/fixtures/README.md`; record accession number, URL, and filing date
   there.
2. **Determine the eras**: format era (txt/HTML/iXBRL) and taxonomy era
   (expected item set — consult `sec10k-domain`). List every expected item
   with its expected status (Part III is often `incorporated_by_reference`).
3. **Pick boundary anchors** per major item: one distinctive phrase from the
   item's first paragraph, one from its last. Anchors must be normalization-
   robust: no entities, no text that spans tag boundaries, no page furniture.
4. **Verify every anchor** by grep against the raw fixture. Record the
   occurrence count in the case's `"provenance"` — every anchor, no
   exceptions. An anchor occurring once is ideal; the TOC pattern (exactly 2
   hits: TOC + body) is acceptable and worth noting — it makes the case a
   TOC-trap tripwire. An anchor with dozens of hits discriminates nothing
   (audit precedent: "General Electric", 101 hits) — pick another phrase.
5. **Derive length bands**: measure the item's raw length; set `min_chars`
   comfortably below and `max_chars` comfortably above (band width is a
   judgment call — note it in provenance; the `max_chars` check lands in T2).
6. **Add cross-item exclusions** for known bleed directions
   (`text_not_contains` — e.g. Item 1 must not contain "Risk Factors").
7. **Write the case JSON** (`id`, `task: "sec10k"`, `suites`, `input.path`,
   `expect.checks`, `provenance`) and **watch it fail** before any
   implementation work counts it.
8. **Request dual-pass**: invoke `extraction-auditor` to independently
   re-verify the anchors; record the pass in provenance. The case is not
   trusted until dual-passed.

## Shallow-tier case

Steps 1–2 and 7 only, with checks limited to `item_present`/`item_absent`
(with statuses), `known_items_only`, `no_overlap_ordered`, `verbatim`,
`no_empty_success`. Minutes per filing; the invariants do the rest.

## Held-out case

Author exactly like a deep or shallow case, but place it in `evals/heldout/`
(directory + `--dir` runner support land in T2) and stop looking at it. Burn semantics: the moment its labeled outcome
influences implementation, it moves to `evals/adversarial/` and is replaced
(see evaluation-strategy.md).
