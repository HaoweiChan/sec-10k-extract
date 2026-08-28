# ADR-042 — the paid tier goes back behind a key, and this time the page can present it

Date: 2026-08-28. Status: accepted. **Supersedes
[ADR-041](ADR-041-escalation-open-by-default.md)**, which deleted the door of
[ADR-036](ADR-036-tiered-escalation.md) §h2 lock 4 the day it shipped. Not a
freeze exception: this is a deployment control, not an extraction capability —
`extract_items` is untouched, its `escalate=False` default is unchanged, and no
fixture's output moves.

**Ruling**: `src/sec10k/web/gate.py` is restored unchanged and the paid model tier again runs only for a request presenting a valid `X-Escalation-Token` — with no `SEC10K_ESCALATION_TOKEN` on the host, or one under `MIN_TOKEN_CHARS` (10 since §f), it runs for NOBODY, so unset stays CLOSED rather than open. What is NEW, and is the whole reason this ADR is not just a revert: the page can now present it. `index.html` carries a `#esc-key` password field, revealed only where `/api/meta` reports `escalation_token_required`, remembered in `localStorage` so it is typed once, and injected as the header inside `call(url, opts)` — the ONE helper all three extract modes funnel through, mirroring `_run` on the server, so a mode cannot forget it the way the whole page forgot it before. Deterministic extraction stays open, free and unauthenticated on all three routes, and the envelope publishes `escalation.reason` either way.
**Because**: ADR-041 removed the door for a real defect — it was shut to every human visitor including the owner — but the defect was the MISSING CLIENT HALF, not the door. Owner, 2026-08-28: "確實會怕非面試官去打我的網站浪費我的錢 我覺得要設個密碼." Deleting the door left the paid tier open to `POST /api/extract/url` on any EDGAR Archives URL for anyone on the internet, bounded only by a process `Budget` that every redeploy refills; a key the interviewer pastes once restores the bound without restoring the outage. The field is chosen over a `?k=` link (owner's call) so the secret never enters a URL, browser history, or a referrer header.
**Enforced by**: `evals/adversarial/escalation-choke-point.json` + `escalation-choke-point-evaded.json` (both `fast`+`invariant`), which now carry BOTH halves — the door's decision table RUN out of `gate.py` (unset, short secret, absent/empty/wrong header, disarmed deployment, and the one row that opens, plus the five production-shaped rows that pass no `token=`), the `llm.Budget` battery ADR-041 added, the single-entrance and escalate/budget-same-name choke point, AND the new `SENDS_TOKEN_UI` pins with `_fn_body`: the page must have the field, must name the header, and must inject it INSIDE `call()` rather than at one of the three call sites. Red-first observed: before the code changed the case failed on five assertions, two of them the exact absence that killed the last door.

---

## a) The rule this ADR exists to write down

> **A credential the client cannot present is not a control, it is an outage.**

ADR-036 §h2 lock 4 was correct on the server and had a complete, executed
decision table behind it. It still failed totally, because nothing in the repo
asserted that the product could open it. Nine eval assertions covered the
door's server side; zero covered whether any human could get through it.

That gap is now a check. `SENDS_TOKEN_UI` and the `_fn_body` assertion fail if
the field disappears, if the header literal disappears, or if the header moves
out of the shared helper to a single call site — the last being the subtle one,
since a count of 1 alone cannot tell "all three modes send it" from "one mode
sends it and two are silently broken".

## b) What a visitor sees, measured in a browser rather than asserted

Driven against a real uvicorn with `SEC10K_ESCALATION_TOKEN` set, reading the
envelope out of the live page's own `VIEW`:

| in the browser | `escalation.ran` | what the viewer gets |
|---|---|---|
| no key typed | `false` | 18 extracted + 5 IBR, strip says the tier is behind the header |
| key typed | `true` | same items, plus the routing strip |
| reload, key restored from `localStorage` | `true` | typed once, not once per visit |
| key cleared | `false` | free tier intact |

The free deterministic tier is identical in all four rows. That is the point:
the key gates the spend, never the product.

## c) What is still true from ADR-041

- The money ceiling stays where ADR-041 put it: `SEC10K_ESCALATION_MAX_USD`,
  default $10.00, `SERVER_MAX_CALLS` = 20, refilled by every redeploy. It is
  once again a backstop BEHIND a door rather than the only bound, which is why
  it was not lowered again.
- `extract_items(path)` still defaults `escalate=False` — gate and CI stay $0
  and offline.
- D11's acceptance in ADR-036 §k stays **NOT MET**: $4.02 spent, no item
  resolved on any held-out filing. A key does not make the tier work; it
  decides who pays to watch it not work.
- ADR-041's §b analysis of why the first door failed is not withdrawn. It is
  the reason this one has a field.

## d) How a non-human client escalates, and the one trap in it

Three routes, all working today with no further code. Measured against a live
uvicorn, not asserted:

**1. Plain HTTP — the right answer when the agent wants RESULTS, not the UI.**
No DOM, no browser, nothing to break:

```
curl -X POST https://…/api/extract/url \
  -H 'Content-Type: application/json' \
  -H 'X-Escalation-Token: <key>' \
  -d '{"url":"https://www.sec.gov/Archives/…"}'
```

**2. Driving the page — type into `#esc-key`, then click Extract.** The field
is revealed by `/api/meta`, so the agent must wait for boot before filling it.
Works exactly as a human's does.

**3. The deep link, `?fixture=…&run=1` — and this is the trap.** That link
extracts during `boot()`, BEFORE any agent can type anything, so a fresh
browser context escalates on it NEVER. Measured: fresh context + deep link
gives `escalation.ran: false`. The fix is one call before navigating —

```js
localStorage.setItem("sec10k.escalation-key", "<key>")
```

— after which the same link gives `ran: true` with the routing strip. This is
why `KEY_STORE`'s literal value is pinned in `SENDS_TOKEN_UI` rather than left
as an implementation detail: an out-of-repo consumer depends on that exact
string, and renaming it would drop the agent to the free tier with every check
green on both sides of the boundary.

A `?k=` URL parameter was NOT added for this. It would put the secret in
browser history and referrer headers — the reason the owner chose a field over
a link in the first place — and route 1 already covers every case where the
caller is not a browser.

## e) The secret floor, lowered 16 -> 10, and why the secret is memorable

`MIN_TOKEN_CHARS` was 16 — the length `secrets.token_urlsafe(12)` happens to
produce, a convention rather than a derived bound. At that floor a 10-character
secret would have been treated as ABSENT: door closed to everyone, field
hidden, and the only clue a line in the envelope. Silently doing nothing is the
worst of the available behaviours, so the floor moved to 10.

**The secret is deliberately memorable, and that is a requirement, not a
concession.** The owner's decision, and the reason is the thing an
availability-first reading of this ADR keeps missing: this key is handed to
*another person*. It gets read out on a call, pasted from an email, or typed
off a phone screen during an interview. A 43-character random string is the
design that fails — the viewer mistypes it, or gives up, and the paid tier is
closed to the only person it was opened for. That is the same failure ADR-041
had to delete a whole door over, arriving by a different route.

**What actually bounds the money is `SERVER_MAX_USD`, not this constant.** A
guesser's prize is permission to spend at most $10 of someone else's money on
10-K extraction before the process budget refuses. Nobody brute-forces for
that. The threat this key is built against is the casual passer-by and the
crawler that found the URL — and a memorable password stops both completely,
because neither is guessing at all.

So the floor's job is the ACCIDENT (`"x"`, `"test"`, an empty string that got
through a config UI), not the adversary. It is not a strength policy and does
not pretend to be one. Below ~8 characters the accident case starts to overlap
the guess case, which is where it would stop doing even that job.

What did NOT change: unset is still CLOSED, a secret under the floor is still
refused in the same words an absent one is, and no refusal ever quotes the
secret.

## f) The ledger

TD-158 returns to `superseded` pointing here rather than at ADR-041 — the
original finding stands, and this is its second and better fix.
