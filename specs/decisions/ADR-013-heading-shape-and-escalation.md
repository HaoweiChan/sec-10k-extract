# ADR-013 — A heading's title may live on the next line; missing items escalate by proportion

Date: 2026-08-16. Status: accepted. Amends ADR-007 (the same-line heading rule)
and ADR-008 (`AMBIGUOUS_CODES`). Both findings come from H1, the first held-out
run — `docs/evals/audits/2026-08-16-h1-heldout-triage.md`.

## Ruling 1 — the same-line rule is a default, not a law

ADR-007's discriminator is that a real body heading carries its title on the
same line. It is what makes the TOC filter free: a contents-page cell
normalizes to a bare `Item 1.` and dies without any cluster analysis.

JNJ 2016 puts the item code and its title in separate markup blocks. After
normalization, 18 of its 21 headings read `Item 1.\n\nBUSINESS` and 3 read
`Item 2.PROPERTIES`. The rule rejected the 18 and kept the 3 — the run returned
**3 of 21 items**. The discriminator did not merely weaken, it **inverted**: the
shape that identifies a TOC entry in every dev fixture is the shape of a real
heading in this filing.

**Decision**: when a heading line carries no title, take the next non-empty
line as the title if it scores at or above `SIM_FLOOR` for that code.

**No new threshold is introduced, and that is the point.** The obvious version
of this fix is catastrophic: measured across the dev set, promoting on
next-line similarity alone resurrects *every* TOC entry in premier-pacific
(20), nvda (23) and cat (23), because their contents pages put the code and
title in adjacent cells too — and since a TOC precedes the body, greedy ordered
assignment would take it. That is the repo's most-cited trap, re-armed.

What separates them is density, and the repo already owns that mechanism.
Measured gaps between promotable candidates:

| filing | promotable | gaps ≤ 400 | median gap |
|---|---|---|---|
| premier-pacific-2016 | 20 | 19/19 | 50 |
| nvda-2024 | 23 | 22/22 | 57 |
| cat-2023 | 23 | 22/22 | 59 |
| **jnj-2016** | **18** | **4/17** | **2,824** |

So promoted candidates are handed to the existing TOC-cluster rule, whose
thresholds ADR-007 already measured, and it separates them cleanly. The fix
reuses a mechanism rather than adding a heuristic.

**One guard beyond that**, and it came from the module's own self-check rather
than from a fixture: a bare code whose title-line is *immediately followed by
another item code* is an index row, whatever its length. The cluster rule needs
`TOC_CLUSTER_MIN` (5) distinct codes, so a shorter run would slip through. No
real 10-K has a 2-item contents page — every one has 15 to 23 — so no fixture
covers it, and rewriting the self-check to use a bigger TOC would have been
fitting the test to the code. The guard is three lines and closes the hole
honestly.

Enforced by `jnj-bare-headings`, which asserts items across all four Parts so a
fix repairing only Part I cannot pass, plus `toc-titled` and every existing
fixture standing still.

## Ruling 2 — a quarter of the items missing is a refusal, not a footnote

JNJ lost 18 of 21 items and reported `success_with_warning`. Eighteen
`expected_item_missing` warnings fired — the battery saw everything — but that
code is not in `AMBIGUOUS_CODES`, so **no volume of it could ever escalate**.
The contract calls `doc_status` "the frontend's headline banner" and invites
consumers to threshold on it, so this is a document that lost most of its
content presenting as a qualified success.

**Decision**: a new escalating warning, `expected_items_mostly_missing`, fires
when the missing fraction exceeds `MISSING_MAX = 0.25`.

Measured over all 17 non-refused dev fixtures: fifteen lose **zero** items; the
only two that lose any are `heading-unnumbered` (1/23 = 0.043) and
`malformed-html` (1/21 = 0.048), and both already escalate by another route.
Held-out JNJ sat at 0.857. The empty band is 0.048–0.857.

The floor is **0.25, not the band midpoint** this repo usually takes. The cost
asymmetry differs from a content-shape validator: a false `ambiguous` is a
conservative report a consumer can inspect, while a false `success_with_warning`
on a collapsed document is exactly the silent failure the battery exists to
prevent. 0.25 still sits five times above the worst real filing in the set.
Deviating from the convention is recorded here rather than left for a reader to
notice.

Enforced by `items-stripped-escalation`. That fixture's design carries the
ruling: an earlier draft stripped only the body headings, which left the items
on the contents page, fired `toc_manifest_mismatch` and escalated **already** —
it would have passed before and after the fix and proved nothing. Removing the
contents-page rows as well leaves the missing proportion as the only signal,
and `warning_absent(toc_manifest_mismatch)` holds it there.

## Consequences

- JNJ 2016: **3/21 → 21/21 items**, `doc_status: success`. No other fixture's
  output changed; fast 25 → 27 cases, invariant 8 → 10, all green.
- `jnj-2016` is **burned** as held-out and promoted to `evals/adversarial/`.
  `gs-2002` is not fixed here and is not burned — see below.
- **Deliberately not fixed**: the era-model finding. `gs-2002` item 15 is absent
  because Goldman used the post-Sarbanes-Oxley numbering (14 = Controls,
  15 = Exhibits) on a FY2002 filing, ahead of the 2003-08-14 date `ADDED`
  encodes. This is the third confirmation of the debt ADR-010 recorded — *the
  era table is a single point of silent failure* — and the general fix (letting
  a physically present heading for a known code surface regardless of era
  expectation) conflicts with INV-S3 as written. That is A-level scope and a
  spec change, not a bug fix. It stays enumerated as honest debt, which is what
  the held-out case now documents.
- The escalation rule has a known blind spot it does not close: an item that is
  *mis-assigned* rather than missing still counts as present. Proportion
  measures absence, not correctness.
