# 023 — D11: the model tier ships, and four things the spec said that the measurements changed (2026-08-26)

ADR-020 ruled an LLM fallback NOT JUSTIFIED on the 2026-08-19 corpus. The
2026-08-24 demo and D8's `low_item_coverage` are the new data that reopen it,
and the D11 row asked for a fast-slow ladder with a vision rung in the middle,
routing provenance in the envelope and the inspector, and success defined on
held-out. Ruling:
[ADR-036](../specs/decisions/ADR-036-tiered-escalation.md).

The owner's framing for this pass was explicit and is what made it possible to
finish anything: **build everything including the real client, make no live
call, leave the held-out exam UNRUN, and never fabricate a result to make the
column look full.** Four decisions came out of holding that line.

## The prompt decisions that mattered

- **"The D8 trigger" is two codes with opposite semantics, and picking the
  wrong one costs 60× more money to fix a class nobody agrees is broken.**
  The row says "when the D8 item-level signal fires … the document escalates".
  Taken literally that is `item_span_near_empty`, which fires on 9 of 28 real
  dev filings — Chevron, JPMorgan, GE, Exxon, Coca-Cola, NVIDIA and three
  more — i.e. a 28% escalation rate against a row that also demands the rate
  stay "near zero so the default cost stays $0". Those two sentences cannot
  both be satisfied, and the tie-break came from D8's own ADR: §c already
  ruled that one pointer item is a fact about that item and not a verdict on
  the document. So the router escalates on `low_item_coverage` (1 of 43, 0 of
  28 real) and uses the item-level code only to say WHICH items to ask about
  once something else has escalated. ADR-036 §d4 publishes the price of the
  road not taken — an estimated $3.4 per dev sweep versus $0.056 — because
  the number is the argument, and because D9's falsifier may yet reopen it.

- **Re-derive, do not cite — and report the disagreement you find.** The row
  asked for trigger precision/recall "re-derived rather than cited". Doing
  that turned up two things a citation would have carried forward silently.
  First, ADR-034 §e2's stated reason for declining the A2 class ("the D8
  trigger is measured silent on all five filings") is **false as written**:
  the item-level code fires on four of the five. The ruling survives, but its
  reason had to be replaced with a weaker and more honest one, in the open
  (§c3). Second, ADR-035 §b1 describes `tgt-2002` item 1 — the upper edge of
  the band that fixed `SPAN_FLOOR` — as "real Business prose"; read in full it
  is a hybrid, a 530-character incorporation-by-reference list followed by
  1,560 characters of genuine Item 1 content. That moves recall between
  17/17 and 17/18 depending on how one adjudicates a single span, so **both
  figures are published** rather than the flattering one. The instrument
  prints every firing span in full for exactly this reason: a reader should be
  able to disagree with the adjudication on the evidence.

- **A precision of 1.000 over a positive set of size one is not a result, and
  saying so is the deliverable.** The dev corpus contains exactly one
  document the router's trigger fires on, and it is synthetic. The number the
  ledger row asks for is therefore 1/1, and publishing it without the
  paragraph that undercuts it would be the same trust-amplification failure
  the 2026-08-24 demo is a postmortem about — a confident figure over a thin
  measurement. §c2 carries the number and the disclaimer in the same
  paragraph, and §k states plainly that the evidence which would settle it is
  the held-out run, which is UNRUN.

