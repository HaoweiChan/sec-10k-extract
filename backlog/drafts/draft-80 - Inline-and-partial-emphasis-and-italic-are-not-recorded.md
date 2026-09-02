---
id: DRAFT-80
title: 'Inline and partial emphasis, and italic, are not recorded'
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-97
  - ADR-032 §b2
  - >-
    §e; `msft-2013-blocks` window 3 and `xom-2021-blocks` window 2 pin the
    whole-block rule
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Inline and partial emphasis, and italic, are not recorded** (added 2026-08-23, Origin: S9) — `strong` is a whole-block property (every visible character bold); a bold lead-in (`<B><I>Principal Products and Services</I></B>: Windows…`, msft-2013) or a bold phrase inside a paragraph is lost, and `<i>/<em>/font-style:italic` is never read (xom-2021's italic `(millions of dollars)`, aapl-2025's bold-italic lead sentences carry only `strong`)

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
