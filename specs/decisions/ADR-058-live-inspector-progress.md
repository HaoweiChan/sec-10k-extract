# ADR-058 — live inspector progress

Date: 2026-08-30. Status: accepted.

**Ruling**: the inspector polls a fixed process-local background extraction; the normal API stays synchronous.
**Because**: a blocking response cannot truthfully expose cached, skipped, failed, and slow backend stages.
**Enforced by**: `d35-live-progress-flowchart`, `d35-live-skipped-stages`, `d35-busy-live-region`, `d35-progress-event-queue`, `d35-terminal-refusal-progress`, `d37-readable-progress-detail`, and the web contract test.

---

The browser sends `X-Progress: 1`. The server returns an opaque id immediately,
runs the same extraction entrance in a daemon thread, and accepts stage events
only from `extract_items` and `escalate.route`. Polling publishes only the fixed
stage names and bounded statuses. The completed classify-through-decide graph
is replaced by the extraction response's own `routing.stages`, preserving its
skipped and failed outcomes; the result remains available at a separate URL.
Each job retains at most one sanitized snapshot per fixed stage so fast real
transitions are delivered in backend order instead of disappearing between
browser polls.

No progress response includes filing text, prompts, model output/reasoning,
credentials, targets, errors, or cost. The existing status live region
announces the backend-authored active label. Native HTML/CSS draws the connected
graph, and the existing reduced-motion rule disables its pulse animation.

The graph also explains the active stage in fixed plain language and displays
browser-observed elapsed time. If no sanitized stage or status changes for 30
seconds, it says that the request is still running and may be waiting on the
model/provider. A failed verification is explained while decide remains active.
These are presentation-only interpretations of the fixed progress snapshot;
they neither infer backend progress nor expose additional backend content.

**Residual**: jobs and their opaque ids are process-local and bounded. A restart
loses an in-flight inspector run; multi-worker or restart-durable execution
would require a shared job store and is outside this single-instance inspector.
