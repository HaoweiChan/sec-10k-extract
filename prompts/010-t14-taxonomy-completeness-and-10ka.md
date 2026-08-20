# 010 — T14/A6: diffing a table against the law, and ruling a stretch out (2026-08-20)

A pr-loop cycle with two deliverables that pull in opposite directions: find
everything wrong with the era taxonomy (open-ended), and decide whether 10-K/A
gets built (a decision whose correct answer, under the T8 freeze, was almost
certainly *no*). Outcome:
[ADR-023](../specs/decisions/ADR-023-era-label-corrections.md) (five era-label
corrections, item set unchanged),
[ADR-024](../specs/decisions/ADR-024-10ka-out-of-scope.md) (10-K/A out, with the
refusal asserted rather than assumed), five new `era-label-*` cases, and no new
fixture.

## The prompt decisions that mattered

- **"The gap becomes a failing eval case before any code changes" was stated as
  the validation gate, not as a reminder.** Hard rule 2 is in `CLAUDE.md`
  already; quoting it *into the task block* is what made the red commit
  (921be5f, 47/51 = 0.922, `--no-verify` explained) a deliverable rather than an
  inconvenience on the way to green. The eleven failing assertions in that
  commit are the only durable evidence that the five defects were real and not
  reconstructed after the fix.

- **"If a gap turns out to be correct as-is, that is a legitimate finding too:
  record it, do not invent a change."** This did most of the work. Three of the
  eight things the diff flagged survived scrutiny — `ADDED["7A"]`'s single
  phase-in date, `ALIAS_FROM["6"]`'s early-compliance date, and (for a different
  reason) `ALIAS_FROM["5"]` — and the pre-authorization to report a non-change
  is why they are three sourced paragraphs in ADR-023 §f–§g plus three open-debt
  rows, instead of three plausible edits to a frozen table. A taxonomy audit
  with no such clause converges on churn: every date can be argued a few weeks
  either way, and each argument looks like progress.

- **The one-sided-compromise framing was handed over, not rediscovered.** "*several
  are deliberate one-sided compromises (period-end keying vs. rule
  effective/filing dates) recorded in ADR-007, ADR-010, ADR-013, ADR-015 …
  read the whole taxonomy block and its comments first — every date in it
  already carries a recorded rationale.*" That sentence is why
  `ALIAS_FROM["15"]` reuses `ADDED["9B"]`'s existing 2004-05-23 constant rather
  than introducing a fourth date derived the same way from the same release, and
  why §g's 7A finding is written as *the asymmetry is correct* rather than *the
  date is incomplete*. Under-expecting an item is silent; over-expecting it is
  loud. Only one of those is a bug.

- **The stretch was pre-disposed as a ruling, in both directions.** "*'out of
  scope, and here is the evidence and reasoning' is a complete, acceptable
  outcome, and given the T8 freeze guard it is the likelier correct one.*" Then
  the shape of an acceptable *out*: what it is, what the pipeline does today,
  what support would cost, what reopens it. That converts the cheap answer into
  a real one — ADR-024's argument is not "the freeze forbids it" but the
  measured claim that merely accepting the form would report `ambiguous` on a
  correct Part III-only amendment, which is *worse* than the refusal it
  replaces. The freeze is the second reason, not the first.

- **"Do not ship an untestable code path — that is the ADR-010 sin this repo
  names explicitly."** Cited once in the task, load-bearing three times: it kept
  `ALIAS_FROM["5"]` unmoved (§f), it kept the 10-K/A ruling from becoming a
  best-effort parse, and it pushed the 10-K/A refusal into a `_demo` assertion
  on *both* detection routes — the ADR-016 treatment for behaviour no fixture
  can carry. A repo whose sins are named and numbered can have them cited at an
  implementer in one clause.

## What the diff actually found, and what that says about the eval set

