# Decisions index

Current-rules digest: one line per ADR, in numeric order,
its ruling and what enforces it. Full context — Context/Decision/Consequences
— lives in the ADR file; this index is the map, not the territory.

- ADR-000 — specs/ holds only invariants, contracts, and ADRs; the eval set IS the spec — enforced by `.githooks/pre-commit`, `evals/run.py`
- ADR-001 — durable docs live in docs/, specs/ stays restricted, no plan files beyond the session — enforced by advisory (CLAUDE.md `Layout`)
- ADR-002 — output contract v2 adds doc-level + item-level fields, additively over v1 — enforced by `specs/001-sec10k-contract.md`
- ADR-003 — B-level normalization is stdlib `html.parser` only, no parsing dependency — enforced by `evals/adversarial/malformed-html.json`
- ADR-004 — `incorporated_by_reference` only for whole-item pointers to another document — enforced by `evals/golden/textron-2001-content.json` · amended by ADR-017
- ADR-005 — a present heading is always `extracted`; absence is `omitted`/`missing` by era rule, never status-by-triviality — enforced by `evals/golden/jpm-2024-content.json`
- ADR-006 — iXBRL metadata skipped, HTML newlines collapse, txt newlines pass through, txt entities undecoded — enforced by `evals/adversarial/ixbrl-hidden-metadata.json`
- ADR-007 — same-line heading rule + per-candidate TOC-cluster filter, thresholds measured not guessed — enforced by `evals/adversarial/toc-titled.json` · amended by ADR-010, ADR-013, ADR-015, ADR-027
- ADR-008 — six label-free validators kept, four rejected as measured false-positive generators — enforced by `src/sec10k/validate.py` · amended by ADR-013, ADR-018, ADR-027
- ADR-009 — exactly one milestone ledger (`tasks/TODO.md`), UNRUN gates written explicitly, never omitted — enforced by `tasks/TODO.md` convention · amended by ADR-022
- ADR-010 — fixes 4 silent-success bugs: date parsing, 9C boundary, IBR pointer-sentence scope, collapse-before-form-identity — enforced by `evals/adversarial/fy2021-item-9c.json` · amended by ADR-015, ADR-017
- ADR-011 — IBR items carry real offsets, checked by every span-level check like any other status — enforced by `specs/000-invariants.md` INV-S1
- ADR-012 — `.eval-baseline.json["fast"]` armed at 1.000, invariant suite stays unbaselined — enforced by `evals/run.py`, `.github/workflows/ci.yml`
- ADR-013 — bare headings promote from the next line under the TOC-cluster filter; >25% missing items escalates `doc_status` — enforced by `evals/adversarial/jnj-bare-headings.json`
- ADR-014 — Item 4 "Reserved" era window (2010–2011); sentence splitter rejoins at "No. \<digit\>" — enforced by `evals/adversarial/item4-reserved-window.json`
- ADR-015 — trailing-index echo rule (last-member + majority-elsewhere test); interim Item 14/15 and Item 9B eras; semicolon isn't a sentence end — enforced by `evals/golden/intc-2002-shallow.json` · amended by ADR-019
- ADR-016 — every warning code and adapter check dispositioned as fixture/unit/ruled; `verbatim` gains a real text comparison — enforced by `src/sec10k/test_eval_adapter.py::test_checks_that_had_never_gone_red`
- ADR-017 — `IBR_RE` tolerates an interposed phrase; pointer evidence must sit in the leading run of pointer sentences — enforced by `evals/golden/wfc-2008-shallow.json`
- ADR-018 — `BASE_MISSING` phantom collapsed (0.55→0.40), shadow scale deleted, no remap-to-empirical — enforced by `src/sec10k/validate.py::_demo` · amended by ADR-019, ADR-027
- ADR-019 — silent-failure rate measured at 1/30 sampled (3.3%); `EXEC_OFFICERS_RE` boundary fix ships — enforced by `evals/oracle.py`, `src/sec10k/segment.py`
- ADR-020 — no LLM fallback ships; the one real recall gap is closed by a $0 deterministic fix instead — enforced by `specs/001-sec10k-contract.md` method enum
- ADR-021 — `evals/bench.py` is the committed source of every perf/cost number, replacing v3's uncited §3/§4/§5 figures — enforced by `evals/bench.py --self-check`, `evals/bench.py --check-docs`
- ADR-022 — `tasks/DONE.md` is the second sanctioned ledger; a row leaves TODO.md only with no `UNRUN` gate — enforced by `tasks/DONE.md` line format · amends ADR-009
- ADR-023 — a retitle is its own rule with its own date: five era-label corrections (items 5, 10, 12, 13, 15), item set unchanged — enforced by `evals/adversarial/era-label-*.json`, `src/sec10k/segment.py::_demo` · amends ADR-010, ADR-015
- ADR-024 — 10-K/A stays out of scope; the refusal is asserted on both detection routes, not left to `ACCEPTED_FORMS` — enforced by `src/sec10k/normalize.py::_demo`
- ADR-025 — one `history.jsonl` line every run, a full report only for `--report`/`all`/`--dir`/red; 165 uncited gate dumps pruned, backfilled first — enforced by `evals/run.py`, `src/repo_hygiene/eval_adapter.py::check_report_citations`
- ADR-026 — boilerplate chrome is reported as opt-in `{start,end,kind}` spans, never removed; `normalized_text` and every offset are byte-identical with exclusion on and off — enforced by `evals/adversarial/boilerplate-offsets-invariant.json`, `src/sec10k/boilerplate.py`
- ADR-027 — an `ambiguous` document caps every item at 0.75; `method` derives from the same `STRICT_SIM` cut as the confidence base; `FLOOR` deleted; `boundary_hygiene` reuses `HEADING_RE`; every validator threshold pinned inside its measured band — enforced by `evals/adversarial/items-stripped-escalation.json`, `evals/adversarial/spaced-letter-heading.json`, `src/sec10k/eval_adapter.py::envelope_shape` · amends ADR-007, ADR-008, ADR-018
- ADR-028 — build identity is injected at build time (`BUILD_SHA` from Zeabur's build-phase `ZEABUR_GIT_COMMIT_SHA`) and outranks the `GIT_SHA` override; anything that is not `[0-9a-f]{7,40}` reports `unknown` rather than a label — enforced by `evals/adversarial/build-identity.json`, `src/sec10k/web/build_id.py` · amended in place 2026-08-23 (§g1, post-merge gate ran)
- ADR-029 — HTML tables are reported as opt-in `{start,end,header,rows}` offset records into an UNCHANGED `normalized_text` (`extract_items(path, tables=True)`), the grid and Markdown derived by `src/sec10k/tables.py`, never stored; table fidelity (cells, rows) is a per-run metric gated against `.eval-baseline.json` — enforced by `evals/golden/aapl-2025-table.json`, `evals/golden/msft-2013-table.json`, `evals/golden/tgt-2002-table-th.json`, `evals/adversarial/tables-offsets-invariant.json`, `evals/run.py` (metric gate) · amended in place 2026-08-23 (§i, corpus blast-radius measurement)

Amended-by is also recorded on each amended ADR's own Status line — this
index only cross-references it for scanning.
