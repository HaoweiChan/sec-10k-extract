# ADR-026 — S6: boilerplate chrome is reported as spans, never removed from the text

Date: 2026-08-22. Status: accepted. Implements S6. Sanctioned exception to the
T8 feature freeze (`tasks/TODO.md`, **Freeze guard**), on the pattern
[ADR-020](ADR-020-fallback-not-justified.md) established for T12.

**Ruling**: boilerplate chrome detection ships as an **opt-in annotation, not an edit**. `extract_items(path, exclude_boilerplate=True)` adds one envelope key, `boilerplate` — a list of `{start, end, kind}` runs into `normalized_text`. `normalized_text` and every item offset are byte-for-byte identical with the flag on and off; the stripped view is a derived string produced on demand by `src/sec10k/boilerplate.strip_chrome()` and is never stored.
**Because**: the only way to "remove" text and still satisfy INV-S2 is to not remove it. Rewriting the text moves every offset after each removal, which breaks INV-S2 for exclusion-on runs; carrying a second, stripped copy of the document in the envelope is the second-copy drift hazard the contract already refuses for item text ("there is deliberately no separate `text` field to drift from them"). Spans cost nothing, are addressable, and make offset invariance true by construction rather than by care.
**Enforced by**: the five `evals/adversarial/boilerplate-*.json` cases (`boilerplate-offsets-invariant` in the `invariant` suite) and `src/sec10k/boilerplate.py::_demo`, which `.github/workflows/ci.yml`'s unit-tests job runs — see §g.

---

## a. Why this is a sanctioned exception and not scope creep

The freeze guard says: *"at T8 (B-freeze) the system stops taking features …
A new capability after the freeze is scope creep no matter how good it looks."*
S6 is a new capability. It is in scope for exactly one reason, and it is worth
writing the reason down rather than leaning on the fact that it was asked for:

1. **The human asked for it in writing, on the record** (2026-08-22, recorded
   in the S6 row of `tasks/TODO.md`). CLAUDE.md's delivery-loop clause reserves
   spec-writing to the human. The freeze is a guard against *the implementer*
   inventing work, not against the spec author extending the spec.
2. **T12/ADR-020 is the precedent for the shape of this document, not for the
   answer.** ADR-020 declined a post-freeze capability *on measured data*. The
   pattern it set is: a post-freeze capability gets a written ruling with the
   cost named, whichever way the ruling goes. This one is ruled IN, and the
   cost is named in §f.
3. **It changes no existing behaviour.** §e is the whole argument: with the
   flag off — which is every existing caller, every existing eval case, and
   the web inspector — not one byte of any envelope moves. A capability that
   is invisible unless asked for cannot regress the frozen system; the freeze
   exists to stop the frozen system moving.

What would have made it scope creep: turning it on by default, or changing
`normalize()` so the chrome never reaches `normalized_text` in the first place.
Both were considered and both are refused, in §d and §f2.

## b. What "boilerplate chrome" is defined as

Chrome is **line-shaped**: the unit is one physical line of `normalized_text`,
including its terminating newline and its leading indentation (txt-era
fixed-width layout is part of the line, ADR-006 ruling 2). A line is chrome if
it matches exactly one of three kinds, resolved in this order — a line gets one
kind and one span, so spans never overlap:

| kind | a line is this if… |
|---|---|
| `edgar_chrome` | the whole line, stripped, is nothing but EDGAR SGML page/table furniture — one or more of `<PAGE>` `<TABLE>` `</TABLE>` `<CAPTION>` `<S>` `<C>` `<FN>` and their closers, separated only by whitespace. |
| `running_head` | its exact stripped text occurs **≥ 8** times, the coefficient of variation of the character gaps between consecutive occurrences is **≤ 0.60**, and the first and last occurrence are **≥ 0.70** of the document apart. |
| `page_number` | the whole stripped line is a number of **1–3 digits**, optionally prefixed `Page ` and optionally wrapped in dashes/periods, **and** the nearest non-blank line above or below it is already an `edgar_chrome` or `running_head` line. |

A reader can predict every decision from that table. Three worked predictions,
all confirmed against the corpus in §c:

- `Total`, 39 occurrences in msft-2013 — **not chrome.** Its gap CV is 2.52; it
  clusters in the financial statements. Repetition is not the test.
- `Table of Contents`, 96 occurrences in msft-2013 — **chrome.** CV 0.35,
  spread 1.00. It is the per-page back-link every modern filer puts at the top
  of each rendered page.
- `17` on its own line in the middle of a cvx-2015 table — **not chrome**, because
  no chrome line is adjacent to it. The same `17` inside a sentence is not even a
  candidate: the *whole line* must be the number.

Head versus foot is deliberately not distinguished. Once normalization has
discarded the page breaks there is no signal left that separates them, and
inventing a `running_foot` kind we could not decide would be an assertion
nobody measured.

