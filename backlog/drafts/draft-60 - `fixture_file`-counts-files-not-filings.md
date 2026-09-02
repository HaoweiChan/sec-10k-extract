---
id: DRAFT-60
title: '`fixture_file` counts files, not filings'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-77
  - >-
    `src/sec10k/web/fixtures.py::fixture_file` (`ponytail:` comment names it);
    `evals/adversarial/fixture-discovery.json` triage note
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`fixture_file` counts files, not filings** (added 2026-08-23, Origin: D1) — the D1 rule is 'exactly one file', the rule `_fixture_file` always applied; a directory under `evals/fixtures/` holding one NON-filing file (a lone README, a PDF) would be listed by `/api/meta`, offered by the dropdown and yielded by `iter_fixtures`. Measured ceiling, not a silent failure: extract_items refuses such a file on content — `evals/fixtures/repo_hygiene/fixture-discovery/README.md` -> `failed` (`normalization_collapse`), `repo_hygiene/boilerplate-wire-values.html` -> `unsupported` (`unsupported_form`) — so the worst case is a dead dropdown entry again, never fabricated output. No such directory exists today (42 directories, 41 single-file, all 41 `filing.htm`/`filing.txt`).

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
