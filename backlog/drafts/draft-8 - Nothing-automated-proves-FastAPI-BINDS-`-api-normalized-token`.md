---
id: DRAFT-8
title: 'Nothing automated proves FastAPI BINDS `/api/normalized/{token}`'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-8
  - >-
    `src/repo_hygiene/eval_adapter.py::check_offset_reproduction_contract` and
    its `WIRE_NORMALIZED` allow-list; the debt row above it for the extract
    routes
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Nothing automated proves FastAPI BINDS `/api/normalized/{token}`** (added 2026-08-26, Origin: D12) — the hole `check_boilerplate_plumbing`'s own row already carries for the three extract routes, now extended to the download. `offset_reproduction_contract` pins the decorator, the six expressions on the wire and a rebind guard on each of the two functions that bind `norm`, all by allow-list over the file text, and cannot issue a request. PR #54 R1 measured what that gap is worth: the first version of the allow-list pinned only the expressions that MENTION `norm`, so `norm = hit[1]` served the raw filing under a matching sha header with the whole gate green. That specific hole is closed and its three mutations are watched red; what remains open is the class it belongs to, since no text pin can prove a route is bound and served.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
