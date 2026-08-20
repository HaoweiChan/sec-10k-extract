# ADR-024 — 10-K/A stays out of scope: the form is accepted by EDGAR, the item set is not the era's

Date: 2026-08-20. Status: accepted.

**Ruling**: Form 10-K/A is **out of scope** and keeps returning `doc_status: unsupported` with `unsupported_form` naming the detected form; the refusal is now pinned by a self-check on both detection routes rather than left as a side effect of `ACCEPTED_FORMS`.
**Because**: an amendment's item set is whatever it chose to restate, not what its era requires, so every unamended item would report `missing` — supporting it means a second expected-set model, which is a capability the T8 freeze forbids and no committed fixture could test.
**Enforced by**: `src/sec10k/normalize.py::_demo` (both routes), `src/sec10k/normalize.py::ACCEPTED_FORMS`

---

## Context

T14 carried 10-K/A as an explicit **stretch**: ruled in or out, in writing,
either way. `docs/product/task2-problem-definition.md` had already flagged the
reason it is interesting — *"often contain only amended items, which breaks
the expected-set assumption"* — but nothing had ever been decided or measured.

### What a 10-K/A is

An amendment to an annual report already filed on Form 10-K: its own accession
number, the same CIK and the same period as the original. It is not a
re-filing: Exchange Act Rule 12b-15
requires the amendment to set forth **the complete text of each item it
amends**, and it says nothing about the items it does not. In practice
amendments come in three shapes, in descending frequency:

1. **Part III only** — the registrant expected to incorporate Items 10–14 from
   a proxy statement, missed the 120-day window of General Instruction G(3),
   and files the Part III items directly. The document contains a cover page,
   an explanatory note, Items 10–14 and Item 15's exhibit index, and nothing
   else.
2. **A single item or exhibit** — a restated Item 8/9A after a
   non-reliance determination, or a re-filed exhibit or auditor consent.
3. **Full restatement** — the whole 10-K re-filed. The rarest of the three.

Only shape 3 has the item set this pipeline's `expected_items` assumes.

### How common

Measured, not estimated: EDGAR's own quarterly index
`sec.gov/Archives/edgar/full-index/2024/QTR1/form.idx` — the busiest quarter of
the annual-report season — lists **4,980 filings of form type `10-K` and 169 of
`10-K/A`** — 3.4% of the originals, 3.3% of the 5,149 combined
(counted by the first whitespace-delimited field of each index line, which is
the form type; `10-KT` accounts for 5 more and is a transition report, not an
amendment). Retrieved 2026-08-20 with the declared User-Agent this repo uses
for every EDGAR fetch. Small, but not negligible — and note it is a *lower*
bound on the amendments relevant to a reader, since one company can amend the
same 10-K more than once.

### What the pipeline does with one today

It refuses, by name, on both routes an amendment can arrive by — verified
2026-08-20 against the current code:

| Route | `form_type_declared` | `form_type_sniffed` | `form_type` | Result |
|---|---|---|---|---|
| Full submission with the EDGAR SGML header (`<TYPE>10-K/A`) | `10-K/A` | `10-K/A` | `10-K/A` | `doc_status: unsupported`, warnings `whole_submission_fallback` + `unsupported_form` |
| Primary `.htm`, no SGML header, cover page reads "FORM 10-K/A" | `None` | `10-K/A` | `10-K/A` | `doc_status: unsupported`, warning `unsupported_form` |

The second route is the one that matters, and the corpus says how much: 27 of
the 37 committed fixtures carry an SGML `<TYPE>` (including many `.htm`
primary documents, as `docs/architecture/overview.md` notes), but the 10 that
do not include **every iXBRL-era filing in the set** — aapl-2025, cat-2023,
jpm-2024, nvda-2024, xom-2021, sandston-2021. For the newest documents, the
ones a reader is most likely to paste in, the cover-page sniff is the only
signal there is, and `FORM_SNIFF_RE`'s `(?:/A)?` group is all that stands
between an amendment and a parse. That group is why the refusal is specific
rather than incidental, and it was there before this ADR — untested, which is
what changes here.

