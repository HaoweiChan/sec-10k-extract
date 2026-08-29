# D22 CVX bounded live-run report — 2026-08-29

One allowed live run over `evals/fixtures/cvx-2015/filing.htm` made three
uncached calls: 4,578 tokens, $0.004122, and 21.710292 seconds. All actions
were rejected. The deterministic spans for items 2, 6, and 7A were unchanged;
the loop retained `review_required` and emitted `escalation_unresolved`. There
was no positive live recovery. The stop rule prevents a retry.

The failure exposed a prompt invariant gap: turn 1's rejected out-of-target
item-1 proposal became the complete turn-2 prompt, losing the assigned targets
and compact outline. D23 records a $0 cached red-first reproduction and fixes
only that context retention.

Deployment evidence from the merged `acadbedb1596` build is intentionally
limited: `/api/meta` reported escalation enabled and token required. A public,
tokenless AAPL 2025 request was clean at $0 (18 extracted, 5 IBR; no routing;
explicit invalid/missing-token reason); tokenless CVX was `success_with_warning`
at $0 with items 2/6/7A review-required (534/119/453 chars) and the documented
unattributed, near-empty, and internal-pointer warnings. Neither is an
authorized agentic deployed replay or positive recovery.
