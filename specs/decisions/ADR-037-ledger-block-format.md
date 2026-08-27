# ADR-037 — The ledger converts to the groundwork pr-loop block format

Date: 2026-08-27. Status: accepted. Amends: ADR-009, ADR-022.

**Ruling**: `tasks/TODO.md`'s format is now the groundwork pr-loop block format (`### <id> — <title> [status: ...]`); the ADR-009 UNRUN doctrine and the ADR-022 DONE split are unchanged; the "Open debt, carried deliberately" table becomes `TD-*` blocks, each carrying a mandatory `Priority:`.
**Because**: the milestone table was invisible to the shared pr-loop dependency board (`ready.py`), and its Depends/priority information was unreadable by tooling built to parse the block format, not a Markdown table.
**Enforced by**: `ready.py` (the pr-loop dependency board; advisory, no hook parses it) plus the existing `repo_hygiene` checks unchanged by this diff — `ledger_table_shape`, `ledger_line_refs`, `adr_headers`/`adr_index`

---

## Context

`tasks/TODO.md` has been a Markdown table since ADR-009 (2026-08-16): one row
per milestone, a `Depends` column, a `Status` column carrying `UNRUN` in the
open rather than letting a gate go missing inside prose, and a second "Open
debt, carried deliberately" table for decisions not to build something. That
design has held up — the UNRUN doctrine has caught real gaps (T3-T5's
cold-reviewer clause, D10's post-deploy M41 re-probe) — and this ADR does not
touch it.

What changed is that this repo installed the groundwork plugin's `pr-loop`
skill, which ships a dependency board (`ready.py`,
`~/.claude/plugins/marketplaces/groundwork/plugin/skills/pr-loop/scripts/ready.py`,
verified at commit `f80c609` — after `a063df6`, the commit that first parses
hyphenated word-ids without digits, which `TD-*` needs) that renders "what is
ready to run right now" by parsing `### <id> — <title> [status: ...]` blocks
with `Depends:`/`Priority:` lines. A Markdown table has no representation the
board can parse: the Depends column exists in prose only, and there is no
priority signal at all. The board is advisory tooling, not a gate — but a
ledger a shared script cannot read is exactly the "gate that has not run [or
cannot be observed]" class ADR-009 exists to prevent, one level up: not an
unobserved validation gate, but an unobservable ledger.

## Decision

1. **Format**: every live row becomes a block —
   `### <id> — <title> [status: todo|in-progress|pr|merged|blocked|done|parked]`,
   optionally followed by `Depends:`, `Priority:` (`P1`/`P2`/`P3`), `Origin:`,
   `Spec:`, `Reviewer evidence:` (Queue only), `Acceptance:`, `Not taken
   because:` (Debt only) and, whenever a gate is still outstanding, a
   `Status:` line carrying the full original status prose verbatim — so an
   `UNRUN` gate is never hidden behind the short bracketed tag. The bracketed
   tag is a best-effort machine label for the board; the `Status:` line (or,
   for a row with no outstanding gate, the Acceptance itself) remains the
   authoritative, human-readable account ADR-009 requires.
2. **Sections unchanged in purpose**: `## Queue` holds every non-done
   milestone row in the table's own order (D8-D11 today; the two currently-
   empty post-freeze/pre-submission tracks keep their header prose with no
   blocks). `## Debt` holds the former "Open debt" table, one block per row,
   in the table's own order.
3. **`TD-*` is a new, disjoint id namespace for Debt.** This repo already
   uses `D<N>` for milestone tasks (D1-D12); minting Debt ids in the same
   space would make a `Depends:` reference ambiguous between "blocked on
   milestone D9" and "carries the same debt as row D9". `TD-1` through
   `TD-154` are minted in the pre-conversion table's row order, skipping the
   ten rows the table had already struck through and marked PROMOTED to a
   milestone id (D1-D5) — those are archived under that milestone id in
   `tasks/DONE.md` already, and the struck row is unchanged in git history.
4. **Priority is mandatory on every Debt block** (`P1` = correctness/honesty
   risk in shipped behavior, `P2` = a contained/declared limitation, `P3` =
   speculative or documentation-only) and optional on Queue blocks, added
   only where the content itself argues for a non-default value.
5. **Nothing about what is decided moves.** No row's status flips, no id is
   renumbered, `tasks/DONE.md` is untouched (struck/PROMOTED rows already
   have their DONE.md line), and every `Spec:`/`Acceptance:`/`Not taken
   because:` carries its source cell's substance losing no decision-relevant
   fact — the Debt cells are reproduced verbatim, since ADR-009's gate-
   observability doctrine binds the Acceptance text of a live milestone row
   the same way whether it sits in a table cell or a block field.

## Alternatives rejected

- **Leave the table and teach `ready.py` to parse it.** `ready.py` is
  upstream groundwork tooling shared across every repo that installs the
  plugin; forking its parser for one repo's table dialect is the opposite of
  what an installed, shared skill is for, and the block format is already
  the convention this repo's own `docs/product/milestones.md` A-track
  decomposition anticipates ("Milestone-level only... micro-tasks live in
  the session").
- **Convert only the Queue table, leave Debt as a table.** Considered and
  rejected: Debt rows carry real `Origin`/reasoning structure the block
  format expresses more legibly than a three-column table already straining
  under paragraph-length cells (`ledger_table_shape`'s whole existence is
  evidence the table format was under strain), and a mixed file is a worse
  reading experience than a converted one.
- **Renumber Debt ids to continue the `D<N>` sequence.** Rejected in Decision
  point 3 above: collision risk with milestone ids in `Depends:` lines is a
  parsing ambiguity a shared board should never have to resolve.

## Consequences

- `tasks/TODO.md` is now block-formatted throughout `## Queue` and `## Debt`;
  the `## Settled — IBR offsets (G1)` prose section is untouched, since it
  was never a table row.
- `ready.py` renders the file: 4 Queue blocks (D8 `pr` with no dependency,
  D9 `pr` depending on D6, D10 `merged` with no dependency, D11 `blocked`
  depending on D6 and D8) and 154 Debt blocks, all shown `parked` per the
  board's own Debt-section rule.
- The three `repo_hygiene` checks that read `tasks/TODO.md`
  (`ledger_table_shape`, `ledger_line_refs`, and `evals/bench.py
  --check-docs`'s fixture-decimal scan) all still pass unchanged: the first
  finds no table rows left to check (vacuously green), the second finds the
  same `` `path:line` `` citations it always did since every cell's text is
  reproduced verbatim, and the third finds the same fixture-attributed
  decimals in the same relative order.
- `specs/decisions/INDEX.md` gains one line for this ADR; ADR-009 and
  ADR-022's own Status lines each gain `ADR-037` to their `Amended by:` list.
