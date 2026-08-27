# 024 — "make it default on, remove the button": the escalate toggle goes, and what had to be re-bound so that is safe (2026-08-27)

The owner's whole instruction, verbatim: **"make it default on, remove the
button"**. Context: the deployed inspector was rendering a disabled checkbox
that explained at length why it could do nothing, which is a worse thing to
ship than either state it was mediating.

Ruling and record:
[ADR-036 §h2](../specs/decisions/ADR-036-tiered-escalation.md), amended in
place with a dated owner note.

## The decisions that mattered

- **The library default is NOT part of "default on", and saying so was the
  first job.** `extract_items(escalate=False)` stays false. Flipping it would
  put paid OpenRouter calls on every `python3 -m evals.run` and in CI —
  destroying the $0 offline gate the entire eval harness rests on — and would
  turn §l's falsifier "escalation is free by default" from a testable claim
  into a meaningless one. Default-on is a WEB LAYER change: `web/app.py`, and
  nothing below it. The boundary is stated in the ADR amendment rather than
  left to be inferred from the diff.

- **An off-switch is not a toggle.** "Remove the button" removes the *viewer's*
  say, not the *operator's*. `SEC10K_ESCALATION_ENABLED` was inverted rather
  than deleted: `== "1"` (arm) became `!= "0"` (disarm). It costs nothing, does
  not contradict the instruction, and means a runaway is stopped by an env var
  on the host instead of by a code change and a redeploy. Deleting it would
  have made the credit limit on the API key the *first* brake rather than the
  last.

- **A check that survives a re-pin unproved is the failure mode this repo keeps
  having.** Four mechanisms pinned the removed behaviour — `escalation_locks`,
  `routing_provenance`, `WIRE_API`, `WIRE_UI` — built over four review rounds.
  None was deleted to make the gate pass. Each was re-pinned to the new
  property and then falsified: ten mutations, each red through the real gate by
  exit code and green again on restore
  (`tasks/reviews/escalate-default-on-red.txt`). Two of the re-pins are
  genuinely new properties rather than re-spellings:
  - the arming SEMANTICS pin inverted with the variable. Under `== "1"` the
    danger was an expression that read True with the variable unset; under
    `!= "0"` unset means on *by design*, and the danger is a stop button wired
    to a comparand nobody documents (`!= "off"`), which is worse than no stop
    button because someone will believe it. `escalation-locks-evaded.py` was
    re-derived around that, since its old evasion — R18's `!= "0"` — is now the
    correct expression.
  - a new call-site pin. With no request-level flag left to AND against,
    `escalate=True` in `_run` would hard-wire paid work and orphan
    `ESCALATION_ENABLED`, which would sit above it still reading the
    environment, still looking like the switch, and read by nothing.

- **`routing_provenance` inverted rather than shrank.** It used to pin that the
  checkbox shipped unchecked and enabled. The lazy move was to delete those
  pins; the correct one was to pin their mirror — six ABSENT-pins forbidding
  the control, the helper, an `escalate` flag on any of the three wires, the
  arming round-trip, and the now-dead `escalation_disarmed` note. A deleted pin
  binds nothing, and a stray `&escalate=1` creeping back onto one wire is
  exactly the shape that would go unnoticed.

- **The exposure is stated, not softened.** The deployment has no auth and no
  rate limit, so with the opt-in gone any caller can trigger paid work by
  uploading a document that collapses — no account, no ticked box, one HTTP
  POST. The process budget is the bound and **a redeploy refills it**, so
  "spent" is a state a push undoes. The real remaining brake is the credit
  limit on the OpenRouter key itself. That paragraph is in ADR-036 §h2, in the
  D11 ledger row, in `README.md` and in `app.py`'s own header comment, and it
  is a P1 debt row (`TD-158`) rather than a caveat. The owner accepted it
  knowingly; the record says so in those words.

## The review round that followed, and the one thing it changed my mind about

PR #61 round 1 returned 1 HIGH and 4 MEDIUM. The HIGH is the one worth
recording here, because it is a failure of exactly the reasoning this file
defends. I wrote "any caller can trigger paid work by uploading a document
that collapses" in four places and was pleased with how plainly it was said.
It was false. Two committed fixtures fire the trigger and both sat in the
deployed dropdown, so no upload was needed — one click did it, and
`?fixture=intc-2025&run=1` did it on page load, because D10's deep link ends
`$("#go-fx").click()`. Removing the control made the dropdown the whole attack
surface and I did not go and look at what was in it.

The owner's fix — exclude the two — has a trap the reviewer named and I would
otherwise have walked into: excluding them from the LISTING is cosmetic,
because the deep link and a hand-written POST both resolve a fixture by name.
So resolution now goes *through* the listing (`if name not in
deployed_fixtures()`), which makes the two impossible to disagree. It also
breaks D1's invariant on purpose (one predicate, all readers equal), so
`fixture-discovery` is re-pinned to the new relationship rather than edited to
pass: the eval corpus is untouched and both remain eval fixtures; only the two
web readers shrink, together, by a named set.

The other four are all the same shape as each other: a brake whose stated
property nothing bound. `server_budget()`'s memo — the only thing making the
budget process-wide — could be deleted with the gate byte-identical, while the
check's own docstring claimed to pin it. `EXTRACT_WINDOW` had a floor and no
ceiling. `/api/meta`'s arming key lost its consumer and its pin in the same
edit that made the ADR start claiming it. And the off-switch accepted only the
literal `0`, so `SEC10K_ESCALATION_ENABLED=false` — what an operator actually
types — left it spending; that one I widened rather than documented, because
this repo's own evasion fixture argues that a stop button wired to an
undocumented comparand is worse than none, and documenting a footgun on a
money path leaves the footgun.

The lesson I would keep: I re-pinned four checks carefully and proved each one
bites, and still shipped a HIGH — because every mutation I wrote attacked the
code I had just changed. None of them asked what the *product* now does. The
reviewer's first move was to open the dropdown.

## What did not change

The two budget ceilings and `EXTRACT_WINDOW`. The owner removed the toggle, not
the spend ceilings — and with nobody having to tick anything, those ceilings
went from one brake among three to the only one inside the process.
