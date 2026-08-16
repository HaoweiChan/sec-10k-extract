# ADR-016 — Every warning code and every check, dispositioned

Date: 2026-08-17. Status: accepted. Discharges the open item ADR-010's
consequences section left in `tasks/TODO.md` row G1: *"four of the six layer-8
validators still have no case proving they fire, and four adapter checks are
structurally incapable of going red. 25/25 green means less than it appears,
and saying so is the point of writing it down."*

The rule this ADR applies: **a check that no case can turn red is a claim, not
a check.** Its thresholds are free to move, its predicate is free to be
inverted, and the suite stays green either way. That is the same defect ADR-010
found in the confidence table (no case read the field) and ADR-013 found in the
escalation rule (no volume of a non-escalating warning could ever escalate).

Disposition is one of three, and every code gets one:

- **fixture** — a committed case asserts `warning_present` and the pipeline
  produces it end to end
- **unit** — the code path is proved against the function that owns it, because
  no document can reach it
- **ruled** — deliberately not proved, with the reason recorded here

## The eight layer-8 codes and the four upstream warnings

| code | disposition | where |
|---|---|---|
| `toc_manifest_mismatch` | fixture | `heading-unnumbered` |
| `expected_items_mostly_missing` | fixture | `items-stripped-escalation` — **assertion added by this ADR**, see §1 |
| `unattributed_content` | fixture | `ibm-1997-shallow` |
| `last_item_dominates` | fixture | `jpm-2024-structure` |
| `boundary_hygiene` | **unit** | `validate._demo`, added by this ADR — see §2 |
| `numeric_density_inversion` | **fixture** | `spans-transposed`, new — see §3 |
| `keyword_fingerprint` | **fixture** | `spans-transposed`, new — see §3 |
| `expected_item_missing` | fixture | `items-stripped-escalation`, `ge-1994-oldformat` |
| `normalization_collapse` | fixture | `truncated-download` |
| `unsupported_form` | fixture | `10q-unsupported`, `ksb-unsupported` |
| `form_type_disagreement` | unit | `normalize._demo` (the `loud` case) |
| `period_end_unknown` | **ruled** | see §4 |

## 1. `expected_items_mostly_missing` was firing but unasserted

`items-stripped-escalation` — the fixture ADR-013 built specifically to enforce
the new escalation rule — asserted `doc_status: ambiguous` and
`warning_present: expected_item_missing`, but never the escalating code itself.
Three codes can reach `ambiguous` and only one of the other two was pinned
absent, so the rule the fixture exists for could have stopped firing with the
case still green, `last_item_dominates` carrying the status instead. One line:
`warning_present: expected_items_mostly_missing`.

That is the pattern worth naming: **asserting the consequence is not asserting
the cause.** The same shape is why `doc_status` alone is never enough to pin a
validator.

## 2. `boundary_hygiene` cannot be fired by any document, and that is fine

Spans are built from heading matches, so a span opens with its heading **by
construction**, and the check re-applies a copy of the regex that produced the
offset. ADR-010 called this "can only fire as a false positive". That reading is
right about documents and wrong about the check's purpose: it is a **consistency
assertion between two layers** — segmentation's offsets against validation's
reading of them — not a statement about any filing. Its value is that it would
catch a future change to `assign_boundaries`, `heading_end`, or normalization
that silently shifted an offset.

**Ruling**: prove it where it lives. `validate._demo` now feeds `validate()` a
span deliberately offset by 40 chars and asserts the warning fires, and does it
twice — once for an `extracted` span and once for an `incorporated_by_reference`
one, because ADR-011's extension to IBR spans was itself unproved.

Chasing a fixture for it would mean deliberately corrupting offsets somewhere
between the two layers, i.e. writing a bug into the pipeline to prove a check
that watches for that bug. The unit boundary is the honest place.

## 3. `numeric_density_inversion` and `keyword_fingerprint`: one fixture, both fired

Neither had fired on any of the thirty-one fixtures in the set. Both judge
content shape — *does this span read and count like its label?* — so firing them
requires a span that is genuinely mislabelled, which no real filing supplies.

**Ruling**: `spans-transposed`, a **pure transposition** of `sgrp-2019`. Two raw
byte ranges are exchanged — the block after the Item 1A heading title and the
block after the Item 8 heading title — so the mutated file is a
character-for-character permutation of its source (the derivation asserts
`sorted(out) == sorted(raw)`). Nothing is added, deleted, or edited.

