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
| `incorporated_by_reference` | the item's content lives in another document; offsets point at the pointer sentence (ADR-011) — or, when the pointer is a footnote resolving a marked empty heading, at that heading line with the footnote's offsets at `evidence.footnote` (ADR-031) |
| `omitted` | era/filer rules permit the absence (ADR-005) |
| `missing` | expected, and we did not find it — an admission, not a silence |

At the document level, `doc_status` ∈ `success` / `success_with_warning` /
`ambiguous` / `unsupported` / `failed`. **`unsupported` and `failed` mean the
pipeline refused**; it never emits a best-effort parse of a document it could
not identify.

Four opt-in annotations add a key each and move nothing else:
`extract_items(path, exclude_boilerplate=True)` reports page-chrome runs as
offsets (ADR-026); `extract_items(path, tables=True)` reports every HTML
`<table>` as `{start, end, header, rows}` offset records into the same
`normalized_text` (ADR-029) — a cell's text is a slice, exactly like an item's,
and the Markdown rendering is derived on demand by `src/sec10k/tables.py`; and
`extract_items(path, blocks=True)` reports the filing's block structure —
headings (item headings promoted), paragraphs (bold flagged), list items,
tables, or one `pre` block for a txt-era filing — as `{kind, start, end, …}`
records, from which `src/sec10k/markdown.py` derives the whole document or any
item as Markdown (ADR-032). The inspector's *render as Markdown* box shows that
view; `normalized_text` itself is never rewritten — ADR-032 §f2 measures what
that would have moved. Finally,
`extract_items(path, images=True)` reports every `<img>` as
`{offset, src, alt, width, height}` (ADR-033), the offset a point in the same
text. The image *bytes* are not fetched: every image in a 10-K is an external
reference to a sibling document in its EDGAR accession, and resolving one is a
network call this pipeline deliberately does not make (ADR-033 §c).

### Reproducing an item's text from its offsets

The offsets are **character offsets into `normalized_text`**, not into the raw
filing. There is deliberately no raw-to-normalized offset map — ADR-026 §a
refuses one — so reproducibility ships as a contract instead: the inspector
serves the exact text the offsets index, and this recipe checks any published
span end to end, from a machine with no access to this repo.

1. Extract: POST the filing to /api/extract/fixture (or /upload, or /url) and
   keep three things from the response: source.token, norm_sha256, and each
   item's start and end.
2. Download: GET /api/normalized/{token} — the exact normalized_text those
   offsets index, served as UTF-8 text.
3. Verify: sha256 of the downloaded bytes must equal norm_sha256 from step 1.
   If it does not, the download is not that run and the offsets do not apply
   to it.
4. Slice: item_text = normalized_text[start:end], where normalized_text is the
   DECODED string — start and end are character offsets into that string,
   never byte offsets into a file.

WARNING: these offsets do not index the raw filing. Slicing the raw HTML — what
/api/source/{token} serves, or the file you uploaded — by the same start and end
yields different bytes, because normalization rewrites the document. There is
deliberately no raw-to-normalized offset map (ADR-026 §a).

Worked, against a local inspector:

```python
import hashlib, json, urllib.request

post = urllib.request.Request(
    "http://localhost:8000/api/extract/fixture",
    data=json.dumps({"fixture": "aapl-2025"}).encode(),
    headers={"content-type": "application/json"})
run = json.load(urllib.request.urlopen(post))                       # step 1

norm = urllib.request.urlopen(                                      # step 2
    "http://localhost:8000/api/normalized/" + run["source"]["token"]).read()
assert hashlib.sha256(norm).hexdigest() == run["norm_sha256"]       # step 3

text = norm.decode("utf-8")
item = next(i for i in run["items"] if i["item"] == "1")
assert text[item["start"]:item["end"]][:len(item["text"])] == item["text"]   # step 4
print("item 1 reproduced:", item["end"] - item["start"], "chars")
```

(`item["text"]` is the API's display copy, truncated at 40,000 characters —
`chars` always reports the full span, so compare prefixes on a long item.)

The same recipe is the OpenAPI description of `/api/normalized/{token}` itself,
so it travels with the deployed service and not only with this file;
`evals/adversarial/ui-offset-reproduction-contract.json` pins both copies and
the two facts they rest on — that the slice is byte-for-byte the text the API
serves, and that the raw-bytes slice is not.


