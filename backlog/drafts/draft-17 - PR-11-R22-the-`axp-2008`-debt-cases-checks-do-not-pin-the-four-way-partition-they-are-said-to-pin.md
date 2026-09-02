---
id: DRAFT-17
title: >-
  PR #11 R22: the `axp-2008` debt case's checks do not pin the four-way
  partition they are said to pin
status: Draft
assignee: []
created_date: '2026-09-02 17:44'
labels:
  - debt
dependencies: []
references:
  - TODO.md TD-17
  - 'PR #11 comment (reviewer round 4'
  - R20–R25); `evals/adversarial/axp-2008-combined-part-iii.json`
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**PR #11 R22: the `axp-2008` debt case's checks do not pin the four-way partition they are said to pin** (added 2026-08-20 as 'Five documentation defects carried from PR #11 round 4'; **doc halves (1)(2)(4)(5)(6) CLOSED by L1 (2026-08-23, PR #35 R2)** — (1) `evals/fixtures/README.md:47` now agrees with ADR-020 §c row 7 ('Yes, all four'); verified `sed -n 47p evals/fixtures/README.md` piped to `grep -c 'only item 10 can be recovered'` → 0; (2) ADR-020's header ('Corrected three times under review' paragraph) and §h3 ('The headline has now carried four figures' paragraph) now say four figures across three corrections, two of the three wrong ones the same error (rounds 0 and 2; round 1's 4 of 989 was the R7 denominator), 'committed twice'; verified `grep -c 'carried four figures' specs/decisions/ADR-020-fallback-not-justified.md` → 2; wide sweep (PR #35 round 2) `grep -rn 'four times' specs docs README.md prompts tasks/TODO.md` → ADR-021 §Verification 3 'corrected four times' reworded to 'three times (four figures)'; `prompts/008:241` and `prompts/009:61` say 'four times' and are left — curated records of their date, not live claims; (4) §h2's R8 bullet now reads 'correct under round 1's 2,000-char item-10 floor' and says why §h3 lowered it to 500; (5) the Verification citation now carries the report's own `git_sha` — `c5af644…-dirty`, the parent commit plus the uncommitted tree (`python3 -c` json-load of `evals/report/20260820-013206-fast.json` → `c5af644186dcfc85bb5e81df8f028e26ec966265-dirty`; `git log -1 c3513eb^` → c5af644); (6) the backwards 'costs item-10 coverage — 956 of 3,263' reading reworded to 'item 10 keeps 956 of the block's 3,263 chars; the cost is 2,307' at FIVE spots — three in PR #35 round 1 (ADR-020 §b's `axp-2008` items 10–13 table row, `docs/architecture/overview.md`'s ADR-020 fallback paragraph, the Combined-multi-item-heading row above) and two the round-1 grep `'956 of 3,263'` could not match, found by PR #35 R6 (ADR-020 §a 'no partition gives item 10 the complete block' paragraph: 'of the block's 3,263'; §h3 'The true claim is narrower' paragraph: '956 chars of 3,263'); verified by the wide sweep `grep -rnw 956 specs docs README.md tasks/TODO.md prompts evals/adversarial` read hit by hit — ADR-020 §a (reworded), §b row (reworded r1), §h 'item 10 `[328690,329646)` 956 chars' (span length, correct), §h2 'Item 10 takes 956 of the block's 3,263' (correct), §h3 listing 'len 956' (correct), §h3 paragraph (reworded), overview.md (reworded r1), this file's Combined-heading row (reworded r1) and L1 rows (references), `evals/adversarial/axp-2008-combined-part-iii.json` triage 'item 10 gets 956 of the block's 3,263' (correct) — and `grep -rn 'costs item-10 coverage — 956' specs docs README.md tasks prompts` → only this row's own quotation of the phrase and the `tasks/reviews/pr35-r2.json` trace, no live claim (ADR-020 §h2 'it costs item-10 coverage, not items 11–13's reachability' carries no figure and reads correctly); `python3 -m evals.bench --check-docs evals/report/20260820-031540-bench.json` unchanged at 56 checked, 4 unmatched) — **(3) stays open**: the debt case's checks do not pin the four-way partition they are said to pin — an equal-quarters chop satisfies every one, and `min_chars 500` is cleared at 694 by a heading+lead-in-only attach, with `text_contains` available and unused (also unrecorded: item 9B spans `[326887,331953)` through the block, so a fan-out must truncate it or `no_overlap_ordered` fails on '9B and 10')

Probe: none — migrated from TODO.md
<!-- SECTION:DESCRIPTION:END -->
