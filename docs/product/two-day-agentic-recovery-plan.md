# Two-day agentic recovery plan

Date: 2026-08-29

Status: proposed. This document schedules work; an ADR and executable cases
must bind any contract or architecture change before implementation.

## Outcome

Use the remaining two days to prove one thing the current system has not yet
proved: a bounded model-driven loop can repair or supplement a difficult real
10-K, survive deterministic verification, and publish the result without
claiming success when it cannot finish.

The target is not another validator census. Deterministic code remains the
sensor and trust boundary; the model explores an unfamiliar filing between
those two boundaries.

Success by the end of day 2 means:

1. at least one real dev-side filing gains non-empty, verified primary repair
   or alternative evidence through the model loop;
2. one invalid proposal is rejected and causes a bounded re-plan or an honest
   abstention;
3. the inspector shows the actions, verifier feedback, final decision, and
   measured cost from the real routing record;
4. a clean filing remains on the deterministic path with zero model calls;
5. invariant and fast pass at 100% with zero paid calls and no baseline move.

## Starting evidence

- D11 shipped a two-rung text escalation ladder, but its real exam resolved no
  item after $4.023452 of measured calls. Transport, cost reporting, and
  abstention worked; recovery did not.
- D21, merged in PR #78, classifies failure shapes, supports verified
  alternative regions, publishes five visible stages, and can use live vision
  only to confirm or reject already text-verified evidence.
- The text rung still asks only for `[start,end] | null`, although the
  alternative route accepts `{"regions":[...]}`. A model following the prompt
  cannot produce the alternative shape.
- The current stages describe a fixed ladder after it runs. Verifier rejection
  does not return to the model as an observation for another bounded attempt.
- The web projection still drops the contract's explicit `review_required`
  field and relies on `evidence.warnings` for the UI.
- PR #75 contains a narrow, measured fix for AIG's long-span running-header
  silent loss but now conflicts with main. It is a known defect to land, not a
  reason to open another deterministic exploration track.

## Scope

### Build

- One compact filing outline: item statuses and spans, warnings, coverage,
  candidate headings, cross-reference annotations, and the largest unclaimed
  regions. It contains locations and short samples, not the whole filing.
- One existing-model action loop with at most three model turns. Reuse
  `src/sec10k/llm.py` caching and `Budget`; add no agent framework or model.
- The minimum action vocabulary:
  - `search`: find literal text in `normalized_text`;
  - `read_window`: inspect a bounded range;
  - `propose_primary_span`: submit one replacement span;
  - `propose_alternative_regions`: submit item-scoped evidence regions;
  - `finish`: accept verified survivors or abstain.
- Existing deterministic verifiers remain the only publication boundary.
  Rejection reasons become the next turn's observation; the model cannot
  waive bounds, provenance, item scope, or INV-S1.
- One end-to-end cached replay through `route()`, not helper-only tests.

```text
deterministic extraction
        |
        v
honesty signals -> compact outline -> agent action -> deterministic verifier
                                      ^                    |
                                      +---- rejection -----+
                                                    max 3 turns
```

### Do not build

- no new issuer, title, word-count, or page-number heuristic except landing
  the already measured D18 fix;
- no XBRL numeric cross-check, raw-to-normalized map, full-page renderer, OCR,
  scanned-filing support, new filing form, agent framework, or new model;
- no unconditional model pass over clean filings;
- no claim that vision extracted text: D21 vision stays a verifier only.

## Routing decision to bind in the ADR

The loop starts from existing honesty evidence, not from a new collection of
corner-case rules. The initial vertical slice may route an item when the
document is ambiguous or the item is `review_required`, including the existing
internal-pointer warning class. Cross-reference-index results that D20/D21
already resolve deterministically remain suppressed.

The ADR must name the exact entry predicate and measured dev firing rate before
code changes. If broadening from `low_item_coverage` to item-level warnings has
no acceptable empty band, narrow the milestone to one already adjudicated
warning class; do not tune a new content heuristic against the demo filing.

## Day 1 — make the loop real

### First 90 minutes: close known seams

1. Port or rebase PR #75's D18 fix onto current main and rerun its blast-radius
   comparison. Stop if the narrow fix no longer applies; do not redesign TOC
   filtering inside this milestone.
2. Add `review_required` to the web projection.
3. Reconcile the method/outcome enums and make `envelope_shape` bind D21's
   route, target, stage, alternative-evidence, and cost fields.

### Red-first cases

Before the resolver implementation, add and observe failures for:

1. a cached model response using the documented alternative-region schema
   through the real `route()` parser;
2. a mixed document with missing and bad-primary targets, proving neither
   target class disappears during planning;
3. a plausible but wrong first proposal followed by verifier rejection and a
   valid second proposal;
4. exhaustion after three turns producing `ambiguous` / `review_required`, not
   a fabricated resolution;
5. `/api/extract` preserving `review_required`;
6. contract checks rejecting an unknown method, outcome, route, stage, or
   malformed alternative region.

### Implement

Update the prompt to describe the same action schema the parser accepts. Feed
only the outline and requested windows to the model. Keep one loop counter,
one action parser, and the existing verifier functions; a framework, planner
class hierarchy, and separate memory layer are out of scope.

## Day 2 — prove recovery, then deploy

1. Run the loop from cache on all new cases; invariant and fast must remain
   offline and $0.
2. Use one adjudicated real dev filing as the positive proof. The preferred
   candidate is the CVX internal-pointer class because its real destination
   text is already known to sit outside the published primary spans; the model
   must locate evidence, while the verifier decides whether it can publish.
3. Use a separate real or adversarial case as the negative proof: a proposal
   is rejected and the loop abstains without changing primary output.
4. Make at most one live evidence run after cached cases are green. The loop is
   capped at three model calls per filing, remains inside the existing shared
   call/token/USD budget, and records actual calls, tokens, dollars, latency,
   cache state, and verifier decisions. No estimate substitutes for a run.
5. Run a fresh cold review focused on silent non-entry, prompt/schema drift,
   verifier bypass, and cost escape. Every in-scope finding becomes a red case
   before repair.
6. Run invariant, fast, the targeted full/cached cases, and one browser walk.
   Deploy once, verify `/api/meta` reports the merged SHA, then execute a clean
   filing and the positive/negative agentic cases through the deployed path.

## Acceptance and stop rules

The milestone is complete only when all of these are recorded:

- one real non-synthetic filing has at least one model-proposed result accepted
  by the deterministic verifier;
- the accepted text reproduces from `normalized_text` offsets and the previous
  deterministic answer remains in provenance;
- one rejected proposal is visible as an observation before re-plan/abstain;
- no unresolved item is reported as clean success;
- the three-turn cap, shared budget, cache replay, and zero-paid fast/invariant
  paths are executable checks;
- D18's known AIG silent loss is either merged and green or explicitly blocked
  with its conflicting evidence preserved;
- deployed build identity and the two agentic runs are recorded.

Stop rather than broaden scope when any of these occurs:

- no real filing produces a verified resolution after the one allowed live
  run: report the negative result and keep abstention;
- verifier feedback cannot be expressed without weakening an invariant;
- a fourth model turn, new model, OCR, renderer, or issuer-specific rule seems
  necessary;
- a second live run would only repeat an already cached failure.

