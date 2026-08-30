# ADR-053 — evidence-driven per-item agent graph

Date: 2026-08-30. Status: accepted.

**Ruling**: run bounded actions through pinned `langgraph==1.2.11` `StateGraph` nodes—`diagnose → plan → act → evaluate → decide`—with `decide → plan|END`, compact item provenance, and deterministic evidence/failure-manifest routing rather than confidence alone.

**Because**: document-level stages can show that a route ran while hiding which item was risky, what was attempted, why a verifier rejected it, and whether it must remain under review.

**Enforced by**: `d28-per-item-agent-graph.json` and `envelope_shape`.

---

## Decision

The routing record carries `graph`: engine/version/checkpointer metadata, one
normalized-text SHA-256, the fixed role order, compact process-local checkpoint
history, `complete`, and one state per route target. Each state snapshots
the deterministic candidate, evidence/failure-manifest signals, attempts with
actions/rejections, every role checkpoint, and its `next_route`.

The graph reuses the existing maximum-three-turn action budget and does not
create calls. `InMemorySaver` is intentionally in-run/cache replay only; no
durable restart checkpoint is claimed or attempted. Checkpoint values exclude
filing text/images, credentials, callbacks, model secrets and `Budget`; cost
remains in the public routing record. Models receive
only declared JSON actions over
bounded deterministic evidence. Filing text and images are untrusted data, no
secret or tool is exposed, and deterministic verification alone may change an
item. A refused/unresolved substantive target stays `review_required`, sets
`next_route: review_required`, and makes graph completion false.

The existing key gate, cache, shared Budget, and public `routing` envelope
remain the sole choke point. No key makes zero model calls and leaves
deterministic text, statuses, and spans unchanged while routing warnings state
the refusal.
