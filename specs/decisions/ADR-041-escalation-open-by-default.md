# ADR-041 — the paid tier is OPEN to every request; the token door is removed

Date: 2026-08-28. Status: accepted. **Supersedes the door half of
[ADR-036](ADR-036-tiered-escalation.md) §h2 lock 4** (TD-158, PR #61 R10),
which shipped on 2026-08-28 and is removed here the same day. Not a freeze
exception: this removes a deployment control, it adds no extraction
capability — `extract_items` is untouched, its `escalate=False` default is
unchanged, and no fixture's output moves.

**Ruling**: `src/sec10k/web/gate.py` is DELETED, and with it `SEC10K_ESCALATION_TOKEN`, the `X-Escalation-Token` header and `/api/meta`'s `escalation_token_required` key. The model tier runs for every request on all three input modes whenever the deployment is armed, and `SEC10K_ESCALATION_ENABLED` is the operator's only stop; the envelope still publishes `escalation.{ran, reason}` and the page still prints the server's own sentence, so a viewer is never left guessing whether the tier ran. The money is held by the process-wide `Budget` ALONE — `SEC10K_ESCALATION_MAX_USD`, **raised from $5.00 to $10.00 by this ADR** on owner instruction, and `SERVER_MAX_CALLS` = 20 — alongside ADR-040's global rate limit, the 25 MB `MAX_BYTES` cap and both rungs' input caps (§a); the budget is REFILLED BY EVERY REDEPLOY, which is an accepted recurring cost and explicitly NOT a bound (§a).
**Because**: the deployed inspector exists to be opened by an interviewer who configures nothing, and the door was closed to exactly that person — `index.html` makes four `fetch()` calls, sets two headers, both `Content-Type: application/json`, and has no field to collect a secret, so the only interface the service advertises could not reach the paid tier for anyone including the owner (§b). The owner's decision, verbatim: "我就要 default 有 escalation — 面試官不想管這種細節." PR #61 R10's finding is ACCEPTED rather than refuted: `POST /api/extract/url` takes any `https://www.sec.gov/Archives/…` URL, so an anonymous caller can now reach the paid tier on any collapsing EDGAR filing. The door was the correct answer to R10 and the wrong answer to what the deployment is for.
**Enforced by**: `evals/adversarial/escalation-choke-point.json` + `escalation-choke-point-evaded.json` (both `fast`+`invariant`), replacing `escalation-door.json` / `escalation-door-open.json` — with the perimeter deliberately weaker the checks concentrate on the ceiling behind it: exactly one `extract_items` entrance and it is inside `_run`; `escalate=` is the `ESCALATION_ENABLED` NAME so a literal cannot defeat the operator's stop; `budget=` is conditioned on that same name so nothing escalates unbilled; `view['escalation']` is built from it; and `llm.Budget` is RUN, refusing on both its dollar and its call limit, with `SERVER_MAX_USD`'s fallback read from the tree because `app.py` imports fastapi and the eval environment has none. Red-first observed before the code changed: the new case failed on exactly the three assertions the door's shape violated.

---

## a) What is left holding the money

| bound | value | who refills it |
|---|---|---|
| process-wide `Budget` dollars | `SEC10K_ESCALATION_MAX_USD`, default **$10.00** (was $5.00) | **every redeploy** |
| process-wide `Budget` calls | `SERVER_MAX_CALLS` = 20 | every redeploy |
| free-tier rate limit (ADR-040) | burst 20, 30/min, global | rolling window |
| per-document size | `MAX_BYTES` = 25 MB | per request |
| per-call input caps | `llm_localize` 60,000 chars; `llm_extract` `EXTRACT_WINDOW` | per call |

The redeploy refill is the honest weak point and is **not** a bound: a
deployment redeployed *n* times can spend *n* × `SEC10K_ESCALATION_MAX_USD`. The ceiling was RAISED rather than lowered when the door came off, which looks backwards and is deliberate: it stopped being a backstop behind a header and became the demo's whole risk appetite, and $5 was set when a token holder was the only spender. $10 pairs with `SERVER_MAX_CALLS` = 20 — an escalation is at most 2 calls, a rung 1 at ~$0.004 and a rung 2 at ~$1 — so ~10 escalations reach both ceilings together instead of one masking the other.
Nothing in this repo can observe that, and `escalation_choke_point`'s negative
space says so. The mitigation is operator judgement — lower the variable, or
disarm with `SEC10K_ESCALATION_ENABLED=0` when the demo window closes — not a
mechanism, and it is recorded here as accepted risk rather than as solved.

## b) Why the door failed as a demo control, in one line of evidence

`src/sec10k/web/static/index.html` makes four `fetch()` calls and sets exactly
two headers, both `Content-Type: application/json`. It never sent
`X-Escalation-Token` and had no field to collect one. So from the day the door
shipped, the browser — the only interface the deployment advertises — could not
open the paid tier at all, for anyone, including the owner. The refusal string
a visitor saw ("this deployment has no `SEC10K_ESCALATION_TOKEN` of at least 16
characters configured…") was accurate and useless.

Two fixes existed: add a secret field to the page, or remove the door. A secret
field on a public demo page is a worse artifact than no door — it invites the
viewer to type something they do not have, and it publishes that a paid path is
being withheld from them. The door was removed.

## c) What did NOT change

- `extract_items(path)` still defaults `escalate=False`, so the eval gate and
  CI stay $0 and offline. Nothing here touches the extraction library.
- The D8 coverage trigger is unchanged: escalation being *allowed* still is not
  escalation *happening*. On the 29 real dev filings the trigger fires on 1.
- With no `OPENROUTER_API_KEY` the tier refuses loudly and publishes
  `unavailable`; it never degrades and never fabricates an item (ADR-036 §e).
- ADR-040's free-tier limiter is untouched and now fronts the paid path too,
  since every escalating request is also an `/api/extract/*` request.
- D11's acceptance in ADR-036 §k stays **NOT MET**. Opening the tier does not
  make it work: the measured record is $4.02 spent and no item resolved on any
  held-out filing.

## d) The ledger

TD-158 is reopened as superseded rather than deleted — it was `done`, its
finding was real, and the record of a correct fix that was then withdrawn for a
stated reason is worth more than a tidy row. TD-162/D15 (the free-tier limiter)
was split out of TD-158 and is unaffected.
