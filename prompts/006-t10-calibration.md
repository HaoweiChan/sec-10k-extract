# 006 — T10: confidence calibration (2026-08-18)

Orchestrated session: the planning/audit model wrote the measurement design and
ADR-018's ruling; implementation was delegated to a smaller model in three
briefs (instrument, remap, audit-fix batch), each returning red-watch proof and
verification output for the orchestrator to audit. Two repo agents
(cold-reviewer, extraction-auditor) ran against the uncommitted change.

## The prompt decisions that mattered

- **Instrument before ruling.** The delegated brief for the measurement
  explicitly forbade any scoring change, and the orchestrator committed the
  instrument + measured report (d3a28df) before writing a word of ADR-018.
  T10's gate ("table before remap") got a commit boundary, not a promise.
- **Red-watch as a deliverable.** Every implementation brief required the
  failing output verbatim before the fix ("if it passes, stop and report").
  This caught nothing by luck — it caught by construction: the Fix-1 brief's
  tripwire ("verify the span is clean; if not, STOP, do not invent a fixture")
  is the only reason the spans-transposed case was not shipped green-by-
  accident over a span that could never fire.
- **Audits scoped to the change, not the repo.** The extraction-auditor brief
  named the exact artifacts and claims to verify (both reports, the phantom-
  0.55 claim, the net-zero claim, contradictions in committed held-out data);
  it came back with eight findings including two false claims in the
  milestone's own freshly written prose.

## Assumption → Eval contradiction → Correction

- Assumed: the debt failures both sat at 0.95 (both ba-2003 items looked
  strict-match).
  Eval said: the metric 8 v2 join (report 20260818-123114) put item 13 at
  0.75 — overconfident wrongness spans the top AND middle of the scale.
  Corrected: ADR-018's "status defect, not scale defect" ruling was written
  from the measured pair, not the assumed one.
- Assumed: "the debt suite runs every run" (stated in ADR-018's draft, the
  ba-2003 triage note, and tasks/TODO.md).
  Eval said: extraction-auditor F2 — the fast and invariant reports carried
  `"debt": []`; debt cases loaded only under `--suite all`, so the pre-commit
  gate never exercised the calibration's only failure channel.
  Corrected: run.py loads debt-suite cases on every suite; the claim became
  true instead of the prose becoming softer.
- Assumed: metric 8's note could point unaudited debt items at metric 6.
  Eval said: both audits independently — metric 6 never reads debt rows; 12 of
  the debt case's 13 confident items were counted nowhere.
  Corrected: `debt_unaudited` computed and published in metric 8 itself.
- Assumed: a `keyword_fingerprint` positive case (spans-transposed, item-scoped
  to 1A) could be watched red on a committed fixture.
  Eval said: the probe inside the fix brief — the transposed financial prose
  still contains "risk" and "could" as whole words; no committed fixture can
  make the 1A branch fire.
  Corrected: proved red→green at the validator's own layer (`_demo`, ADR-016
  pattern) with a revert/recapture zero-delta bracket over all 45 fixtures;
  the fixture-level check was NOT added.
- Assumed: net-zero could be evidenced by comparing the before/after reports.
  Eval said: extraction-auditor F5 — reports don't record the two fields that
  changed, and a dirty tree stamps a clean sha; identical outputs can't
  distinguish "net-zero change" from "same code twice".
  Corrected: the ADR's net-zero claim now rests on the algebraic identity
  (0.55 − 0.15n ≡ 0.40 − 0.15(n−1), n ≥ 1 always), and `git_sha()` stamps
  `-dirty` so the next before/after pair is honest by construction.
