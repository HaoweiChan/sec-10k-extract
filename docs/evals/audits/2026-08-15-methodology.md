# Methodology audit — sec10k eval design, pre-implementation

Date: 2026-08-15. Mode: methodology. Auditor: `extraction-auditor`
(first invocation, run before any pipeline code exists). Findings verbatim;
disposition by the invoking session appended at the end.

## Scope

Gaming resistance of the check implementations, leakage design of the
held-out split, taxonomy coverage of the committed cases, dual-pass
verification of both existing cases' anchors, computability of the defined
metrics.

## What was run / read

Read: evaluation-strategy.md, failure-taxonomy.md, specs/000 + 001,
`src/sec10k/eval_adapter.py`, `evals/run.py`, all 3 case JSONs, hooks,
baseline, committed report. Ran: grep/regex occurrence counts and position
mapping over both fixtures (AAPL 1,520,208 chars; GE 7,879 lines); confirmed
`extract.py` is a stub and the committed report shows 0/3 all-red.

## Findings

1. **HIGH** — INV-S3/S4's backing case (`ge-1994-oldformat`) is tagged
   `["fast"]` only; both sec10k invariants are outside the 100%-required
   invariant gate — decorative by the spec's own criterion.
2. **HIGH** — INV-S4 has no enforcing check anywhere: no check type tests
   expected-set completeness; an extractor silently dropping Items 2–6 and
   8–13 passes every committed check on both fixtures.
3. **HIGH** — the `verbatim` check is a bounds check only; "verbatim slice" is
   true by construction (no separate text field), and the real INV-S2 risks
   (normalization instability, non-determinism) have no check at all.
4. **MED/HIGH** — `no_empty_success` passes if a single ≥100-char item exists
   among otherwise-empty ones, and never reads `doc_status`; as enforced
   today INV-0 ≈ "at least one 100-char span exists".
5. **MED** — boundary checks satisfiable with wrong boundaries: no end-of-item
   anchors or `max_chars` committed, so the tightness proxy evaluates over
   zero qualifying items; AAPL 1A anchor "macroeconomic" occurs 5× (incl. the
   FLS preamble and MD&A); GE "General Electric" occurs 101× (near-zero
   discrimination); `aapl-2025-content` in isolation is passed by
   `item 1A = entire document` — protection lives only in the sibling
   structure case sharing the suite.
6. **MED** — silent-failure rate (metric 6) not computable from `run_case` +
   per-check echo alone: needs per-item confidence, the run's `doc_status`,
   and machine-joinable audit findings; unchecked items are structurally
   invisible to the metric (denominator bias). Metrics 7/8/10/11 share the
   echo gap.
7. **MED** — burn-on-influence is honor-system; three trail holes:
   `--no-report` permits traceless held-out runs; reports carry no git SHA;
   run-before-fix ordering only provable via report commit position. Closers:
   forbid `--no-report` on held-out, embed SHA, commit report in own commit.
8. **LOW** — `rglob` case discovery: any stray nested JSON under golden/ or
   adversarial/ silently joins the fast suite.
9. **LOW** — `min_chars` raises TypeError on contract-conformant null offsets
   (non-extracted statuses) — reads as harness crash, not judgment.
10. **LOW** — era-invalid codes with non-extracted status pass everything
    (`item_absent` fails only on `extracted`; `known_items_only` checks the
    era-union registry); era validity enforced for exactly 1A/9A/16.
11. **Coverage** — F1 represented; F2 partial (mid-era HTML fixture absent);
    F3 status modes unrepresented (zero committed `status:` assertions; AAPL
    structure case skips exactly items 6 and 10–14 — the [Reserved]/IBR
    items); F4 partial (no end anchors; the F7 table's "7 swallowing 7A" row
    cites checks no committed case contains); F5 essentially unrepresented;
    F6 partial (10-Q case absent, flagged T2); F7 weak (finding 4). Everything
    docs flag as not-yet-existing is genuinely absent; nothing absent is
    claimed present except the two invariant citations and the 7A row.
12. **Dual-pass** — both cases' provenance matches reality: AAPL anchors exact
    at verified offsets ("Company Background" 1×, headings exactly 2×, CSOO
    unique, "Risk Factors" occurrences sit precisely at bleed positions);
    GE "Item 405" at line 124 col 0 (real heading-regex trap), "Item 601"
    inside the EX-4 exhibit (exercises document selection), 12 `<DOCUMENT>`
    blocks confirmed. Gap: only one of five anchors has its occurrence count
    recorded; 101× "General Electric" should have been disqualified.
    Structural positive: the committed 0/3 all-red report proves anchors were
    authored before any pipeline existed — leakage-impossible by ordering;
    worth preserving deliberately for future cases.

## Not checked

Actual extraction outputs (no pipeline); anchor survival through
normalization (unwritten); held-out mechanism in operation; metrics.py;
second-extractor oracle (A-level by design); architecture overview (outside
methodology-mode read scope).

## Disposition (invoking session, per failure-triage)

- Fixed pre-commit in this batch (doc/spec bugs): contract v2 example
  contradiction and wrong INV citation; eval-protocol `full`-suite
  description; metric-6 prerequisites + denominator rule and held-out audit
  trail (evaluation-strategy.md); F7 table committed-vs-pending note;
  case-authoring anchor-count rule + T2 markers.
- Scheduled as T2 scope (eval/case/adapter/runner work, recorded in
  milestones.md): findings 1–5, 8–11 — expected-set check, era-validity
  strengthening, `no_empty_success` reconciliation, determinism check,
  end anchors + `max_chars`, anchor replacement + counts, status assertions
  for AAPL 6/10–14 + 7A, per-item echo, `--dir`, SHA-in-report, discovery
  hardening.
- Finding 12's ordering property (author cases before implementation exists)
  is now deliberate practice via the case-authoring skill's watch-it-fail
  step.
