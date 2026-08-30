# D28 — evidence-driven per-item agent graph

Escalation now runs and reports a compact, fixed five-role LangGraph control
path for each risky item. The graph snapshots the deterministic candidate and
source hash, records evidence/failure signals that selected the route, bounded
attempts, verifier rejections, and the next route. Its `InMemorySaver` history
is process-local to a run/cache replay, not restart-durable state and never
contains filing bodies, images, credentials, callbacks, or model secrets.

Only deterministic verification can change an item. A missing or invalid key
causes no model call; deterministic text, statuses, and spans remain unchanged,
while the route and warnings state why paid work did not run. Any unresolved
substantive target remains review-required and the inspector labels the route
partial rather than complete. Intel FY2025 covers the no-key refusal path;
the cached positive replay uses XOM FY2021 and makes no live model call.
