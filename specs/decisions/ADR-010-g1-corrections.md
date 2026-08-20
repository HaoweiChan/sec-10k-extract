# ADR-010 — Four corrections the G1 audits forced

Date: 2026-08-16. Status: accepted. Amends ADR-007 (the 9C boundary and the
IBR shape rule). Amended by: ADR-015, ADR-017. Findings from the G1 gate
recorded in `tasks/TODO.md`.

**Ruling**: fix four silent wrong-output bugs — case-insensitive date parsing, the 9C era boundary keyed to the earliest late-fileable period end, IBR requiring pointer evidence inside the pointer sentence itself (not anywhere in the body), and `doc_status` collapse diagnosed before form identity.
**Because**: every one of the four reported success — none crashed — which is exactly the silent-failure class this pipeline exists to catch.
**Enforced by**: `evals/adversarial/caps-cover-taxonomy.json`, `evals/adversarial/fy2021-item-9c.json`, `evals/golden/textron-2001-content.json`, `evals/adversarial/truncated-download.json`

---

## Context

The cold review of T3–T5 and the spec↔code audit ran together as ledger row
G1. Between them they produced three silent wrong-output bugs and one wrong
refusal. All four are now cases, each watched red before the fix (hard rule 2);
this ADR records the rulings, not the discovery.

The four share a shape worth naming: **every one of them reports success.**
None crashes, none produces an obviously broken envelope, and three of them
carry confidence 0.95 on the wrong answer. That is the failure class the
analysis report's silent-failure-rate metric exists to measure, and the eval
set could not see any of them.

## Ruling 1 — the date parser is case-insensitive

`COVER_DATE_RE` carried `(?i)`; the `DATE_RE` it hands its capture to did not,
and its month pattern `[A-Z][a-z]{2,8}` requires exactly one leading capital.
An ALL-CAPS cover — `FOR THE FISCAL YEAR ENDED DECEMBER 31, 2016`, a common
filer typesetting choice with no semantic content — matched the first and
failed the second. `period_end` returned `None`, and `expected_items`' guard
`period_end and period_end >= ADDED[c]` is falsy for **every** dated code, so
the modern taxonomy collapsed to the 14-code 1993 set.

**Decision**: `DATE_RE` gets `(?i)` and a case-blind month class. `_parse_date`
now walks **every** match rather than only the first — the widened pattern lets
a non-month word match ahead of the real date, and returning `None` on the
first non-month would have reintroduced exactly the bug being fixed.

Enforced by `caps-cover-taxonomy`, whose max_chars bands come from the exact
arithmetic of the failure: item 1 was 7,496 + 129 (all of 1A) + 142 (all of
1B); item 9 was 102 + 7,166 (all of 9A) + 186 (all of 9B).

**Known gap, not fixed here**: `COVER_DATE_RE`'s own capture group cannot match
a floating comma (`December 31 , 2024`), the shape `normalize.py` documents as
real for nested iXBRL spans. `DATE_RE` handles it, but `COVER_DATE_RE` is the
gate. JPM survives only because its dei path fires first. No case exercises it,
so it is recorded as debt rather than fixed blind — per the same discipline
ADR-006 ruling 3 used for txt-era entities.

## Ruling 2 — Item 9C's boundary keys on the earliest period end that can be filed late

`ADDED` keys on **fiscal period end**; Item 9C's rule keys on **filing date**
(annual reports filed on or after 2022-01-01). Different dates. Every
calendar-FY2021 registrant — the largest cohort of that filing season — filed
in Feb–Mar 2022 and must address 9C, and at `date(2022, 1, 1)` all of them lost
it. Not merely unextracted: `find_candidates` skips codes outside `expected`,
so the heading never became a candidate, could not enter the TOC manifest, and
therefore could not raise `toc_manifest_mismatch`. Its text was annexed to
Item 9B and the run could still report `success`.

Filing date is not recoverable from the document: 2 of 15 fixtures carry an
SGML header with `FILED AS OF DATE`, and a modern primary `.htm` never does.

**Decision**: the boundary is the earliest period end whose report can land
after the cutoff — `date(2021, 10, 1)`. Filers who legitimately have no 9C
heading fall through to `omitted`, which `classify` already did. ADR-007 left
this open pending "an FY2022 fixture"; the answer came from the opposite
direction and moves the boundary **back**, not forward.

