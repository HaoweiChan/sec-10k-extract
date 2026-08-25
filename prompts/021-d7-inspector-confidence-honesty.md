# 021 — D7: qualifying a number the pipeline is not allowed to change (2026-08-26)

D7 closes the second failure line of the 2026-08-24 demo: not that `conf 0.95`
was wrong, but that it stood alone. `doc_status` and the warnings list live in
the top banner; the side panel a viewer actually reads showed a per-item number
with no visual link back to either, and, as the postmortem puts it, during a
demo the panel is the product. Display layer only — `extract_items` is
untouched and every default-flag envelope is byte-identical. No ADR: nothing
here rules on anything ADR-018, ADR-019 or ADR-027 has not already ruled on,
and the row that *does* need one (making the number itself move on a stub or a
pointer span) is D8.

## The prompt decisions that mattered

- **The qualifier reads `evidence.warnings`, not a re-filter of `v.warnings`.**
  Both would produce a list of codes targeting this item; only one of them is
  already the list that MOVED the number. `evidence.warnings` is `score()`'s own
  `hits`, so the panel names exactly the codes that each cost the item
  `WARN_PENALTY`, and inherits ADR-018's exclusion of `expected_item_missing`
  — which only restates the `missing` status the status badge already shows —
  for free. Re-deriving "item-targeted" in the display layer would have been a
  second definition of the same thing, free to drift from `score()`'s. The
  regression fixture pins that: shape (5) re-derives it from the NUMBER
  (`it.confidence < 0.9`), which flags clean IBR items at 0.85 and stays silent
  on a 0.95 no validator ever touched — i.e. on every item of the demo's own
  cvx-2015 shape.

- **The check pins an ADJACENCY, not a question.** The first instinct is to ask
  the file a question — does it mention `doc_status` near the badge? A question
  about a hop is answerable by a broken hop; `boilerplate_plumbing`'s allow-list
  records two rounds of exactly that (PR #27 R5/R6), where `not bool(...)`,
  `!= "1"` and `return true` all answered correctly while severing the wire. So
  `check_confidence_honesty` finds every live interpolation of `it.confidence`
  and requires the next characters to be the pinned
  `${docQual()}${itemQual(it)}`; `min_conf_sites` stops the check passing by
  deleting the sites instead.

  **That claim was overstated in round 0 and is corrected here.** The first
  version of this file said a bare confidence was "unrepresentable". PR #53
  found three attacks through that word in one review: the pinned call to the
  banner strip was never pinned at all (R1), the pinned *lines* of `docQual`
  and `itemQual` survived intact below an inserted `if(true) return "";` (R2),
  and site discovery was a literal search for `conf ${`, so a site spelled
  `confidence ${it.confidence ?? "—"}` printed a bare number the scan could
  not see (R4). The lesson is the one the check itself was written to teach,
  applied one level up: asking whether TEXT IS PRESENT is not asking whether
  it RUNS. The repair pins the three helper bodies WHOLE, pins the call inside
  the banner assignment that makes it, and scans for the FIELD rather than for
  one spelling of its label. What remains out of reach — a site that copies the
  number into a local first — is now written in the case's `ceiling` instead of
  being claimed away.

- **The coverage figure is surfaced, never inverted.** The interviewer-feedback
  gap (postmortem §8 gap 1) is stated as "37% attributed, 63% unattributed", and
  the obvious banner sentence is "63% of the document is attributed to items".
  It would be wrong. `validate.py`'s own comment says the figure counts the
  preamble and the tail only — interior gaps between spans are not counted, and
  on ibm-1997 that understates true non-coverage by 9.7 points — so `100 −
  outside` OVERSTATES attribution by exactly the gaps the figure misses. The
  banner therefore publishes the computed number in the direction it was
  computed ("73% of the document lies outside every item") plus the caveat, and
  `must_not_say` forbids the inversion in three forms: the prose claim, the
  attributed-share label, and the `100 -` arithmetic itself. Following the D5
  note's precedent, a display that overstates is a failure of the task, not a
  shortcut, so it is pinned as forbidden wording rather than as wording that
  merely went missing.

- **No figure where none was computed.** `unattributed_content` fires only above
  `UNATTRIBUTED_MAX`, so a document at 20% non-coverage gets no coverage line at
  all. The tempting fix — compute the fraction in the view layer for every
  document — is the envelope change D8 owns (a coverage field plus an escalation
  threshold), and doing it here would put a second producer of the same figure
  in the display layer, which is the shape S9 already taught this repo to
  distrust (`display_text`'s second producer, PR #46 R1). The ceiling is stated
  in the case's own `ceiling` field and demonstrated in the walk: jpm-2024 is
  `ambiguous` with no `unattributed_content`, and the banner says nothing rather
  than deriving something.

- **The exact count came from the run, not from the plan.** The regression
  fixture was written expecting ten failures and reported eleven: the `${100 -
  …}` expression trips the `"100 -"` pin separately from the prose that labels
  its result. The honest move is the one D5's PR #46 R12 established — correct
  the count and the fixture header to what the check actually sees, rather than
  weaken the check to the number already written down. Eleven is now pinned as
  `min_failures == max_failures`, so both a regressed miss and a regressed
  over-fire go red.

## What was deliberately not done

`hdrRight` still ellipsises at 1280 (band 316px, string 655px), so the pane
header degrades to `· DOC…` while the side panel badge — the surface D7's
acceptance names — shows the qualifier in full. Both closes cost something D7
does not own: hoisting the qualifier to the front of the header breaks the
adjacency to the number that this task and its eval case both ask for, and
letting the band wrap changes the `.src-hdr` height S5 made equal to
`#source`'s. Logged as debt with two others (`Origin: D7`) rather than absorbed.

## Assumption → Eval contradiction → Correction

- Assumed: the regression fixture's eleven-shape mutation would report **ten**
  failures — one per shape, with the inverted `100 - outside` arithmetic and the
  "attributed to items" label counted as a single publish-the-complement defect.
- Eval said: `ui-confidence-honesty-regression` reported **11**, because
  `must_not_say` catches the `${100 - (m ? +m[1] : 0)}%` expression separately
  from the prose that labels its result.
- Corrected: the case's `min_failures`/`max_failures` moved to 11 and the shape
  list was split into (10) the arithmetic and (11) the label — the check sees a
  real distinction (a strip that computed the complement but labelled it
  honestly would fire only the first), so the record was corrected to the run
  rather than the check loosened to the record. The fixture's own header comment
  moved from "TEN ways" to "ELEVEN ways" in the same pass, since PR #46 R12
  established that a fixture header contradicting its case's count is itself a
  defect.

- Assumed: the browser walk would run through `preview_start` and this repo's
  committed `inspector` launch configuration, as D5's did.
- Eval said: the server exited 126 with `getcwd: Operation not permitted` — this
  worktree lives under `.claude/`, which the preview sandbox cannot read, and
  the harness resolves `launch.json` from the MAIN repo, so a launch entry added
  in the worktree is never consulted.
- Corrected: the walk drives a uvicorn server run from an rsync of the branch in
  the session scratchpad, and `tasks/reviews/d7-browser-walk.json` records that
  substitution in its own `method` block rather than presenting the evidence as
  if it came the sanctioned way.
