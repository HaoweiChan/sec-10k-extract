---
id: TASK-4
title: >-
  The door's argument pin is one token wide, and no in-repo pin over `app.py`
  can be otherwise
status: To Do
assignee: []
created_date: '2026-09-02 17:45'
labels: []
dependencies: []
references:
  - TODO.md TD-163
  - >-
    `tasks/reviews/pr61-r4.json` R23 (verification pass on PR #61's bounded
    round); `src/repo_hygiene/eval_adapter.py`'s `escalation_door` first-operand
    check; `src/sec10k/web/app.py`'s single `gate.paid_path_open` call site
priority: medium
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The door's argument pin binds `headers.get`'s arity but not the expression around it.** `(request.headers.get(gate.HEADER) or gate.configured_token())` satisfies all four assertions the check makes — exactly one `headers.get`, off the `request` parameter, one argument, `gate.HEADER` — while handing an anonymous request the deployment secret. Measured: **invariant 86/86, a perfect score**, with `paid_path_open` returning `(True, 'a valid x-escalation-token header was presented...')` for a request that presented nothing. M4 (secret as the `headers.get` default) and M6 (literal `True` for the off-switch) both still red, so the pin is not vacuous — it is one token wide.

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
