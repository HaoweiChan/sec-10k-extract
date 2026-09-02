---
id: TASK-6
title: >-
  Rung 2 returns `empty_completion` on `intc-2025` even after the §h4 allowance
  fix
status: To Do
assignee: []
created_date: '2026-09-02 17:45'
labels: []
dependencies: []
references:
  - TODO.md TD-165
  - '`tasks/reviews/d17-intc-measurement.txt` RUN 2 (D17 deliverable (b)'
  - >-
    2026-08-28); ADR-036 §h4's dated note and §k; the committed response
    `evals/cache/llm/bb51f410….json`
priority: medium
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The §h4 fix did not close the failure it was built for.** §h4 diagnosed the D11 exam's `empty_completion` as sending 2,048 output tokens with no reasoning budget to a reasoning model, and fixed it by sending `MAX_TOKENS` 2048 + `REASONING_TOKENS` 4096 = 6,144 with an explicit `reasoning: {"max_tokens": 4096}` — satisfying OpenRouter's documented rule that `max_tokens` exceed the reasoning budget. Measured 2026-08-28 with a real credential: the rule IS satisfied (6,144 > 4,096) and the failure REPRODUCES IDENTICALLY — `finish_reason: length`, `output_tokens: 6144` of 6,144, empty text, **billed $0.997760** for 168,832 input tokens on 517,976 input chars. Tripling the allowance moved the failure, it did not remove it, so `intc-2025` — the one real collapsed filing this repo owns — is not reachable by the ladder as built. What the run does NOT establish: whether a larger allowance would work, and whether the binding constraint is the allowance at all rather than the input size Decided 2026-08-28 (orchestrator acting as human-in-the-loop), and PARTLY TAKEN: **the next paid attempt is deferred until it can explain itself, and the $0 half of that was shipped in this same decision.** Reading the client settled one hypothesis for free — the `reasoning` parameter IS sent correctly (`llm.py::_body` sends `{"max_tokens": 4096}` with `max_tokens` 6144, so OpenRouter's documented rule is satisfied and a malformed request is ruled OUT). What could not be settled for free is the one that matters: `usage.output_tokens` counts thinking AND answer, so `6144 of 6144` with empty text has two readings — the reasoning cap was not enforced and thinking consumed everything, or it was enforced and the ANSWER was truncated — and `finish_reason: length` is identical under both. `_normalize` was DROPPING `completion_tokens_details.reasoning_tokens`, the single field that separates them, so a second $1 call would have returned exactly as uninformative as the first. That is §h4's own lesson recurring at the next field along ("a diagnostic nothing asserts is one that quietly stops being written"), and it is now closed: the field is recorded, `None` when the provider omits it rather than 0, and pinned by `llm.py::_demo` (added red-first, then re-proved by deleting the field and watching `_demo` exit 1) Stop rule, pre-declared so the next taker does not drift: at most ONE further paid attempt, and only after a run carries `reasoning_tokens`. If it shows thinking consumed the whole allowance again, the honest conclusion is that the A1 whole-document-collapse class is out of this ladder's reach, recorded in an ADR that supersedes §h4's optimism — NOT a third ceiling. If instead it shows reasoning stopping at its cap with the answer truncated, then raising `MAX_TOKENS` alone is the indicated fix and is worth one call. Either way the decision is made BEFORE the money, which is the part the first two attempts got backwards

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
