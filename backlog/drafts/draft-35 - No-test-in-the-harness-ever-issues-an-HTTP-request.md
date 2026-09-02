---
id: DRAFT-35
title: No test in the harness ever issues an HTTP request
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-39
  - >-
    `src/repo_hygiene/eval_adapter.py::check_boilerplate_plumbing` and its
    docstring; `evals/adversarial/ui-boilerplate-exclusion-regression.json`
    (pair A
  - 9 shapes) and `ui-boilerplate-wire-values.json` (pair B
  - 8 shapes)
  - both at exact counts
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**No test in the harness ever issues an HTTP request** (added 2026-08-22, Origin: S8; corrected twice, Origin: PR #27 R2 and PR #27 R5/R6) — `boilerplate_plumbing` reads `app.py` and `index.html` as TEXT, and this row has now under-stated the gap twice, which is worth more than the gap itself. First it named only "a wrong parameter name, a wrong body shape or a 422", and R2 measured four silent breakages passing. Then the check bound the two ends by NAME, and R5/R6 measured seven more — five inverting the VALUE at a hop whose names were all correct (`not bool(...)`, `!= "1"`, `False and bool(...)`, `return true`, `$("#exclude-bp-OLD")`), and two deleting the `display_text ??` the pane renders. The check is now an ALLOW-LIST of the ten expressions that carry the value, each required exactly once in the file's live text. **What remains, stated as narrowly as it can be**: a pin proves an expression is present and not commented out; it cannot prove the expression is REACHED. Delete the `$("#go-fx").onclick =` binding and leave the call expression behind, or gate the pane render behind a condition that is never true, and every pin still passes. **Widened 2026-08-22 (PR #27 R13)**: that example breaks a whole button loudly, and the ceiling also covers quiet single-mode losses — hoist `const bpq = (excludeBp() ? "&exclude_boilerplate=1" : "");` and then call upload without ever using `bpq`, and the pin is satisfied while upload alone silently ignores the checkbox (invariant 37/37). Same class: a pinned expression inside a string literal, or behind `if (false)`. Nor can it prove FastAPI BINDS any of it — a decorator typo, a body-model mismatch, a 422, or a route that never registers would all read correctly and still break. Also unbound: the two truthiness rules the request boundary carries (`bool(body[...])` vs `== "1"`), so a JSON caller sending the STRING `"false"` gets exclusion ON.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
