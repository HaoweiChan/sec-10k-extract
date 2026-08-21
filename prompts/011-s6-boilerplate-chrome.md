# 011 — S6: boilerplate chrome, and the instruction that decided the design (2026-08-22)

A pr-loop cycle whose deliverable is a **post-freeze capability** — the second
one after T12, and the first that ships. Outcome:
[ADR-026](../specs/decisions/ADR-026-boilerplate-chrome-exclusion.md), four eval
cases, `src/sec10k/boilerplate.py`, and one debt row.

## The prompt decisions that mattered

- **Two named prior sins were quoted at the implementer before any code.** The
  task prompt did not say "write a good ADR"; it said the ADR must state *"every
  threshold and where its value came from (measured from the fixture corpus, or
  explicitly a judgment call said to be one — do NOT write 'measured' over a
  guessed number, that is the exact defect T5's row is still open for)"* and
  pointed at ADR-010's other standing sin, shipping a code path no eval case can
  exercise. Both fired. The first forced §c4 to label `PAGE_DIGITS = 3` a
  judgment call in bold rather than dressing it as derived. The second **deleted
  a threshold**: a `MAX_LINE_LENGTH = 80` gate was written, then measured, then
  found to reject nothing in the corpus — no line over 35 characters passes the
  other three gates anywhere — so it was removed instead of kept and justified.
  A prompt that had only asked for "measured thresholds" would have got four
  measured-looking numbers and the dead one among them.

- **The near-miss direction was specified as three concrete shapes, not as a
  principle.** *"a repeated legitimate heading, a table row that looks like a
  running head, a page-number-like figure inside real prose."* That is what made
  the first design die on contact with data. The obvious rule — a line repeating
  often is chrome — was tested against those three shapes and lost immediately:
  `$` repeats 1,058 times in cvx-2015, `Total` 39 times in msft-2013, and
  msft-2013 prints a bare `Item 8` on 41 pages. Naming the false positives in
  the spec turned "detect repeated lines" into "find what separates a page
  header from a table column", which is where the gap-regularity idea came from.

- **The corpus was declared off-limits to growth, with the reason attached.**
  *"ADDING a new fixture joins the benchmark corpus and moves the n=33 figures
  ADR-021 publishes."* The constraint turned out to improve the work rather than
  constrain it: the adversarial material this feature most needed was already
  committed, and real filings are harsher input than anything hand-written. Zero
  fixtures added.

- **"Watch them fail" was made specific enough to be checkable.** The prompt
  asked for the failing output pasted into the report. That is a low bar — an
  unimplemented check type fails too — so it was raised in-session: after the
  cases went green, each was re-falsified by mutation (§ below). The gap between
  "I saw it red" and "I saw it red for its own reason" is the whole difference
  between an eval and a decoration, and only the second one is evidence.

## The mutations, and what each proved

| mutation | expected red | observed |
|---|---|---|
| A — make `normalized_text` actually strip the chrome (the design ADR-026 §d rejects) | the invariance cases | `boilerplate-offsets-invariant`: *normalized_text differs with exclusion on vs off*; `verbatim`: *item 15 offsets outside normalized_text* |
| B — `MIN_SPREAD` → 0.0 (repetition alone is enough) | the near-miss cases | `boilerplate-near-miss` 30 runs > max 0; `boilerplate-chrome-detected` red on `Item 8` (41), `Item 7` (23), `PART I` (21), `Item 1` (11) |
| C — page numbers with no adjacency requirement | the near-miss case | `boilerplate-near-miss` 1,814 runs > max 0 |
| control — unmutated | none | all four green |

Mutation A is the one worth keeping: it is not a hypothetical, it is the design
a reasonable implementer would have reached for, and it fails the invariant
suite by name.

## Assumption → Eval contradiction → Correction

- Assumed: a repeated short line is a running head, which is what "repeated
  running heads" in the task's own wording invites.
- Eval said: the corpus sweep, before any case existed — `$` × 1,058 and `)` ×
  860 in cvx-2015, `Total` × 39 and `Item 8` × 41 in msft-2013. A count-only
  rule strips thousands of table cells out of one filing.
- Corrected: repetition became one of three gates. Gap regularity (CV ≤ 0.60)
  and document spread (≥ 0.70) do the discriminating; `boilerplate-near-miss`
  is the committed case, and mutation B is the proof it can go red.

- Assumed: `exclude_boilerplate=True` should hand the caller cleaner text —
  i.e. `normalized_text` with the chrome removed.
- Eval said: INV-S2's enforcement, run as mutation A — every item offset after
  each removal shifts, and `verbatim` reports *item 15 offsets outside
  normalized_text*.
- Corrected: exclusion is an annotation, never an edit. The envelope carries
  `{start, end, kind}` spans; the stripped view is `strip_chrome()`, computed on
  demand and never stored. ADR-026 §d, `boilerplate-offsets-invariant`
  (invariant suite).

- Assumed: the eval-check vocabulary's `min` should default to 1 whenever a
  case names a `value` or `kind`, so a typo fails loudly.
- Eval said: every near-miss check in all three fixture cases went red —
  `boilerplate 'Total'/<any kind>: 0 runs < min 1` — because `{"value": "Total",
  "max": 0}` is asserting absence and was being made to demand a hit.
- Corrected: `min` defaults to 1 only when no bound is given at all; `max`
  alone implies `min: 0`. Pinned in
  `src/sec10k/test_eval_adapter.py::test_boilerplate_checks`, which is also the
  only place the `boilerplate_spans_sane` off-by-one branches are exercised.

- Assumed (in the first draft of `boilerplate-txt-chrome`): ge-1994's Item 7 is
  `extracted`.
- Eval said: `item 7 not extracted: incorporated_by_reference`.
- Corrected: the case now asserts `incorporated_by_reference`, taken from
  `evals/adversarial/ge-1994-oldformat.json`, which pins the same status
  independently. A small one, recorded because it is the ordinary case for why
  cases are watched red before they are trusted — the author's belief about a
  fixture was simply wrong, and nothing but the run would have said so.
