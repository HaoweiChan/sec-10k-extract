# ADR-018 — T10: confidence calibration — the measurement, and what it licenses

Date: 2026-08-18. Status: accepted. Implements T10/A2 (layer 9,
`src/sec10k/validate.py`). Instrument and measured table landed first in
`d3a28df` (metric 8 v2 + report `20260818-123114-all.json`), per T10's gate:
the table exists in history before any remap does.

## The measurement

Per distinct confidence value, over the T9-expanded set (44 scored cases over
36 fixture dirs — 28 EDGAR filings + 8 self-created, per
`evals/fixtures/README`) plus the enumerated debt channel
(`ba-2003-asterisk-ibr`, unscored — and as of this ADR's audit fixes, loaded on
*every* suite run including the pre-commit gate, which the earlier draft
claimed before it was true):

| value | scored targeted | scored failed | debt targeted | debt failed | what lives at this value |
|---|---|---|---|---|---|
| 0.95 | 162 | 0 | 1 | **1** | extracted, strict title match, no item warning |
| 0.85 | 66 | 0 | 0 | 0 | incorporated_by_reference |
| 0.80 | 8 | 0 | 0 | 0 | omitted; or strict extracted carrying one warning |
| 0.75 | 14 | 0 | 1 | **1** | extracted, weak title match |
| 0.65 | 1 | 0 | 0 | 0 | weak title match plus one warning |
| 0.40 | 2 | 0 | 0 | 0 | missing — **every** missing item in the population |
| 0.55 | 0 | — | 0 | — | `BASE_MISSING` as published — **no item ever carries it** (authored row: the instrument emits only observed values, so a zero-count row cannot come from it) |

Two findings, neither visible before the instrument:

1. **The measured overconfidence is not a scale defect.** The debt failures are
   ba-2003 items 11 (`extracted` at 0.95 over 34 chars) and 13 (`extracted` at
   0.75 over 59 chars) in a document reporting plain `success` — wrongness at
   the top *and* middle of the scale. The defect is the *status* (`extracted`
   over an empty body whose IBR pointer lives in another item's span, ADR-005
   rule 1); no constant move fixes an item that should not be `extracted` at
   all. Ruled debt (cross-item resolution is a capability, TODO debt table);
   the *rate* of this shape is T11's charter.
2. **`BASE_MISSING = 0.55` is a phantom.** Every `missing` item carries its own
   `expected_item_missing` warning, which is item-targeted, so every one lands
   at 0.55 − 0.15 = 0.40. The only warning a missing item can ever catch is the
   one that restates its own status (all other item-targeted validators require
   a span). Two constants encode one value, and the published scale claims a
   number that cannot occur.

## What the table cannot license

