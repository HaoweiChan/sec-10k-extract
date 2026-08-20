# ADR-014: T9 tranche-1 rulings — the Item 4 Reserved window, and one more abbreviation

Status: accepted, 2026-08-17. Amended by: ADR-015.
Driven by: `item4-reserved-window`, `ibr-pointer-window` (both watched red
before any code moved — hard rule 2), found by `wmt-2010-shallow` on the first
T9 expansion filing that was chosen to stress IBR density, not these defects.

**Ruling**: model Item 4's 2010-02-28→2011-12-15 "Reserved" era as its own label window, and rejoin the sentence splitter at "No. \<digit\>" so a pointer sentence isn't cut mid-reference.
**Because**: WMT FY2010's Item 4 heading was in plain sight and still classified `missing`, and its Item 14 IBR pointer was cut by the ordinal in "Proposal No. 2" before the external-document phrase could be seen.
**Enforced by**: `evals/adversarial/item4-reserved-window.json`, `evals/adversarial/ibr-pointer-window.json`

---

## 1. Item 4 carries a third era: "Reserved" (2010-02-28 → 2011-12-15)

Release 33-9089A removed "Submission of Matters to a Vote of Security Holders"
effective 2010-02-28; Mine Safety Disclosures arrived 2011-12-15 (Dodd-Frank
§1503). In between, filers wrote `ITEM 4. RESERVED` or `(Removed and
Reserved)`. The era model knew only the two neighbors, so title similarity
rejected a heading in plain sight and WMT FY2010's Item 4 classified `missing`
at conf 0.4 — a wrong statement about a filing that did nothing wrong.

Rulings:

- `TITLES["4"]` gains the alias `"Reserved"`. Matching takes the max over all
  aliases era-blind (existing behavior, unchanged) — the longer "(Removed and
  Reserved)" variants clear `SIM_FLOOR` on ratio against it.
- The **label** window is era-gated in `item_label`: period end in
  [2010-01-01, 2011-12-15) → "Reserved". Keyed on period end like the rest of
  the table; Jan-2010+ period ends necessarily file after the effective date,
  Dec-2009 enders mostly filed before it. Same one-sided compromise as the 9C
  boundary, documented at the site.
- Status for a present Reserved heading is `extracted` (span runs to the next
  heading), following the nvda-2024 Item 6 "[Reserved]" precedent. WMT's span
  carries the Executive Officers chart that follows the heading — correct
  under the segmentation model, which assigns unnumbered supplemental text to
  the preceding item.

## 2. `_sentences` rejoins ordinals: "Proposal No. 2" is not a sentence end

WMT Item 14's body is a single pointer sentence, the exact shape ADR-007's
correction was built for — and it classified `extracted` because the sentence
splitter cut at the ordinal in "Proposal No. 2", leaving `sents[0]` with the
IBR phrase but without the words "Proxy Statement". `EXTERNAL_DOC_RE` then
failed exactly as designed, on a sentence that wasn't one. Item 11, same
filing, same shape, no ordinal: classified IBR correctly. Same failure family
as pre-B finding 2 ("Item 1. Election of Directors" captions), one
abbreviation over.

Ruling: rejoin when a part ends in `No.` and the next part starts with a
digit — the demonstrated defect, nothing speculative. Other abbreviations
(Inc., Corp., U.S.) stay out until an eval case demonstrates one; the pre-B
finding and this one both earned their rejoin the same way.

Note for the record: the case's authoring-time hypothesis (a fixed pointer
window overflowed by a longer title) was **wrong**; the provenance keeps it
beside the actual mechanism, per the instrument-vs-pipeline discipline the
held-out triages established.

## Verification

Both cases red before the fix (fast 29/32 at the red commit), green after;
full suite 32/32 = 1.000 with the gs-2002 debt unchanged, so the `_sentences`
change flipped no existing IBR classification (the ADR-011 regression concern,
re-checked). Invariant 10/10.
