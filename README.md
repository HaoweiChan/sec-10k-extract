# sec-10k-extract

Item-level structured extraction of SEC 10-K filings — split a raw filing
(2019+ inline XBRL, 2001–2019 HTML, or a 1990s plain-text submission) into
independently consumable Items 1–16, each with explicit status, character
offsets, and confidence that does not pretend to be calibrated.

**Live inspector: <https://whaleforce-sec10k.zeabur.app>**

![The sec10k inspector: fixture aapl-2025 extracted, item list on the left with
per-item status, confidence and method, and Item 1's text on the right rendered
from its character offsets](docs/assets/inspector.png)

The repo is eval-first, and that choice is the point of the project: 10-K
extraction has no public ground truth, so correctness is encoded as executable
invariants and hand-labelled cases rather than prose, and every claim below is
traceable to a committed run in `evals/report/history.jsonl`.

The inspector above is the same pipeline behind a three-mode front end — a
committed fixture, your own uploaded filing, or an EDGAR URL. Item text is
sliced from the `start`/`end` offsets at response time, so what you read is
the offsets, not a second copy that could drift from them (INV-S2).

---

## Run it

```bash
python3 -m evals.run --suite all        # 44 cases, no dependencies
```

The extraction pipeline and the eval harness are **stdlib-only** (ADR-003).
`fastapi`/`uvicorn` are needed only for the web inspector:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn src.sec10k.web.app:app --port 8000     # then open localhost:8000
```

```bash
python3 -m evals.metrics                # the eleven metrics over the newest report
python3 -m evals.run --suite invariant  # must-always-hold assertions, 100% required
```

Extract one filing directly:

```bash
python3 -c "from src.sec10k.extract import extract_items; import json; r=extract_items('evals/fixtures/aapl-2025/filing.htm'); print(json.dumps({k:v for k,v in r.items() if k!='normalized_text'}, indent=1, default=str)[:2000])"
```

## What it produces

A contract-v2 envelope (`specs/001-sec10k-contract.md`). Item text is readable
**only** through `start`/`end` offsets into the extractor's `normalized_text` —
there is deliberately no second copy of the text to drift from the offsets
(INV-S2). Every item in the filing era's expected set appears with one of four
statuses; silence is never how absence is reported (INV-S4):

| status | meaning |
|---|---|
| `extracted` | heading found, span assigned |
| `incorporated_by_reference` | the item's content lives in another document; offsets point at the pointer sentence (ADR-011) |
| `omitted` | era/filer rules permit the absence (ADR-005) |
| `missing` | expected, and we did not find it — an admission, not a silence |

At the document level, `doc_status` ∈ `success` / `success_with_warning` /
`ambiguous` / `unsupported` / `failed`. **`unsupported` and `failed` mean the
pipeline refused**; it never emits a best-effort parse of a document it could
not identify.

Two opt-in annotations add one key each and move nothing else:
`extract_items(path, exclude_boilerplate=True)` reports page-chrome runs as
offsets (ADR-026), and `extract_items(path, tables=True)` reports every HTML
`<table>` as `{start, end, header, rows}` offset records into the same
`normalized_text` (ADR-029) — a cell's text is a slice, exactly like an item's,
and the Markdown rendering is derived on demand by `src/sec10k/tables.py`.

## Key design decisions

Full rationale in `specs/decisions/` (18 ADRs). The ones that shaped the system:

- **Deterministic first, LLM ruled out** (ADR-000/003, settled in ADR-020). No
  model is in the extraction path. Cost is therefore structurally $0 — not
  "cheap", zero. The fallback stage was gated on residual-failure data; that
  data was measured (ADR-019) and the decision taken (ADR-020): **not
  justified**. Not because deterministic coverage reads 100% — that number is
  circular while no fallback exists — but because six of the seven residual
  failures measured here are confidently *wrong* spans, which no honest trigger
  reaches, and the seventh is a heading-shape gap a regex closes identically at
  $0. Addressable surface across both eval sets: **4 of 768 items**, one filing,
  one root cause, all four reachable by that same deterministic change.
  ADR-020 §e says what would reopen it.
- **Stdlib-only parsing** (ADR-003). `html.parser`, no dependencies. The
  revisit clause has never fired; malformed HTML normalizes cleanly.
- **Offsets, not text** (contract + INV-S2). Makes drift structurally
  impossible rather than tested-against.
- **A label-free validator battery** (ADR-008, ADR-013). Six validators that
  need no annotations and therefore run on every filing, including ones the
  eval set has never seen. This is where robustness beyond the labelled
  fixtures comes from — and it earned its keep: on held-out filings it caught a
  real tail bleed unprompted and made a catastrophic under-extraction loud.
- **Warn, don't hard-fail** (failure taxonomy F7). Validators emit warnings and
  move confidence; only three may escalate `doc_status` to `ambiguous`.
- **Held-out discipline** (`evals/heldout/README.md`). Five filings authored
  frozen, structurally unreachable by the normal suites, results committed
  before any fix.

## What works well

Verified by committed cases; run `python3 -m evals.run --suite all` to reproduce.

| Stratum | Examples | Result |
|---|---|---|
| Modern iXBRL (2019+) | AAPL FY2025, NVDA FY2024, CAT FY2023 | `success`, full item sets (23 items) |
| Mid-era HTML (2001–2019) | MSFT FY2013, NIKE FY2006, JNJ FY2016 | `success`. JNJ is the filer whose bare-block headings once cost 18 of 21 items (ADR-013) |
| Plain-text submissions (1993–2001) | GE FY1993, IBM FY1997 | `success_with_warning`; the txt era was kept in scope, its stop-loss never invoked (ADR-007) |
| 10-K405 checkbox variant | Textron FY2001, IBM FY1997 | handled; the form cross-check compares families, not strings (ADR-006) |
| Shell / tiny filers | Sandston FY2021, Premier Pacific FY2016 | `success`, including correct `omitted` for absent optional items |
| Table-of-contents traps | `toc-titled` (synthetic hard form) | TOC suppressed, body headings win |
| Non-10-K input | Apple Q1 FY2026 10-Q | **refused** as `unsupported`, zero items |
| Truncated download | 0 normalized chars | **refused** as `failed`, with the right diagnosis (ADR-010) |
| Large filings | JPM FY2024, 12.25 MiB | **0.55 s** (median of 3, `evals/report/20260820-031540-bench.json`), and it flags its own boundary problem |

## What is difficult, unreliable, or unsupported

Concrete, with the case or run that demonstrates each. Nothing here is
speculative.

**Closed since B-freeze**

- **2002–2003 transitional numbering** — listed here as unfixed until T9.
  Goldman Sachs FY2002 used the post-Sarbanes-Oxley scheme (Item 14 =
  Controls, Item 15 = Exhibits) *ahead* of the 2003-08-14 effective date the
  era table encoded, so Item 15 was absent from the output entirely. ADR-013
  read it as one filer's early adoption needing an INV-S3 amendment and
  declined the repair. Two more filings from the same window (`intc-2002`,
  `tgt-2002`) showed it is a **regulatory era** — Release 33-8124, effective
  2002-08-29 — and a table correction, not a conflict: `gs-2002` moved from
  the `debt` suite into `fast` with **not one of its assertions edited**
  (ADR-015 §1). The lesson survives the fix, and is
  the reason it is still written down here: **the era table remains the
  pipeline's most brittle component**, and this was its third confirmation.

**Fails today — known and unfixed**

- **Permitted omissions read as `missing`.** Exxon FY2021 drops Item 6 entirely
  — allowed since the Feb 2021 S-K amendment — and the extractor reports
  `missing` rather than `omitted`, because only codes 16 and 9C auto-omit.
  Honest but imprecise.
- **Appendices after the last item.** JPM FY2024 puts its whole financial
  appendix after the Item 15 exhibit index, so Item 15's span swallows 83% of
  the document. The `last_item_dominates` validator catches it and the filing
  reports `ambiguous` — the failure is loud, but the boundary is still wrong.
  Exxon FY2021 shows the same shape on Item 16.

**Thin evidence — claimed, but not strongly demonstrated**

- **1 of the 8 layer-8 codes cannot be fired by any document** —
  `boundary_hygiene`. This list named three until T9; ADR-016 §3 closed the
  other two with `spans-transposed`, a pure byte-transposition of `sgrp-2019`
  (the derivation asserts `sorted(out) == sorted(raw)`) that mislabels two
  spans without adding or deleting a character, and both
  `numeric_density_inversion` and `keyword_fingerprint` fire on it.
  `boundary_hygiene` is not merely unproven but unprovable from a filing:
  spans are built from heading matches, so a span opens with its heading by
  construction. It is proved against the layer boundary in `validate._demo`
  instead, and ADR-016 §2 records why that is the honest place for it.
- **Three eval checks can go red — where the honest count was zero of four.**
  ADR-010 recorded that `no_overlap_ordered`, `verbatim`, `known_items_only`
  and `boundary_hygiene` were structurally incapable of failing, and that
  `verbatim` asserted bounds and never compared text. ADR-016 §5 proves the
  first three on hand-built results and gives `verbatim` a real comparison: a
  span must open with its own `heading_text`. The count is three and not four
  because §2 and §5 prove **one** relation at two layers, stated that way
  rather than double-counted. Firing a check once still proves the code path,
  not the threshold — per-bucket calibration is T10's job.
- **The silent-failure rate covers 22% of the confident items.** 0.0 is
  measured over 109 audited items out of 490 confident ones: 280 are targeted
  by no check, and 101 more sit in non-success documents and fall outside the
  metric's definition — including the JPM span this README names as wrong.

**Explicitly unsupported** — refused, never item-extracted: non-10-K forms
(10-Q, 8-K, 20-F), scanned/image/PDF filings, inputs with no detectable 10-K
document. 10-K/A amendments and 10-KSB are out of scope — the 10-K/A half is ruled,
measured and dated in [ADR-024](specs/decisions/ADR-024-10ka-out-of-scope.md). The refusal names the
form and returns the normalized text; it does not return items, and it does not
claim the file was unreadable (ADR-016 §6).

## Performance, cost, scalability

Measured, not estimated. Every figure below is a field of one committed file —
`evals/report/20260820-031540-bench.json`, regenerated by
`python3 -m evals.bench --json …`. **Sizes and rates are binary** (MiB =
1,048,576 bytes), so a quoted size divided by a quoted time reproduces the
quoted rate. **The instrument is good to about ±3%** — three full runs on a
clean tree are committed and the spread between them is measured in
`docs/analysis-report.md` §3.1 — so everything here is two significant figures
and no more. Numbers printed beside a fixture name anywhere in this repo are
checked against that artifact mechanically by
`python3 -m evals.bench --check-docs`. Method, the full per-fixture table, the population boundaries and
the cost counterfactual: `docs/analysis-report.md` v4 §3–§5 and
[ADR-021](specs/decisions/ADR-021-benchmark-instrument.md).

| | |
|---|---|
| Latency p50 / p95 | **0.041 s / 0.51 s** across the 37 dev-corpus fixtures |
| Largest filing | JPM FY2024, 12.25 MiB → **0.55 s** |
| Throughput | **14.8 MiB/s** aggregate, 58.37 MiB in 3.942 s; 6.6–33.8 MiB/s per fixture over the 34 the pipeline actually processes (3 are refusals on a shorter code path) |
| Peak memory | **119–124 MiB** driving all 37 filings in one process — a plateau, not a function of the largest document (94.6 MiB alone) |
| Cost per filing | **$0.00** — structural, no paid dependency exists |
| Full EDGAR year (~7,000 10-Ks) | **~17 min** single process, embarrassingly parallel — mean over the 33 real EDGAR filings committed, not over the synthetic-diluted dev mean |

*(Corrected 2026-08-20, T13. This table previously carried the **B-freeze**
numbers over 21 fixtures, and said "analysis-report v2 re-measures at T10",
which it did not. Of its five rows: **p95 0.249 s → 0.51 s**, **largest filing
0.53 s → 0.55 s**, **throughput ~19 MB/s → 14.8 MiB/s** — decimal MB against
binary MiB/s was part of the old confusion, hence the unit note above — and
**peak memory 110 MB → 119–124 MiB**. **p50 reads the same 0.041 s**, over a
different population, and cost per filing is unchanged. ADR-021 §c has the
old-vs-new comparison and why four of these were wrong rather than stale. The
EDGAR-year row is new in v4 and was corrected in PR #12 review from ~13 min to
~17 min when the multiplier's population was challenged; every figure here was
re-measured again in round 2 on a clean tree, after review found the previous
artifact had been produced from an uncommitted working tree.)*

## Where AI helped

The whole system was built in collaboration with Claude; `prompts/` holds the
curated record (5 documents) and `prompts/README.md` the curation rules. The
part worth reading is not the code generation — it is the **separation of
roles**, which is where most of the defects in this repo were found:

- An **implementing** agent wrote the pipeline.
- A **cold-reviewer** agent read it without the author's reasoning and found
  three silent wrong-output bugs the eval set could not see (ADR-010).
- An **extraction-auditor** agent independently re-verified anchors and outputs.
- **Held-out filings** caught what all of them missed (ADR-013).

Four separate times in this project, a check turned out to be unable to fail —
skipped review gates, an untested `failed` branch, an empty eval baseline, and
a coverage-map row that verified an adjacent thing. Each is recorded in an ADR
rather than quietly fixed, because *"a check nobody can observe is
indistinguishable from a check that passed"* is the most useful thing this
project learned.

## Repo map

```
specs/            invariants, the output contract, 18 ADRs — binding
docs/             product, evals, architecture, audits — descriptive
tasks/TODO.md     milestone ledger with per-milestone exit gates
evals/golden/     hand-labelled cases (anchors verified, counts recorded)
evals/adversarial/ cases designed or found to break the pipeline
evals/heldout/    frozen; unreachable by the normal suites
evals/fixtures/   committed EDGAR filings, provenance per file
evals/report/     history.jsonl line per run; full report on --report/all/--dir/red (ADR-025)
prompts/          curated AI-collaboration record
src/sec10k/       the pipeline; web/ is the inspector
```

Working rules for contributors and agents: `CLAUDE.md`.
