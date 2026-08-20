# ADR-011 — Incorporated-by-reference items carry offsets, and are checked like any other span

Date: 2026-08-16. Status: accepted. Amends `specs/001-sec10k-contract.md`
(offset rules) and **INV-S1** (scope). Closes the open question left by
ADR-010.

**Ruling**: `incorporated_by_reference` items carry real `start`/`end` offsets over their pointer text, and every span-level check (overlap, boundary hygiene, `verbatim`, content checks) now covers IBR spans exactly like `extracted` ones.
**Because**: the pointer sentence is the evidence a human needs to confirm the claim, and unvalidated IBR offsets were the worst of both worlds — nothing checked them at all.
**Enforced by**: `specs/000-invariants.md` INV-S1, `evals/golden/textron-2001-content.json`, `src/sec10k/test_eval_adapter.py::test_ibr_spans_are_checked`

---

## Context

The contract said: *"For any other status: `start`/`end` are null."* The
extractor never implemented it — `classify` can only return
`incorporated_by_reference` when a heading was found, so those items always
carried real offsets.

The spec↔code audit found the divergence. What made it worth an ADR rather
than a one-line fix is what had already happened because of it: during T4
authoring the mismatch was noticed and resolved **in favour of the spec, by
deleting eval coverage**. `textron-2001-content`'s provenance records the
reasoning verbatim — that content checks against IBR items "can never pass
under any correct extractor; those checks are removed entirely, not just for
items 7/8 but as a rule". Anchors on correctly-located, correctly-extracted
spans were removed from the eval set on the authority of a line the code had
never honoured.

That is the failure mode worth naming: **a stale spec line does not merely sit
there being wrong, it actively destroys the evidence that would contradict
it.**

## Decision

`incorporated_by_reference` carries `start`/`end` pointing at the item's own
pointer text. `missing` and `omitted` stay null — they have no span.

And the part that makes the first part safe: **every span-level check covers
IBR spans.**

- **INV-S1** is rescoped from "extracted item ranges" to "span-carrying item
  ranges". Same for the adapter's `verbatim` bounds check.
- **Boundary hygiene** (layer 8) checks IBR spans like any other.
- The adapter's content checks (`text_contains`, `text_not_contains`,
  `min_chars`, `max_chars`) reach IBR text. Their refusal message changes from
  `"item not extracted"` to `"item has no span"`, which is now the accurate
  statement.
- The **content-shape** validators — `unattributed_content`,
  `last_item_dominates`, `numeric_density_inversion`, `keyword_fingerprint` —
  deliberately do **not** include IBR spans. Their thresholds were measured
  over extracted spans (ADR-008), and a pointer paragraph has no vocabulary or
  numeric profile to judge; SUBSTANTIVE_MIN exists for exactly that reason.

## Why keep the offsets rather than null them

Two reasons, one of which only became visible while investigating.

**The pointer text is the evidence.** Textron's Item 7 span reads *"Management's
Discussion and Analysis," appearing on pages 19 through 32 of our 2001 Annual
Report to Shareholders is incorporated by reference*. That sentence — naming
the target document and the page range — is what a human uses to confirm the
extractor's claim. `heading_text` alone cannot show it, so nulling the offsets
would take the T7 inspector's only means of displaying why an item is IBR.

**Unvalidated offsets were the worst of both worlds.** `validate()` built its
span map from `status == "extracted"`, and the adapter's `no_overlap_ordered`
and `verbatim` did the same. So IBR spans existed and *nothing* checked them —
not one of the six validators, not either structural check. That is precisely
what let `ibr-pointer-first` disown 4,805 chars of GE 1994 with a clean
envelope and zero warnings. Nulling the offsets would have hidden that hole
rather than closed it; the choice was never "offsets or no offsets" but
"checked or unchecked".

Verified before committing: all **44** IBR spans across the 14 fixtures already
satisfy both boundary hygiene and ordering. Extending coverage introduced no
false positive on any committed filing.

## Consequences

- `textron-2001-content` regains anchors on items 6, 7, 7A and 8 — four items,
  twelve checks, each anchor grep-verified at exactly 1 occurrence against the
  raw fixture. Coverage deleted by a stale spec line is restored.
- `test_ibr_spans_are_checked` proves the structural checks now catch an
  overlapping IBR span and out-of-range IBR offsets, and that null-offset
  statuses stay exempt. Watched red first: before the change,
  `no_overlap_ordered` returned `None` on a deliberately overlapping IBR span.
- Two further stale contract lines corrected while in the file, both from the
  same audit: the `item` registry pointer named `eval_adapter.py` (the judging
  mirror) rather than `segment.py` (what actually emits); and the `confidence`
  bullet claimed the eval set "contains cases that punish overconfident
  wrongness" while no case read the field. The weaker, true statement replaces
  it — cases pin the constants, calibration is A-level work.
- INV-S1's rescoping is the first invariant change in this repo. It widens what
  the invariant covers and never narrows it, so no previously-passing case can
  be made to pass by it.
