---
id: TASK-1
title: Classify escalation failures and verify alternative regions
status: To Do
assignee: []
created_date: '2026-09-02 17:44'
labels: []
dependencies: []
references:
  - TODO.md D21
  - owner request
  - '2026-08-29'
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replace the one-code escalation switch with a deterministic failure classification that routes each detected shape either to ordinary contiguous span repair or to verified alternative evidence regions. Alternative evidence may be discontiguous, overlapping, or nested and therefore never rewrites the INV-S1 primary spans; every region is still anchored verbatim to `normalized_text`, bounded, item-scoped, and deterministically verified before publication. Accept verified results per item, preserve unresolved items as `ambiguous` / `review_required`, and keep deterministic resolvers ahead of all paid work. Publish the same flow to the inspector as five user-visible stages — classify, plan, route, verify, decide — each naming its status, reason, target items, cost, and why it was skipped, so the user can inspect the agentic process rather than see only its final answer. Add a bounded, live vision-verification route for eligible filing images: record image annotations whenever escalation is enabled, resolve at most two relative image references only against the validated SEC Archives document URL, and send those public image URLs as multimodal inputs to a model whose committed catalogue record declares image input. The vision verdict may confirm or reject only proposed alternative evidence that already passed text-offset verification; it can neither create an offset nor turn an otherwise failed extraction into success. The call uses the same cache and shared budget as text escalation, and acquisition, model, verdict, failure/skip reason, token count, and cost are visible in the verify stage. Uploads, fixtures, unsafe/non-SEC URLs, absent images, exhausted budget, and provider failure skip or fail loudly rather than pretending vision ran. This is one vertical slice, not a claim to enumerate issuers: full-page OCR/rendering, new models, and silent precision failures for which no existing signal fires stay explicit residual classes.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ADR-046 and the output contract bind the typed routes and evidence shape; new adversarial cases are observed red before implementation; Intel and Citi remain deterministic and make zero model calls; `fast` and `invariant` make zero paid calls and pass at 100% without a baseline move; cost/call/token limits and cached replay remain enforced; the deployed inspector renders the five-stage flow and live vision-verification evidence without exposing a secret or silently claiming vision ran; one cold review is recorded and every in-scope finding becomes a red adversarial case before repair.
<!-- AC:END -->
