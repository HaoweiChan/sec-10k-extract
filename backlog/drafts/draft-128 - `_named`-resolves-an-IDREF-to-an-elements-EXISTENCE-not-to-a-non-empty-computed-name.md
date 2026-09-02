---
id: DRAFT-128
title: >-
  `_named` resolves an IDREF to an element's EXISTENCE, not to a non-empty
  computed name
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-146
  - >-
    `tasks/reviews/pr55-r2.json` R11; `src/repo_hygiene/eval_adapter.py`
    `_named`; the ceiling paragraph in its docstring
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`_named` resolves an IDREF to an element's EXISTENCE, not to a non-empty computed name** (added 2026-08-26, `Origin: PR #55 R11`, LOW) — verbatim from the reviewer: *`_named`'s IDREF resolution answers "does an element with that id exist" rather than "does the name compute non-empty", so a labelledby pointing at an element with no accessible text still reads as named — the same defect class R2 was raised for.* Evidence verbatim: *`src/repo_hygiene/eval_adapter.py:1649` `all(re.search(r'\bid="' + re.escape(t) + r'"', live) ...)`. Concrete input: `<div id="banner" class="s-idle" role="status" aria-labelledby="up">` — `id="up"` is the `<input type="file">` at `index.html:303`, whose accname computes to the empty string, so `get_by_role('status', name=...)` still matches nothing; measured `run_case(...)` passed=True, failures=[]. R2's stated acceptance ("resolves every token against an id present in the same live file") is met, so R2 is closed; the docstring's ceiling at :1638-1643 says the limit is "what does it say", which under-describes this — the limit is also "is it named at all".* Acceptance verbatim: *Either the docstring ceiling names this case explicitly (a resolving reference to a text-less element is still accepted), or the browser walk asserts the banner's computed name non-empty via `get_by_role('status', name=...)` so the static check is not the only thing standing behind the claim*

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