## c. Every threshold, and where its value came from

Measured over the **28 real EDGAR filings** in `evals/fixtures/` — every
committed fixture that is an actual filing. The 9 self-created mutants
(`toc-titled`, `malformed-html`, `spans-transposed`, …) are excluded from the
measurement because each is a copy of a filing already counted; including them
would double-weight their source. Raw sweep: for every line text occurring ≥ 4
times, its count, gap CV, and spread were tabulated, then each threshold was
moved until a false positive appeared.

### c1. `MIN_REPEATS = 8` — measured, with two counts of margin

Every line in the corpus that clears the CV and spread gates, ordered by count.
The chrome/not-chrome split is total and it happens between 6 and 8:

| fixture | line | count | CV | spread | chrome? |
|---|---|---|---|---|---|
| ba-2003 | `Net earnings before cumulative effect of accounting change` | 4 | 0.49 | 0.81 | no — prose |
| ba-2003 | `Diluted earnings per share before cumulative effect…` | 4 | 0.48 | 0.83 | no — prose |
| cvx-2015 | `66` | 4 | 0.51 | 0.83 | no — table cell |
| cvx-2015 | `389` | 5 | 0.22 | 0.84 | no — table cell |
| jnj-2016 | `89` | 5 | 0.58 | 0.96 | no — table cell |
| ibm-1997 | `<CAPTION>` | 6 | 0.49 | 0.89 | **yes** |
| jnj-2016 | `12` | 6 | 0.59 | 0.98 | no — table cell |
| ibm-1997 | `</TABLE>` | 8 | 0.58 | 0.97 | **yes** |
| … | (everything at 14 and above) | | | | **yes** |