**This ruling also fixes the eval set, which had encoded the bug as ground
truth in three places at once**: the `ADDED` table, `sandston-2021-shallow`'s
21-item whitelist, and `segment._demo`'s `assert len(...) == 21  # no 9C/1C
yet`. Sandston genuinely has no 9C heading, so its case was green for a wrong
reason — the filing is FY2021 filed 2022-03-25, 9C is era-*valid* for it, and
the honest report is `omitted` (ADR-005 rule 2), not silence. That is precisely
the INV-S4 distinction between "we did not find it" and "the filer was allowed
not to file it".

**Recorded as debt, not fixed**: the era table is a single point of silent
failure for this whole class. `find_candidates`' `if code not in expected:
continue` means any future item addition mis-dated by one season repeats this
exactly. The general fix — letting a physically present heading for a known
code surface regardless of era expectation — conflicts with INV-S3 as written
and is a spec change, not a bug fix. Not taken here.

## Ruling 3 — incorporated-by-reference means the content is elsewhere

The T4 rule tested whether the **first sentence** was a pointer, then searched
for external-document evidence across the **entire body** — so "proxy
statement" 40,000 chars away could justify a first-sentence pointer. Because
the decision rested on sentence order, moving two paragraphs of GE 1994
(a pure reordering, no content changed) flipped a 4,805-char extracted item to
`incorporated_by_reference`. Pointer-first-then-content is the *more* common
real-world Item 10 layout.

The damage is silent by construction: `validate()` builds its span map from
`status == "extracted"` only, so an IBR item escapes all six validators, and
`extract` drops it before `doc_status` is derived. The eval adapter is equally
blind — `no_overlap_ordered` and `verbatim` both iterate the extracted list.

**Decision**, two parts:

1. The external-document evidence must appear in the **pointer sentence**, not
   anywhere in the body.
2. A body carrying substantive inline prose is `extracted` however many
   pointers it opens with. `IBR_REMAINDER_MAX = 300` chars of non-pointer
   remainder.

Measured over all 34 pointer-bearing bodies in the fixture set: genuine
whole-item pointers leave 0–166 chars of non-pointer remainder (the 166 is
NIKE's Item 10, whose remainder is itself a pointer phrased without the trigger
words); bodies with real inline content start at 414 and run to 3,186. The
floor sits in that empty band, ADR-008's method.

**Three committed goldens were reclassified by this rule, and each was read
before the change was accepted** — a threshold that silently moves real items
is not a fix:

- **IBM 1997 Item 5** → `extracted`. Carries exchange listings and "There were
  622,092 common stockholders of record at March 9, 1998."
- **CAT 2023 Item 12** → `extracted`. Carries the equity-compensation-plan
  table, with numbers.
- **CAT 2023 Item 10** → `extracted`. Carries the Code of Conduct paragraph and
  the family-relationships statement.

All three are *mixed* items. Calling a mixed item `incorporated_by_reference`
tells a consumer to go read another document for text that is right there —
the more damaging of the two errors, and the invisible one. Genuine whole-item
pointers (IBM 3/6/7, CAT 11/13, and every Part III pointer in the set) are
unmoved, which is what makes the rule discriminating rather than merely looser.

## Ruling 4 — collapse is diagnosed before form identity

The contract fixes the `doc_status` derivation order and says in terms that the
ordering is not implementation-owned. The code tested `ACCEPTED_FORMS` first
and collapse second, so a truncated download — 13 normalized chars, no
detectable form — was reported `unsupported`.

**Decision**: the contract's order stands and the code follows it. This is not
pedantry about precedence. The two statuses are different diagnoses shown to a
person: `failed` says we could not read this document, which sends them to
re-download it; `unsupported` says this is not a 10-K, which sends them to
check the wrong thing entirely. For the T7 upload path, a truncated or
interrupted download is the likeliest bad input a real user supplies.

Enforced by `truncated-download`, which also closes a gap the audit found
independently: **no case in the suite produced `failed` at all**, so
`COLLAPSE_FLOOR` and the whole branch were untested. A contract status with no
eval representation is decorative — the defect ADR-005 was written to fix for
`omitted`.

## Consequences

- Fast suite 21 → 25 cases, all green; invariant suite 5 → 8.
- New `confidence` check type. No case read the field before, so every constant
  in ADR-008's confidence table was free to change with the suite still green
  — while the contract claims the eval set punishes overconfident wrongness.
  Now pinned: 0.95 strict, 0.85 IBR, 0.80 omitted, and JPM item 15 at 0.80,
  which makes `WARN_PENALTY` observable for the first time.
- `ibm-1997` pinned to `success_with_warning` + `warning_present`, so
  `UNATTRIBUTED_MAX` can no longer move to 0.90 unnoticed; `jpm-2024` pinned to
  `ambiguous` + `warning_present`, so `last_item_dominates` can no longer be
  switched off. `nvda-2024` already pinned both bands from above.
- **Still open, and larger than anything fixed here**: four of the six layer-8
  validators still have no case proving they fire, and four adapter checks
  (`no_overlap_ordered`, `verbatim`, `known_items_only`, `boundary_hygiene`)
  are structurally incapable of going red. `verbatim` asserts bounds and never
  compares text; `boundary_hygiene` re-applies a copy of the regex that
  produced the offsets and can only fire as a false positive. 25/25 green means
  less than it appears, and saying so is the point of writing it down.
- The IBR offset question raised by the spec↔code audit is **not settled here**
  — see the open recommendation in `tasks/TODO.md` row G1.
