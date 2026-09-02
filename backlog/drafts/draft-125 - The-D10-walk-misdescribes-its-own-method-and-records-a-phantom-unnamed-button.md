---
id: DRAFT-125
title: 'The D10 walk misdescribes its own method, and records a phantom unnamed button'
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-142
  - '`tasks/reviews/pr55-r1.json` R4; `tasks/reviews/d10_agent_walk.py:15-18'
  - '47-53`; `tasks/reviews/d10-agent-walk.json:31-35`'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The D10 walk misdescribes its own method, and records a phantom unnamed button** (added 2026-08-26, `Origin: PR #55 R4`, LOW) — verbatim from the reviewer: *`a11y_names()` docstring says it reads names "through the ARIA engine (not the DOM attribute)" while its body reads the DOM attribute, and the module docstring's "never through a CSS selector on the attribute we just added" is contradicted by three id-selector `get_attribute` reads.* Evidence verbatim: *`tasks/reviews/d10_agent_walk.py:47-53` (an `evaluate` returning `el.getAttribute('aria-label')` falling back to `el.textContent`), vs the claim at :48-49 and the module claim at :15-18; the direct attribute reads are at :89, :117, :141-142. Visible consequence in the committed evidence: `tasks/reviews/d10-agent-walk.json:33` records an empty-string button name, which is the `<input type="file" id="up">` whose real accessible name is 'upload a filing (.htm / .html / .txt)' from its `<label for="up">`. The recorded name list is therefore not an accessibility-tree reading and shows a phantom unnamed button.* Acceptance verbatim: *`a11y_names` uses the computed accessible name (e.g. Playwright `aria_snapshot()` or `evaluate` over the a11y tree), or the docstrings are corrected to say the recorded lists are DOM-attribute reads while only the `get_by_role(..., name=...)` assertions go through the ARIA engine; the regenerated JSON no longer carries a nameless button*

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
