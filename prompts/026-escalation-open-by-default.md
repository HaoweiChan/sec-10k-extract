# 026 — Remove the escalation token door; the paid tier is open by default

Date: 2026-08-28. Outcome:
[ADR-041](../specs/decisions/ADR-041-escalation-open-by-default.md),
`web/gate.py` deleted, `escalation-door*` cases replaced by
`escalation-choke-point*`.

## The prompt

Owner, on being shown the deployed page's own refusal string ("model tier: did
not run — this deployment has no `SEC10K_ESCALATION_TOKEN` of at least 16
characters configured, so the paid tier is closed to everyone including the
operator"):

> 我不想用什麼 SEC10K_ESCALATION_TOKEN 我就要 default 有 escalation
> 面試官不想管這種細節

That is the whole instruction, and it is a product decision, not a coding one:
the deployment's audience is an interviewer following a link, and any control
that audience has to configure is a control that will never be used.

## What the assistant said back before building

One paragraph of concern, then the work — not a refusal and not a negotiation.
The concern: removing the door re-opens PR #61 R10 in full, because
`POST /api/extract/url` accepts any EDGAR Archives URL, so an anonymous caller
on the public internet can reach the paid tier on any collapsing filing. The
number that matters was named rather than left implicit: after this change the
only money bound is the process-wide `Budget`, `SEC10K_ESCALATION_MAX_USD`,
default **$5.00**, and **it is refilled by every redeploy**.

The owner had already been given that trade and repeated the instruction, so it
was built. ADR-041 records the exposure as ACCEPTED rather than as refuted —
the door was the right answer to R10 and the wrong answer to what the
deployment is for.

## What the eval set forced

Hard rule 2 was followed literally: `escalation-choke-point.json` was written
and run against the UNCHANGED tree first, and it failed on exactly three
assertions — `escalate=` was the door's verdict rather than `ESCALATION_ENABLED`,
`budget=` was conditioned on that verdict, and `view['escalation']` was built
from it. Only then did `app.py` change.

The replacement checks are deliberately a WEAKER perimeter and a STRONGER
ceiling, which is the shape the decision actually has. Gone: the header
decision table. Kept and tightened: one `extract_items` entrance inside `_run`;
`escalate=` must be the off-switch NAME so a literal cannot defeat the
operator's stop; `budget=` conditioned on that same name; and `llm.Budget`
itself is now RUN — it must refuse on both its dollar and its call ceiling —
because it is the only thing left holding the money.

## Assumption → Eval contradiction → Correction

- Assumed: the door could be kept and simply opened by configuring the secret
  on the host, so the owner's ask was a deployment-settings answer.
- Eval said: not an eval — a read of `web/static/index.html`. It makes four
  `fetch()` calls and sets exactly two headers, both
  `Content-Type: application/json`. The page never sent `X-Escalation-Token`
  and had no field to collect one, so configuring the secret would have opened
  the tier for `curl` and for nobody using the deployed interface.
- Corrected: the answer stopped being "set these two variables" and became
  ADR-041 — delete the door, because a door whose only key is a header the
  product never sends was closed to 100% of its actual users.

- Assumed: the new check could `import` `web/app.py` to read `SERVER_MAX_USD`
  and to call `server_budget()` twice for its singleton property.
- Eval said: `ModuleNotFoundError: No module named 'fastapi'` — the eval
  environment has never had it, which is precisely why every money pin in this
  repo reads `app.py` with `ast`.
- Corrected: the ceiling's BEHAVIOUR is run for real out of `llm.py` (stdlib
  only, and it must refuse on both limits), while `SERVER_MAX_USD`'s fallback
  and `server_budget()`'s memoization are read from the tree — and the
  docstring names that half as a shape read instead of letting it look
  executed.

- Assumed: swapping two eval cases for two others was the whole eval-side cost.
- Eval said: `ui-boilerplate-exclusion` went red — `boilerplate-wire-values`
  pins the `extract_items(...)` call as EXACT TEXT, so changing the call's
  arguments broke a check about a different feature entirely.
- Corrected: the text pin and its known-bad fixture were updated to the new
  call shape, and the comment above the pin now records that the door came and
  went rather than describing a `gate.py` that no longer exists.

- Assumed: a 10-character secret needed the operator warned to GENERATE rather
  than invent it, and the ADR said so.
- Eval said: nothing — the owner did. "密碼要給對方的 我會用好記字元 這沒得商量."
  The secret is handed to another person, read out or typed off a phone during
  an interview, so memorability is a REQUIREMENT and a random string is the
  design that fails. The brute-force arithmetic was real but aimed at a threat
  model nobody occupies: the prize for guessing is permission to spend $10 of
  someone else's money on 10-K extraction.
- Corrected: ADR-042 §e and `gate.py`'s comment now say the floor's job is the
  ACCIDENT and not the adversary, and that `SERVER_MAX_USD` is what bounds the
  money. The advice to generate is gone rather than softened — it was wrong for
  this deployment, not merely unwelcome.
