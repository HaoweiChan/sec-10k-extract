---
id: DRAFT-37
title: >-
  "OFF is unchanged" rests on per-item assertions over two fixtures, not on a
  whole-payload snapshot
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-41
  - >-
    `tasks/reviews/pr27-r1.json` finding R4;
    `src/repo_hygiene/eval_adapter.py::check_boilerplate_exclusion`;
    `src/sec10k/web/view.py`'s `build_view` return
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**"OFF is unchanged" rests on per-item assertions over two fixtures, not on a whole-payload snapshot** (added 2026-08-22, Origin: PR #27 R4) — R4 is a VERDICT, and the verdict is that the additive `boilerplate_excluded` key is fine: nothing in `specs/` or `docs/` enumerates the view payload (`grep -rn -e build_view -e norm_chars specs/ docs/` returned nothing when this row was written; at 1efc457 it returns one line, ADR-029:173, which lists `norm_chars` among the envelope fields its offset-invariance equality compares — still not an enumeration of the view payload), so it breaks no contract, and `index.html` holds the only consumers. The residue is what the reviewer named: `check_boilerplate_exclusion` pins the OFF path per ITEM on ge-1994 and msft-2013 only, and nothing pins `warnings`, `counts`, `trace` or `meta` against a pre-S8 snapshot on any fixture.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
