---
id: DRAFT-132
title: >-
  `mrk-1995` items 5 and 7 report `extracted` over pure external-document
  pointers
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-150
  - ADR-034 §b3 (rejected hits); `evals/heldout/mrk-1995-heldout.json`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**`mrk-1995` items 5 and 7 report `extracted` over pure external-document pointers** (added 2026-08-26, Origin: D9 / ADR-034 §g) — both bodies read, in substance, "the information required for this item is incorporated by reference to pages 28 through 37 of the Company's 1995 Annual Report to stockholders" (231 and 247 chars). ADR-034 rejected them OUT of the internal-pointer class because the target is an external document, which puts them in ADR-004's IBR territory instead. Whether `extracted` or `incorporated_by_reference` is the right call there was not answered. Note the filing is a plain-text full submission, so whether the Annual Report is physically inside these same bytes is itself unestablished

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
