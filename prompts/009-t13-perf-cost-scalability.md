# 009 — T13: making the performance numbers reproducible (2026-08-20)

A pr-loop cycle whose deliverable looked like a documentation refresh and was
not. The ledger row asked for "large-filing + batch benchmarks, projection to N
filings"; the report already had all three. What it did not have was an *input*.
Outcome: [ADR-021](../specs/decisions/ADR-021-benchmark-instrument.md), one dev
instrument (`evals/bench.py`), analysis-report v4, and four published numbers
retracted.

## The prompt decisions that mattered

- **The validation gate was quoted at the implementer as the hard part, not as
  boilerplate.** "*every number measured from committed `evals/report/` runs,
  none guessed; the report cites its inputs*" — and then, explicitly: today's
  §3 numbers "came from ad-hoc timing that left nothing committed — a reviewer
  cannot reproduce or even locate them. Closing that gap is the substance of
  this milestone." Without that sentence the obvious reading of T13 is "re-run
  the timings and update the table", which would have reproduced the same
  uncitable numbers one corpus later. The gate was the task.

- **A precedent was named instead of a design.** "*Precedent for a committed
  measurement instrument that is not part of the scored suite: `evals/oracle.py`
  … Follow that shape if you add one.*" Pointing at an existing artifact rather
  than specifying an interface is what kept the instrument stdlib-only, dev-only
  and C7-safe without any of that having to be re-argued. Rung 2 of the ladder —
  reuse what is already here — applied to *process*, not just code.

- **The unavailable measurement was pre-disposed, with the fallback written
  out.** ADR-020 §f had asked T13 to firm the token estimates with
  `count_tokens`. The prompt closed that loop in advance: no paid call, no new
  dependency, "*and if neither is available without adding a dependency … or
  making a network call, keep the existing chars/4 estimate and say so
  explicitly in the prose, with the caveat.*" That converts an impossible
  instruction into a reportable non-result. The temptation it defused is real:
  an inherited "~$0.14" reads better without the word *estimate* next to it.

- **The recurring failure mode of this project was named by its shape.** "*do
  not assert a property of an executable contract in prose without running
  it*" — the error PR #11 caught four separate times in T12. In this milestone
  it bit twice anyway, once in the instrument's own self-check (chain entry 4)
  and once in the descending-size-order reading of memory (chain entry 2). Both
  were caught by *running* the thing rather than by re-reading it, which is the
  only reason they are chain entries and not shipped claims.

- **The instrument was told to make one specific question falsifiable.**
  Fixtures are timed in descending size order for a single reason: it turns
  "peak RSS scales with the largest document" from an assumption into a fact
  readable off the artifact. Designing the measurement around the claim most
  likely to be wrong is what found the one memory claim that was.

## What the instrument confirmed, and why that is recorded

A benchmark that only ever falsifies its predecessor is as suspect as one that
only ever confirms it. ADR-021 §d records three confirmations alongside §c's
four retractions — the no-warm-up property (v3 asserted it from one filing; it
holds across 37, with `first_s` in the artifact), ADR-020 §d's character counts
reproducing to the character, and ADR-020's four-times-corrected
addressable-surface arithmetic reproducing exactly. The last one matters most:
768 distinct items, 15 `missing`, the four improvable ones exactly `axp-2008`
10–13, recomputed from today's reports by a different person on a different
day. A headline that moved four times under review lands where §h3 left it.

## Assumption → Eval contradiction → Correction

- Assumed: §3's numbers were stale — measured over 21 fixtures instead of 37 —
  and a re-run at the current corpus would restate them larger.
- Eval said: `evals/report/20260820-020815-bench.json` — aggregate throughput
  **14.34 MB/s** against v3's 18.9, p95 **0.533 s** against 0.249, and a
  per-fixture spread of **6.3–42.8 MB/s** against a claimed "roughly flat
  8–37". `bac-2006` (4.5 MB) takes 2.1× longer than `xom-2021` (6.2 MB).
- Corrected: four numbers **retracted rather than replaced** — ADR-021 §c and
  report v4 §3 both print the old value beside the new one. "Cost tracks bytes,
  not document complexity" is narrowed to a first-order term plus a
  markup-density coefficient, with the R²=0.78 that licenses only that.

- Assumed: peak RSS scales with the single largest document, so the corpus peak
  and the largest filing's peak are the same number (v3 said 110 MB for both).
- Eval said: with fixtures processed in **descending** size order, `jpm-2024`
  alone takes the high-water to 96.4 MB and the corpus reaches 122.1 MB by
  roughly the tenth fixture, then holds flat for the remaining 27.
- Corrected: v4 §5 says *plateau*, not *largest document*. The 256 MB per-worker
  sizing survives; the reason given for it did not. Recorded because the sizing
  advice being accidentally right is not the same as it being justified.

- Assumed: ADR-020 §f's instruction to firm the token counts with `count_tokens`
  was executable at T13.
- Eval said: `count_tokens` is a network call, and neither `anthropic` nor
  `tiktoken` is importable here or listed in `requirements.txt` — checked by
  import, not assumed from the file.
- Corrected: chars/4 carried forward **with its caveat intact**, the ±20%
  margin stated, and the price basis marked *carried, not re-verified* with
  `cost.price_basis_date` stamped in the artifact next to every dollar figure.
  ADR-021 §b choice 7 records the non-result as a decision rather than leaving
  a silently unexecuted instruction in ADR-020.

- Assumed: the instrument's "this module cannot make a network call" self-check
  could be a substring scan of its own source.
- Eval said: `--self-check` failed on its first run — the scan matched its own
  banned-strings list.
- Corrected: the check parses its own AST and asserts the imported module roots
  are disjoint from the network set. Watched red first, per hard rule 2's
  spirit at the layer where this milestone had any executable logic at all.

- Assumed: v3's §6/§7 described current state.
- Eval said: both still called the sampled silent-failure rate "T11's work"
  after ADR-019 shipped it on 2026-08-19 — a forward reference to a milestone
  the same document reports on in §1.
- Corrected: both bullets closed with dated correction notes, and §7 item 5's
  successor restated honestly — the open question is the **interval**, not the
  point estimate, because n=30's upper bound is what stops the < 5% target
  being demonstrated.

- Assumed: correcting the report was enough.
- Eval said: `README.md`'s performance table carried the same four retracted
  figures, plus a claim that "analysis-report v2 re-measures at T10", which it
  did not.
- Corrected: README's table rebuilt from the same artifact, with its own dated
  correction note. A number is not retracted while a copy of it is still
  published one file over.
