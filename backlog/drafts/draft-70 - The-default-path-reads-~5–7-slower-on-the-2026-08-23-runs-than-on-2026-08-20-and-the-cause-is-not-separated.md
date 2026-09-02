---
id: DRAFT-70
title: >-
  The default path reads ~5–7% slower on the 2026-08-23 runs than on 2026-08-20,
  and the cause is not separated
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-87
  - >-
    `evals/report/20260820-031501/-031540/-031620/-115810-bench.json` vs
    `20260823-185543/-185626/-185707-bench.json`; report v5 version block and
    §3.1; ADR-021 §g
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The default path reads ~5–7% slower on the 2026-08-23 runs than on 2026-08-20, and the cause is not separated** (added 2026-08-23, Origin: D2) — every 2026-08-23 clean-tree run (`ba263ee`) is slower than every 2026-08-20 clean-tree run (`13761cc`, `9753c58`) on the same fixtures: batch 14.53–15.02 → 14.04–14.23 MiB/s, the largest filing 0.541–0.568 → 0.580–0.589 s, the sum of medians 3.88–4.05 → 4.30–4.32 s (the four added fixtures account for ~0.13 s of that), outside the ±3% run-to-run spread either trio shows. `src/` changed between the two dates (T3's `<title>` skip, S7's table marks in `normalize.py` — ADR-029 §f says the flag-off branch is the original three `re.sub` calls — D1's discovery rule) and the runs are on different days of the same machine; the instrument cannot tell tree from machine, and `docs/analysis-report.md` v5 says so rather than attributing it

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
