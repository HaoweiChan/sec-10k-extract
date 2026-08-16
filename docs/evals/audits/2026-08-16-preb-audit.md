# Pre-B-freeze audit — findings and disposition

Independent `extraction-auditor` run, 2026-08-16, before the B-freeze. Twelve
findings, three HIGH. It also returned substantial clean bills, which are
recorded here because a clean bill someone tried to break is evidence.

## Disposition

| # | Finding | Disposition |
|---|---|---|
| 1 | **Confidence ordering is inverted** where it varies at all | **OPEN** — see below |
| 2 | JNJ Part III pointers `extracted` @0.95, zero warnings | **FIXED** (31b07c3), cases first |
| 3 | `title`/`part` wrong for the whole pre-2003 era; no check read either field | **FIXED** (31b07c3), `item_field` check type added |
| 4 | Held-out `csco-2016`/`cost-2022` have no anchors — "passed" means presence, not correctness | **CLAIM SCOPED** in README + report |
| 5 | Metric 6 coverage is 22%, not the 27% the report quoted | **CORRECTED**; `metrics.py` now publishes both exclusions |
| 6 | Six metrics are pinned by the gate, not measured | **DISCLOSED** in the report |
| 7 | Metric 5's denominator padded with checks that cannot discriminate | **DISCLOSED** |
| 8 | Status coverage: `omitted` only on auto-omit codes, `missing` only on synthetic mutants | **OPEN**, recorded |
| 9 | txt era attributes 23–72% of the document while listed under "works well" | **OPEN**, recorded |
| 10 | Validator disclosure wrong in both directions | **CORRECTED** — 3 of 7 have never fired; the manifest check *is* pinned |
| 11 | Two different p50/p95 in one document | **ANNOTATED** — different populations, both reproducible |
| 12 | `gs-2002`'s held-out value is spent but still counted | **OPEN** — burn-semantics question, needs a decision |

## Finding 1 in full, because it is the most damaging and is not fixed

Measured over 21 fixtures (388 items), confidence is a re-encoding of `status`
for **98.7%** of items. Of the five that deviate, four are correctly penalised
weak-title matches at 0.75 — and the fifth is **JPM item 15 at 0.80, a span
wrong by roughly one million characters**. The one genuinely wrong span in the
corpus scores *above* four perfectly correct ones.

"Uncalibrated" (ADR-008, README, analysis report) is a fair disclosure. **"The
ordering is inverted wherever it is not constant" is the stronger true
statement**, and it was nowhere in the docs before this audit. It is now in the
analysis report §6.

Fixing it means making the penalty reflect *evidence of wrongness* rather than
title-match quality — which is calibration work, A-level, and not a B-freeze
change. Recorded rather than rushed.

## Clean bills — verified, not assumed

The auditor re-derived these independently and could not break them:

- **Every self-created fixture's provenance reproduces to the byte** — 27-byte
  caps-cover diff, 124-byte items-stripped deletion, 13-byte heading-unnumbered
  deletion at raw offset 686,815, 566-byte 9C insertion, and `ibr-pointer-first`
  as a pure reordering with an identical non-blank-line multiset.
- **All 45 `text_contains` anchors resolve inside the item they name; all 23
  `text_not_contains` hold; all 47 length bands bracket the measured span.**
- **Independent boundary sweep: every span in all 21 fixtures begins with its
  own item code — zero exceptions.**
- **Item 8 boundaries are where a human would put them** in aapl-2025,
  msft-2013, cat-2023 and nike-2006; the short Item 8s elsewhere are genuine
  pointer bodies, verified sentence by sentence.
- **Run-before-fix ordering is provable from git**, exactly as claimed:
  `a72d8f7` (report alone) → `c0ae224` (triage) → `f0c54b5` (red cases) →
  `ff965a3` (fix).
- **The §3 performance numbers reproduce** (JPM 0.539 s against a claimed
  0.526 s).

## What the auditor could not check

Network-dependent provenance (accessions taken on trust), any held-out
extraction behaviour (instructed not to spend it), and the deployed inspector.
