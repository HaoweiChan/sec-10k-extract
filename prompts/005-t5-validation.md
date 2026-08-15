# 005 — T5: measuring a validator battery instead of asserting one

## Purpose

T5 built layers 8–9 — the label-free validators that are supposed to catch
extractions that are wrong without looking broken. Curated per hard rule 6
because the outcome is mostly *negative* results: half the proposed battery
does not survive contact with real filings, and the single strongest validator
turned out to be incapable of firing.

## The prompt

> continue on task 5

Scope from `milestones.md`: "the layer-8 **label-free validator battery** …
with priors and thresholds measured from eval-set distributions, ADR-recorded
— no pre-data numbers."

## The constraint that made this a real test

Two committed cases pull in opposite directions:

- `nvda-2024-shallow` demands `doc_status == "success"` **exactly**, and
  `success` requires zero warnings. Every validator must be silent on NVDA.
- `jpm-2024-structure` requires `success_with_warning` or `ambiguous` — JPM
  must produce at least one warning.

A battery that fires on everything satisfies JPM and fails NVDA; one that fires
on nothing does the reverse. Both were written at T2, before any validator
existed. They turned out to be a sensitivity/specificity test the eval set had
been holding in reserve.

## What measurement did to the design

Four of the eight proposed validators are false-positive generators:

| Rejected prior | Measured reality |
|---|---|
| Item 8 is the longest item | false in 6 of 13 fixtures — and it fires on NVDA |
| Item 1A ≫ Item 1B | inverts for smaller reporting companies (Premier Pacific: 0.9) |
| Spans end at sentence punctuation | fires on 10 of 18 AAPL items — page furniture rides at span ends by ADR-003's own policy |
| Part-region consistency | fires on 7 of 13 fixtures, 14× on JPM: `Part I` appears there 25× as a running page header |

The last one is the same trap as T4's bare `Item 8` headers, one level up: page
furniture defeats "the last structural marker before this item" just as it
defeated "this line names an item". Recording the rejections with their rates
matters more than the four that shipped — a validator that cries wolf is a
defect (failure-taxonomy F7), and the honest artifact is the measurement, not
the intention.

## Assumption → Eval contradiction → Correction

- Assumed: the eval set passing 20/20 at T4 meant the extractions were right.
- Eval said: nothing bounds JPM's Item 15. Its span is 1,010,422 chars — 83% of
  the document — because JPM puts its entire financial appendix *after* the
  exhibit index, and the last item runs to the signature block. Every case
  passed while a million characters were misattributed.
- Corrected: `last_item_dominates` (>50%; JPM 83.3%, next highest 18.9%) now
  pushes that filing to `ambiguous`. Per ADR-004 the span itself is left alone
  — the extractor reports what the filing labels and surfaces the unlabelled
  region — but it is no longer silent.

- Assumed: the TOC manifest cross-check was working, just never needed.
- Eval said: it had **never fired on any fixture**, and building a case for it
  showed it *could not* fire. The manifest was assembled from TOC entries whose
  code recurs later in the document — so the one item listed in the contents
  and never headed, which is the entire mismatch being hunted, was filtered out
  before the comparison ran.
- Corrected: `_toc_runs` now separates its two uses — drop only recurring
  entries (or the run deletes the first real heading), report every code in the
  run as the manifest. `malformed-html` immediately started catching its
  corruption-destroyed Item 1A heading as well.

- Assumed: writing warnings was enough to have tested them.
- Eval said: the check vocabulary could only assert warnings *absent*
  (`warning_absent`, added at T3). A validator that silently never fires was
  indistinguishable from one that works.
- Corrected: `warning_present`, plus `heading-unnumbered` — NVDA with seven
  characters (`Item 8.`) removed from one heading. Nothing is corrupt, 22 of 23
  items still extract correctly, and only the filing's own contents page
  reveals the gap. That is the silent-failure shape the whole battery exists
  for.

## What is deliberately still weak

Confidence is evidence-derived but nearly binary: 224 of 283 items sit at 0.95,
and JPM's Item 15 keeps 0.8 despite being the most wrong span in the set. The
numbers rank items sensibly and are recomputable from `evidence{}`, but they
are not probabilities. Calibration against measured per-bucket accuracy stays
the A-level item — claiming it now would be exactly the fake precision the
architecture doc warns against.

## Cost

Zero LLM calls, zero dollars. Whole 21-case suite: ~3.5 s.
