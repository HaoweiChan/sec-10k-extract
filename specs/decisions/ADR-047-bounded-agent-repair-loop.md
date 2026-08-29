# ADR-047 — bounded agent repair loop

Date: 2026-08-29. Status: accepted.

**Ruling**: when the existing internal-pointer-unreached honesty warning names an item, route a compact outline through at most three cached-or-live actions from the existing small text model. Every turn repeats immutable `target_items` and the compact item/warning outline; only the immediately preceding observation changes. Only deterministic verification may publish a primary span or alternative region; rejection becomes the next observation. Clean and cross-reference-resolved documents remain zero-call paths.
**Because**: D21 can classify and verify a fixed proposal but cannot ask again after rejection; its prompt also cannot emit its own alternative-region shape. The internal-pointer class is an already-adjudicated real dev signal, not a new issuer or content heuristic.
**Enforced by**: d22-agent-loop.json, envelope_shape, and the inspector's backend-authored routing actions/observations. Each filing is capped at three text calls under the existing shared Budget; no OCR, renderer, model, or agent framework is added.

---

## Action contract and residuals

The shared JSON action schema is search {query}, read_window {start,end},
propose_primary_span {item,start,end}, propose_alternative_regions
{item,regions}, or finish {}. Search and windows only return bounded
observations. A malformed action, a rejected proposal, or three exhausted
turns leaves the deterministic result in place and marks unresolved target
items review_required; no action can waive offset, heading, provenance, or
ordering checks.

The loop does not solve scanned filings, unknown silent failure classes, or a
destination that the deterministic verifier cannot publish. Those remain
explicit abstentions rather than reasons to add a second search heuristic.

## D22 live result and D23 correction

The single allowed 2026-08-29 CVX replay used three uncached calls (4,578
tokens, $0.004122, 21.710292 seconds). All proposals were rejected; deterministic
spans were unchanged and there was no positive live recovery. Turn 1 proposed
out-of-target item 1. The pre-D23 turn-2 prompt retained its rejection but lost
the targets and outline, then guessed item 1 again. D23 binds persistent context
with cached search/read/verifier replays; it does not claim a live recovery.
The pre-declared stop rule prevents a retry.
