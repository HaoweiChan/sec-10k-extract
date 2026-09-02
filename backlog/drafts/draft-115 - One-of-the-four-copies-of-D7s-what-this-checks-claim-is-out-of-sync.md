---
id: DRAFT-115
title: One of the four copies of D7's "what this checks" claim is out of sync
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-132
  - >-
    `tasks/reviews/pr53-r3.json` finding R12; `src/sec10k/web/static/index.html`
    the `// What the eval buys` comment vs `src/repo_hygiene/eval_adapter.py`
    `check_confidence_honesty`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**One of the four copies of D7's "what this checks" claim is out of sync** (added 2026-08-26, Origin: PR #53 R12) — the `index.html` comment says the pins assert the marker and qualifier "around every mention of `it.confidence`", dropping the "sitting inside an interpolation" qualifier that `eval_adapter.py` and the case `ceiling` both carry (`prompts/021` does not restate the bullets and is in sync). The unqualified version is false BY DESIGN: a correct non-rendering line such as `const low = it.confidence < 0.9;` is deliberately skipped and the case stays green — which is also the confirmation that R4's inverse fix is real and the check does not punish valid edits

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
