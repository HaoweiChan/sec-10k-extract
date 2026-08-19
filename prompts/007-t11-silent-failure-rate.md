# 007 — T11: silent-failure rate (2026-08-19)

Orchestrated session, three independent measurement passes feeding one ruling:
a planning/audit pass that scanned the codebase for the debt-row and
internal-pointer findings (`scratchpad/t11-my-audit.md`); an extraction-auditor
subagent that blind-adjudicated a random sample of 30 untargeted confident
items (`docs/evals/audits/2026-08-19-t11-silent-failure-sample.md`); and an
OSS-oracle investigation run in two stages — a throwaway spike comparing
`sec-parser` and `edgartools` on three fixtures, then a full-corpus run of the
adopted tool (`scratchpad/t11-oss-spike.md`, `t11-oss-oracle-findings.md`).
This session's job was the one code ruling the evidence pointed to
(`EXEC_OFFICERS_RE`) plus the written record — ADR-019, the TODO/analysis-
report/evaluation-strategy reconciliation, and this file.

## The prompt decisions that mattered

- **Sample before ruling, and record the seed.** The extraction-auditor's
  30-item sample was drawn with `random.Random(11).sample(population, 30)`
  before any adjudication happened, and the seed is committed in the audit
  file — the draw is reproducible and cannot have been adjusted after seeing
  which items looked easy or hard.
- **The auditor was blind to implementation reasoning.** Its own scope note
  says explicitly: "no implementation plans, ADRs, or
  `docs/architecture/overview.md` were read." That is what makes its one
  disagreement with the implementer (cvx-2015 item 6) worth recording instead
  of discarding — two readers who did not compare notes landed in different
  places on the same shape.
- **The OSS spike was told to look for the failure mode, not just the
  success rate.** The instruction to quote actual tool failures (not just a
  pass/fail count) is what caught `sec-parser`'s worst property: on plain
  text it doesn't crash, it emits a confidently mislabeled section — worse
  than a crash for a cross-check oracle, and invisible to a simple
  agree/disagree tally.

## Assumption → Eval contradiction → Correction

- Assumed: metric 6, which has read 0.0 since it was built, measures the
  silent-failure rate — ADR-018 named it "T11's charter" without qualifying
  what it can see.
  Eval said: metric 6's denominator is items a *declared check* targets, and
  the pre-commit gate requires every declared check to pass — so it reads 0.0
  by construction, and excludes 447 of 781 confident items as untargeted.
  Corrected: the rate is measured by sampling the excluded population
  directly (ADR-019 §a/§b); `evals/metrics.py`'s metric-6 note now says the
  value is gate-bounded and points at the sampled figure instead of standing
  alone.
- Assumed: an OSS second-extractor oracle would drop in cleanly — T11's own
  TODO row named it as a viable second measurement instrument without having
  tried one.
  Eval said: the spike found `sec-parser`'s entire taxonomy is 10-Q-only (zero
  hits for "10-K"/"Edgar10K" in its own package), it never classifies Items
  1A/7/8 as sections on any fixture tried, and on plain text it emits
  confidently mislabeled sections rather than failing loudly.
  Corrected: `sec-parser` ruled out outright. `edgartools` adopted instead,
  but only via its low-level, network-free `HTMLParser` entry point (not the
  network-touching `Filing`/`TenK` path), compared on content similarity only
  (its offset fields are dead, always 0 — confirmed directly), with zero
  plain-text coverage disclosed as a limitation rather than assumed away.
- Assumed: `tasks/TODO.md`'s "no span-coverage validator" row was correctly
  specified and, per ADR-015 §5, the strongest candidate for the first
  post-freeze exception.
  Eval said: direct computation over all 36 fixtures showed coverage already
  equals `1 - unattributed_content`'s own "outside" fraction to float
  equality (33/33), and the largest inter-span gap is structurally always 0.0
  on every fixture, because `assign_boundaries` makes accepted spans
  contiguous by construction — the planned capability would have caught
  neither Intel's nor Target's failure, the two filings ADR-015 §5 cited to
  justify it.
  Corrected: the row is retired (ADR-019 §d) with a dated correction note
  added to ADR-015 §5, not a rewrite of its history; the correctly-specified
  successor — a non-last span dominating the document, plus the
  escalation-policy question — is named as the real debt instead.
- Assumed: the `EXEC_OFFICERS_RE` fix, already proven on 6 of 7 affected
  fixtures, would take the 7th (`msft-2013`) the same way.
  Eval said: `--suite fast` dropped to 0.977 — `msft-2013-content`'s Item 1
  closing anchor died, because this fixture's layout interleaves the officer
  bios *between* two pieces of genuine Item 1 content (the body, then a
  1,643-char "Available Information" paragraph after the bios), and INV-S2's
  contiguous-span rule means no fix can keep both.
  Corrected: ADR-019 §f rules to keep the clip anyway — over-attributing
  Part III content to Item 1 is worse than a boundary-tightness loss the
  item's own length band already tolerates. The dead anchor is not deleted;
  it moves into a new permanently-red debt case
  (`evals/adversarial/msft-2013-website-block.json`) that keeps the lost
  content visible. Fast returns to 44/44 (+3 enumerated debt, unscored).
- Assumed: a disagreement the extraction-auditor's charter raises should be
  resolved in favor of whichever reading has better evidence.
  Eval said: the auditor read `cvx-2015` item 6 (an internal pointer to a
  paginated section) as CORRECT — the pointer sentence is honestly the whole
  labeled answer — while the same planning pass read the identical shape in
  the same filing's items 7/8 as WRONG; item 6 itself was never checked
  against items 7/8 by the same reader, so there is no single adjudication to
  defer to.
  Corrected: ADR-019 §e records the disagreement explicitly rather than
  picking a winner, per the auditor's own charter (a disagreement it raises
  needs an ADR to settle, not a return prompt to overrule it), and the
  sensitivity analysis in ADR-019 §b publishes both readings (1/30 and 2/30)
  side by side instead of collapsing to one number.
