# ADR-023 — A retitle is its own rule with its own date: five era-label corrections from the A6 taxonomy diff

Date: 2026-08-20. Status: accepted. Amends: ADR-010 (era-table corrections), ADR-015 (interim-era labels).

**Ruling**: The item *set* is complete in every era and stays as it is; five era *labels* were wrong and are corrected — Item 5's legacy wording, Items 12 and 13's missing legacy captions, and Items 10 and 15's `ALIAS_FROM` boundaries, each now keyed to the release that actually wrote it.
**Because**: four codes shared the date 2003-08-14 because SOX was the boundary the table was built around; only two of them belong to it, and the other two rendered captions from a rule three years away over spans whose own headings read the older one.
**Enforced by**: `evals/adversarial/era-label-{ge-1994,textron-2001,ba-2003,nike-2006,bac-2006}.json`, `src/sec10k/segment.py::_demo`

---

## Context

T14/A6 asked for one thing that had never been done directly: diff this repo's
taxonomy — `TITLES`, `ADDED`, `ORDER`, `ALIAS_FROM`, `LEGACY_PART`,
`SOX_INTERIM` — against the authoritative Form 10-K, era by era, rather than
against whichever filing last broke.

The diff ran in three passes:

1. **The item set per era**, against the SEC's own Form 10-K
   (`sec.gov/files/form10-k.pdf`, read for its verbatim captions) and the rule
   history behind each code's arrival.
2. **The era labels**, against the release that wrote each caption.
3. **The corpus**, as an independent check on both: the `heading_text` every
   one of the 37 committed fixtures actually wrote, which is the filer's
   wording rather than the canon, and therefore evidence rather than proof.

Pass 1 came back clean. Every code the form has ever carried is in `ORDER`;
every `ADDED` date is the right rule's; no part is wrong; the 1993, 1997, SOX-
interim, 2005, 2010–2011, 2016, 2021 and 2023 phases all produce the item set
the form does. That is a real finding, not an absence of one: the six months of
era work recorded in ADR-007, ADR-010, ADR-013 and ADR-015 arrived at a
complete set, and this ADR changes none of it.

Pass 2 did not. Eleven assertions across four filings failed, on five distinct
table defects. The shape they share is the reason this ADR exists: **the table
treated a renumbering and a retitle as the same event.** Four `ALIAS_FROM`
dates read `2003-08-14` — the SOX renumbering that moved Controls to 9A and
Exhibits to 15 — because that was the boundary the table was originally built
around. Two of the four belong to it. The other two are captions written by
other releases, years away.

## Decision

Five corrections, each named by the release that dates it. §f and §g record
what the diff found and deliberately did **not** change.

### §a — Item 5's legacy caption said "Common Stock". No era of the form does.

`TITLES["5"]`'s legacy alias read *"Market for the Registrant's Common **Stock**
and Related Stockholder Matters"*. The item tracks Reg S-K Item 201 (17 CFR
229.201), *"Market price of and dividends on the registrant's common **equity**
and related stockholder matters"*, and the caption has read "Common Equity"
before and after every amendment to it. All eight committed pre-2005 fixtures
write Equity — ge-1994, ibm-1997, ko-1997, textron-2001 (as "MARKETS FOR"),
intc-2002, gs-2002, tgt-2002, ba-2003 — and not one writes Stock.

This is a wording fix with no date attached: no boundary moves, the same alias
applies over the same window, and it is the only one of the five that could
have been found by reading the table alone.

### §b — Item 12 had one caption where the form has two.

The `"...and Related Stockholder Matters"` suffix is the equity-compensation-plan
table's. Release Nos. 33-8048 / 34-45189, *Disclosure of Equity Compensation
Plan Information* (adopted 2001-12-21, effective 2002-02-01), required that
table in Item 12 of Form 10-K **for fiscal years ending on or after
2002-03-15** and lengthened the caption to match. `TITLES["12"]` carried only
the post-2002 caption, so every filing before it was labeled with a suffix that
did not exist yet.

`ALIAS_FROM["12"] = date(2002, 3, 15)`. The rule keys on fiscal-period end and
so does this table, so unlike the 9B and 9C boundaries no one-sided compromise
is involved. The corpus brackets it independently: textron-2001 (period end
2001-12-29) writes the unsuffixed caption, gs-2002 (2002-11-29) and intc-2002
(2002-12-28) both write the suffixed one, and 2002-03-15 is the only rule date
in that interval.

