---
id: DRAFT-135
title: >-
  `ledger-line-refs` checks `tasks/TODO.md` only, so line citations INTO other
  files rot unnoticed
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-154
  - >-
    `src/repo_hygiene/eval_adapter.py::check_ledger_line_refs`;
    `evals/adversarial/ledger-line-refs.json` input.files; ADR-034 §g and §h;
    `tasks/reviews/pr56-r3.json` R16
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`ledger-line-refs` checks `tasks/TODO.md` only, so line citations INTO other files rot unnoticed** (added 2026-08-26, Origin: PR #56 R16) — the round-2 amendment inserted 33 lines into `evals/heldout/README.md` and silently invalidated all three of ADR-034 §g's citations into it; one was a block quote labelled "verbatim" whose quoted string the same amendment had deleted from the file. Nothing on the gate caught it: `check_ledger_line_refs` iterates only the files named in `evals/adversarial/ledger-line-refs.json`, which is `tasks/TODO.md`, and ADR-034 §h already records that `bench --check-docs` does not read this ADR at all. So the repo has a working rot detector pointed at one file and a documented blind spot everywhere else — and the round-2 repair walked straight into it

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
