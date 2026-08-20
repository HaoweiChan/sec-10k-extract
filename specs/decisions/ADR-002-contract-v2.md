# ADR-002 — Output contract v2: document envelope + item evidence

Date: 2026-08-15. Status: accepted.

**Ruling**: extend the output contract additively with document-level fields (`doc_status`, `warnings`, `meta`, `trace`, `timings`, `cost`) and item-level fields (`heading_text`, `method`, `evidence`); v1 fields and rules stay unchanged.
**Because**: honest failure reporting, confidence inspectability, and a measured analysis report all need fields v1 has no room for.
**Enforced by**: `specs/001-sec10k-contract.md`; `doc_status` check type in `src/sec10k/eval_adapter.py`

---

## Context

Contract v1 describes items well but has no document-level semantics: no way
to say "this run succeeded with caveats", "this input is not a 10-K", or "here
is why confidence is what it is". The assignment grades honest failure
reporting, confidence inspectability, and an analysis report backed by
measured numbers — all of which need fields v1 lacks.

## Decision

Extend `specs/001-sec10k-contract.md` **additively** (no v1 field or rule
changes). Document level: `doc_status` (fixed derivation order; `unsupported`/
`failed` mean refusal, never best-effort output), `warnings`, `meta`, `trace`,
`timings`, `cost`. Item level: `heading_text`, `method`, `evidence`.
Normative/informative split is recorded in the contract itself: statuses,
derivation order, refusal semantics, and `method` values are normative;
`meta`/`trace`/`timings`/`cost`/`evidence` shapes are implementation-owned.

## Consequences

- Existing eval cases and the adapter are untouched (additive change). A
  `doc_status` check type is added to the adapter in T2, with adversarial
  cases (10-Q → `unsupported`) that go red first.
- The frontend and the extraction-auditor consume `trace`/`evidence` — the
  observability requirement is satisfied by the contract, not by logging
  bolted on later.
- `cost` being structurally zero at B is itself a reportable result for the
  analysis report.
