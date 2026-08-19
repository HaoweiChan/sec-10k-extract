# 008 — T12: ruling the LLM fallback stage out (2026-08-19)

A pr-loop delivery cycle whose deliverable is a *decision*, not a feature. The
implementer prompt was written so that both outcomes were explicitly legitimate
completions — "do not ship a fallback to look productive, and do not decline one
to avoid work" — and so that the decision had to survive a named, pre-existing
objection rather than be argued from the number closest to hand. Outcome:
[ADR-020](../specs/decisions/ADR-020-fallback-not-justified.md), **not
justified, no fallback ships**, plus one new enumerated debt class and one
burned held-out case.

## The prompt decisions that mattered

- **The task was framed as a decision with two valid answers, and the null
  result was named as the cheap one.** A task defined as "build the fallback
  stage" produces a fallback stage. Naming "*'not justified' recorded in an ADR
  is a valid completion*" in the ledger row, *before* the data existed, is what
  made the null result reportable instead of embarrassing. Every other rule in
  the prompt then applied symmetrically to both answers.

- **A specific bad argument was pre-banned.** The prompt named the metric-11
  circularity — already sitting in `docs/analysis-report.md` as a known defect —
  and said "*a ruling that leans on metric 11 without disposing of this
  circularity is not an argument. Whichever way you rule, dispose of it
  explicitly.*" That is the single most load-bearing instruction in the session:
  the easy path was "deterministic coverage is 100%, therefore no fallback",
  which is the circular claim wearing a number. Banning it forced the search for
  a non-circular substitute, which is where the actual finding came from (§b
  below).

- **The candidate design was pinned, and the right to reject the pin was
  granted.** "*Judge THIS candidate, and say so if you judge a different one.*"
  Without the pin, "an LLM fallback" is a moving target that can be redefined
  around every objection; with it, the design's own safety property (one
  contiguous verbatim slice, INV-S2 by construction) could be turned into an
  argument against it on `msft-2013`, where the fix requires a discontiguous
  span and the safety property therefore makes the stage structurally useless.

- **The evidence was enumerated as a checklist of failure classes, each with a
  forced question**: "*for each, would the candidate fallback have fixed this,
  and at what cost, and with what new failure mode?*" Requiring the third
  clause — the new failure mode — is what surfaced the strongest single result,
  that on the one case where the fallback *would* fire it makes the output
  worse rather than better.

- **Spending was fenced off from the agent's authority.** "*Any code path that
  would spend money must not be exercised against a live paid endpoint in this
  task — the human owns that spend decision… never invent a key, never mock a
  response to make a case green.*" This kept hard rule 4 and the cost-discipline
  skill from colliding: the cost model in ADR-020 §d is computed from committed
  fixture character counts and a published price sheet, never from a live call,
  and it says so.

## Assumption → Eval contradiction → Correction

- Assumed: metric 11 ("deterministic coverage %") is the number that decides the
  fallback question — `docs/evals/evaluation-strategy.md` said so in its own
  metric table, and `docs/analysis-report.md` §4 used it that way ("today it
  kills it").
  Eval said: metric 11 reads **1.0 (n=636)** on the committed all-suite report
  and would read 1.0 on any report, because it counts an *output* of a stage
  that does not exist. The claim is circular; `analysis-report.md:101-102` had
  already conceded this and then used the number anyway three hundred lines
  later.
  Corrected: the ruling rests on a different quantity — the fallback-**addressable
  surface**, an *input* (which items any honest trigger would fire on),
  computable today from committed reports with zero fallback code: 11/868 dev
  items and 4/121 held-out items report `missing`, of which **0 of 989 would be
  improved**. Metric 11 is demoted to a dependence monitor in
  `evaluation-strategy.md`, in `evals/metrics.py` (a `note`, the only code change
  this milestone makes), and by a dated correction in `analysis-report.md` §4.

- Assumed: a fallback stage is the natural instrument for the residual failures
  T11 measured — that is what the architecture doc had reserved layer 10 for
  since T1.
  Eval said: walking all six committed debt rows, the candidate never triggers
  on five of them. `ba-2003` items 11/13, `cvx-2015` items 7/8, `msft-2013`
  Item 1 and the `EXEC_OFFICERS_RE` TOC gap are all reported `extracted` at
  0.95 — ADR-019 measured the defect population and it sits at full confidence,
  not at absence. A fallback fires on absence.
  Corrected: ADR-020 §c states the general form — *a fallback is a recall
  instrument and this pipeline's remaining defects are all precision* — and
  §e names, as the first reopening condition, the specific evidence that would
  falsify it: one real-filing `missing` item whose content a reader can point to
  and which no deterministic heading-shape change reaches.

- Assumed: the corpus contains no real-filing item-recall failure at all, so
  the addressable surface is trivially empty and the ruling is easy.
  Eval said: the committed held-out report `20260817-224952-fast.json` has
  `axp-2008` items 10–13 all `missing` at 0.40 — and the filing *does* contain
  them, under one combined heading. Verified in the **raw bytes**, not through
  the normalizer: exactly one `ITEMS\b` match in 1,296,375 bytes, at offset
  1225493, reading `ITEMS 10, 11, 12 and 13.` followed by the four-item title
  and an explicit proxy incorporation by reference.
  Corrected: enumerated as a new debt class
  (`evals/adversarial/axp-2008-combined-part-iii.json`, `debt` suite, permanently
  red, **watched red before the ADR was written**, no fix attempted under the
  T8 freeze). And it strengthened rather than weakened the ruling: the candidate
  fallback would locate this text and emit `extracted` where the truth is
  `incorporated_by_reference` — converting an honest `missing` (low confidence,
  warning fired, `doc_status` escalated) into a confident misclassification, for
  money, when a heading-shape change fixes it deterministically at $0.

- Assumed: citing a held-out result in a written ruling is reporting, not
  influence — nothing was fixed because of it.
  Eval said: `evals/heldout/README.md`'s burn rule counts "a new case written
  because of it" as influence, and the `gs-2002` burn of 2026-08-17 had already
  established that *declining* a fix with a case's outcome in hand burns it as
  surely as fixing does.
  Corrected: `axp-2008` is declared burned in ADR-020 §g and in the held-out run
  history; the effective held-out set drops to 5 until T14's refresh. While
  recording the burn, the case's own label turned out to be wrong — its
  provenance scan checked only the **singular** strings `Item 10`…`Item 13`,
  found zero, and concluded Part III had no headings at all. Sixth time in this
  project that the verification instrument rather than the pipeline was at
  fault. Re-labelling it is T14 taxonomy work and was deliberately not done here.

- Assumed: closing the metric-11 circularity properly means shipping a metric
  that computes the addressable surface, so the reopening condition has an
  instrument rather than a promise.
  Eval said: the quantity is a count of `status: "missing"` in `items_summary`,
  which every report the runner writes already carries — the instrument exists
  and the reports are committed.
  Corrected: no new metric. ADR-020 §g records the omission and why, and §e
  names where to look instead. Adding a second way to compute a number the
  reports already carry is the speculative instrument both the ADR-010 sin and
  the repo's own laziness rule argue against.