The headings **stay where they are**, and that is the design decision worth
recording. Swapping the headings instead would put code 8 ahead of code 1A in
document order; greedy ordered assignment then loses every item between them to
a cursor jump, the run collapses, and the case would prove
`expected_items_mostly_missing` — a cascade — rather than the two content-shape
checks it is for. The case pins that with `warning_absent` on
`expected_items_mostly_missing` and `toc_manifest_mismatch`: the filing must
look **structurally intact** and fail only on content shape, which is the exact
silent-failure profile these two validators exist to catch.

Measured at authoring: item 8's digit/`$`/`%` density 0.006 against item 1A's
0.047; and the risk-factor prose now sitting under Item 8 contains neither
"total" nor "net".

The case also pins `doc_status: success_with_warning`. Two validators saying
"these spans may be mislabelled" produce a *qualified success*, because neither
code is in `AMBIGUOUS_CODES` under ADR-008's warn-don't-hard-fail policy for
false-positive-prone content-shape checks. That is defensible and it is also the
kind of decision that should have to be re-argued in an ADR rather than drift —
so it is asserted, not left implicit.

This fixture models a **boundary defect, not a filer style**. No registrant
transposes their risk factors with their financial statements. Stated plainly
here rather than dressed up as a document property.

## 4. `period_end_unknown` is ruled, not proved

It fires when no period of report can be parsed, which degrades the expected
item set to the 1993 taxonomy — a real, user-visible consequence. No fixture is
added anyway:

- No filer omits the period from the cover page; EDGAR rejects the submission.
  A mutation that removed it would be a test of `COVER_DATE_RE` and
  `DEI_PERIOD_RE`, not of a document shape.
- The realistic path to it is the T7 upload of an **excerpt** — pages 20-60 of a
  10-K with no cover — and an excerpt has no "FORM 10-K" line either, so form
  sniffing refuses it first with `unsupported`. That is the correct answer for
  an excerpt, and it means the excerpt does not reach this warning.

If a real input is ever found that is accepted as a 10-K and still yields no
period end, it becomes a case that day. Until then this is enumerated, not
enforced, and the difference is stated rather than hidden behind a green tick.

## 5. The four adapter checks that could not go red

ADR-010 named `no_overlap_ordered`, `verbatim`, `known_items_only` and
`boundary_hygiene`. The last is a validator and is handled in §2. The other
three are **pure functions of a result dict**, so they are provable directly, on
hand-built results, without waiting for a fixture whose segmentation happens to
break — `test_eval_adapter.py::test_checks_that_had_never_gone_red`, covering
overlap, plain disorder, out-of-range and inverted offsets, a non-canonical
code, and a status outside the contract's four.

`verbatim` needed more than a test. ADR-010's specific complaint was that it
"asserts bounds and never compares text", so an offset pair that was in range
but pointed at the wrong region satisfied INV-S2's only enforcement. There **is**
something to compare, and the envelope already publishes it: a span must open
with the item's own `heading_text`.

**Ruling**: `verbatim` now checks bounds and then that
`normalized_text[start:end].lstrip()` starts with the item's `heading_text`.
Verified across all thirty-one dev fixtures before landing — zero mismatches —
so it pins current behaviour rather than describing an aspiration. Items with a
null `heading_text` are exempt, and the unit test asserts that exemption
explicitly so it cannot become a silent pass.

This is the one place in this ADR where a check gained teeth rather than a
proof, and it is the one that most deserved it: `verbatim` appears in
twenty-odd cases and is cited as the enforcement of INV-S2.

## Consequences

- Fast 41/41. Every warning code the pipeline can emit is now either fired by a
  committed case, proved at its own layer, or ruled here with a reason.
- Two new adversarial cases (`spans-transposed`, `ksb-unsupported`), one new
  fixture derived by transposition, one new unit test, two new self-check
  assertions in `validate._demo`, one added assertion in
  `items-stripped-escalation`, and one real comparison added to `verbatim`.
- **What this does not claim.** Firing a validator once proves the code path,
  not the threshold. `SUBSTANTIVE_MIN`, `UNATTRIBUTED_MAX`, `LAST_ITEM_MAX` and
  `MISSING_MAX` are each pinned from one side only — a case proves the warning
  fires above the line, and a different case proves a normal filing stays below
  it, but no case brackets any of them tightly. Per-bucket calibration is T10's
  job and this ADR does not do it early.