Nothing in the corpus occurs exactly 7 times, so 7 and 8 are the same gate on
this data; 8 was taken as the lower of the two true chrome runs at or above the
split, leaving the nearest false positive (jnj-2016's `12`) two counts below.
Consequence, stated rather than hidden: ibm-1997's `<CAPTION>` at 6 is **missed**
by this rule — it is the one true chrome run below the gate, and it is caught
anyway, by `edgar_chrome`. Lowering the gate to 6 to recover it would admit
jnj-2016's `12` at the same count, which is the trade this value refuses.

### c2. `MAX_GAP_CV = 0.60` — measured, with margin

Among all lines clearing the spread and count gates, the highest CV that is
genuinely chrome is **0.58** (ibm-1997 `</TABLE>`; premier-pacific-2016
`Table of Contents`). The lowest CV that is genuinely NOT chrome is **0.84**
(cvx-2015's table cell `29`, count 9, spread 0.88). 0.60 sits inside a real
empty band 0.26 wide. Nothing in the corpus falls between 0.58 and 0.84.

### c3. `MIN_SPREAD = 0.70` — measured, with margin

Among all lines clearing the CV and count gates, the lowest spread that is
genuinely chrome is **0.82** (jpm-2024's `JPMorgan Chase & Co./2024 Form 10-K`,
286 occurrences). The highest spread that is genuinely not chrome is **0.64**
(jpm-2024's `2024`, count 8, CV 0.57). 0.70 sits inside that band.

This is the gate that rejects the section-level running heads, which are the
interesting near-misses: jpm-2024's `Notes to consolidated financial
statements` (73×, CV 0.28 — as regular as a page header) is rejected at spread
0.42, and msft-2013's `Item 8` (41×, CV 0.39) at spread 0.35. The second one is
the important rejection: a repeated bare item code must never be classified as
furniture.

### c4. `PAGE_DIGITS = 3` — a judgment call, not measured

**This is a guess with a reason, and it is labelled one.** Nothing in the
corpus discriminates 3 digits from 4; the observed page numbers run 1–334, so
any cap ≥ 334 fits the data equally well. 3 was chosen because it is the
smallest cap that covers every page number actually observed while excluding
4-digit years, which is the false positive that showed up in the first draft
(ibm-1997's `1997` sitting on its own line next to a `<TABLE>` marker). A
filing longer than 999 pages loses page-number detection past page 999. That
ceiling is accepted, unmeasured, and written here so nobody later reports it as
a bug in a rule that claimed to be derived.

### c5. No maximum line length

A `MAX_LINE_LENGTH = 80` gate was written and then deleted. Measured: **no line
longer than 35 characters passes the other three gates anywhere in the
corpus**, so the gate rejected nothing any eval case could exercise — a code
path no case can reach is the ADR-010 sin, and the fix for it is deletion, not
a case invented to justify it. If a 200-character line genuinely repeats 8
times at page intervals across a whole filing, it is a repeated legal footer,
which is chrome.

### c6. What the thresholds produce

| | |
|---|---|
| Fixtures where detection fires | **16 of 28** |
| Fixtures where it reports nothing | 12 of 28 |
| Total lines excluded | 2,934 (583 `edgar_chrome`, 1,165 `running_head`, 1,186 `page_number`) |
| Share of corpus characters excluded | **0.607%** (44,247 of 7,289,571) |
| Highest single-filing share | ibm-1997, 2.88% (txt-era SGML furniture) |
| Distinct non-`page_number` line texts excluded, corpus-wide | `Table of Contents`, `JPMorgan Chase & Co./2024 Form 10-K`, and literal SGML furniture — nothing else |
| Distinct `page_number` values excluded | the integers 1–334, all 334 of them, and nothing else |

Every distinct excluded line text was read by hand. **Zero false positives** —
no run of filing prose is excluded anywhere in the corpus. That last row is the
claim this ADR most wants checked, so the audit is reproducible: iterate the 28
fixtures, `find_chrome(normalized_text)`, and print the distinct
`(kind, text[start:end])` pairs.

The 5 held-out filings in `evals/heldout/fixtures/` were **not** measured and
not looked at. `evals/heldout/README.md`'s burn rule says an outcome that
influences implementation burns the case; these thresholds are implementation,
so held-out data is exactly what they may not be tuned on. This is also why the
corpus of record here is 28 and not the 33 `docs/analysis-report.md` projects
over — that figure adds the 5 held-out filings by size only.

## d. Why the offsets survive — the provenance argument

INV-S2: *every extracted item's text is a verbatim slice of `normalized_text`*,
with offsets into `normalized_text`.

The design makes this survive **by construction, not by care**:

1. `find_chrome()` is a pure read of `normalized_text`. It returns offsets. It
   has no way to modify anything.
2. `extract_items()` calls it *after* the full pipeline has run, and does one
   thing with the result: assigns it to `envelope["boilerplate"]`. Segmentation,
   boundaries, status, validation and confidence never see it.
3. Therefore, for any input, `normalized_text`, `items`, `warnings` and
   `doc_status` are identical with the flag on and off. This is not an argument,
   it is an equality, and `evals/adversarial/boilerplate-offsets-invariant.json`
   asserts it as an **invariant-suite** case on both an HTML fixture that fires
   and a txt fixture that fires, by running the pipeline twice and comparing.

**What "the item's text" means in the stripped view.** It is
`strip_chrome(normalized_text, boilerplate, start=item.start, end=item.end)`:
the item's own span, with the chrome runs that fall inside it deleted, computed
by the caller at the moment of asking. It is a *view*. The item's text — the
thing the contract defines — remains `normalized_text[start:end]`, unchanged.

**How a reader gets back to the original bytes.** They never left. The
reconstruction is the identity: `normalized_text[start:end]` is the original
run, chrome included, for every span the envelope publishes — including the
chrome spans themselves, which is what makes a stripped run reconstructible
rather than merely reversible in principle. `meta.input_sha256` still pins the
raw file, and normalization is unchanged, so the chain
raw file → `normalized_text` → offsets is exactly the chain that existed before
this ADR.

The rejected alternative is worth naming: **rewrite `normalized_text` when the
flag is on**. It is refused because it makes the offsets mean two different
things depending on a keyword argument. Every consumer — the contract, the
inspector's anchor machinery, `tasks/reviews/` evidence, every committed case —
would have to know which mode produced a given envelope before it could read an
offset. That is a contract fork disguised as a flag.

## e. Default off, and what that buys

`exclude_boilerplate=False` is the default and no caller in the repo passes
anything else. With the flag off, `find_chrome()` is not called at all: no
`boilerplate` key appears, the envelope has the same keys it had before this
ADR, and the cost is zero rather than small. The 70 fast / 32 invariant cases
run against the default path untouched, which is the evidence that the freeze
was not crossed in practice.

The asymmetry drives the tuning: with exclusion off by default, a **missed**
piece of chrome costs a caller who opted in a little noise, while a **false
positive** silently deletes filing text from the view of someone who trusted
the flag. So the thresholds are tuned for precision and the recall misses in §f
are accepted deliberately.

## f. Costs, named

### f1. Recall the rules knowingly do not have

- **Per-page-varying heads are invisible.** aapl-2025 reports zero chrome
  despite having per-page footers, because its footer line carries the page
  number *inside* it, so no two pages produce the same line text and the
  exact-repeat rule never engages. 12 of 28 fixtures report nothing; some
  genuinely have no repeated chrome, and this is why the others do not.
- **Section-level heads are rejected on purpose.** nvda-2024's
  `NVIDIA Corporation and Subsidiaries` (32×, spread 0.26) and jpm-2024's
  `Notes to consolidated financial statements` (73×, spread 0.42) are real
  running heads for one section each. The spread gate that protects
  `Item 8` from being called furniture (§c3) is the same gate that rejects
  these. Precision was chosen over recall; the price is these two.
- **A trailing page number is missed**, one line per document — the last page's
  number has prose before it and nothing after, so no boundary is adjacent.
  Pinned in `boilerplate._demo` so it stays a known shape rather than a
  surprise.
- **Typographic rules and separators** are arguably chrome and are not
  detected: ge-1994's rule line — `- ` followed by 75 dashes, 77 characters —
  occurs 37× at CV 0.82, above the gate. Pinned by
  `boilerplate-txt-chrome`, whose check first shipped naming a 70-character
  string that occurs zero times and therefore pinned nothing (PR #25 R3).

### f2. What was NOT done, and why

Detecting chrome inside `normalize()` and never emitting it would be the
tidiest possible output — and it is refused outright. It would move every
offset in every existing envelope, invalidate every committed case's anchors,
and re-run the ADR-021 benchmark numbers. The freeze guard forbids exactly
that; §a3's claim to be invisible depends on it.

### f3. Corpus untouched

No fixture was added. Every case in §g runs against filings already committed —
`msft-2013`, `cvx-2015`, `ge-1994` — so the **37 timed fixtures / 28 real dev /
33 real committed** populations ADR-021 §b8 defines, and every figure
`docs/analysis-report.md` derives from them, do not move. The S3 row's precedent for synthesizing input outside `evals/fixtures/`
was available and was not needed: the near-miss material this feature has to be
falsified against (`$` × 1,058, `Total` × 39, 2,045 bare-number lines, a
repeated bare `Item 8`) is already in the committed corpus, and real material
is better adversarial input than anything hand-written.

## g. Enforcement

Five cases, both directions, plus the module self-check. Rewritten in PR #25's
round-1 repair; the first version of this table overstated two rows, which is
recorded here rather than quietly fixed.

| case | fixture | suite | asserts |
|---|---|---|---|
| `boilerplate-chrome-detected` | msft-2013 | fast | `Table of Contents` fires as `running_head` (90–100×) and page numbers with it; `Total`, `PART II`, `PART I`, `Item 8`, `Item 7`, `Item 1`, `(In millions)` never do — the fire and refrain directions on one document. Also the stripped view: 2,002 characters removed, exactly the span total, `Table of Contents` gone from it (R2) |
| `boilerplate-near-miss` | cvx-2015 | fast | detection reports **nothing at all** — `$` × 1,058, `)` × 860, `Total`, `2015`, and 2,045 bare-number lines all stay. Also the `MAX_GAP_CV` boundary: this case goes red at 0.84, the lowest CV that admits a false positive anywhere in the corpus |
| `boilerplate-txt-chrome` | ge-1994 | fast | `<PAGE>`/`<TABLE>`/`<CAPTION>`/`<S>`-`<C>` lines are `edgar_chrome`; `Item 1. Business`, `GECS`, `GE` and the 77-character rule line are not. Carries the **txt-era** half of the offset-invariance criterion via its own `offsets_invariant_under_exclusion` check |
| `boilerplate-section-heads` | jpm-2024 | fast | the `MIN_SPREAD` gate: `Notes to consolidated financial statements` (73×, CV 0.28 — more regular than the real page header) and `2024` are never chrome, and the case goes red at `MIN_SPREAD` 0.40. Also the **above** half of page-number adjacency: 286 page numbers, halving to 143 if the rule only looks below (R4, R5) |
| `boilerplate-offsets-invariant` | msft-2013 | **invariant** | `normalized_text`, `items`, `warnings`, `doc_status` byte-identical with the flag on and off, and the `boilerplate` key present on exactly one side (INV-S2 both ways) |

Two corrections to the row set above, both from PR #25 round 1: this table
previously credited `boilerplate-offsets-invariant` with running ge-1994 as
well as msft-2013 — it runs msft-2013 only, and the txt-era half is
`boilerplate-txt-chrome`'s — and `boilerplate-txt-chrome`'s rule-line check
named a 70-character string that occurs zero times in the filing, so it pinned
nothing until the value was corrected (R3).

`src/sec10k/boilerplate.py::_demo` pins the synthetic direction the fixtures
cannot: that a clustered repeat does not fire, that under `MIN_REPEATS`
nothing fires however regular, that a 4-digit year is not a page number, that
spans never overlap, and that `strip_chrome` windows correctly on one item.
**It is run by `.github/workflows/ci.yml`'s unit-tests job** — added in PR #25
(R1), which measured what the claim was worth while it was not: `MIN_REPEATS`
8→20, `MIN_SPREAD` 0.70→0.95, `PAGE_DIGITS` 3→4 and a no-op `strip_chrome` all
left the eval gate 33/33 and 74/74 green with only `_demo` red, and nothing
automated ran `_demo`.
