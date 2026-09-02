---
id: DRAFT-45
title: Nothing in the eval set or CI ever observes the DEPLOYED instance
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-57
  - >-
    ADR-028 §g; `evals/adversarial/build-identity.json`'s
    `what_this_cannot_prove`; the S2 post-merge gate
  - RAN 2026-08-23 (`tasks/reviews/s2-postmerge-gate.json`)
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Nothing in the eval set or CI ever observes the DEPLOYED instance** (added 2026-08-22, Origin: S2) — the defect S2 fixes was only ever visible by hand (`curl -s https://whaleforce-sec10k.zeabur.app/api/meta` -> `{"git_sha":"unknown", …}`, 2026-08-22), and it stays that way after the fix: `build-identity` proves the resolver and pins the `build_command` text, but nothing asserts that the running container agrees with the repo. A `build_command` Zeabur silently ignores, or a build artefact that does not survive into the run image, is green here and `unknown` there — forever, and with no red anywhere

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
