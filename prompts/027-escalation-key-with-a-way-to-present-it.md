# 027 — Put the paid tier back behind a key, with a field the page can send it from

Date: 2026-08-28. Outcome:
[ADR-042](../specs/decisions/ADR-042-escalation-key-with-a-way-to-present-it.md),
`gate.py` restored, `#esc-key` field added, `SENDS_TOKEN_UI` + `_fn_body` pins.

## The prompt

Hours after ADR-041 deleted the door, the owner read what it cost:

> 確實會怕非面試官去打我的網站浪費我的錢 我覺得要設個密碼 要怎麼設定好

Note the shape of this. It is not "you were wrong to remove it" — it is the
owner weighing the exposure ADR-041 had stated plainly and deciding the trade
differently once it was concrete. The ADR did its job.

## The one question worth asking

Not *whether* to add a password — that was decided. **How the interviewer
receives it**, because that is precisely where the previous door died. The
options put to the owner were a `?k=` link (zero friction, secret in the URL),
a field on the page (one paste, secret stays out of history), or both. The
owner chose the field.

That question was worth blocking on. Guessing "link" would have re-shipped a
secret into browser history and referrer headers for a demo whose whole
audience is a stranger clicking a URL from an email.

## What was built, and the rule it encodes

`gate.py` came back byte-identical from `6b48be3^` — it was never the broken
part. The new work is entirely the half that never existed:

- `#esc-key`, a password field, revealed only when `/api/meta` reports a secret
  is configured (a field that opens nothing tells a stranger something is being
  withheld, which is worse than no field)
- the header injected inside `call(url, opts)`, the one helper all three extract
  modes funnel through — the client's `_run`
- `localStorage` persistence so it is typed once, wrapped in try/catch because
  it throws outright in some privacy modes

And the rule, now a check rather than a lesson:

> **A credential the client cannot present is not a control, it is an outage.**

## Assumption → Eval contradiction → Correction

- Assumed: restoring the door was mostly reverting the ADR-041 commit.
- Eval said: the revived `escalation_choke_point` went red on **five**
  assertions, and two of them — `id="esc-key"` found 0, `"X-Escalation-Token"`
  found 0 — were about a file the revert never touched. The revert restores the
  door; it does not restore a way through it, because there never was one.
- Corrected: the case grew `SENDS_TOKEN_UI` and `_fn_body`, and the ADR's
  ruling names the client half as the substance rather than as a detail.

- Assumed: pinning the header string once (count == 1) proves the page sends it.
- Eval said: nothing — this one was caught by reasoning about the pin's negative
  space before writing it. A count of 1 is equally satisfied by the header being
  set at ONE of the three call sites, which leaves two modes silently unable to
  escalate: the same defect class as the original, one third as visible.
- Corrected: added `_fn_body`, a brace matcher that extracts the `call()` body,
  so the pin asserts WHERE the header is set and not merely THAT it is.

- Assumed: the key-field wiring could go anywhere in `boot()` after the
  `/api/meta` fetch.
- Eval said: `ui-deep-link` went red — it pins one **contiguous** span from the
  `#fx` options assignment through the `catch` arm to `deepLink();`, which is
  how it proves the deep link runs on boot's straight-line tail after the option
  list exists. My insertion split that span.
- Corrected: moved the wiring ABOVE the `#fx` line rather than relaxing the pin,
  with a comment saying why, because that pin took three review rounds
  (PR #55 R1/R9/R10) to state correctly and is not mine to weaken.

- Assumed: the eval suite passing meant the feature worked.
- Eval said: it would have said exactly that about the ADR-036 door, which was
  totally broken. The suite cannot see a browser.
- Corrected: drove a real uvicorn with the browser tools across four states — no
  key, key typed, reload, key cleared — reading `VIEW.escalation` out of the
  live page. `ran` was `false/true/true/false`, and the free tier returned an
  identical 18 extracted + 5 IBR in all four. That table is §b of the ADR.
