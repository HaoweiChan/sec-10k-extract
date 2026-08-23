# 016 — D2: re-publishing the numbers of record, by the instrument and not by hand (2026-08-23)

The D2 row promoted six Debt rows that had each said the same thing in a
different key: a published figure had gone stale and the honest fix was a
re-run of the instrument that produced it, not an edit. The bench artifact of
record (`20260820-031540`, n=37) predated the `<title>` skip that moved every
`normalized_chars` integer, four fixtures and the `tables=True` path; the
calibration table (2026-08-18) predated ADR-027 moving its population; the
94.6 MiB RSS figure was contradicted by a sibling artifact in its own PR; and
the mechanical check that was supposed to catch stale fixture-attributed
numbers exited 0 when it checked nothing and ran in no gate. Ruling:
[ADR-021 §g](../specs/decisions/ADR-021-benchmark-instrument.md), amended in
place.

## The prompt decisions that mattered

- **Gate first, then the run.** The orchestrator's ordering — make
  `--check-docs` fail closed and wire it before a single number is
  re-derived — is the whole reason the re-derivation is checkable. Watched
  red on the pre-D2 code: `DOC_WINDOW=0` and a renamed `DOC_FILES` entry both
  exited 0 on "0 checked, 0 unmatched". After the fix both exit 1 with a line
  saying why, and `_demo` drives `check_docs` on scratch docs for every
  outcome, so `--self-check` pins the rule instead of a sentence claiming it.

- **Commit order is an honesty constraint, not housekeeping.** The bench run
  stamps its git sha and a `-dirty` suffix (ADR-018), and PR #12 R15 was a
  dirty-tree artifact of record. So the instrument change (the `tables=True`
  column, the fail-closed check) had to be committed first, the three runs
  made on that clean tree, and the artifacts committed with the docs that cite
  them — which is why the hook's `--check-docs` pointer names the 2026-08-20
  artifact at commit 1 and the 2026-08-23 one at commit 2, and never a file
  that does not exist yet.

- **Match the method, including the part that did not fit.** ADR-021 §b11
  chose its run of record as "the middle of three on every headline". Three
  new runs were made on the same terms; no run was the middle on all six.
  The choice is `-185707`, middle on four and highest on two by 0.0002 s and
  0.010 s, and §b11 now says so — the rule extended in writing rather than
  satisfied quietly.

- **A range where a value was claimed.** Seven clean-tree runs of this
  instrument revision are committed; the largest-filing RSS reads 94.6, 94.6,
  94.6, 102.4, 95.7, 100.5, 94.6 MiB. "Stable to 0.1 MiB" was a three-run
  observation that the fourth falsified (R25). It is published as
  94.6–102.4 MiB everywhere it appears, and the v4 sentence is struck in
  place, not deleted.

- **The `tables=True` column was small enough to take, and the memory
  question was not.** One extra pass per fixture, run *after* every RSS
  reading so the memory family stays comparable with the earlier artifacts;
  two record fields, three derived fields, a golden record and payload pinned
  by hand. Its memory cost is stated as unmeasured rather than estimated.

- **Dated rulings keep their numbers.** ADR-020 §d's character table and
  ADR-010's "13 normalized chars" are what those rulings saw on their dates.
  Each gets a one-line dated note pointing at the new artifact; neither is
  rewritten. The report's §3/§4.1/§5, by contrast, are the *live* statement
  of the numbers and are re-derived in place, with v4's values kept in the
  relabelled "Corrections to v3" table and the version block.

## Assumption → Eval contradiction → Correction

- **Assumed:** re-running the instrument on more fixtures would move the
  headline latencies by the corpus-growth direction — p95 up or flat.
- **Eval said:** p95 read **0.40 s** against v4's 0.51 s, with both of the
  filings involved measurably *slower* than on 2026-08-20. Nearest-rank p95 at
  n=41 is the 39th of 41 medians; four small fixtures had joined below the
  36th-of-37 position, so the rank fell on `cvx-2015` instead of `bac-2006`.
- **Corrected:** every place the p95 appears says "a rank effect, not a
  speed-up", README included; the report's §3.2 has a paragraph on it so the
  drop cannot be read as an improvement.

- **Assumed:** the docs, once re-derived, would read 0 unmatched under
  `--check-docs` with only the dated history entries added to `DOC_ALLOW`.
- **Eval said:** `msft-2013` 1.1 and `bac-2006` 1.1 unmatched — literals that
  exist nowhere in the docs. The check slices the text at the 60-character
  window edge before matching, so the new table's `1.18×` ratio, straddling
  the edge, was read as `1.1`. On the golden corpus the same slicing reads
  `0.45` at the edge as `0.4` — `cat-2023`'s median — and **passes** it.
- **Corrected:** a number that starts inside the window is read whole; pinned
  in `_demo` with both the false-pass and the correct-pass doc; watched red on
  the sliced version first.

- **Assumed:** the cost counterfactual's "median filing" would stay a real
  filing.
- **Eval said:** at n=41 with 13 synthetic members the 21st-of-41 by
  normalized chars is `amended-cover-2021`, a self-created copy (102,453
  chars). The instrument's median is the instrument's median.
- **Corrected:** reported as measured and labelled — "and it is now a
  synthetic derivative, because the median of 41 lands on one" — rather than
  re-defined to land on a real filing.

- **Assumed:** the whole corpus would time within ±3% of the 2026-08-20 runs
  on the same machine.
- **Eval said:** 5–7% slower across the board — batch 14.8 → 14.1 MiB/s, the
  largest filing 0.548 → 0.582 s — and `src/` had changed between the two
  dates (T3, D1, S7) as well as the day. The instrument cannot separate tree
  from machine.
- **Corrected:** stated in the report and ADR-021 §g as not attributed; filed
  as a Debt row (Origin: D2) naming the one measurement that would settle it.

- **Assumed:** `DOC_ALLOW` only ever grows.
- **Eval said:** a hit-count over the list found two entries nothing reaches
  any more (their ledger rows had moved to `DONE.md`) and five that D2's own
  re-derivation rewrote out (four cross-run ranges, §c's 0.55).
- **Corrected:** seven removed, thirteen added, each new entry naming the
  value that superseded it; `len(DOC_ALLOW)` 20 → 26 in ADR-021 §b12.
