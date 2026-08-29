# D23 — persistent bounded-agent context

## Material request

Repair the D22 live CVX context-loss failure offline and red-first. Preserve
the maximum-three-turn loop, existing model/cache/Budget, bounded observations,
and deterministic publication boundary; do not spend another live call.

## Outcome

Every agent turn now receives immutable `target_items` plus the compact
item/warning outline, with only the exact immediately preceding observation
changing. A cached end-to-end CVX route case proves the follow-up prompt after
search, `read_window`, and verifier rejection each carries both parts.

## Assumption → Eval contradiction → Correction

- Assumed: feeding the most recent observation alone was enough for a bounded
  agent to retain the assigned target and filing shape.
- Eval said: the D22 live CVX run rejected out-of-target item 1, and its next
  prompt contained only that rejection; turn 2 guessed item 1 again. The new
  cached `persistent_context` case was observed red on the missing target/outline.
- Corrected: the loop serializes a fixed context beside the changing observation
  on every turn; no live retry or heuristic was added.
