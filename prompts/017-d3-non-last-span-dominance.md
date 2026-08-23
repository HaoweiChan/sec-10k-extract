# 017 — D3: the validator the freeze deferred, and whether dominance escalates (2026-08-23)

ADR-019 §d retired the span-coverage debt row as mis-specified in both halves
and named its successor — "a non-last span dominating the document, plus the
escalation-policy question" — as the real candidate for the first post-freeze
exception, not built. The D3 row promoted it with three demands written into
the row: measure the non-last-span fraction over every committed fixture,
pick the threshold from the measured band and pin both edges, and RULE
whether any single-span dominance escalates `doc_status`. Ruling:
[ADR-030](../specs/decisions/ADR-030-non-last-span-dominance.md). The
"NOT JUSTIFIED" outcome (ADR-020's pattern) was explicitly allowed if the
corpus contradicted a validator; it did not, but the margin it left is the
thinnest in the battery and is published as such.

## The prompt decisions that mattered

- **Measure before designing, and let the measurement pick the shape.** The
  obvious design — apply `LAST_ITEM_MAX` (0.50) to every span — was ruled
  out by the first table: jnj-2016's Item 8 is 53.4% of its document, it is
  the audited financial statements bounded by the filer's own headings, and
  its case asserts `success`. Seven more real filings sit between 0.41 and
  0.53. The non-last distribution is simply different from the last-span one
  (legitimate maximum 0.5336 vs 0.1892), which is why there are two
  constants and not one, and why `last_item_dominates` is kept rather than
  generalized.

- **Reject the cleverer signals with numbers, not taste.** The orchestrator
  asked whether "dominance relative to the next-largest span" or an
  absolute-plus-relative rule would buy a wider band. Measured: the ratio is
  5.15 on the one defective fixture and 5.6–7.4 on legitimate pointer-heavy
  filings (wfc-2008, cvx-2015, mrk-1995) — no separation; the two-parameter
  rule fires on exactly one synthetic point and has no band for its second
  parameter, which is the `vacuous_coverage` finding ADR-027 §c closed.
  Both are in ADR-030 §b2 as ADR-008-style "rejected after measuring".

- **The committed corpus pins the band; a new fixture proves the policy.**
  items-stripped (0.5723) was already in the tree and already `ambiguous`
  through `expected_items_mostly_missing`, so it can pin the upper edge but
  cannot prove that `item_dominates` escalates on its own (ADR-016 §1:
  asserting the consequence is not asserting the cause). The new fixture is
  built to close every other route: wmt-2010 with four item labels deleted —
  no contents page to mismatch, 4 of 20 missing (0.20, under `MISSING_MAX`,
  the same fraction axp-2008 must not escalate on), last span 9.6% — and the
  case pins all three absences. Four labels, not one, because the sweep
  (0.5174 / 0.5179 / 0.5477 / 0.6387) says one is not enough; every number
  in the sweep is in the provenance.

- **Escalate, and say what it costs.** The policy ruling follows ADR-013's
  cost asymmetry and the measured false-positive set (empty on 31 real
  filings), and it says the other half out loud: 1.03× over the worst real
  filing, an unseen 56% Item 8 reads `ambiguous` with every item capped at
  0.75. That is a Debt row (Origin: D3), not a footnote, with the condition
  that would force a re-argument (a legitimate held-out span above 0.55).

- **Held-out is read, not used.** The five held-out fractions were printed by
  the same instrument run and are reported in their own table; no value
  enters the threshold's derivation, `mrk-1995`'s 0.5274 is recorded and not
  adjudicated (reading the filing would burn it), and the ADR says exactly
  that rather than "the held-out set agrees".

- **A met revisit condition is reported, not absorbed.** ADR-020 §e condition
  2 names this exact successor as a trigger that reopens T12 "with its own
  ADR". Shipping the signal meets it in mechanism (and is silent on the two
  rows it names, measured). That is recorded in ADR-030 §g and filed as debt;
  it is not ruled on here, because ADR-020 says it gets its own ADR.

## Assumption → Eval contradiction → Correction

- **Assumed:** the orchestrator's row text — "ADR-015 §0's Intel failure
  (item 4 at 81%, not last)".
- **Eval said:** ADR-015 §0 and ADR-019 §d both attribute the 81% item 4 to
  **Target** FY2002 (`tgt-2002`, 26,861 of 33,196 chars); Intel's failure was
  the 0.47%-coverage stub collapse that `unattributed_content` fired on.
- **Corrected:** the D3 row's Contents cell (first committed verbatim, as
  asked) is corrected in the same PR with the correction named in its Status
  cell; ADR-030 §g lists "would have caught Intel" under NOT claimed.

- **Assumed:** the first commit could be "ADR + the red case", the second the
  fix.
- **Eval said:** the pre-commit gate runs the fast suite on the working tree
  and blocks any red scored case; a red-at-main case cannot be committed
  ahead of its fix without `--no-verify`, which hard rule 5 forbids.
- **Corrected:** commit 1 is the ledger row only; the red-at-main proof is
  the runner line at `origin/main dc3f8f0`, pasted in the ADR (§f), the case
  provenance and the ledger, reproducible by running the case file against
  main's `src/`.

- **Assumed:** a new threshold in the repo's usual 0.50 neighbourhood would
  leave the corpus's real filings silent.
- **Eval said:** at 0.50 `jnj-bare-headings` goes RED (`doc_status 'ambiguous'
  not in ['success', 'success_with_warning']`, item 13 capped 0.85 → 0.75) —
  the 0.53 mutation in ADR-030 §f is that run.
- **Corrected:** `ITEM_MAX = 0.55`, the midpoint of the band the corpus
  actually has, pinned at both edges so the green range IS the measured band;
  the 1.03× margin stated at the constant and carried as debt.
