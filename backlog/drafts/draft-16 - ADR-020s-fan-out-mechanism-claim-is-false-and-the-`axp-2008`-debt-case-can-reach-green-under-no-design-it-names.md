---
id: DRAFT-16
title: >-
  ADR-020's fan-out mechanism claim is false, and the `axp-2008` debt case can
  reach green under no design it names
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-16
  - 'PR #11 comments (reviewer round 4 R19'
  - 'orchestrator halt #2); ADR-020 §a/§b/§c row 7/§h3'
  - uncorrected in place
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**ADR-020's fan-out mechanism claim is false, and the `axp-2008` debt case can reach green under no design it names** (added 2026-08-20, PR #11 round-4 verification) — ADR-020 §a clause 2 / §b / §c row 7 / §h3 state that `segment.classify` returns `extracted` on all four partition bodies. It does not. That computation passes the combined heading line inside `body`; the pipeline never does (`src/sec10k/extract.py:111` derives `body = text[c["heading_end"]:c["end"]]`, and `segment.py:508` documents it as "the span minus its heading line"). Heading-stripped, item 10's partition body is pointer-only and classifies `incorporated_by_reference` (rest = 0 ≤ `IBR_REMAINDER_MAX` 300); the 1,139 chars of Reg S-K prose the `extracted` reading rests on sit at absolute 331084, **after** item 13's span end 330343, so no ordered partition giving 11–13 their own spans can put it inside item 10's body. Consequence: under the partition, `item_present 10 = extracted` fails; under whole-block, items 11–13 stay `missing`. `evals/adversarial/axp-2008-combined-part-iii.json` therefore asserts a status set no contract-valid fan-out produces, and its "NOW GREEN — promote it" contract is unreachable — the fourth survival of the defect PR #11's R1 first raised. **The 4-of-768 headline and the ruling are unaffected**: all four items still go `missing` → span-carrying under fan-out, which is the only property the decision rests on

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
