# ADR-021 — The DONE split: a second sanctioned ledger file, and the rule that keeps its gates observable

Date: 2026-08-20. Status: accepted. Amends: ADR-009.

**Ruling**: `tasks/DONE.md` becomes the second sanctioned ledger file — an append-only, one-line-per-milestone archive; a row may leave `TODO.md` only when its Status carries no `UNRUN` gate.
**Because**: `TODO.md` is a working set (groundwork GW-004's hot/cold split) that has grown to 21 rows of settled history, and archiving it must not let an unobserved gate quietly disappear the way ADR-009 was written to stop.
**Enforced by**: `tasks/DONE.md` line format; advisory — no hook parses either ledger file

---

## Context

ADR-009 put every milestone row, done or not, in one file — `tasks/TODO.md` —
specifically so a **Validation** gate could never go missing inside prose, and
so an unrun gate had a place to say so out loud (`UNRUN`, never omitted). That
worked: three UNRUN markers (T3–T5's cold-reviewer, T5's spec-drift) have
shipped in the file since G1 and are still visible today, not silently
resolved.

The cost of the same design at month's end is legibility. `TODO.md` now
carries T1 through T11, three gate rows (G1–G3), two held-out runs (H1–H2), a
pre-submission row (S1), and an open-debt table — most of it settled weeks
ago and read past every time the file is opened to find what's *next*. That is
exactly the hot/cold split groundwork GW-004 names: a working set that never
sheds its cold history stops being a working set.

## Decision

1. **`tasks/DONE.md` is the second sanctioned ledger file.** Append-only,
   one line per milestone, index-only — the full row (Contents, Reviewer
   evidence, the complete Validation prose) stays in git history at the
   pre-split commit, not duplicated here. `TODO.md` remains the *only* place a
   milestone's status is live; `DONE.md` is where a settled one is indexed.
2. **A row may leave `TODO.md` only when its Status contains no `UNRUN`
   gate.** An `UNRUN` gate never enters cold storage — it either runs, or its
   skip is explicitly disposed in the row (the gate ran late, or was ruled
   unnecessary, with that disposition written into the row) before archival.
   This is the one rule that matters: it is what keeps ADR-009's core property
   — gates stay observable — true across the split. A row that is `done` but
   still carries `UNRUN` (T3, T4, T5 today) stays in `TODO.md`, full stop,
   regardless of age.
3. **Line format**:
   `- T5 — <title> (<date>) — validation: <gate> ran, disposed in <audit/ADR/PR ref>`.
   The date is the milestone's own completion date, not the split date. The
   disposition reference is the 1–3 most load-bearing artifacts a reader would
   need to verify the gate actually ran — an audit file, an ADR, a PR, a
   report path — not every commit sha the original row cited.

## Alternatives rejected

- **Archive by deleting the row outright.** `TODO.md`'s own header already
  promises "every row names its Validation gate" as the reason the file
  exists; deleting a settled row without a trace anywhere but git-log would
  make the promise only apply to work still in flight, which is a quieter
  version of the exact failure ADR-009 was written to fix.
- **One file, with a `done`/`archived` status value instead of a second
  file.** Keeps the legibility problem this ADR exists to solve — a reader
  still has to scroll past 14 settled rows to find T13.
- **Archive everything with Status `done`, UNRUN or not.** Considered and
  rejected in the same breath as rule 2 above: it is the one design that
  reintroduces exactly the failure mode ADR-009 named, an unrun gate that
  becomes unobservable, except now behind a second file instead of a prose
  clause.

## Consequences

- `TODO.md` shrinks to the rows still carrying live status: T3–T5 (UNRUN
  gates), T12 (in PR review, not merged), T13–T14 (todo), S2 (todo). Every
  `done` row with no UNRUN gate — 14 of them — moves to `DONE.md`, referencing
  the pre-split commit sha for the full text.
- The "Open debt, carried deliberately" table stays in `TODO.md` untouched:
  those rows are deliberate non-fixes with their own ADR-level disposition,
  not milestones with a pending gate, and moving them would blur the
  distinction this ADR is drawing.
- `TODO.md`'s header prose gains one line pointing at `DONE.md` and this ADR;
  the UNRUN doctrine text is otherwise untouched, because it is still the
  reason either file can be trusted.
