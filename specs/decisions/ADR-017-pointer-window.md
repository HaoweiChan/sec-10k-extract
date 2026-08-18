# ADR-017 — The pointer may run across two sentences, and may say "into this report"

Date: 2026-08-17. Status: accepted. Amends ADR-004 (`IBR_RE`) and ADR-010
ruling 3 (the pointer-sentence requirement). Driven by `wfc-2008-shallow`,
authored from the document and watched red with twelve failing checks before any
code moved.

## The failure

Wells Fargo's FY2008 10-K reports **ten items** — 1A, 3, 6, 7, 7A, 8, 9A, 11,
12, 13, 14 — as `extracted` at confidence **0.95**, over pointer paragraphs of
250 to 360 characters. Every one of them reads, with only the item number and
the destination changing:

> Information in response to this Item 7 can be found in the 2008 Annual Report
> to Stockholders under "Financial Review" on pages 34-83. That information is
> incorporated into this report by reference.

A consumer asking this pipeline for Wells Fargo's MD&A got that sentence,
labelled a successful extraction with the highest confidence the scale awards.
`no_empty_success` passed — 57,545 chars are spanned across the filing.
`unattributed_content` fired and, correctly under ADR-008, did not escalate.
Nothing else noticed.

Two independent causes, both in `classify`:

1. **`IBR_RE` did not match.** Its alternatives were `incorporated (herein )?by
   reference` and `is incorporated by reference`. This filer writes *"incorporated
   **into this report** by reference"*, and the interposed phrase defeats both.
2. **Even matched, the position rule rejected it.** ADR-010 ruling 3 requires the
   pointer phrase *and* the external-document name to both appear in `sents[0]`.
   Here the document is named in the first sentence and the incorporation is
   stated in the second — the standard institutional phrasing, used uniformly
   across ten items of one filing.

## Ruling 1 — `IBR_RE` tolerates an interposed phrase

`incorporated\b[^.]{0,40}?\bby reference`, replacing the two fixed alternatives.
The `[^.]` class keeps the window inside one sentence, so the match cannot span a
sentence boundary and manufacture a pointer out of two unrelated clauses.

## Ruling 2 — the pointer window is the LEADING RUN of pointer sentences

Both signals must appear within the run of pointer sentences that **starts at the
first sentence** and continues while each sentence is a pointer (carrying
`IBR_RE`, `EXTERNAL_DOC_RE`, or ADR-015's `INTERNAL_REF_RE`). What follows the
run is the remainder, still capped at `IBR_REMAINDER_MAX`.

**The requirement that the pointer OPENS the body is load-bearing and stays.**
This was checked the hard way. An earlier draft of this ruling dropped position
entirely — reasoning that the remainder cap enforces locality more tightly than
sentence order does, which is true — and required only that the two signals
appear among the body's pointer sentences wherever they fall. That draft flipped
**nine committed items** across the fixture set, and the module's own self-check
caught it on the first run:

> `textron-2001` item 5: *"Our Common Stock is traded on the New York Stock
> Exchange. At December 29, 2001, there were approximately 21,000 holders. The
> price range is incorporated by reference to the Annual Report to
> Shareholders."*

That item is `extracted`, and must be. An item that **mentions** a pointer last
is not an item whose content is elsewhere. `bac-2006` item 15, `cat-2023` item
14, `ibm-1997` item 12, `gs-2002` item 10, `nvda-2024` item 9C and `tgt-2002`
item 9 were the others. The generalisation is therefore "one sentence → the
leading run", not "one sentence → anywhere".

## Blast radius

Measured across every dev fixture by diffing item statuses against the state at
the start of T9 tranche 2: the cumulative effect of ADR-015 and ADR-017 together
is **exactly two pre-existing items** — `intc-2002` item 12 and `tgt-2002` item
2, each the target of its own ruling. No fixture that predates this tranche
moved. `wfc-2008`'s eleven changes are the new fixture's own.

## How this filing got here, and the rule it produced

`wfc-2008` was fetched for the T9 held-out refresh and moved to the dev set
**before its first run**. Reading its tag-strip scan, I formed a belief about how
the pipeline would resolve its headings, and that belief implied a code change.

**A prediction you would act on is influence; a prediction you merely record is
not.** Freezing predictions into held-out provenance — which every case in
`evals/heldout/` does, and which H2 scored two of — stays fine. Acting on one
does not, so the filing lost its held-out standing rather than the rule being
argued down. It is replaced in the held-out set by `axp-2008`, a different
crisis-era financial.

For the record **the prediction was wrong**: the scan showed items 5 through 14
with bare `ITEM N.` headings and their titles in a following block, which would
have re-armed the trap ADR-015 had just closed. The normalizer joins within a
block where the scan inserts a newline, so the titles are in fact on the same
line and nothing of the sort happens. That is the **fourth** time the instrument
rather than the pipeline has been at fault (H1's `xom-2021` Item 9C, H2's
`pgr-2023` floating comma, a declined `csco-2016` assertion, now this) — and the
first at *paragraph* granularity, which is the level the scan is supposed to be
trusted at. The held-out authoring rule is tightened accordingly: a structural
reading of the scan is a hypothesis until a run tests it.

The filing was worth the trade. It carried a real defect that no fixture in
either set exposed, and it now sits in the scored suite where it is checked on
every run instead of once a milestone.

## Verification

Twelve checks red before the fix (eleven statuses and one confidence ceiling —
the ceiling is there so a fix that relabels the status without moving the score
off the 0.95 strict band still fails). Fast 44/44 after, invariant 12/12, all
module self-checks green including two new `classify` assertions: the
two-sentence pointer must be IBR, and `textron-2001`'s trailing pointer must not
be.
