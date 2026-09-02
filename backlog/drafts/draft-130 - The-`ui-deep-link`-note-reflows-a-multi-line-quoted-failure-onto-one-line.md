---
id: DRAFT-130
title: The `ui-deep-link` note reflows a multi-line quoted failure onto one line
status: Draft
assignee: []
created_date: '2026-09-02 17:45'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-148
  - >-
    `tasks/reviews/pr55-r3.json` R13; `evals/adversarial/ui-deep-link.json`
    triage.note
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The `ui-deep-link` note reflows a multi-line quoted failure onto one line** (added 2026-08-26, `Origin: PR #55 R13`, LOW) — verbatim from the reviewer: *The ui-deep-link note's quoted mutation-(a) failure is reflowed onto one line while its provenance says every quoted output was "pasted from a run" — the emitted message is three lines.* Evidence verbatim: *`evals/adversarial/ui-deep-link.json:24` (triage.note) quotes the missing-pin failure with a single space before `}catch` and before `deepLink();`. The check emits a newline plus two spaces there, because the pin string itself carries newlines (`input.wire[0]`). The same commit's `tasks/reviews/pr55-r2-resolution.json` `mutation_a_now_red` quotes it correctly WITH the newlines, so the author had the exact text. Line 26 provenance nonetheless asserts "Every output quoted above was pasted from a run observed during the round-2 repair". Content is otherwise identical — whitespace only, no fabricated text, no offsets.* Acceptance verbatim: *The note either carries the message's line breaks (as `pr55-r2-resolution.json` already does) or its provenance says multi-line outputs are reflowed to one line for readability*

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