## Key design decisions

Full rationale in `specs/decisions/` (18 ADRs). The ones that shaped the system:

- **Deterministic first, and a model tier only on a measured trigger**
  (ADR-000/003, settled in ADR-020, **superseded 2026-08-26 by ADR-036, D11**).
  No model is in the DEFAULT extraction path, and cost on that path is
  structurally $0 — not "cheap", zero. ADR-036 adds an opt-in slow path
  (`extract_items(path, escalate=True)`, via OpenRouter) that is entered only when D8's
  document-level `low_item_coverage` fires — measured on **0 of 28 real dev
  filings**, so the default stays free — and whose answers are discarded unless
  a deterministic re-check accepts their offsets. With no API credential it
  refuses loudly rather than degrading, and as of this commit no live call has
  ever been made: the held-out exam is UNRUN (ADR-036 §k). The paragraph below
  is the 2026-08-19 ruling it supersedes, kept because its reasoning about
  *precision* failures is unchanged and still governs.
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
- **A label-free validator battery** (ADR-008, ADR-013, ADR-030, ADR-035, ADR-039). Eleven validators that
  need no annotations and therefore run on every filing, including ones the
  eval set has never seen. This is where robustness beyond the labelled
  fixtures comes from — and it earned its keep: on held-out filings it caught a
  real tail bleed unprompted and made a catastrophic under-extraction loud.
- **Warn, don't hard-fail** (failure taxonomy F7). Validators emit warnings and
  move confidence; only five may escalate `doc_status` to `ambiguous`.
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
| Large filings | JPM FY2024, 12.25 MiB | **0.58 s** (median of 3, `evals/report/20260823-185707-bench.json`; 0.72 s with `tables=True`), and it flags its own boundary problem |

## What is difficult, unreliable, or unsupported

Every row is backed by a committed case or run — nothing here is speculative.

| Limitation | Concrete case | Status |
|---|---|---|
| Legally-permitted omissions are reported as `missing` | Exxon FY2021 drops Item 6, allowed since a 2021 rule change, but the extractor can't tell that apart from a real gap | Known, unfixed — honest but imprecise |
| An appendix placed after the last item inflates that item's span | JPM FY2024: the financial appendix sits after the last item's exhibit index, so that item's span swallows 83% of the document | A validator catches it and flags the filing `ambiguous` — loud, but the boundary is still wrong |
| One validation rule can never actually fire on a real filing | Spans are built from their own heading text by construction, so the check it would catch can't occur | Proven correct in code instead of by example |
| A handful of validation checks were recently proven able to fail, but not yet tuned | 3 of 4 checks once thought unfailable can now go red on hand-built test cases | The logic is proven; per-case sensitivity tuning is still open |
| The "silent failure" rate is measured on a partial sample | 0% measured, but only across 109 of 490 high-confidence items — the rest weren't checked | Disclosed as a narrow measurement, not a full guarantee |
| The historical item-numbering table was fragile around a 2002–2003 SEC rule change | Three different filings from that window broke numbering before the table was corrected | Fixed — kept here because the fragility itself is structural |
| Out of scope by design | Non-10-K forms (10-Q, 8-K, 20-F), scanned/image/PDF filings, 10-K/A amendments, 10-KSB, and inputs with no detectable 10-K document | Refused outright — a refusal names the form and returns the raw text; it never fakes items |

<details>
<summary>Design-decision log for this section (collapsed — click to expand)</summary>

- [ADR-010](specs/decisions/ADR-010-g1-corrections.md) — fixed four bugs that were failing silently, including the 9C boundary and a date-parsing bug.
- [ADR-013](specs/decisions/ADR-013-heading-shape-and-escalation.md) — rule for headings with no body text, and when a filing gets flagged ambiguous for missing too many items.
- [ADR-015](specs/decisions/ADR-015-transitional-era-and-trailing-index.md) — the 2002–2003 numbering-transition fix, plus a rule for trailing index pages that echo earlier items.
- [ADR-016](specs/decisions/ADR-016-validator-provability.md) — every validator and eval check was individually proven either fixture-testable, unit-testable, or provably-can't-fire.
- [ADR-019](specs/decisions/ADR-019-silent-failure-rate.md) — the silent-failure rate was measured directly on a sampled, audited set of items.
- [ADR-024](specs/decisions/ADR-024-10ka-out-of-scope.md) — 10-K/A amendments ruled out of scope, with the refusal enforced on two independent code paths.

