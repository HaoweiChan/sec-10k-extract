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
  road not taken. (Both figures in this bullet were hand-typed and both were later
  found wrong — $3.4 and $0.056 are withdrawn; the derived pair is **$4.5656
  versus $0.0488**, from `tasks/reviews/d11_sweep_cost.py`. Round 3's entry
  below is about exactly this.) The number is published because
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

## Round 2 (PR #58 review repair, 2026-08-27) — three more corrections

- **Assumed:** `verify`'s guards were about OFFSETS, so the item they name did
  not need checking.
- **Eval said:** the reviewer fed it a proposal naming a `missing` item. It was
  accepted with an empty rejection list; `apply` wrote `start`/`end` onto an
  item the contract says has none; and because `meta.coverage` sums every item
  with a non-null `start`, that one malformed item moved a document's coverage
  from **0.0030 to 0.6142** — the exact number the D8 trigger thresholds on.
  `c-2025`, one of the two exam filings, is 21 `missing` + 2 `omitted`, so the
  first live run would have hit it.
- **Corrected:** `verify` refuses any code whose status is not span-bearing,
  AND `envelope_shape` now asserts the contract's null-span rule in both
  directions so the guard binds every producer rather than the one that broke
  it. The honest footnote: on the real fixture the pre-fix hole was
  *accidentally* covered by the neighbouring title-similarity check, so the
  case's red is weaker than the unit repro — both the case provenance and the
  red record say so instead of presenting the fixture red as the proof.

- **Assumed:** publishing "all-or-nothing" in an ADR and a docstring made it
  true, and `_demo` covered it.
- **Eval said:** the loop returned the survivors of a mixed proposal. Every
  mixed proposal `_demo` happened to construct tripped the ordering check as a
  *side effect*, so the property had never once been watched — a test that
  passes for the wrong reason is indistinguishable from one that passes.
- **Corrected:** the code was changed to match the claim (the ADR's own stated
  rationale is right), the ADR carries a marked correction saying the paragraph
  was false as published, and both the new `_demo` block and the eval case use
  a mixed proposal that does *not* trip ordering.

- **Assumed:** naming two `_demo`s under an ADR's **Enforced by** line made
  them enforcement.
- **Eval said:** replacing every trust-boundary guard in `verify` and both
  `Budget` ceilings with `if False:` left invariant 75/75 and fast 138/138
  fully green. This repo had already ruled on exactly this at PR #25 R1 — "a
  self-check no job runs is a claim, not enforcement" — six lines above where
  the two new lines now sit in `ci.yml`.
- **Corrected:** both self-checks wired into CI's unit-tests job, and the
  mutation re-run afterwards now turns *both* the eval gate and that job red.
  The general lesson, which is the one worth keeping: an "Enforced by" line is
  a claim about the repo's wiring, and it needs checking against the wiring.

- **Assumed (owner instruction, not a defect):** the provider was Anthropic's
  Messages API and prices could live in a table in the code.
- **Corrected:** OpenRouter, stdlib client unchanged; and prices are no longer
  written down at all. `usd()` reads the committed dated catalogue record and
  **raises** on a slug it does not carry — which it did, loudly, the moment the
  rung constants still named the old model ids. A price that cannot go stale
  silently is worth more than a price that is convenient to read.

## Round 3 (PR #58 round-2 repair, 2026-08-27) — two corrections and a rule

- **Assumed:** the §d4 sweep figure was arithmetic, so recomputing it carefully
  by hand would fix it.
- **Eval said:** it was wrong again, a second consecutive round. The cost model
  was never the problem — it reproduces every other published figure to the
  digit. The **character counts** had been retyped into the ADR, and five of
  twelve were wrong; `reac-2015` by 3.3×.
- **Corrected:** `tasks/reviews/d11_sweep_cost.py` derives every §d figure from
  the same census `d11_trigger_scan.py` produces, and its committed output is
  pasted into the ADR. The rule worth keeping: **a number that carries an
  argument must be derived by a committed script, not retyped.** §c1's figures
  had a script from the start and were never wrong; §d's did not and were wrong
  twice. That is the whole difference.

- **Assumed:** locks that were verified to WORK were locks that were protected.
- **Eval said:** setting `ESCALATION_ENABLED = True` and building the process
  `Budget` with an infinite ceiling left invariant 76/76, fast 139/139 and both
  CI self-checks green — on the code that guards a credential about to go onto
  a public, unauthenticated host. This is the R3 defect, one round later, on
  the money.
- **Corrected:** an AST check (`escalation_locks`) that reads the *shape* of
  the arming comparison and the `Budget` construction, proven both ways: the
  reviewer's mutations now take the gate to 77/78, the real file returns clean,
  and the mutation fixture returns exactly five. The generalisation: *verifying
  a guard behaves correctly says nothing about whether the guard can be
  removed*, and those are separate tests.

- **Assumed:** rung 2 "sees the whole document" was a design statement.
- **Eval said:** on the deployment the document is attacker-supplied and capped
  only by a 25 MB upload limit, so one uncapped call at $5/MTok roughly doubled
  the configured ceiling — a ceiling checked only against what has *already*
  been spent.
- **Corrected:** rung 2's input is capped at the largest committed dev filing
  rounded up, so no published figure moves and one call's price is bounded on
  arbitrary input; and §h2 states the effective ceiling as MAX_USD **plus one
  call**, because that is what it has always been.

## Round 4 (PR #58 round-3 repair, 2026-08-27) — the pattern the breaker fired on

The circuit breaker fired on a structural observation, not on any one defect:
**each round's new safety mechanism was itself unbound.** R3 fixed
"trust-boundary guards enforced by nothing". Round 2 found the R6 money locks
enforced by nothing. Round 3 found R9's own check evadable and R12's cap
enforced by nothing — both introduced *inside* the commit that fixed the
previous level.

- **Assumed:** writing a `_demo` assertion next to a constant binds the
  constant.
- **Eval said:** `assert len(big[:EXTRACT_WINDOW]) == EXTRACT_WINDOW` on a
  local string is true for *every* value of the constant and never reaches
  `route`. Reverting rung 2's slice left invariant 78/78, fast 141/141 and both
  self-checks green — under a comment that read "a cap nothing slices by is a
  comment".
- **Corrected:** `_demo` drives `route` over an over-long document with a
  stubbed transport and asserts what the tier record actually reports. The
  general rule, which is the whole lesson of four rounds: **an assertion binds
  the property only if mutating the property turns it red — so mutate it, watch
  the red, restore, watch the green, and put the transcript in the artifact.**
  A check whose red was never watched is indistinguishable from no check.

- **Assumed:** pinning an AST *shape* pins the *semantics*.
- **Eval said:** `!= "0"` is still an `ast.Compare` over the right env var, and
  it evaluates True with the variable **unset** — which is the state every host
  is in until someone sets it. The check returned `[]`.
- **Corrected:** the operator and the comparand are the property, so both are
  pinned, and a second fixture pins the *evasion* rather than the *removal*.
  Shape-vs-semantics is the same gap as text-pin-vs-behaviour that
  `check_confidence_honesty`'s docstring has warned about since D7; it recurs
  because a shape check is so nearly right.

- **Assumed:** a sweep over "the documents I edited" is a sweep.
- **Eval said:** the stale figures survived in the ADR's own **Ruling header**,
  its ladder **diagram**, **INDEX.md** — a line the previous repair had edited
  — and this file. Those four are exactly where a diff-shaped sweep does not
  look.
- **Corrected:** swept them explicitly, and found two more counts that *this*
  round had itself invalidated. Sweeping the diff is not sweeping the claim.
