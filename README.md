# sec-10k-extract

Item-level structured extraction of SEC 10-K filings — split a raw filing
(2019+ inline XBRL, 2001–2019 HTML, or a 1990s plain-text submission) into
independently consumable Items 1–16, each with explicit status, character
offsets, and confidence that does not pretend to be calibrated.

**Live inspector: <https://whaleforce-sec10k.zeabur.app>**

Built on [groundwork](https://github.com/HaoweiChan/groundwork), an eval-first
scaffold. That choice is the point of the project: 10-K extraction has no
public ground truth, so correctness is encoded as executable invariants and
hand-labelled cases rather than prose, and every claim below is traceable to a
committed report in `evals/report/`.

---

## Run it

```bash
python3 -m evals.run --suite all        # 27 cases, no dependencies
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

## Key design decisions

Full rationale in `specs/decisions/` (13 ADRs). The ones that shaped the system:

- **Deterministic first, LLM deferred** (ADR-000/003). No model is in the
  extraction path. Cost is therefore structurally $0 — not "cheap", zero — and
  a fallback stage is deliberately not built until residual-failure data
  justifies one. Deterministic coverage is currently **100%**.
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
| Mid-era HTML (2001–2019) | MSFT FY2013, NIKE FY2006, JNJ FY2016 | `success` |
| Plain-text submissions (1993–2001) | GE FY1993, IBM FY1997 | `success_with_warning`; the txt era was kept in scope, its stop-loss never invoked (ADR-007) |
| 10-K405 checkbox variant | Textron FY2001, IBM FY1997 | handled; the form cross-check compares families, not strings (ADR-006) |
| Shell / tiny filers | Sandston FY2021, Premier Pacific FY2016 | `success`, including correct `omitted` for absent optional items |
| Table-of-contents traps | `toc-titled` (synthetic hard form) | TOC suppressed, body headings win |
| Non-10-K input | Apple Q1 FY2026 10-Q | **refused** as `unsupported`, zero items |
| Truncated download | 13 normalized chars | **refused** as `failed`, with the right diagnosis (ADR-010) |
| Large filings | JPM FY2024, 12.8 MB | 0.53 s, and it flags its own boundary problem |

## What is difficult, unreliable, or unsupported

Concrete, with the case or run that demonstrates each. Nothing here is
speculative.

**Fails today — known and unfixed**

- **2002–2003 transitional numbering.** Goldman Sachs FY2002 uses the
  post-Sarbanes-Oxley scheme (Item 14 = Controls, Item 15 = Exhibits) *ahead*
  of the 2003-08-14 effective date the era table encodes, so **Item 15 is
  absent from the output entirely**. Found by held-out run H1, predicted in the
  case's provenance before the run, deliberately not fixed: the general repair
  conflicts with INV-S3 and is A-level scope (ADR-013). This is the third
  confirmation that **the era table is the pipeline's most brittle component**.
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

- **4 of 6 validators have no case proving they fire.** `unattributed_content`
  and `last_item_dominates` are pinned; numeric-density, keyword-fingerprint,
  boundary-hygiene and the manifest cross-check are not all provable.
- **Four eval checks are structurally incapable of failing** —
  `no_overlap_ordered`, `verbatim`, `known_items_only`, `boundary_hygiene`.
  `verbatim` asserts bounds and never compares text. Recorded in ADR-010, not
  papered over: **27/27 green means less than it appears**.
- **284 confident items are targeted by no check at all.** The 0.0
  silent-failure rate covers the 105 that are audited.

**Explicitly unsupported** — refused, never best-effort: non-10-K forms
(10-Q, 8-K, 20-F), scanned/image/PDF filings, inputs with no detectable 10-K
document. 10-K/A amendments and 10-KSB are out of scope.

## Performance, cost, scalability

Measured, not estimated — see `docs/analysis-report.md` for method and full
tables.

| | |
|---|---|
| Latency p50 / p95 | **0.041 s / 0.249 s** across 21 fixtures |
| Largest filing | JPM FY2024, 12.8 MB → **0.53 s** |
| Throughput | **~19 MB/s** aggregate, 37.8 MB in 2.0 s |
| Peak memory | **110 MB** driving all 21 filings in one process |
| Cost per filing | **$0.00** — structural, no paid dependency exists |

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
specs/            invariants, the output contract, 13 ADRs — binding
docs/             product, evals, architecture, audits — descriptive
tasks/TODO.md     milestone ledger with per-milestone exit gates
evals/golden/     hand-labelled cases (anchors verified, counts recorded)
evals/adversarial/ cases designed or found to break the pipeline
evals/heldout/    frozen; unreachable by the normal suites
evals/fixtures/   committed EDGAR filings, provenance per file
evals/report/     every run's raw output, committed
prompts/          curated AI-collaboration record
src/sec10k/       the pipeline; web/ is the inspector
```

Working rules for contributors and agents: `CLAUDE.md`.