### §c — Item 13 had one caption where the form has two.

Same shape, different release. The `", and Director Independence"` suffix comes
from Release 33-8732A, *Executive Compensation and Related Person Disclosure*
(published 2006-08-11), which registrants comply with in Forms 10-K **for
fiscal years ending on or after 2006-12-15**. `ALIAS_FROM["13"] = date(2006, 12, 15)`.

### §d — Item 10's boundary was three years early.

`ALIAS_FROM["10"]` read `2003-08-14`, i.e. the table assumed Item 10 became
"Directors, Executive Officers and Corporate Governance" with the SOX
renumbering. It did not: "and Corporate Governance" arrives with 33-8732A, in
the same stroke as §c's suffix, on the same 2006-12-15 date. For three years of
filings the envelope rendered a 2006 caption over a section whose own heading
reads the 1993 one — ba-2003 (`Item 10. Directors and Executive Officers of the
Registrant*`) and nike-2006 (period end 2006-05-31, six months short of the
boundary) are both in the corpus. `ALIAS_FROM["10"] = date(2006, 12, 15)`.

### §e — Item 15's boundary was a year early, and its legacy alias was a caption the form never had.

Two defects in one entry. Item 15 came into existence at 2002-08-29 (Release
33-8124) carrying the caption it inherited from the old Item 14 —
*"Exhibits, Financial Statement Schedules, and Reports on Form 8-K"*. The
`"and Reports on Form 8-K"` clause outlived the renumbering by two years: it
died with Release 33-8400, *Additional Form 8-K Disclosure Requirements and
Acceleration of Filing Date* (adopted 2004-03-16, effective 2004-08-23), which
eliminated the requirement to list Form 8-K reports in periodic reports.

Meanwhile the legacy alias sitting in `TITLES["15"]` was *"Exhibits and
Financial Statement Schedules"* — a wording Item 15 has never had as its
legacy caption at all (it is a filer variant of the modern one; nike-2006 and
cat-2023 both write it). So a filing in the 2002–2004 window could render
neither the caption it should have nor any caption the form ever used at that
date.

Both are corrected: the legacy alias becomes the 8-K variant, and
`ALIAS_FROM["15"] = date(2004, 5, 23)` — **not a new constant**, but the same
period-end boundary `ADDED["9B"]` already carries, since 33-8400 is the release
that created Item 9B. One release, one date, two entries that now agree.

The corpus confirms the window on both edges: the 8-K clause is present in all
four fixtures inside it (gs-2002, intc-2002, tgt-2002, ba-2003) and absent from
every fixture after it (bac-2006, wfc-2008, sgrp-2019). No fixture has a period
end between 2004-05-23 and 2006-05-31, so the boundary sits inside an empty
band — the same one-sided position ADR-010 ruling 2 and `SOX_INTERIM` occupy,
and the same honest limitation.

### §f — Item 5's `ALIAS_FROM` is probably late by 20 months, and is NOT changed here.

`ALIAS_FROM["5"] = 2005-12-01` dates the *"…and Issuer Purchases of Equity
Securities"* caption to the Securities Offering Reform date that brought 1A and
1B. The diff's reading is that the issuer-purchase clause belongs to Release
33-8335, *Purchases of Certain Equity Securities by the Issuer and Others*
(2003-11-10), whose Item 703 disclosures apply to periods ending on or after
2004-03-15 — 20 months earlier.

It is not changed, for one reason: **no committed fixture has a period end
between 2004-03-15 and 2005-12-01**, so no eval case can tell the two dates
apart, and moving a constant no case can see is the ADR-010 sin this repo names
by name. Fixing it needs one real EDGAR filing with a fiscal year ending in
that window, and adding a fixture moves the T13 benchmark corpus and every
published figure derived from it (`docs/analysis-report.md` §3–§5, ADR-021).
That trade belongs to whoever re-runs the benchmark, so it is logged as open
debt in `tasks/TODO.md`.

**What pins the constant, precisely** (corrected in PR #17 round 1 — the first
version of this paragraph claimed more than it had): `era-label-bac-2006.json`'s
item-5 check asserts the modern caption at period end 2006-12-31, which bounds
`ALIAS_FROM["5"]` from **above** and nothing else. It is blind to every earlier
value, including 2004-03-15 — that move left the whole gate green (fast 51/51,
invariant 13/13, `[segment self-check] ok`). The two-sided assert now in
`segment._demo` is what catches it, and it deliberately pins a value this
section doubts: with no fixture in the band to decide the question, moving the
constant has to be a decision made in the open, not a silent edit.

