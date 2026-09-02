---
id: DRAFT-62
title: '`repo_hygiene` is listed and served as a filing fixture'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-79
  - '`tasks/reviews/s2-postmerge-gate.json` (`debt_found_in_passing`'
  - >-
    probe response recorded verbatim); `src/sec10k/web/app.py:126`;
    `evals/oracle.py:173`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`repo_hygiene` is listed and served as a filing fixture** (added 2026-08-23, Origin: S2 post-merge gate) — `/api/meta` builds `fixtures` from every directory under `evals/fixtures/` (`src/sec10k/web/app.py:126`, `d.is_dir()` only), so the deployed list observed 2026-08-23T07:51:52Z carries `repo_hygiene` — 14 UI/ledger regression stubs (S3/S4/S5/L1), not a filing — and the inspector dropdown (`src/sec10k/web/static/index.html:327`) offers it as one. Measured, not assumed: `POST /api/extract/fixture {"fixture":"repo_hygiene"}` at 2026-08-23T07:51:59Z answered HTTP 404 `bad_input` *expected exactly one filing file in /app/evals/fixtures/repo_hygiene, found 14* — a loud refusal, so no fabricated output, but a dead entry in a menu a stranger is handed. Same root in the eval tooling: `evals/oracle.iter_fixtures()` yields `repo_hygiene -> boilerplate-wire-values.html` (largest non-`.md` file), and `evals/bench.py:246` and `evals/oracle.py:310` consume it unfiltered, so a fresh ADR-021 bench run would time a 2.6 KB HTML stub as a dev fixture (the artifacts of record, `evals/report/20260820-*-bench.json` n_fixtures 37, predate the directory — first added 421fe2b 2026-08-21 — and are unaffected; `SYNTHETIC`/`DOC_FILES` do not name it)

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