**No committed fixture is an amendment.** Census of all 37, by the form the
pipeline itself detects: 32 × `10-K`, 2 × `10-K405`, 1 × `10-Q` (the
unsupported-form case), 1 × `10KSB` (likewise), 1 with no identifiable form
(`truncated-download`). Zero `/A`.

## Decision

**Out of scope, and the refusal becomes an asserted behaviour rather than a
consequence.**

1. `ACCEPTED_FORMS` is unchanged: `{"10-K", "10-K405"}`. A 10-K/A returns
   `unsupported`, which is the contract-v2 refusal — honest about what it will
   not do, per ADR-010's collapse-before-form-identity ordering that already
   distinguishes "we could not read this" from "this is not a 10-K".
2. Two assertions in `normalize.py::_demo` pin the refusal on **both** routes
   above. This is the ADR-016 treatment: a behaviour no fixture can carry is
   proved at the layer that owns it, and CI already runs
   `python3 -m src.sec10k.normalize`.
3. **No new fixture, no new code path.** Shipping an untestable path is the
   ADR-010 sin; so is committing a fixture for a form we refuse, which would
   also move the T13 benchmark corpus (`n=33`, 2.104 MiB, ADR-021 §b) and every
   published figure derived from it.

### Why not "in", when the parser would mostly work

It would parse. That is exactly the trap. A Part III-only amendment (shape 1,
the common one) is a well-formed HTML 10-K-shaped document whose headings the
existing `find_candidates` would match happily — and then:

- `expected_items(period_end)` returns the era's full 21–23 codes. Items 1–9C
  are not in the document, so each classifies `missing` at confidence 0.40,
  with `expected_item_missing` on every one.
- ADR-013's escalation rule (>25% of expected items missing) fires, so
  `doc_status` becomes `ambiguous` — on a document that is *complete and
  correct for what it is*.
- The reader is told a filing is broken when it is not, which is worse than
  the refusal it replaced: `unsupported` sends them to find the original 10-K,
  `ambiguous` sends them to distrust a correct extraction.

Making that right needs a **second expected-set model** — "what did this
amendment undertake to restate?" — derived from the cover page and the
explanatory note ("This Amendment No. 1 amends Part III of…"), free prose with
no standard form. That is a new capability in the sense the T8 freeze means:
not a fix to a layer, but a new question the pipeline would have to answer,
with its own failure modes, its own confidence semantics, and its own fixture
stratum (all three shapes above, minimum, plus the multi-amendment case) before
any of it could be trusted. Cost estimate, in the units this repo uses: one new
layer or a fork of layer 3, 3–5 fixtures with hand-authored goldens, at least
one new `doc_status`/warning code, a contract change to express "this envelope
covers a subset by design", and a benchmark re-run. Against 3.3% of filings,
already refused loudly, in a milestone whose brief is evidence-deepening.

## Consequences

- The `unsupported` path now has three proofs, not one: `10q-unsupported` and
  `ksb-unsupported` as fixtures, 10-K/A as a unit assertion on both routes.
- `README.md`, `docs/architecture/overview.md` and `normalize.py`'s own comment
  already said 10-K/A is out of scope; as of this ADR that statement has a
  ruling behind it and a test under it, rather than being an unexamined
  inheritance from B.
- **Revisit when** the product needs amendment coverage *and* the freeze is
  lifted — i.e. when someone is prepared to add the subset-expected-set model
  rather than just flip `ACCEPTED_FORMS`. Concretely: flipping the set alone,
  with no other change, is the failure this ADR predicts, and the first thing
  a revisit must do is commit a Part III-only amendment fixture and watch
  `doc_status` come back `ambiguous` on a correct document.