The item **set** was complete in every era — 1993, 1997, the SOX interim, 2005,
the 2010–2011 Reserved window, 2016, 2021, 2023 — and nothing in `ORDER`,
`ADDED`, `LEGACY_PART` or `SOX_INTERIM` needed to move. The item **labels** were
wrong five ways, and every one of them was invisible to every check type in the
adapter except `item_field`: no status, offset, confidence, warning or
`doc_status` changes when a span is right and its name is from the wrong decade.

That is the same structural blindness the pre-B audit found when it added
`item_field` for item 14 — and the fact that it recurred, in five more places,
on a table that four ADRs had already corrected, is the honest lesson of this
milestone. A check type that exists but is used by six cases (five of them about
one item) is a check type the eval set has not actually adopted.

## Cost

No LLM calls, no paid API. Two EDGAR fetches with the repo's declared
User-Agent (the SEC's own `form10-k.pdf` for the authoritative captions, and
`full-index/2024/QTR1/form.idx` for the 10-K/A population figure ADR-024 cites),
plus four web searches for release dates. Nothing was added to
`evals/fixtures/`, which is deliberate: the benchmark corpus of record and every
published figure derived from it stay valid.

## Assumption → Eval contradiction → Correction

- Assumed: the four `ALIAS_FROM` entries dated `2003-08-14` were four consequences
  of one rule — the SOX renumbering that moved Controls to 9A and Exhibits to 15
  — because that is the boundary the era table grew around and the comments beside
  them said so.
- Eval said: `era-label-ba-2003` and `era-label-nike-2006`, red on five
  assertions. Item 10's "and Corporate Governance" is Release **33-8732A**'s
  (FY ends on/after **2006-12-15**), three years later, and item 15 kept "and
  Reports on Form 8-K" until Release **33-8400** (effective 2004-08-23) — the
  same release that created 9B, whose period-end boundary the table already
  carried as `ADDED["9B"] = 2004-05-23`. ba-2003 rendered a 2006 caption over a
  heading reading `Item 10. Directors and Executive Officers of the Registrant*`,
  and nike-2006 did the same six months before the boundary.
- Corrected: `ALIAS_FROM["10"]` and a new `["13"]` → 2006-12-15; `["15"]` →
  2004-05-23, **reusing** 9B's constant rather than deriving a fourth date the
  same way from the same release. ADR-023 §c–§e.

- Assumed: the alias lists "already carry the era variants" and only the
  *selection* between them was missing — the pre-B audit's own wording, which
  had been true for items 4, 10, 14 and 15.
- Eval said: `era-label-ge-1994` and `era-label-textron-2001`, red on six
  assertions. Items 12 and 13 have exactly one alias each, both post-2002, so no
  filing before them could be labeled at all: every pre-2002 filing was rendered
  with the equity-compensation-plan suffix (33-8048, FY ends on/after
  2002-03-15) and every pre-2006 filing with ", and Director Independence".
- Corrected: legacy aliases added for both, with their own dates. The audit
  sentence that had been inherited as an invariant was true of the codes that
  audit looked at, and of no others.

- Assumed: `TITLES["5"]`'s legacy caption, "Market for the Registrant's Common
  **Stock** and Related Stockholder Matters" — carried in the table and repeated
  in three synthetic strings inside `segment.py`'s own self-check.
- Eval said: 8 of 8 committed pre-2005 fixtures write "Common **Equity**"
  (ge-1994, ibm-1997, ko-1997, textron-2001, intc-2002, gs-2002, tgt-2002,
  ba-2003) and Reg S-K Item 201 is titled "Market price of and dividends on the
  registrant's common equity and related stockholder matters". "Common Stock" is
  a caption Form 10-K has never had, in any era.
- Corrected: the alias, and the three self-check strings that had been quietly
  teaching it back. The only one of the five defects findable by reading the
  table alone — and the one that had survived longest.

- Assumed: pinning the remaining doubts (the item-5 boundary, and the 10-K/A
  refusal) meant committing one fixture each, the way this repo has answered
  every previous "no case can see it".
