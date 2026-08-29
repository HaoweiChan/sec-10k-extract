# D22 — bounded agent loop decision

## Material request

Turn D21's fixed proposal ladder into a maximum-three-turn, cached-testable
observe → act → verify → re-plan/abstain loop without adding a model,
framework, OCR, renderer, or filing-specific rule.

## Outcome

The loop uses the existing small model, shared cache and Budget, sends only a
compact outline plus bounded search/window observations, and records every
action and verifier observation in routing. Existing deterministic verifiers
remain the sole publication boundary. The existing internal-pointer warning is
the entry signal; clean and deterministically cross-reference-resolved filings
remain zero-call paths.
