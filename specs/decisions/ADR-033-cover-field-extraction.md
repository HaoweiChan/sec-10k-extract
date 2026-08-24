# ADR-033 — S11: the 10-K cover page is reported as opt-in `{value, start, end, confidence, method}` field records into an UNCHANGED `normalized_text`; the EIN is the pivot, not the caption; six fields ship and seven are cut with their measurements

Date: 2026-08-24. Status: accepted. Implements S11. Sanctioned exception to the
T8 feature freeze (`tasks/TODO.md`, **Freeze guard**), on the pattern
[ADR-020](ADR-020-fallback-not-justified.md) established for T12 and
[ADR-026](ADR-026-boilerplate-chrome-exclusion.md) /
[ADR-029](ADR-029-structured-tables-annotation.md) /
[ADR-032](ADR-032-block-structure-markdown-view.md) applied for S6/S7/S9 — this
ADR extends ADR-029's annotation-not-edit pattern from tables to the cover
page and is read with it.

**Ruling**: cover fields ship as an **opt-in annotation, not an edit**. `extract_items(path, cover=True)` adds one envelope key, `cover` — a dict of field records `{value, start, end, confidence, method}` whose offsets point into an unchanged `normalized_text`, so no cover fact is a bare assertion. **Six fields ship**: `registrant_name`, `state_of_incorporation`, `ein`, `commission_file_number`, `fiscal_year_end`, `trading_symbol` (era-gated). **Seven are cut** (§d), each with the measurement that cut it. The resolver's pivot is the **EIN regex, not the caption** (§b2). A field the filing's era cannot carry reports `status: "not_in_era"` at HIGH confidence, never a low-confidence `missing` (§c). `normalized_text`, every item offset, `doc_status` and `warnings` are byte-identical with the flag on and off.
**Because**: the direction was "封面應該要 extract" with the structured-field reading chosen explicitly by the human over a cover span. A throwaway caption-anchored probe over all 38 non-refused fixtures (§a3) showed caption anchoring is *not* the reachable rule — captions appear in three orientations and several wordings, and normalization collapses the cover's two-column typesetting onto one line, so a backward line read returns `California 94-2404110` or the EIN itself as the state on 37 of 38 fixtures. The EIN's `\d{2}-\d{7}` shape is unambiguous, hits 38/38, and sits *between* the two values the caption pair describes — pivoting on it turns the collapsed line back into its two columns without un-collapsing anything. The seven cut fields are cut on measurement, not taste: two of them cannot be read correctly at all from the text the pipeline produces (§d1, §d2).
**Enforced by**: `evals/golden/aapl-2025-cover.json`, `evals/golden/msft-2013-cover.json`, `evals/golden/ge-1994-cover.json`, `evals/golden/premier-pacific-2016-cover.json`; `src/sec10k/eval_adapter.py` (the `cover` check type and `envelope_shape`'s `_cover_shape`); `src/sec10k/cover.py::_demo`

---

## a. Why this is a sanctioned exception and not scope creep

The freeze guard says a post-T8 capability is scope creep "no matter how good
it looks". S11 is in scope for the three reasons ADR-029 §a and ADR-032 §a
gave, re-checked rather than inherited:

1. **The human asked for it in writing, on the record** — the S11 row of
   `tasks/TODO.md`, 2026-08-24, which also demanded "its own ADR before any
   code" and, in the same exchange, that anything undeliverable "要誠實報告".
   §d is that report.
2. **A post-freeze capability gets a written ruling with its cost named**,
   whichever way it goes. This one is ruled IN for six fields and OUT for
   seven, each cut carrying the number that cut it.
3. **It changes no existing behaviour.** With the flag off, not one byte of
   any envelope moves — the same property ADR-029 and ADR-032 asserted, and
   pinned here by the `cover` cases carrying `offsets_invariant_under_cover`.

The assignment does **not** mandate this. T1 is "extract individual Items";
the cover is not an Item, and this ADR does not pretend otherwise. It ships
because the human directed it, and it is scoped so that failing to ship it
would have cost nothing.

### a3. The probe

A throwaway regex probe (session scratchpad, never committed, never imported)
ran caption-anchored extraction over the 38 non-refused fixtures. It is the
evidence base for §b and §d, and it is a *floor on difficulty*, not a promise
of the shipped resolver's accuracy. Its headline numbers, uncorrected:

| field | probe hit | what the hits actually were |
|---|---|---|
| `ein` | 38/38 | correct on inspection — the format is unambiguous |
| `state_of_incorporation` | 37/38 | **mostly wrong**: `California 94-2` (value+EIN), `91-0425694` (the EIN itself), `San Ramon, Cali` (the address), `Nevada 2821 38-` (SIC code bleed) |
| `commission_file_number` | 35/38 | correct with dirty tails: `1-6991.`, `000 26460` |
| `registrant_name` | 34/38 | correct; the 4 misses are §b3's caption variants |
| `fiscal_year_end` | 34/38 | `normalize.COVER_DATE_RE` already does this better — reuse, §b4 |
| `aggregate_market_value` | 17/38 | **mostly wrong** — §d1 |
| `shares_outstanding` | 22/38 | **ambiguous** — §d2 |

## b. The resolver

### b1. Three layout families, one region

The cover region is `normalized_text[0:first_item_start]` — 3.2k–10.4k chars,
0.6%–11.0% of the document across the corpus. It carries the cover page and,
usually, the table of contents. The region is not sub-divided: every rule
below is a search inside it, so a TOC that precedes the cover (ge-1994 opens
with a `SECTIONS` index and does not reach `FORM 10-K` until ~offset 1000)
costs nothing.

Three typesetting families produce it, and they differ in what survives
normalization:

1. **Table-typeset HTML/iXBRL** — aapl-2025 has 3 `<table>` / 23 `<td>` before
   the jurisdiction caption; premier-pacific-2016 has 2 / 7. The value/caption
   pairs are cells.
2. **`<p>`-typeset HTML** — msft-2013 has zero tables on the cover.
3. **Fixed-width `.txt`** — ge-1994, ibm-1997, ko-1997, textron-2001.

The families matter for *why* the text looks the way it does, but the resolver
does **not** branch on them, because §b2's pivot is family-independent. This
is the main simplification this ADR buys: an earlier sketch had a
`tables.py`-grid path for family 1 and a positional path for families 2–3.
Measured against the four goldens, the grid path recovers nothing the EIN
pivot does not already give, so it is not built. If a future filing needs it,
`src/sec10k/tables.py`'s grid is still there — this is a deferral with a named
upgrade path, not a claim that cells are useless. Confirmed on the shipped
resolver: `src/sec10k/cover.py` imports no table machinery and branches on no
era, and all four goldens pass.

### b2. The EIN is the pivot, not the caption

Normalization flattens the cover's two columns. What the resolver actually
sees, verbatim from `normalized_text`:

```
aapl-2025      California 94-2404110\n\n(State or other jurisdiction\n\nof incorporation or organization)\n(I.R.S. Employer Identification No.)
msft-2013      WASHINGTON 91-1144442\n\n(STATE OF INCORPORATION) (I.R.S. ID)
ge-1994        New York                              14-0689340\n(State or other jurisdiction of     (I.R.S. Employer Identi
premier-2016   NEVADA\n\n90-0920687\n\n(State or other jurisdiction\n\nof incorporation or organization)\n\n(I.R.S. Employer\n\nIdentification Number)
```

Four filings, four caption layouts — split across lines (aapl), abbreviated
(msft), interleaved mid-phrase (ge, where `(State or other jurisdiction of`
and `(I.R.S. Employer Identi…` share a line because the fixed-width columns
survived as columns), and split across four lines (premier). No caption rule
covers all four.

`\b\d{2}-\d{7}\b` covers all four, and 38/38 of the corpus. So:

- **`ein`** — the match itself. Method `ein_regex`.
- **`state_of_incorporation`** — the text immediately before the EIN, on the
  same line if there is any, else the previous non-empty line. This is what
  turns `California 94-2404110` back into two columns without reconstructing
  the table. Method `ein_pivot`.

The EIN is also what makes the *state* readable on the filings where the
caption is wrong or absent, which is exactly where §a3's probe failed.

### b3. `registrant_name`: caption with three orientations, then position

The name caption exists in three orientations across the corpus, and the probe
handled only the first:

| orientation | example | fixtures |
|---|---|---|
| value **before** caption | `Apple Inc.\n\n(Exact name of Registrant as specified in its charter)` | the majority |
| caption **before** value, colon-separated | `Exact name of registrant as specified in its charter: Bank of America Corporation` | bac-2006 |
| alias wording | `SANDSTON CORPORATION\n(Name of small business issuer in its charter)` | sandston-2021, fy2021-item9c |
| **no caption at all** | `Commission File Number 0-14278\n\nMICROSOFT CORPORATION\n\nWASHINGTON 91-1144442` | msft-2013 |

The resolver takes them in that order: caption match (either orientation,
either wording) → method `caption_anchored`, confidence `BASE_STRICT`.
Failing that, **position**: the non-empty line between the commission file
number and the line the EIN pivot sits on → method `positional`, confidence
`BASE_WEAK`.

The earlier reading of this — recorded in the S11 row as a "family 2" of
caption-less covers — was **wrong, and is corrected here**: of the four probe
misses, three are caption *variants* (bac-2006's orientation, sandston's and
fy2021's alias) and exactly **one** filing in 38 has no name caption at all.
The positional path is a 1-in-38 fallback, not a family.

### b4. `fiscal_year_end` and `commission_file_number`

`fiscal_year_end` is **not re-implemented**. `normalize.COVER_DATE_RE` already
resolves it and already handles the ALL-CAPS cover (`DECEMBER 31, 2016`). The
cover record reports that regex's match with its offsets. A second regex for a
fact the pipeline already resolves is exactly the drift `specs/001`'s
"no separate `text` field" rule exists to prevent.

**Corrected after cold review (2026-08-24).** The method was named
`reused_meta` and this paragraph claimed the field "already feeds `meta`" and
handles "the JPM two-column interleave". Both were false. `normalize.period_end`
resolves the date from three sources in order — the SGML header, the dei fact,
then this regex over `text[:6000]` — and the cover resolver only ever runs the
third. Measured: on **ibm-1997, ibr-security-holders and jpm-2024**,
`meta.period_end` is known and the cover field reports `missing`. That
behaviour is kept, because for a COVER field it is the correct one: the header
and the dei fact do not survive into `normalized_text`, so there is no span to
point at, and a record with a value and no offsets is the bare assertion §e
exists to forbid. Only the NAME was wrong, and it is now `cover_date_re` —
named for what the function does rather than for what the ADR wished it did.
A `_parse_date` guard was added at the same time, for the reason
`normalize.period_end` has one: the capture group is `[A-Z][a-z]{2,8}...`,
which a non-month satisfies.

`commission_file_number` is caption-anchored forward (`Commission File
Number`/`No.`, case-insensitive, with or without the colon) and the match is
**right-trimmed of trailing punctuation** — the probe's `1-6991.` was a
sentence period, not part of the number. spatz-2014's `000 26460` (space where
the corpus uses a hyphen) is left as the filing wrote it: normalizing it would
be inventing a value the document does not carry.

## c. Era gating is a status, not a failure

`trading_symbol` exists on 9 of 38 fixtures. It is not missing from the other
29 — the *concept* postdates them: the Trading Symbol column entered the cover
with the 2019 iXBRL cover-page taxonomy. Reporting `missing` there would be
false, and would put a low confidence on the one thing the pipeline is
completely certain about.

So a cover field carries `status`:

- `"resolved"` — a value with offsets.
- `"not_in_era"` — the era cannot carry this field. `value`/`start`/`end` are
  null, confidence is `BASE_STRICT`. **This is a positive claim**, and the
  goldens pin it (`ge-1994` asserts `trading_symbol` `not_in_era`, so a future
  regex that hallucinates a symbol out of a 1994 filing turns that case red).
- `"missing"` — the era carries it and the resolver did not find it.
  Confidence `BASE_MISSING`.

**Corrected during implementation (2026-08-24).** The draft of this section
read the era boundary off `meta.format_era`. That is wrong, and shipping it
would have produced a confident false negative: `sgrp-2019` is a legacy-HTML
filing that *does* carry the Trading Symbol column, so a `format_era ==
"ixbrl"` gate reports `not_in_era` on a cover that visibly has one. The gate
shipped is the **column caption's own presence** in the cover region — a cover
that never names the column cannot carry a value from it. That is
self-evidencing, needs no era table, and cannot disagree with the document.

## d. What is cut, and the measurement that cut it

Seven fields were considered and are **not** shipping. Each is cut on a number,
and each cut is reversible by an ADR that supplies the missing measurement.

### d1. `aggregate_market_value` — CUT (cannot be read correctly)

Probe reach 17/38, and most of the hits are wrong, because filers write the
figure two incompatible ways:

```
213,260,291,645        bac-2006   — a literal figure
$43.6 billion          axp-2008   — prose, scale in a word
$27.5 billion          ba-2003
$63.08 billion         xom-2021
0.10                   spatz-2014 — NOT a market value at all; a par value
```

Extracting `43.6` and calling it an aggregate market value is off by nine
orders of magnitude, and one hit is a different quantity entirely. Shipping it
would produce confidently wrong numbers, which is the failure mode
`docs/evals/` exists to prevent. Reversible by: a scale-word resolver
(`billion`/`million`) with its own goldens, plus a rule separating the market
value from the par value on the same page.

### d2. `shares_outstanding` — CUT (ambiguous referent)

Probe reach 22/38, and the referent is undetermined: a cover routinely carries
*authorized*, *issued* and *outstanding* share counts, plus an as-of date that
is not the fiscal year end. premier-pacific-2016's `5,169,000` is correct by
luck of ordering, not by method. Reversible by: date-anchored resolution
(`as of <date>` within the same sentence) with goldens on a filing that
carries all three counts.

### d3. `address`, `zip`, `phone` — CUT (deferred, not impossible)

These have the same two-column collapse as the state, and the EIN pivot does
not reach them (no unambiguous shape to pivot on — `95014` and `98052-6399`
are both plausible ZIPs, and `(408) 996-1010` shares its shape with nothing
else on the page, but `ONE MICROSOFT WAY, REDMOND, WASHINGTON 98052-6399`
puts address, city, state and ZIP on one line while aapl splits them across
three). Reachable with the `tables.py` grid for family 1, unreached for
families 2–3. Cut for now because no consumer named them; the S11 row's
"CUT rather than ship a field it cannot measure" applies.

### d4. `filer_status`, `shell_company` checkboxes — CUT (a different problem)

28/38 and 27/38 respectively, and the extraction is not a field read but a
**checkbox read**: `Yes ☒ No ☐`, `Yes x No ¨`, `(x)`, `[X]` — four glyph
conventions in the corpus, and the answer is which of two adjacent glyphs is
ticked. That is a distinct sub-problem with its own failure mode (a filing
that ticks neither, or whose glyphs did not survive normalization), and
folding it into a field resolver would hide it. Reversible by: its own ADR,
with a glyph census over the corpus first.

## e. Contract shape

`specs/001-sec10k-contract.md` gains one optional key. The item registry rule
("`item` codes come from … `TITLES`/`ORDER` … Nothing else") is **untouched**:
no cover pseudo-item is emitted, so every existing `only_items`,
`known_items_only` and `expected_set_complete` check is unaffected by
construction.

```json
"cover": {
  "registrant_name": {"value": "Apple Inc.", "start": 400, "end": 410,
                      "status": "resolved", "confidence": 0.95,
                      "method": "caption_anchored"},
  "state_of_incorporation": {"value": "California", "start": 468, "end": 478,
                      "status": "resolved", "confidence": 0.95,
                      "method": "ein_pivot"},
  "trading_symbol": {"value": null, "start": null, "end": null,
                      "status": "not_in_era", "confidence": 0.95,
                      "method": "era_gate"}
}
```

`normalized_text[start:end] == value` for every `resolved` field — the same
verbatim rule INV-S2 puts on item spans, and the `cover` check type asserts it
rather than trusting the label.

## f. Confidence reuses the existing scale

No second scale. `src/sec10k/validate.py`'s constants, unchanged:

| situation | value | constant |
|---|---|---|
| caption-anchored, EIN regex, EIN pivot, era gate | 0.95 | `BASE_STRICT` |
| positional fallback (msft-2013's name) | 0.75 | `BASE_WEAK` |
| era carries the field, resolver found nothing | 0.40 | `BASE_MISSING` |

ADR-018's ruling — publish the scale as measured-with-stated-bias, do not
remap — carries over unchanged. These are evidence grades, not probabilities,
and §a3's probe is not a calibration.

## g. The goldens, watched red first

Four cases, one per layout family, hand-labeled per the `case-authoring` SOP
and **verified against `normalized_text` rather than typed**: every value's
offsets were computed by locating the literal in the actual envelope, and
every occurrence count was checked so that a short value (ge-1994's `1-35`,
which occurs 15 times in the document) is pinned at the cover occurrence and
not the first one anywhere.

| case | family | pins |
|---|---|---|
| `aapl-2025-cover` | table-typeset iXBRL | all six fields; `trading_symbol` resolved (`AAPL` @950) — the only golden that has one |
| `msft-2013-cover` | `<p>`-typeset, no name caption | `registrant_name` via `positional` at `BASE_WEAK`; the abbreviated `(STATE OF INCORPORATION)`/`(I.R.S. ID)` captions ignored in favour of the EIN pivot |
| `ge-1994-cover` | fixed-width `.txt` | the interleaved caption pair; `trading_symbol` **`not_in_era`**; `commission_file_number` `1-35` at the cover occurrence |
| `premier-pacific-2016-cover` | small-filer table | values on separate lines, caption split across four |

All four are `fast`-suite. `offsets_invariant_under_cover` rides on
`aapl-2025-cover` in the `invariant` suite: item output byte-identical with
the flag on and off, the ADR-029/032 property.

### g1. Three reds, and only the third one proves anything

**Red 1, at origin/main `5df5896`** — `run_case` does not pass `cover=` and
`eval_check` has no `cover` type, so all four fail with `unknown check type
'cover'`. Required, but *shallow*: it proves the case file parses, nothing
more.

**Red 2, after the check type landed** — `no cover key — case asked for
cover=true`, on all four, with the other 111 `fast` cases green. This proves
the check reaches the envelope and that nothing else regressed. Still not a
statement about any field value.

**Red 3 — mutation.** The check types cannot be shown to discriminate *values*
by watching a resolver that does not exist yet, so the real red is the
ADR-030 instrument: break the shipped resolver three ways and watch exactly
the right cases go red.

| mutation | red | green | what it proves |
|---|---|---|---|
| state read from the caption instead of the EIN pivot (§b2) | **all four** | — | the pivot is load-bearing on every layout family, not a preference |
| positional name allowed `BASE_STRICT` instead of `BASE_WEAK` (§b3) | **msft-2013 only** | the other three | the 1-in-38 fallback's honesty is pinned, and pinned on the one case that exercises it |
| era gate deleted, `trading_symbol` resolved everywhere (§c) | **ge-1994, msft-2013, premier-pacific** | **aapl-2025** | `not_in_era` is a positive claim: the three covers that lack the column go red while the one that has it stays green |

The second row is the one worth reading twice. A confidence constant that
nothing can turn red is decoration, and ADR-018 §1 was written after exactly
that defect.


## h. Cold review round, 2026-08-24 — the goldens were not a corpus

A read-only cold review of the first resolver, plus a whole-corpus sweep it
prompted, found **8 of 39 non-refused fixtures carrying a confidently-wrong
field at 0.95** — while all four goldens, both suites and all three §g
mutations were green. That is the finding worth recording, above any
individual defect: **§g's mutations proved the check types discriminate
values; they proved nothing about coverage**, because every case had been
written against a filing the resolver already handled. A resolver has no right
to be trusted on the cases it was written from.

Every defect below became an `evals/adversarial/` case, watched red on the
shipped resolver, before it was fixed (CLAUDE.md hard rule 2).

| # | class | case | red on the first resolver | corrected to |
|---|---|---|---|---|
| 1 | caption/value **stack**, caption ends in `:` on its own line | `cover-caption-stack` (bac-2006) | name `'Delaware'`, state `'IRS Employer Identification No.:'` | `'Bank of America Corporation'`, `'Delaware'` |
| 2 | filer's label **inside the EIN cell** | `cover-ein-cell-label` (wfc-2008) | state `'Delaware No.'` | `'Delaware'` |
| 3 | caption broken across lines, EIN on the **tail** line | `cover-caption-tail` (gs-2002), `-intc` (intc-2002) | state `'incorporation or organization)'` | `'Delaware'` |
| 4 | **SIC code** in a third column | `cover-sic-bleed` (sgrp-2019) | state `'Nevada 2821'` | `'Nevada'` |
| 5 | `no trading symbol` **in prose** | `cover-symbol-prose` (reac-2015) | symbol `'K'` (the K of `Form 10-K`) | `not_in_era` |
| 6 | column present, value row is `N/A` | `cover-symbol-not-applicable` (sgrp-2019) | symbol `'A'`, then `'YES'` from a check-mark line 700 chars later | `missing` |
| 7 | refusal envelope carried **no `cover` key** | `cover-refusal-envelope` (amended-cover-2021) | key absent while `boilerplate`/`tables`/`blocks` were all threaded into the same two returns | key present, name resolved |
| 8 | value **underlined with a rule** (.txt era) | `cover-underline-rule` (ksb-2007) | name `'---------------'` | `'24HOLDINGS INC.'` |

### h1. Three ADR claims that were false

1. **§b3 listed bac-2006 as a covered orientation.** It was covered only in
   `cover.py::_demo`, against a synthetic one-liner that does not reproduce the
   committed bytes. The fixture uses a *third* orientation — caption on its own
   line ending in a colon, value on the next line — and the self-check was
   green on a layout that exists nowhere in the corpus. §b3's table now has it.
2. **§b2 implied the EIN pivot had fixed the SIC bleed** that §a3's probe
   table recorded (`Nevada 2821 38-`). It had not; it moved which fixtures show
   it. Fixed by `_clean_state`, pinned by case 4.
3. **§b4's `reused_meta`** — see the correction inline in that section.

### h2. The era gate was wrong three times

`format_era == "ixbrl"` (would report `not_in_era` on sgrp-2019, which has the
column) → bare `trading symbol` substring (reports `resolved` on reac-2015,
which says "and no trading symbol") → header-row co-occurrence, plus a value
that is neither `N/A` nor a token from a check-mark line 700 characters later.
Each wrong version produced a **confidently-wrong 0.95**, and none of them was
visible to any check that existed at the time. §c calls `not_in_era` a positive
claim; a positive claim needs a case that can falsify it, and now there are two.

### h3. State after the round

All 42 fixture directories, refusals included: **0 suspect fields**, every
`resolved` field verbatim at its own offsets, `fast` 124/124, `invariant`
63/63. Also landed in this round: `COVER_MAX` (12,000 chars, 1.16x the largest
committed cover region) so a document where no item carries a span cannot hand
the whole filing to the resolver, and the `_is_name` letters rule applied to
all three caption orientations and the positional fallback at once.
