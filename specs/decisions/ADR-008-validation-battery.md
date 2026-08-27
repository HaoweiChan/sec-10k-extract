# ADR-008 — T5: the validator battery that survived measurement

Date: 2026-08-16. Status: accepted. Amended by: ADR-013, ADR-018, ADR-027,
ADR-030, ADR-035, ADR-039 (the last five in place — each amended figure carries its marker).
Implements layers 8-9 (`src/sec10k/validate.py`).

**Ruling**: ship six label-free validators with measured thresholds (TOC manifest, unattributed content, last-item domination, boundary hygiene, relative numeric density, keyword fingerprints) — seven since ADR-013 added `expected_items_mostly_missing` (amended 2026-08-22, ADR-027 §g; `grep -c 'warn("' src/sec10k/validate.py` → 7), eight since ADR-030 added `item_dominates` (amended 2026-08-23; the same grep → 8), ten since ADR-035 (D8) added `item_span_near_empty` and `low_item_coverage` (amended 2026-08-26; the same grep → 10), eleven since ADR-039 (D16) added `internal_pointer_unreached` (amended 2026-08-28; the same grep → 11); reject the other four proposed ("Item 8 longest", "1A ≫ 1B", "spans end at sentence punctuation", part-region consistency) as false-positive generators.
**Because**: a validator that cries wolf is a defect, not caution — each rejected check was measured to misfire on real fixtures (AAPL, Premier Pacific, JPM).
**Enforced by**: `src/sec10k/validate.py`; `evals/golden/*-structure.json` cases; `evals/adversarial/heading-unnumbered.json`

---

The architecture doc proposed eight label-free validators. Measured against
the eval-set distributions, **four discriminate and four are false-positive
generators**. Shipping a validator that cries wolf is a defect, not caution
(failure-taxonomy F7), so the four are rejected here with their measured
false-positive rates rather than quietly omitted.

## Kept, with measured thresholds

| Validator | Threshold | Measured basis |
|---|---|---|
| TOC manifest cross-check | any mismatch | the filing's own contents page vs what we resolved — no threshold to set |
| Unattributed content | > 17% | clean modern filings leave 0.7–7.6% before the first span / after the last (*amended 2026-08-22, ADR-027 §g: not "outside every item" — interior gaps are not counted, and ADR-019 §d measured them nonzero on the 7 EXEC_OFFICERS_RE fixtures, up to 9.7 points*); IBR-heavy and appendix-carrying ones leave 26.5–76.9%. Floor sits in the empty band |
| Last-item domination | > 50% | JPM 2024's Item 15 is 83.3% of the document; next highest in the set is 18.9% (Textron's exhibit list). Band midpoint |
| Non-last domination (*added 2026-08-23, ADR-030*) | > 55% | the largest non-last span of a real filing is jnj-2016's Item 8 at 53.4% (the financial statements, `success`); the smallest that must fire is items-stripped's Item 4 at 57.2%. Band midpoint; both edges pinned |
| Boundary hygiene | any | every span must open with its own heading; 0 failures across 14 fixtures, kept as a tripwire |
| Numeric density, relative | d(8) ≤ d(1A) | absolute bands overlap across filers (d(1A) 0.001–0.008 vs d(8) 0.008–0.095 — they touch), but the *ordering* holds in 9 of 9 filings where both items are substantive |
| Keyword fingerprints | no prior word present | gated to spans ≥ 5,000 chars |
| Per-item span floor, items 1/7/8 (*added 2026-08-26, ADR-035*) | < 1,500 chars | all 14 item-1/7/8 spans under 2,094 chars on the dev corpus are pointers or stubs; every span at or above it is substantive. Band (930 ko-1997 item 8, 2,094 tgt-2002 item 1), midpoint to 2 s.f.; both edges pinned. Items 1A/7A excluded — "not required for smaller reporting companies" is a complete 41-129-char answer on 6 fixtures |
| Document coverage (*added 2026-08-26, ADR-035*) | < 13% | the lowest real dev filing places 23.06% of its text in item spans (ge-1994), the synthetic stub collapse places 3.03%. Band midpoint; both edges pinned; escalating |

`SUBSTANTIVE_MIN = 5000` gates both content-shape validators. It is a judgment
call, not a measured gap — item lengths are a continuum — but the classes it
separates are not: GE 1994's Item 8 is `See index under item 14.` (86 chars)
and NVDA's is a 209-char internal pointer. Both are legitimately `extracted`
per ADR-004 shape 2, and a vocabulary test on a pointer paragraph measures
nothing.

## Rejected after measuring

- **"Item 8 is the longest item"** — false in 6 of 13 fixtures. AAPL's Item 1A
  is longer; GE, IBM and Textron incorporate their financials by reference so
  Item 8 is a stub; JPM's is a 372-char pointer. It would fire on NVDA, whose
  case demands a clean `success`.