- Eval said: not the eval set — the **benchmark** artifact of record. ADR-021's
  published corpus figures (`n=33`, 2.104 MiB mean, the §5 projection) are
  derived from the fixture directory itself, so a fixture added for a label
  boundary silently restates numbers in `docs/analysis-report.md` §3–§5.
- Corrected: neither fixture added. The 10-K/A refusal is asserted at the layer
  instead (`normalize.py::_demo`, both detection routes, ADR-016 treatment), and
  the item-5 boundary is left unmoved and logged as open debt naming the fixture
  that would settle it. A corpus that is load-bearing for two different
  measurements is not free to grow for one of them.

- Assumed: `era-label-bac-2006`'s item-5 check pins `ALIAS_FROM["5"]` — written
  in four places, including this file's chain entry above, in the same breath as
  a debt row about moving that constant to 2004-03-15.
- Eval said: nothing, which was the finding (PR #17 R1). The check asserts the
  modern caption at period end 2006-12-31, so it bounds the constant from
  **above** and is blind to every earlier value: the debt row's own candidate
  move leaves fast 51/51, invariant 13/13 and the module self-check green. A
  claim about what a check catches is an executable claim, and this one was
  written from the intent of the check rather than from running the mutation —
  the exact failure mode `prompts/009` named ("do not assert a property of an
  executable contract in prose without running it"), one milestone later.
- Corrected: a two-sided assert on `ALIAS_FROM["5"]` in `segment._demo` (red
  under the reviewer's own repro), and all four claims restated to say the case
  gives an upper bound and nothing else.

- Assumed: a wrong era label is invisible to every check type except
  `item_field` — "no status, offset, confidence, warning or `doc_status` moves".
- Eval said: `confidence` moves on **10 spans across 5 fixtures**, 0.75 → 0.95,
  because `validate.score` picks `BASE_STRICT` on `title_similarity >= 0.8` and
  that similarity is computed against the aliases this diff edits (PR #17 R2).
  For those ten items the envelope had been publishing a real signal of the
  defect — a *lower* confidence — and no case in the suite read the field, which
  is how a claim that "nothing else moves" survived a full green gate.
- Corrected: ten `confidence` checks added (three in `era-label-ba-2003`, the
  rest into the existing `gs-2002`, `ibm-1997`, `intc-2002`, `tgt-2002` cases),
  all ten watched red at 0.75 against the pre-fix taxonomy, and the ADR sentence
  narrowed to what is actually true — no status, offset, warning or
  `doc_status`.

- Assumed: with R1 closed, the table was covered — "every constant the comment
  describes is correct and pinned by a case or a `_demo` assert", written into a
  debt row and a resolution artifact while fixing the *previous* round's
  overstatement about what a check proves.
- Eval said: nothing again, and that was the third instance of one species
  (PR #17 R5). `ALIAS_FROM["6"]` was pinned by neither a case nor an assert:
  moving it to 1990-01-01 relabels item 6 as "[Reserved]" on 26 committed
  fixtures and the gate stays 51/51. "Correct" was overstated too — that entry
  holds an early-compliance date the repo's own §g says mislabels one side of a
  six-month window.
- Corrected: a two-sided assert for item 6 (red under the reviewer's repro,
  `AssertionError` at `segment.py:664`), and then — the part that matters — an
  **executed mutation sweep over all eight `ALIAS_FROM` keys, both directions**,
  before rewriting the sentence: seven caught by `_demo`, `"4"` caught by the
  fast suite at 50/51, none uncaught. The lesson is not "check your claims"; it
  is that a universal quantifier about a table is a script that takes a minute
  to run, and three rounds went by asserting one from memory instead. The
  restated sentence also separates the two words that had been fused: pinned
  (executed, now true of all eight) and correct (still open for `"5"` and `"6"`,
  by ADR-023 §f and §g).

