---
id: DRAFT-54
title: Tables split across pages are two records
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-71
  - ADR-029 §e
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Tables split across pages are two records** (added 2026-08-23, Origin: S7) — a long table continued on the next rendered page is two `<table>` elements in every filer's HTML, and nothing joins them; a consumer sees two records whose header rows repeat

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