- **"Item 1A ≫ Item 1B"** — false for smaller reporting companies. Premier
  Pacific's ratio is 0.9: as an SRC it answers Item 1A with "we are not
  required to provide" while Item 1B is boilerplate. Flagging every small
  filer is noise.
- **"Spans end at sentence punctuation"** — fires on 10 of 18 AAPL items.
  Page furniture legitimately rides at the end of a span (`Apple Inc. | 2025
  Form 10-K | 51`), which is ADR-003's deliberate policy. The validator would
  be measuring our own normalization decision.
- **Part-region consistency** — fires on 7 of 13 fixtures, 14 times on JPM
  alone. `Part I` appears 25 times in JPM as a running page header, so
  "the last PART marker before this item" resolves to furniture, not
  structure — the same trap that bare `Item 8` page headers set for candidate
  detection. It is also largely redundant: greedy ordered assignment already
  guarantees items appear in canonical order, which is what part-region
  consistency would re-derive.

## The manifest cross-check could not fire

Worth recording as a finding, not just a fix. The TOC manifest check is the
strongest claim in the architecture — "a mismatch is a strong, free warning" —
and it fired on **zero of 13 fixtures**. Building `heading-unnumbered` (NVDA
with the seven characters `Item 8.` deleted from one heading) revealed why:
the manifest was assembled from TOC entries whose code **recurs later in the
document**, so an item listed in the contents and then never headed — exactly
the mismatch being hunted — was filtered out before the comparison ran.

`_toc_runs` now separates the two uses: only recurring entries are *dropped*
as candidates (a TOC sits close enough to the body that the run swallows the
first real heading, whose code does not recur — dropping the whole run would
delete it), while the *manifest* reports every code in the run. Knock-on
effect: `malformed-html` now catches its corruption-destroyed Item 1A heading
the same way, which it previously missed.

## Escalation policy

Only `toc_manifest_mismatch` and `last_item_dominates` may push `doc_status`
to `ambiguous` (*amended 2026-08-22, ADR-027 §g: three codes since ADR-013
added `expected_items_mostly_missing` — `len(AMBIGUOUS_CODES)` → 3; amended
2026-08-23, ADR-030 §c: four since `item_dominates` joined — `len(AMBIGUOUS_CODES)`
→ 4; amended 2026-08-26, ADR-035 §d: five since `low_item_coverage` joined —
the same expression → 5*).
`unattributed_content` deliberately may not: IBM 1997 leaves
43% of its document outside every item and Textron 28%, because those filings
incorporate by reference — that shape is normal, the honest report is a
warning, and the eval set agrees (both cases require `success` or
`success_with_warning`). *(Amended 2026-08-26, ADR-035 §d: that ruling stands
and `unattributed_content` is unchanged. `low_item_coverage` is a different
measurement — what the items HOLD, not what the preamble and tail leave — at a
threshold 13%, an order of magnitude below the IBM/Textron shape this
paragraph protects: IBM places 46.92% and Textron 66.86%.)*

The architecture's third escalating validator, **dual-method boundary
agreement**, is not built. It needs TOC anchor targets (`href="#i13..."`)
resolved to offsets, and normalization deliberately discards tags — preserving
anchor offsets through the normalizer is invasive enough to deserve its own
ADR, and the manifest cross-check already captures most of the value. Recorded
as deferred, not forgotten.

## Confidence (layer 9)

Base by heading-match quality (0.95 strict title match / 0.75 weak), by status
for non-extracted items (0.85 IBR, 0.80 omitted, 0.55 missing — *amended
2026-08-22: 0.40 since ADR-018 collapsed the phantom*), minus 0.15 per
validator warning naming that item, clamped to [0.20, 0.95] (*amended
2026-08-22, ADR-027 §a: capped at 0.95, or at 0.75 when the document is
`ambiguous`; there is no floor — the 0.20 clamp was unreachable on pipeline
output and is deleted*) and rounded to two places. Every input lands in the
item's `evidence{}` — `title_similarity`, `chars`, `warnings`,
`confidence_base` — so an auditor can recompute or dispute any score.

**Known limitation, stated plainly**: the distribution is nearly binary — 224
of 283 items sit at 0.95. The scale is uncalibrated (*amended 2026-08-22: it
is measured with stated bias since ADR-018 — an ordinal evidence encoding
whose per-value table is published, not remapped; ADR-027 §h re-runs the
instrument*), so JPM's Item 15 keeps
0.8 despite being the most wrong span in the eval set (its 1,010,422-char
extent is flagged at document level, but the item-level number does not yet
reflect how wrong it is). Calibration — bucket dev + held-out items by score,
measure empirical accuracy per bucket, remap through the table — is the
A-level item the architecture already commits to. Until then these numbers
rank items sensibly and should not be read as probabilities.