Full context for any of these — the problem, the alternatives considered, the
consequences — lives in the linked file.

</details>

## Performance, cost, scalability

Measured, not estimated. Every figure below is a field of one committed file —
`evals/report/20260823-185707-bench.json`, regenerated by
`python3 -m evals.bench --json …` (n=41 dev fixtures, 13 of them synthetic,
4 refusals; median of 3 repeats; Python 3.14.6 on macOS arm64, clean tree at
`ba263ee`). **Sizes and rates are binary** (MiB = 1,048,576 bytes), so a
quoted size divided by a quoted time reproduces the quoted rate. **The
instrument is good to about ±3% on its aggregates** — three full runs on a
clean tree are committed and the spread between them is measured in
`docs/analysis-report.md` §3.1 — so everything here is two significant figures
and no more. Decimals printed within 60 characters after a backticked fixture
name, on the same line, in the five files `evals.bench.DOC_FILES` names (this
README, `docs/analysis-report.md`, ADR-021, `tasks/TODO.md`, `prompts/009`)
are checked against that artifact mechanically by `python3 -m evals.bench
--check-docs` — except decimals adjacent to `$`, `%` or `×` (prices,
percentages, ratios) and the `(file, fixture, value)` triples
`evals.bench.DOC_ALLOW` lists as legitimate non-measurements; the window also
stops at the next backticked fixture name. Integers, aggregates and numbers
anywhere else are not checked (ADR-021 §b12). Since D2 the check **fails
closed** — a run that checks nothing, or a `DOC_FILES` entry that no longer
exists, exits non-zero — and both it and `evals.bench --self-check` run in
`.githooks/pre-commit` and CI's unit-tests job. Method, the full per-fixture
table, the population boundaries and the cost counterfactual:
`docs/analysis-report.md` v5 §3–§5 and
[ADR-021](specs/decisions/ADR-021-benchmark-instrument.md).

| | |
|---|---|
| Latency p50 / p95 | **0.044 s / 0.40 s** across the 41 dev-corpus fixtures (p95 is the 39th of 41 medians under nearest-rank; it read 0.51 s at n=37 because the rank fell on a slower filing, not because anything got faster) |
| Largest filing | JPM FY2024, 12.25 MiB → **0.58 s**; **0.72 s** with the opt-in `tables=True` annotation (ADR-029) |
| Throughput | **14.1 MiB/s** aggregate, 60.54 MiB in 4.307 s; 6.2–32.2 MiB/s per fixture over the 37 the pipeline actually processes (4 are refusals on a shorter code path) |
| `tables=True` overhead | median **1.19×**, max 1.3× the default path's wall-clock, per fixture |
| Peak memory | **119–124 MiB** driving all 41 filings in one process — a plateau, not a function of the largest document (that alone reaches **94.6–102.4 MiB** across the seven committed clean-tree runs; v4 said "94.6, stable to 0.1" from three) |
| Cost per filing | **$0.00** — structural, no paid dependency exists |
| Full EDGAR year (~7,000 10-Ks) | **~18 min** single process, embarrassingly parallel — mean over the 33 real EDGAR filings committed, not over the synthetic-diluted dev mean |

*(Re-published 2026-08-23, D2. The previous table was read from
`20260820-031540-bench.json`, n=37, and is history: p95 0.51 s → 0.40 s (a
rank effect at n=41, above), largest filing 0.55 → 0.58 s, throughput 14.8 →
14.1 MiB/s, EDGAR year ~17 → ~18 min, peak memory unchanged at 119–124 MiB
with the largest-filing figure re-qualified as a range. The whole corpus reads
about 5–7% slower than on 2026-08-20 — outside the ±3% spread — and
`docs/analysis-report.md` v5 says so without attributing it to the tree or the
machine; `src/` changed between the runs (T3, D1, S7) and so did the day.
Corrected 2026-08-20, T13, before that: the table had carried the **B-freeze**
numbers over 21 fixtures — p95 0.249 s, throughput ~19 MB/s, peak memory
110 MB — four of which ADR-021 §c shows were wrong rather than stale, and
said "analysis-report v2 re-measures at T10", which it did not.)*

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
