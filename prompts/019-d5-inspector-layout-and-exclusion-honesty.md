# 019 — D5: two display-only debt rows, and the line between a pin and a render (2026-08-23)

D5 promoted two rows out of `## Open debt, carried deliberately`: **V5** (PR #21
R1 — `.split`'s `@media(max-width:1100px)` stacked `#source` below `#pane`, so
the compare feature did not exist at 1024px) and **the compare-pane note** (S8 —
with exclusion on the two panes visibly disagree and nothing said why). Both are
display-only; neither touches extraction. No ADR: neither half rules on anything
ADR-026 has not already ruled on, and the second half exists *because* of
ADR-026 §a rather than in tension with it.

## The prompt decisions that mattered

- **The V5 row's Why cell offered two fixes; the task took BOTH.** *"Either the
  sync-scroll control should be disabled/labelled inactive when the panes are
  stacked, or the breakpoint should keep them side by side with narrower
  columns."* Choosing one leaves the other true somewhere: keeping the panes
  side by side to 1024 does nothing for 768, where they still stack, and a
  disabled control at 1100 is a correct label on a layout nobody wanted. So the
  panes stay in one row down to 1024 **and** the control goes disabled with an
  on-screen "inactive: panes stacked" label wherever they do stack.

- **What gives way is the SIDEBAR, not a pane.** At 1024 the grid had
  `290px 1fr 1fr` asking for more width than `main` has. The obvious reading of
  "narrower columns" is to narrow the compare panes; the honest one is that the
  fixed 290px item list is what runs them out of room, so it drops to 196px
  between 1180 and 1000 and the two panes keep the rest. Measured: at 1024 the
  grid resolves to `196px 349.266px 349.281px` with both pane tops at 582.
  Deliberately NOT taken: dropping to two tracks, which is the shape the D5
  regression fixture pins as failure (1) — "narrower columns" read as "one
  fewer pane" hides the compare pane at every width instead of below one.

- **The stacking width is one number, pinned in two places.** The CSS stacks at
  1000 and the JS watches `matchMedia("(max-width:1000px)")`. `check_split_
  breakpoint` derives the expected `matchMedia` width FROM the CSS, so raising
  one without the other reports twice — which matters because the gap between
  two such numbers is the original V5 complaint (a live-looking control over
  panes that cannot honour it) reintroduced in a form neither number shows on
  its own.

- **The note states the limit; it does not imply a fix.** The debt row rules the
  real fix — a raw↔normalized offset map — out as post-freeze scope creep
  (ADR-026 §a), and that ruling stands here. The interesting part is how the
  case enforces it: alongside `must_say` (derived `normalized_text`, raw filing
  bytes, "the two panes will not agree", "no raw-to-normalized offset map in
  this pipeline") there is a **`must_not_say`** list — "panes agree", "panes
  match", "offset map exists". The task named a note that implies the map exists
  as a failure of the task rather than a shortcut, so that failure is pinned as
  forbidden wording, not merely as wording that went missing. A note softened
  into "the two panes match once the offset map exists" goes red three ways.

- **New convention: every new case carries a `ceiling` in its triage.** These
  two checks are STATIC reads — CSS text and markup text. No test in this
  harness issues an HTTP request or lays anything out, and the existing pin
  mechanism has documented holes (a pinned element can be `hidden` and still
  satisfy its pin — this note deliberately is, at rest). So each case says in
  its own triage what it CANNOT see, and names the artifact that can:
  `tasks/reviews/d5-browser-walk.json`, measured at 1280 / 1024 / 900 / 768.
  The alternative was a sentence in a PR body claiming the eval proves the
  rendered layout, which would have been false in exactly the way this repo
  exists to catch.

- **The browser walk was run against a pristine `c13aa5c` too.** The same script
  against the unfixed tree reports 9 failures (`d5-browser-walk-c13aa5c.json`) —
  1024 panes 651px apart, no `disabled` and no inactive label at 900/768, no
  note at any width. A walk that only ever ran green after the fix would prove
  the same nothing an unwatched eval case does.