- **Remap-to-empirical is rejected.** Scored pass rates are upper bounds — the
  pre-commit gate forces every targeted scored item green, so 1.0 rows measure
  the gate, not accuracy. Mapping through them would raise 0.40 (n=2) and 0.75
  (n=14) toward 1.0 on gate-biased single-digit samples and flatten the scale's
  ordering — fake precision of exactly the kind ADR-008 banned ("coarse and
  clamped").
- **No magnitude moves.** Nothing in the *current-code* measurement shows a
  scored value overstating. The historical record is not silent — committed
  held-out reports carry scored failures at 0.95 and 0.85 (`20260816-225101`,
  `20260817-035222`) — but each is disposed on the record as a since-fixed
  status defect (ADR-017's pointer windows) or an instrument error (H3's bad
  length floors), consistent with finding 1: the scale reported the evidence it
  was handed; the evidence was wrong. The demonstrated overstatements are
  status defects (finding 1). Raising the
  low values is forbidden by the bias direction; lowering 0.95 by the debt
  evidence (1 enumerated failure, not a sample) would be tuning a constant to
  one known bug. The ceiling stays 0.95 — 1.0 remains unclaimable.

## What it licenses (shipped with this ADR)

1. **Collapse the phantom.** `BASE_MISSING` 0.55 → 0.40, and
   `expected_item_missing` is excluded from the warning penalty — it restates
   the status that already set the base, and the double-count is what
   manufactured the phantom. Net behavioral change on all 31 fixtures: zero
   (every missing item read 0.40 before and after). Watched red at its own
   layer per ADR-016's precedent: the new `_demo` assertion
   `score(missing, [its own expected_item_missing warning]) == BASE_MISSING`
   reads 0.40 ≠ 0.55 against the old constants. Stronger than the empirical
   check, the audit proved the equivalence algebraically: old
   0.55 − 0.15·n ≡ new 0.40 − 0.15·(n−1) for every n ≥ 1, and n ≥ 1 always
   holds because `extract_items` emits the warning unconditionally — net-zero
   for **all** inputs, not just the committed fixtures.
2. **Delete the shadow scale.** `extract.py`'s `CONF_STRICT/CONF_WEAK_TITLE/
   CONF_NON_EXTRACTED` (0.9/0.7/0.8) are dead: layer 9 rescores every item
   unconditionally, so those values never survive to the envelope, and they
   disagree with the real constants (0.95/0.75/0.80). One scale, one owner
   (`validate.py`). The stale "calibration is T5" comment goes with them.
3. **Publish the semantics.** The scale is an ordinal evidence encoding —
   status tier, title-match quality, warning count — not a probability. The
   per-value meaning column above is the published meaning; the contract's
   confidence bullet is updated to say the scale is now *measured* (metric 8
   v2, upper bounds + enumerated debt) rather than "uncalibrated and
   unmeasurable".
4. **Pin it.** A `confidence: 0.40` check lands on an already-targeted missing
   item, so the collapsed constant is case-pinned like the others (ADR-010).
   Disclosed plainly: because the collapse is net-zero, this pin passes under
   the old constants too — it guards *future* drift of the value, and cannot
   discriminate a wholesale ADR-018 revert. The only revert detector is the
   `_demo` assertion above; that asymmetry is inherent to pinning a net-zero
   change, not an authoring choice.

## Consequences

- Envelope change, two fields on missing items only: `evidence.confidence_base`
  now reads 0.40, and `evidence.warnings` no longer lists
  `expected_item_missing` — that list records the hits that moved the score,
  and the restating warning no longer does (the top-level `warnings` array
  still carries it, unchanged). `extractor_version` bumps to `0.6.0-t10` so
  audits can segment.
- The "before" table (four buckets, all 1.0, structurally unable to fail) and
  this "after" table are published side by side in `docs/analysis-report.md`
  v2, per T10's validation gate.
- T11 inherits the real question this measurement isolated: the *rate* of
  confident-wrong items, sampled rather than enumerated — ba-2003's
  trivial-body shape is its first target. The span-coverage validator remains
  the named post-freeze candidate for catching it label-free.

## Audit dispositions (2026-08-18, cold-reviewer + extraction-auditor)

Both agents ran against the uncommitted change; every finding below is either
fixed in this batch or ruled with a reason. Corrections the audits forced on
this document's own prose are applied in place above (the fixture denominator,
the authored 0.55 row, the rescoped "nothing measured" sentence, the pin
disclosure, the debt-gate claim).

1. **`keyword_fingerprint` was structurally dead for items 1A and 3** (cold
   review): the judged span opens with its own heading, and "Risk Factors" /
   "Legal Proceedings" satisfy their own fingerprints, for any content at all.
   Fixed — the fingerprint now judges the span minus its first line, with
   word-boundary matching (the substring form also let `"net"` match
   "internet"). No committed fixture can prove the 1A branch red — the
   spans-transposed probe showed transposed *financial* prose still carries
   "risk" and "could" as whole words — so the fix is proved red→green at the
   validator's own layer (`_demo`), ADR-016's pattern, with a zero-delta check
   against the full fixture set. The finding also stands as a caution: "could"
   makes the 1A fingerprint weak on any English prose; tightening the wordlist
   is a threshold change that would need its own measured basis.
2. **A crashed case counted its declared checks as passing** in metrics 1–6
   (cold review): the runner's exception path emits no `failures` list, and the
   join read absence as green. Fixed conservatively — an errored row's declared
   checks count as failed — with a red-first self-check.
3. **Metric 8's note claimed debt unaudited items were counted in metric 6**
   (both audits, independently): false — metric 6 never reads debt rows, and
   the doc holding the measurement's only real failures was itself 12/13
   unaudited. Fixed: `debt_unaudited` is computed and published in metric 8's
   note, and the false cross-reference is gone.
4. **"Runs every run" was false** (extraction-auditor): debt cases loaded only
   under `--suite all`, so the pre-commit gate never exercised the calibration's
   sole failure channel. Fixed in `run.py`: a `debt`-suite case now loads under
   every suite (still unscored); the gate prints the `[DEBT]` line on every
   commit.
5. **Stale-report joins failed silent** (extraction-auditor, demonstrated on
   `20260817-035222`): failures are matched to *currently declared* checks by
   exact JSON, so a post-run case edit silently zeroes the `failed` column
   under a note claiming nothing fails. Fixed: `unmatched_failures` is counted
   and rendered loudly when non-zero. The structural caveat stands: a metric 8
   table is reproducible only against case files as of its run's sha.
6. **Reports could not distinguish a dirty tree** (extraction-auditor):
   `git_sha()` now appends `-dirty` when the working tree is not clean, so a
   report can no longer claim a commit it wasn't run on. The net-zero evidence
   chain for this ADR rests on the algebraic proof above, not on report pairs.
7. **Ruled, no action**: `CEIL = 0.95` cannot currently bind (max base equals
   it) — kept deliberately as the "never 1.0" guard should a base ever rise;
   metric 2 ≡ metric 1 is declared in its own note and splitting the check
   type is not T10 work.
