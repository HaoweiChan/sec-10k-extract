# 012 — S8: the "exclude boilerplate" checkbox, and two rulings made before any code (2026-08-22)

The S6 follow-through: make [ADR-026](../specs/decisions/ADR-026-boilerplate-chrome-exclusion.md)'s
capability reachable from the deployed inspector. Deliberately small. The
interesting record here is not the diff — it is the two scope rulings the task
prompt carried, and the falsification discipline it imposed, both of which
changed what shipped.

## The prompt decisions that mattered

- **"NO NEW ADR", with the test for when one is owed.** The instruction did not
  merely forbid an ADR, it said *why* one was not owed: this "applies ADR-026's
  existing ruling to an existing caller… adds no extraction behaviour and is
  not a T8-freeze exception." That is a reusable rule — the freeze guard bites
  on new capability, not on new callers of an existing one — and without it the
  default move would have been a ceremonial ADR-027 restating §d. The whole
  design instead reduced to one line: `build_view` switches on the *presence* of
  the envelope's own `boilerplate` key, which by ADR-026 exists exactly when the
  caller asked. No new parameter, no new flag to keep in sync, and the "display
  only" property becomes structural rather than a promise.

- **The human's own phrase was overruled, on the record, for a technical
  reason.** The spec said render "the source/item text" with boilerplate
  excluded. Taken literally that includes the compare pane — and the compare
  pane cannot do it: `/api/source` serves the ORIGINAL filing bytes into a
  sandboxed iframe, while `boilerplate` offsets index the DERIVED
  `normalized_text`, and no raw↔normalized offset map exists anywhere in this
  pipeline. Building one is a new capability inside `normalize.py`, i.e. exactly
  the post-freeze scope creep ADR-026 §a rules out. The ruling arrived as a
  scoping decision with its reason attached rather than as a preference, so it
  could be checked rather than obeyed — and it survived checking. It is now a
  debt row, which also corrects the closed S6 debt row's proposed cheap fix ("a
  greyed-span render in the existing source pane"), wrong for the same reason.

- **"What wrong implementation still satisfies this?" as a required step, not
  advice.** The prompt named four mutation classes the new case had to catch
  (OFF stripping, ON not stripping, ON stripping the wrong range, any movement
  in `normalized_text`/`start`/`end`/`chars`) and demanded each be *built* and
  observed red. Ten were built. Two paid for themselves immediately: the
  off-by-one mutation (`end - 1`) is invisible to any check that compares the
  pane against `strip_chrome`'s own output, which is why the oracle in
  `check_boilerplate_exclusion` marks covered characters and rebuilds the
  expected string instead of calling the implementation; and `chars` following
  the shown text — the natural, wrong reading of "hide the boilerplate" — is
  caught only because the check pins `chars` to `end - start` rather than to
  what is rendered. The repo's last two review rounds were dominated by checks
  that could not fail; this is the cheapest known antidote.

- **Where the check could NOT go was written down instead of faked.** The flag
  crosses an HTTP boundary six ways, and nothing in the eval harness can issue a
  request: ADR-003 keeps the harness and CI's unit job stdlib-only, and the
  absence of `pip install` in that job *is* the enforcement. So the plumbing
  check reads `app.py` and `index.html` as text, says so in its docstring, and
  is paired with two known-bad fixtures proving it catches a default-on checkbox
  and a dropped flag. The real HTTP path was exercised manually on a throwaway
  venv and recorded as a one-off, not a gate, in its own debt row. The
  alternative — three CI jobs growing a web dependency to gate two keyword
  arguments — was the more expensive lie.
