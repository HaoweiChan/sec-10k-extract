# 024 — D13: adjudicating the internal-pointer disagreement (2026-08-27)

A decision row, not a capability. The question was two ADRs old: when an
item's body is a short, well-formed sentence pointing at a page inside the
same document, while the item's real content sits unreached elsewhere — is
that a defect in the extraction, or a correct extraction of what the filing
put there? ADR-019 §e recorded the disagreement and declined to settle it;
ADR-034 §e2 then declined the whole A2 class *because* it was unsettled. The
output is [ADR-038](../specs/decisions/ADR-038-internal-pointer-adjudication.md),
one new `debt` case, and no line of `src/` touched.

## The prompt decisions that mattered

- **State the rule before applying it, in the document.** ADR-038 §b is
  written before §c and says so. The failure mode this repo keeps hitting —
  PR #56 R2 is the worked example — is applying a rule to some filings and not
  others in the direction that makes the headline stronger. A rule written
  after the verdicts cannot be checked for that; a rule written before it can,
  and §g2 records the one item that flips under the variant §b rejected.
- **Adjudicate on a printed measurement, never on a summary of a span.** The
  brief said "quote what is actually there — do not summarise a span and then
  rule on your summary", and `tasks/reviews/d13_span_dump.py` exists so every
  span in §c is pasted from a committed dump rather than paraphrased. Two of
  the seventeen items read differently once quoted in full than they had in
  either ADR's prose description of them.
- **The instrument prints the distribution; the ADR makes the call.** The
  first version of the dump script emitted a `reached: True/False` boolean per
  target. It was wrong on four items — a regex cannot tell the *content* from
  a cross-reference *to* it, and `FS-60` matched inside the exhibit index. The
  boolean was deleted in favour of "matches per owning item, matches outside
  every span", which is a measurement, with the adjudication left to §c. The
  same concession `d9_class_scan.py` already makes for its Class B hits.
- **Blind means blind, and one run only.** The `extraction-auditor` subagent
  was handed nine spans with their published envelope fields and one question
  — RIGHT or WRONG — with an explicit list of what not to read
  (`specs/decisions/`, `tasks/`, `docs/`, eval cases, git history) and an
  explicit statement that the implementer held a view and was not disclosing
  it. Its full output is committed verbatim at
  `tasks/reviews/d13-auditor-verdicts.md`, and its input is regenerable with
  `d13_span_dump.py --auditor-input`.
- **Do not re-run the judge until it agrees.** It disagreed on five of nine.
  ADR-038 §d records all five as divergences, with the auditor's own
  weak/strong grading, and §d3 states outright that on `bac-2006` "this ADR
  has no reply". A second invocation would have been tuning a judge, and the
  temptation to make one was the strongest pull in the session.

## Assumption → Eval contradiction → Correction

- **Assumed:** the class is what ADR-034 §b3's scan found — page-numbered
  pointer bodies — and the enumerated list in the D13 task block is the class.
- **Eval said:** `d13_span_dump.py` on `xom-2021`, a filing §b3 names only in
  its *rejection* list, prints four pointer-only items (7, 7A, 8, 15) whose
  targets are titled sections rather than page numbers. §b3 rejected its
  item 15 for "no page number at all" while admitting `ge-1994` item 8 ("See
  index under item 14."), which has no page number either.
- **Corrected:** R1 prong 2 is "a locatable position", not "a page number",
  §b3's rejection of `xom-2021` item 15 is overturned in place, and the
  adjudicated dev census moves 14 items/5 filings → **17/6** (TD-149 widened).
  The uncomfortable half is taken twice: `nvda-2024` item 8, which ADR-019
  §e's own amendment called a fourth class member, is ruled OUT on prong 2 —
  and `xom-2021` item **8**, which the first draft readmitted along with 7/7A/15,
  is ruled OUT on prong 1 under PR #60 R3, which is what makes the census 17
  and not 18. Prong 1 is a test of KIND, not of length: ADR-007's
  `IBR_REMAINDER_MAX = 300` was the obvious candidate and it fails the
  calibration — `intc-2002` item 5's standalone content is 110 chars and
  ADR-034 §b3 rejects it anyway.

- **Assumed:** `cvx-2015` items 7 and 8 — the two the committed `debt` case
  actually asserts — are the defects, as ADR-019 §e read them.
- **Eval said:** they are the two the envelope already flags. ADR-035's
  `item_span_near_empty`, built after §e was written, carries both at 0.80
  with `review_required: true`. Items 2, 6 and 7A of the same filing publish
  0.95 with `review_required: false` and no warning carrying their code.
- **Corrected:** 7/8 ruled `correct`, 2/6/7A ruled `defect`, and the new case
  `cvx-2015-silent-pointer-items.json` asserts the three the old case does
  not. The old case's `min_chars` assertions now encode a capability outcome
  on two items the ruling calls correct — logged as TD-156 rather than
  re-authored, because re-authoring changes what is red.

- **Assumed:** a blind auditor that agreed on the disputed item would settle
  the class, and a nine-item pointer sample was a fair test.
- **Eval said:** the auditor returned WRONG on nine of nine and flagged the
  uniformity itself as suspicious. Every item in the sample was pointer-bodied,
  so a blanket verdict was available without discriminating anything. It
  supplied the control the sample lacked — `spatz-2014` items 2/3/6 (`None.`,
  `None.`, `Not applicable.`), also 0.95 / `review_required: false`, which it
  judged **correct** — which is ADR-005 re-derived blind and is what makes its
  other verdicts usable.
- **Corrected:** the sample-design defect is recorded as a weakness in
  ADR-038 §d6 rather than fixed by drawing a better sample after seeing the
  answers. A D13-shaped adjudication should carry two or three non-pointer
  controls in the sample it hands the auditor.

- **Assumed:** appending amendment notes to ADR-034 is a documentation edit
  with no gate consequence.
- **Eval said:** `ledger_line_refs` — `tasks/TODO.md` cites
  `ADR-034…md:493` and `:532` and quotes the sentence at each. The inserted
  notes moved both (`:509`, `:561`). This is the third recorded occurrence of
  an ADR insertion invalidating ledger line refs in this repo, and the first
  one the check caught *before* commit rather than in a review round.
- **Corrected:** both citations re-pointed, three new citations into ADR-038
  added, `min_refs` raised 11 → 14, and the raise mutation-tested in all three
  directions (wrong line number → RED; reworded quotation → RED; deleted
  citation → RED on the floor; restored → GREEN). The check was run **after**
  the final ADR edit, not before.
