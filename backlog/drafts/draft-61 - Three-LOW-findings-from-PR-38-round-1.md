---
id: DRAFT-61
title: 'Three LOW findings from PR #38 round 1'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-78
  - '`tasks/reviews/pr38-r1.json`'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Three LOW findings from PR #38 round 1** (added 2026-08-23, Origin: PR #38 R1/R2/R3) — (a) **R1** the `fixture_discovery` check's live-text pins on `app.py` (one `list_fixtures()` call at the meta route, one `fixture_file(d)` call, no local def of either name) are satisfied by a wrong program that rebinds either name with a trailing lambda or re-imports `fixture_file` from another module — the def-regex and the call-site counts pass, 0 failures; the same ceiling `build_identity`'s git_sha pin has; (b) **R2** the new 'exactly one file' rule, now applied to the oracle and bench, silently drops a real fixture if a stray file (`.DS_Store`, an editor backup) lands beside the filing — main's `iter_fixtures` tolerated that (largest non-.md); today 42 dirs / 41 single-file, the one exception is `repo_hygiene`, so nothing is dropped at HEAD; (c) **R3** the D1 row's Contents cell says 'exactly one filing-shaped file' while the shipped predicate, the Status cell, the fixtures README rule and the D1 debt row say 'exactly one file, suffix not inspected' (a lone `.md` resolves)

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