- **The vision rung: rule on it, do not quietly not build it.** The owner's
  own 2026-08-25 correction makes the ladder failure-class-conditional —
  vision-as-verifier where text exists, vision-as-extractor where it does not
  — so the scope question about scanned filings decides the second branch. It
  is ruled OUT, on a structural fact rather than a preference: a text-less
  input dies at `normalization_collapse` **before any item exists**, so the
  trigger cannot fire and admitting the class means turning a refusal into a
  trigger, which is unbounded and adversary-controlled. That kills
  vision-as-extractor. For vision-as-verifier the argument is weaker and is
  stated as weaker: a rendered page cannot name a character offset, which is
  what the rung must return. And then the part that a reader should trust
  least about the ruling, written into it: **there is no stdlib HTML renderer,
  a headless browser is a new dependency CI forbids, and that constraint would
  have blocked the rung whichever way the principle went.** Recording the
  constraint next to the principle is the difference between a ruling and a
  rationalisation. The interviewer-facing claim ("cost-proportionate
  escalation with visual backing") is therefore delivered by half, and the
  debt row says so in those words.

- **Never trust the model's answer — make the deterministic layers the
  gatekeeper.** The single most important line of code in this milestone is
  `escalate.verify`: a rung returns offsets, and those offsets are re-derived
  against bounds, `SPAN_FLOOR`, INV-S1 ordering and a `SIM_FLOOR` heading
  match before anything moves. A model can therefore only move a span to
  somewhere the deterministic segmenter would itself have accepted. This is
  also the part most likely to be wrong: if `SIM_FLOOR` proves too strict the
  ladder is an expensive no-op, that failure is invisible without a
  credential, and it is why every rejection reason is published in the routing
  record rather than counted.

- **Refuse loudly, and make the refusal a case.** With no `ANTHROPIC_API_KEY`
  the tier raises before a socket is opened, the routing record carries
  `outcome: "unavailable"` with the message verbatim, and a doc-level
  `escalation_unavailable` warning appears. `escalation-no-credential` pins
  all of it — including the things that must NOT happen: no invented item, no
  cost reported, no quiet fallback to the deterministic answer. The eval
  adapter strips the credential from the environment for every sec10k case, so
  the `fast` suite makes zero paid calls by construction rather than by
  convention, and the case behaves identically on a machine that has a key.

## What this pass did not settle

The live half, entirely: no call has been made, every dollar figure is an
estimate from a 4-chars-per-token proxy, `verify` has never met a real answer,
and the held-out exam is unspent. ADR-036 §k is the list, and §l is what would
falsify each ruling. That column is empty on purpose and must not be read as
full.

## Assumption → Eval contradiction → Correction

- **Assumed:** "the D8 trigger" names one signal, so routing on it is a matter
  of wiring, and ADR-034 §e2's "measured silent on all five A2 filings" could
  be carried forward as established.
- **Eval said:** `tasks/reviews/d11_trigger_scan.py` over all 43 dev filings —
  `item_span_near_empty` fires on `cvx-2015`(7,8), `jpm-2024`(7,8),
  `ge-1994`(8) and `spatz-2014`(8), four of the five A2 filings, at a 27.9%
  document rate; `low_item_coverage` fires on 1 of 43 and 0 of 28 real
  filings. Two codes, opposite escalation semantics, a 60× cost gap between
  them.
- **Corrected:** `escalate.TRIGGER_CODES` is `("low_item_coverage",)` with the
  measurement in the comment beside it; ADR-036 §c3 records D9's falsifier as
  TRIPPED and replaces its stated reason with a weaker, true one; the price of
  the wider trigger is published in §d4 so the decision can be reversed on
  evidence rather than re-argued.

- **Assumed:** the near-miss band above `SPAN_FLOOR` was empty, per ADR-035
  §b1's description of `tgt-2002` item 1 as "real Business prose".
- **Eval said:** the scan prints spans in full, and that one opens with ~530
  characters of incorporation-by-reference page pointers ("The first paragraph
  of Fourth Quarter Results, Page 19; …") before ~1,560 characters of genuine
  Item 1 content.
- **Corrected:** both recall figures are published (17/17 if substantive,
  17/18 if a pointer), the adjudication and its reasoning are written out in
  ADR-036 §c2, and the mis-description is a debt row rather than a silent
  threshold change — re-deriving `SPAN_FLOOR` from a (930, 2955) band would
  move eleven dev fixtures and is D8-sized work.

- **Assumed:** adding an opt-in flag is additive, so nothing else in the tree
  moves.
- **Eval said:** `ui-boilerplate-exclusion` and `ui-confidence-honesty` went
  red immediately — `check_boilerplate_plumbing` pins the EXACT expression at
  each hop of the ADR-026 wire, and three of those hops now carry `escalate`;
  the banner pin moved because the banner now also calls `routingStrip`. Then
  `ui-boilerplate-exclusion-regression` and `ui-boilerplate-wire-values` went
  red in turn, because their mutation fixtures carry the correct halves of the
  same expressions.
- **Corrected:** the pins and the three mutation fixtures were re-spelled
  together, the same move ADR-032 §S9 made for `blocks=markdown`, and ADR-036
  §g2 lists them explicitly as the one change in the diff that could hide a
  regression. `evals/snapshot.py` then confirms 0 of 43 filing documents moved
  and the held-out digest is byte-identical.

- **Assumed:** clearing the credential inside the adapter's first
  `extract_items` call is enough to keep the suites at $0.
- **Eval said:** `escalation_invariant`, `deterministic` and
  `offsets_invariant_under_exclusion` each re-run the pipeline from inside the
  check loop, which sits outside that scope.
- **Corrected:** the whole of `run_case` runs inside `_no_credential()`, so a
  case cannot spend money on its second run of a file either.