### §g — Two more investigated, both left alone, both for the same reason.

- **Item 7A's second phase.** Release 33-7386 phased market-risk disclosure in
  twice: fiscal years ending after 1997-06-15 for banks, thrifts and
  registrants over $2.5B market cap, and after 1998-06-15 for everyone else.
  `ADDED["7A"]` carries only the first date, so a small FY1997 registrant is
  expected to have an item it was exempt from. The direction of that error is
  the reason it stays: over-expecting produces a loud `missing` plus
  `expected_item_missing`, while under-expecting would drop 7A from `expected`,
  which means `find_candidates` never makes its heading a candidate and the
  section is annexed to its neighbour **in silence** — exactly the failure
  ADR-010 fixed for 9C. ibm-1997 and ko-1997 (both large, both with a real 7A)
  would be the filings to lose it. The exemption also is not recoverable from
  the document: nothing on the cover states market cap.
- **Item 6's `[Reserved]` boundary (2021-02-10).** Release 33-10890 permitted
  early compliance from 2021-02-10 and mandated it for fiscal years ending on
  or after 2021-08-09. Either date mislabels somebody in that six-month window
  — early adopters under the late date, everyone else under the early one —
  and no fixture has a period end inside it, so there is no evidence to choose
  with. Unchanged.

## Consequences

- **The gate**: fast 51/51, invariant 13/13 after the fix; 47/51 at the
  red commit that precedes it (four cases red, eleven assertions).
- **`item_field` is now the load-bearing check type it was built to be.** Before
  this milestone it appeared in six cases, five of them about item 14, and no
  case asserted a title for items 5, 10, 12, 13 or 15 in any era — the same
  structural blindness the pre-B audit found, and the reason `item_field` exists.
- **Confidence was NOT untouched, and the first version of this ADR said it was**
  (corrected in PR #17 round 1). `validate.score` takes `BASE_STRICT` (0.95) over
  `BASE_WEAK` (0.75) on `title_similarity >= 0.8`, and `title_similarity` is
  computed against the very `TITLES` aliases this ADR edits. Measured across all
  37 fixtures, `main` vs this branch: **10 spans move 0.75 → 0.95** — ba-2003
  items 12/13/15, gs-2002 item 15, ibm-1997 item 12, intc-2002 items 5/15,
  tgt-2002 items 12/13/15 — and 30 titles change across 11 fixtures. The
  direction is right (a heading that now matches a caption the form actually had
  is better evidence, not worse), which is precisely why it needed saying: for
  those ten items the envelope had been publishing a 0.75 that was **a real
  signal of the defect**, and no case in the suite read the field. All ten are
  pinned now — three in `era-label-ba-2003`, the rest added to the existing
  `gs-2002-transitional-numbering`, `ibm-1997-shallow`, `intc-2002-shallow` and
  `tgt-2002-shallow` cases, each red at 0.75 against the pre-fix taxonomy.
  What survives of the original claim is narrower and still true: **no status,
  offset, warning or `doc_status` moves**, so nothing escalated and nothing in
  the envelope's headline said a label was from the wrong decade.
- **Filer wording is evidence, never ground truth**, and this milestone is where
  that got demonstrated rather than asserted: tgt-2002 writes the pre-2002
  Item 12 caption 11 months after the rule bound it, ba-2003 writes the pre-2006
  Item 10 caption, and bac-2006 writes a pre-2004 Item 5 caption while writing
  the current caption for four other items in the same document. All three are
  labeled by the canon, and `era-label-ba-2003.json` and `-bac-2006.json` pin
  exactly that.
- **Two dates in the table are still one-sided compromises** (`ADDED["9B"]`,
  `ADDED["9C"]`) and `ALIAS_FROM["15"]` now deliberately reuses the first of
  them rather than adding a third. The compromise is unchanged, not multiplied.
- **What would reopen this**: a fixture whose period end lands in the
  2004-03-15 → 2005-12-01 band (§f), in the 2021-02-10 → 2021-08-09 band (§g),
  or a smaller-reporting-company filing from FY1997–98 (§g). Each turns one of
  the two "no evidence to choose with" entries into a case that can decide.
