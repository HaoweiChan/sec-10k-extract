# D28 — evidence-driven per-item agent graph decision

## Material request

Make the bounded escalation path inspectable and replayable per item with
the pinned `langgraph==1.2.11` `StateGraph` and `InMemorySaver`, without a
database or new paid roles. Deterministic
candidates/source hashes are immutable; agents may propose only strict JSON
actions/evidence over untrusted filing data and the deterministic verifier is
the publication authority.

## Outcome

The route executes and records the fixed `diagnose → plan → act → evaluate →
decide` graph with its conditional repair/END edge. The process-local compact
checkpoint history contains only hash/risk/action/observation/verifier/decision
facts, never filing payloads or secrets. Each target stores evidence-derived
risk, candidate snapshot, item-specific attempts/rejections, checkpoints, and
next route. The Intel FY2025 no-key refusal proves zero cost, unchanged
deterministic spans, explicit warning, and `review_required`; the separate XOM
FY2021 cached replay proves a verified alternative path without a live call.
