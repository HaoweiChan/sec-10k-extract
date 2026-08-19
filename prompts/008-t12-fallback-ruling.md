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
  clause — the new failure mode — is what drove the walk-through of all seven
  classes. It also produced the draft's one real error: on the single row where
  the fallback *would* fire I asserted a new failure mode that did not exist,
  and review caught it (last chain entry). The forced question was right; the
  answer wanted a run, not a recollection.

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
  computable today from committed reports with zero fallback code: **15 of 989**
  distinct items across both eval sets report `missing`, of which **4 would be
  improved** (that figure was first published as 0 and corrected in review — see
  the last chain entry). Metric 11 is demoted to a dependence monitor in
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
  T8 freeze). These four items are the entire real-filing addressable surface.
  They do not flip the ruling, because combined-heading fan-out — a heading-shape
  change — produces the identical span and status through the same classifier,
  deterministically, at $0, for the whole class rather than the instances a model
  is invoked on. *(This entry originally claimed the fallback would make the row
  **worse** by emitting the wrong status. That was wrong — see the last entry.)*

- Assumed: citing a held-out result in a written ruling is reporting, not
  influence — nothing was fixed because of it.
  Eval said: `evals/heldout/README.md`'s burn rule counts "a new case written
  because of it" as influence, and the `gs-2002` burn of 2026-08-17 had already
  established that *declining* a fix with a case's outcome in hand burns it as
  surely as fixing does.
  Corrected: `axp-2008` is declared burned in ADR-020 §g and in the held-out run
  history, and — after review pointed out that a burn declared in prose while the
  file stays put is enforced by nobody — **moved in the same milestone**, per the
  rule's own wording and the `gs-2002` precedent: case to
  `evals/adversarial/axp-2008-combined-heading-burned.json`, fixture to
  `evals/fixtures/axp-2008/`. Held-out is now 5 cases / 101 items because the
  file system says so, not because a README asserts it. While recording the burn,
  the case's own label turned out to be wrong — its provenance scan checked only
  the **singular** strings `Item 10`…`Item 13`, found zero, and concluded Part III
  had no headings at all. Sixth time in this project that the verification
  instrument rather than the pipeline was at fault. The four wrong assertions were
  dropped in the move rather than re-enshrined.

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

- Assumed: `axp-2008`'s Part III items are `incorporated_by_reference` — the
  block opens with "a definitive proxy statement… is incorporated herein by
  reference" followed by ten caption bullets, which is ADR-004 shape 1 on sight.
  The first draft of ADR-020 built its headline on that reading: the candidate
  fallback emits `extracted`, so it would get this row *wrong*, so the
  addressable surface was **0 of 989** and the fallback fixed nothing.
  Eval said: the pr-reviewer, with no access to any of this reasoning, ran the
  classifier. `segment.classify('10', body, True)` returns **`extracted`**.
  ADR-004 reserves IBR for bodies that are *solely* pointers and ADR-007
  implements it as `rest <= IBR_REMAINDER_MAX (300)`; this body carries **1,139
  chars** of substantive standalone prose after the pointers — the Corporate
  Governance Principles / Code of Conduct paragraph, Reg S-K Item 406
  code-of-ethics content that explicitly says the linked material "is not
  incorporated by reference into this report". Shape 3, `extracted`. So the
  candidate would have got the row **right**, the surface was **4**, and the
  debt case's `incorporated_by_reference` assertions were unreachable — it could
  never have gone green even after the capability it names shipped, breaking its
  own "NOW GREEN — promote it" contract.
  Corrected: the case is re-labelled to `extracted` ×4 (plus a `min_chars` floor
  pinning that the real block is attached, not the heading line) and watched red
  again; ADR-020 §a/§b/§c row 7 are rewritten and §h records the whole exchange;
  every propagated number is updated. **The ruling was re-derived, not
  preserved** — it survives on the escalation ladder, which is also what §e
  condition 1 had already said. The prompt instruction that made this
  recoverable was the coordinator's: *"if the evidence now points the other way,
  say so. A reversed ruling caught by review is a success of this loop."*
  The lesson is narrower and sharper than "check your work": I matched a
  pointer-shaped opening to an ADR shape **from memory** and never ran the
  classifier that owns the decision, on a repo whose entire premise is that
  correctness is executable. Seventh time in this project that the instrument —
  here, me — rather than the pipeline was at fault.
