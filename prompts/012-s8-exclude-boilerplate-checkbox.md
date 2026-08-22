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

## Round 1: what the falsification discipline did NOT catch

The round-1 mutation battery was ten wrong implementations of the thing being
built, and every one went red. The reviewer then found a HIGH the battery could
not have found, because it was not a wrong implementation of this feature at
all — it was a correct one colliding with a different feature's contract.

- **`item.text` had two consumers, and the diff only looked at one.** Besides
  the pane, `text` is the body-agreement oracle `findAnchor` matches against the
  ORIGINAL filing to tell an item's real heading from its table-of-contents
  entry (PR #21 spent three rounds on that). The original filing still contains
  the chrome, so feeding that consumer the stripped string cost six items their
  source anchor — silently, on fixtures reachable from the dropdown. Every
  mutation in the battery asked "is the stripped string right?"; none asked
  "who else reads this field?". The generalisable rule is the ponytail one
  already in the toolchain and not applied hard enough here: *before you change
  a function, grep every caller* — and a payload key is a function signature.
  The fix is the same shape as the rule: `text` keeps its single meaning for
  every consumer and the render point gets its own `display_text`, rather than
  the anchor path getting a special case.

- **A check written to bind two things can still be checking one.** R2 showed
  four ways to sever the wire that the plumbing check called green, because it
  asked each END whether it mentioned the flag rather than asking whether the
  two ends AGREED. Two of them defeated the feature's headline requirement. The
  rewrite derives what the client puts on the wire and what the server reads off
  it and compares the two sets — and re-running R2's own mutation (b) against
  the *rewritten* check immediately found a second defect in it (a 400-character
  window that ran into the next call site, so a hardcoded call site borrowed its
  neighbour's `excludeBp()`). Re-running the mutations after the repair, rather
  than assuming the repair covered them, is what turned that up.

- **An honest "cannot" beats a green that needs a dependency.** The reviewer
  offered an HTTP TestClient case as the alternative, and it was rejected on a
  mechanical fact rather than taste: `evals/run.py` scores `passed / len(results)`
  over a bool and has no skip state, so a fastapi-dependent case is either
  silently green where the dependency is absent or red in three CI jobs that
  install nothing by ADR-003. The debt row was corrected instead — it had named
  three failure shapes and missed four measured ones, which is its own small
  version of the same sin the checks keep being caught for.

## Round 2: asking a question versus pinning an answer

Round 1's lesson was "grep every caller". Round 2 found that lesson applied to
the code and not to the check, twice in the same PR, and the second time it
was the round-1 repair that caused it.

- **A repair can relocate a property instead of covering it.** Before round 1,
  `item.text` carried the stripped string, so the eval that pinned `text`
  pinned the rendered string as a side effect. Splitting out `display_text`
  fixed the anchor bug and, in the same stroke, moved the feature's headline
  behaviour into a client-side expression nothing read: deleting
  `it.display_text ?? ` left both suites at 1.000 while the pane showed
  un-stripped text under a header saying "boilerplate hidden". The rule worth
  keeping: after any repair, ask what the pre-repair check was pinning *by
  accident*, because that is what the repair just released.

- **Allow-list, not block-list, for a wire made of strings.** The reviewer's
  acceptance for the second finding was phrased as a ban — no `not`, no `!=`,
  no constant between the request read and the kwarg. Banning is the wrong
  shape: it only ever excludes the inversions somebody already thought of, and
  three rounds running the next unbanned one was found (`not bool(...)`,
  `!= "1"`, `False and bool(...)`, `return true`, a wrong element id). Pinning
  the *permitted* expression whole makes everything else red by default,
  including the inversion nobody has thought of yet. It also made the check
  shorter than the "binding" version it replaced, which is the usual sign the
  shape was wrong before.

- **Then attack the new check, before the reviewer does.** Four attacks were
  written against the allow-list itself rather than against the hops it pins.
  Three passed it: a second `excludeBp` definition shadowing the pinned one
  (declarations hoist, the last binds), a `disabled` checkbox that leaves every
  hop intact and the capability unreachable, and a call site commented out with
  its pinned text still in the file. All three are now closed and committed as
  fixture shapes. The one above them — an expression that is present, live, and
  never reached — is not closed, and is written into the debt row as the
  ceiling of what reading two files as text can ever prove. Naming the ceiling
  is the part that stops the next round rediscovering it.
