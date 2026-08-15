# Task 2 problem definition — 10-K item-level extraction

Split a raw SEC 10-K filing into its individual Items so each can be consumed
independently, with honest per-item status and confidence. The normative output
contract is `specs/001-sec10k-contract.md`; this doc scopes inputs, justifies
the contract fields, and fixes what "supported" means.

## Inputs (v1)

All three modes converge on the extractor's single entry point
`extract_items(path)` — acquisition lives in the web service, never in the
extractor.

1. **Select a committed fixture** — zero-friction demo path; satisfies the
   assignment's "select filings" clause.
2. **Upload a raw `.htm`/`.html`/`.txt` file** — the guaranteed held-out
   verification path: no network, no SEC dependency, no rate limits. Evaluators
   will test with their own filings; this mode must never break.
3. **EDGAR document URL** (`sec.gov/Archives/...`) — server-side fetch with the
   declared User-Agent from `evals/fixtures/README.md`, one fetch per request
   (far under SEC's 10 req/s fair-access ceiling), size cap (~25 MB,
   provisional), sha256 recorded. **Known risk**: EDGAR sometimes blocks
   cloud-datacenter IPs. URL mode is best-effort with a loud, surfaced error;
   upload is the first-class path. Verified by an early deploy spike (T2).

**Stretch**: accession-number / ticker lookup (index parsing to resolve the
primary document — sugar over URL mode). **Non-goals**: bulk crawling, filing
discovery, full-text search.

## Output contract — why each field exists

Schema and rules live in `specs/001-sec10k-contract.md` (v2, ADR-002). The
justification, field by field:

| Field | Level | Why it exists |
|---|---|---|
| `normalized_text` + item `start`/`end` | v1 | verbatim provenance — item text is *only* readable through offsets, so it cannot drift from the source (INV-S2) |
| `item`, `part`, `title` | v1 | canonical identity; era-valid codes only (INV-S3) |
| `status` (extracted/missing/incorporated_by_reference/omitted) | v1 | absence must be explicit, never silence (INV-S4); consumers must distinguish "not in filing" from "extractor missed it" |
| `confidence` | v1 | downstream thresholding; the eval set punishes overconfident wrongness |
| `doc_status` (success/success_with_warning/ambiguous/unsupported/failed) | v2 doc | honest failure reporting is graded; the frontend's headline banner; refusal (`unsupported`) beats mangled output |
| `warnings[{code,message,item?}]` | v2 doc | machine-readable "success but look here"; separates clean success from qualified success |
| `meta` (format_era, taxonomy_era, document_selected, input_sha256, extractor_version) | v2 doc | reproducibility — audits and re-runs must be comparable; era decisions inspectable |
| `trace[]` | v2 doc | observability: which candidates were found, which were rejected and why, which boundaries won — consumed by the frontend debug panel and the extraction-auditor |
| `timings`, `cost` | v2 doc | the analysis report is written from logs, not guesses; at B `cost` is structurally $0 — itself a reported result |
| `heading_text` | v2 item | the actually-matched heading vs canonical `title` — the single most useful evidence for a human inspector |
| `method` (heading_strict/heading_lenient/status_keyword/llm_fallback) | v2 item | feeds the deterministic-coverage metric; tells an inspector how much to trust the path taken |
| `evidence{}` | v2 item | the features confidence was computed from — makes confidence auditable rather than vibes |

## Supported scope

**Required v1 — all three format eras** (see `sec10k-domain` skill for era
detail):

- 2019+ inline XBRL `.htm`
- 2001–2019 HTML primary documents
- 1993–2001 plain-text multi-`<DOCUMENT>` full submissions — **under an
  explicit complexity stop-loss**: if by the end of T4 txt-era handling demands
  disproportionate special-casing or threatens the milestone, an ADR demotes it
  to stretch and `ge-1994-oldformat` remains as enumerated adversarial debt
  with honest reporting. It is never silently dropped.

10-K405 (pre-2003 checkbox variant) is a 10-K — only the form sniffer needs to
accept it.

**Stretch**: 10-K/A amendments (often contain only amended items, which breaks
the era-expected-set assumption behind INV-S4 — needs a relaxed expected-set
mode); 10-KSB.

**Explicitly unsupported** → `doc_status: unsupported`, never best-effort
output: non-10-K forms (10-Q, 8-K, 20-F), scanned/image/PDF filings, inputs
with no detectable 10-K document. Detect-and-refuse is a graded honesty
feature and gets its own adversarial case.

## Frontend requirements

Inspectability over polish; the frontend is how evaluators judge the system,
not a demo veneer.

- Filing input: fixture picker, file upload, EDGAR URL field.
- `doc_status` banner + warnings panel, always visible.
- Item sidebar: every expected item with status / confidence / method badges.
- Item pane: extracted text (via offsets) with `heading_text` shown as evidence.
- Debug view: `trace` as a collapsible pretty-printed panel — candidates found,
  rejections with reasons, boundary decisions.
- Timings (and cost, once any paid stage exists).
- Link to the works-well / difficult-and-unsupported lists.
