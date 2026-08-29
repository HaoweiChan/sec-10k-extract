# ADR-042 — the cross-reference index, the ABS refusal, the collective Part pointer, and the trailing annex

Date: 2026-08-28. Status: accepted. Authored from a curated list of eight
deliberately hard recent filings (owner instruction, 2026-08-28: "make the
extractor crawl these, escalation is fine, token cost is not a constraint, and
confirm the Zeabur build works"). Amends
[ADR-036](ADR-036-tiered-escalation.md) §c (the trigger gains a suppressor) and
`specs/001-sec10k-contract.md` (one sanctioned null-offset shape, one new
`evidence` key). Re-affirms [ADR-004](ADR-004-pointer-item-status.md),
[ADR-011](ADR-011-ibr-offsets.md), [ADR-031](ADR-031-footnote-marker-ibr.md)
and INV-S1 against the readings that would have overturned them.

**Ruling**: four defects on four named real filings — a cross-reference index resolves to `evidence.cross_reference` and NOT to `start`/`end` (§a); General Instruction J refuses `unsupported` (§b); a collective Part pointer gives null offsets plus `evidence.collective_reference` (§c); the last item stops at a trailing annex (§d).
**Because**: each pre-fix envelope stated something false or useless about a real filing, three of the four at 0.95 with no warning; and the resolved page ranges overlap and nest, so INV-S1 forbids them being spans.
**Enforced by**: `evals/adversarial/intc-2025-cross-reference-index.json`, `c-2025-cross-reference-index.json` (debt), `bridgecrest-2025-abs-trust.json`, `brka-2025-part-iii-collective.json`, `spg-2025-dual-registrant.json`, `spg-2019-item16-annex.json`, and `src/sec10k/xref.py`'s self-check.

---

## a) The cross-reference index, and why the spans do not move

Two of the largest real filings in this corpus organize themselves the same
way, and the ordinary segmenter is right to fail on both.

| filing | index at | rows read | pre-fix |
|---|---|---|---|
| Intel FY2024 (`intc-2025`, 517,976 chars) | offset 514,332 — the last 0.7% | `Item 1. Business:` … `Pages 3-24, 33, 52, 72-75` | 23 items, all spans inside the index, coverage **0.0033**, `ambiguous` |
| Citigroup FY2025 (`c-2025`, 1,163,303 chars) | offset 4,145 — the **front** | `1. Business 4–36, 121–127, 129, 160–164, 299–300` | **zero** candidates anywhere, coverage **0.0000**, all 23 items `missing` |

Citi is the harder of the two and it is harder for one reason of typography:
it never writes the word `Item` and never writes the word `Page`. `Item 1A`
appears nowhere in 1.16 MB. There is no bad span to correct — there is no
span.

What both filings do is answer the question somewhere else and say exactly
where, in a machine-readable table, in printed page numbers a reader is
expected to follow. `src/sec10k/xref.py` reads that table and follows those
numbers. The page ladder is the longest strictly increasing subsequence of
standalone integer lines — a filing's page furniture is the only run of
integers that climbs monotonically through the whole document, and the
subsequence discards financial-table integers without needing a rule per
table. Intel's ladder is 117 rungs, 1 through 117, complete; Citi's is 306.

**The spans do not move, and this is the load-bearing ruling.** Intel's item
3 (Legal Proceedings) is pages 102–105, *inside* item 8's 56–108, because
Intel answers it in Note 19 to the financial statements. Item 2 (Properties)
is pages 11 and 32, inside item 1's 3–24. Citi's item 7A is pages 64–120,
165–169, 190–228 and 235–278, threaded through item 8's 134–298. These
overlap and nest. INV-S1 requires span-carrying items to be non-overlapping
and in document order. **No assignment of these ranges to `start`/`end`
satisfies the contract**, so the resolved regions travel as
`evidence.cross_reference` — the shape and the reasoning ADR-031 already
established for the footnote case.

The ONE exception is a filing where segmentation found no heading at all
(Citi). There the index's own rows become the spans: rows partition the index
region, so they are ordered and disjoint by construction, which is precisely
what INV-S1 asks of them, and the result is the same shape Intel already
produces rather than a second kind of answer. `method` is
`cross_reference_index`, and `validate`'s boundary-hygiene assertion reads
those spans back with `xref.ENTRY_RE` — the regex that produced them — rather
than with `HEADING_RE`, which is ADR-016 §2's layer-consistency rule applied
where it had not been.

**Qualified by ADR-045:** `low_item_coverage` stays fired and the primary
spans remain index rows — 0.33% of Intel, 0.06% of Citi — but a reliable
`cross_reference_index` resolution makes that code alone a
`success_with_warning`, not `ambiguous`. Resolution adds successful alternative
content; it does not withdraw the coverage admission or move overlapping spans.

**What it resolves, measured.** Intel: 13 items, 736,554 chars, every anchor
verified against the run's own text — item 7's first region opens
"Management's Discussion and Analysis / Overview", item 8's "Financial
Statements and Supplemental Details", item 9A's "Controls and Procedures".
Citi: 11 items, 1.9 MB — item 1 to 164,021 chars opening "OVERVIEW /
Citigroup's history dates back to the founding of the City…", item 7 to
296,268, item 8 to 582,266 opening "CONSOLIDATED FINANCIAL STATEMENTS". The
strongest single piece of evidence is not a size: Citi's held-out item 1A
anchor, "As a large, global financial institution, Citi faces particularly
complex", was written down and frozen on 2026-08-26 — before this resolver
existed — and it is inside the resolved 1A region.

## b) General Instruction J — the refusal

Bridgecrest Lending Auto Securitization Trust 2024-1 files a document that is
legally a 10-K and that `sniff_form` correctly identifies as one. Its
substance is Items 1112(b)/1114(b)(2)/1117/1119/1122/1123 of **Regulation
AB**, a taxonomy this pipeline does not model. Pre-fix it returned
`success_with_warning` over 18 `extracted` items — including a 96-char "Item 7
Management's Discussion and Analysis" at 0.80 and a 54-char "Item 8 Financial
Statements" at 0.80 — and reported items 1, 1A, 1C, 2 and 3 `missing`, which
was wrong even in kind: the filing is not silent about them, it lists them as
omitted.

The document names the rule itself, twice: "The following items have been
omitted in accordance with General Instruction J to Form 10-K" and "Substitute
information provided in accordance with General Instruction J to Form 10-K".
So the detector reads the filing's own words rather than inferring from the
filer's name. Tested BEFORE the form check, for the same reason collapse is:
"this is not the kind of 10-K we read" is a different diagnosis from "this is
not a 10-K", and only the first is true here. The phrase occurs in no other
fixture in the 49-document corpus.

This is the README's promise being kept rather than a new capability:
"`unsupported` and `failed` mean the pipeline refused; it never emits a
best-effort parse of a document it could not identify."

## c) The collective Part pointer

Berkshire Hathaway FY2024 carries no per-item heading anywhere in Part III.
The whole of Part III is one sentence at offset 484,921: "Except for the
information set forth under the caption 'Executive Officers of the
Registrant' in Part I hereof, information required by this Part (Items 10,
11, 12, 13 and 14) is incorporated by reference to the definitive proxy
statement…". Pre-fix, all five items were `missing` at 0.40 with five
`expected_item_missing` warnings — honest, and the wrong diagnosis.

`segment.collective_pointer` requires **three** codes, not two (two-code
phrases are ordinary internal navigation and occur in filings that also carry
real headings), plus both the IBR phrasing and an external-document name, so
an internal pointer cannot reach this path — ADR-004 shape 1 only. It is read
off the codes segmentation left unassigned, so it can only ever upgrade a
`missing`; it can never displace a heading the filing actually carries.

**The offsets are null, and that is a contract amendment.** One sentence names
five items; INV-S1 forbids them sharing it, and slicing it five ways would
publish five spans whose text is "10, ", "11, " and so on — worse than
nothing. `specs/001-sec10k-contract.md` previously said a span-carrying status
"must have both" offsets, enforced by `envelope_shape`. It now permits exactly
one null pair: a `incorporated_by_reference` item carrying
`evidence.collective_reference`. Narrow enough that it cannot be used as a
loophole, and enforced as a *conjunction* rather than as a status exemption.

GPT's prediction for this filing was that letter-spaced headings (`Par t I`,
`Busines s`) would defeat normalization. That prediction was **wrong**:
normalization handles them and coverage is 97.6%. The record says so because
a prediction set is only an instrument if its misses are counted too.

## d) The trailing annex

Simon Property FY2024 and MetLife FY2024 both close with `Item 16. Form 10-K
Summary` whose entire body is the word "None." — and then print the exhibit
index (SPG: 23,401 chars) or the glossary and exhibit index (MetLife: 38,153)
before the signature block. `assign_boundaries` gives the last item everything
up to `TAIL_RE`, so both envelopes attributed tens of KB of exhibit list to an
item that says "None.", at 0.95, with no warning. It is the exact mirror of
`item_span_near_empty`, which can only see a span that is too SMALL.

`ANNEX_RE` clips the LAST item only, and never when that item is 15 — whose
subject matter the exhibit index is. Where the annex then belongs is left to
`unattributed_content` to report rather than guessed at: attributing it to
item 15 would be a second guess dressed as a fix.

## e) The escalation trigger gains a suppressor

ADR-036 §k records what the paid tier did on `intc-2025`: two attempts, the
second billed **$0.997760**, both returning `empty_completion`, zero items
resolved, running total $4.023452 with no item resolved on any filing. §a
above answers the same filing deterministically at $0.00.

So `escalate.trigger` now returns `fired: False` with
`suppressed_by: "cross_reference_index"` when the deterministic layer already
resolved the index. The *warning* is not withheld — the sensor stays defined
by the battery it reads — only the spend is. Consequences, both intended:

1. the deployed inspector cannot burn a dollar on the one document shape where
   a paid rung is *known* to fail;
2. `intc-2025` and `c-2025` leave `web/fixtures.DEPLOY_EXCLUDED`. They were
   excluded because the deployment escalates by default, which made the
   dropdown a paid button and `?fixture=intc-2025&run=1` a paid page load.
   That cost is no longer incurred, so the two real filings this repo now
   handles best are back in the demo. `deployed-exclusion-derived` follows:
   it derives the set from `escalate.trigger`, the actual sensor, instead of
   from the raw warning code the two used to agree on.

## f) The inspector

`web/view.py` appends the resolved regions to `display_text` only. `text`
stays the verbatim slice, because the pane is not its only consumer — the
anchor oracle `findAnchor` matches it against the original filing, and PR #27
R1 is the record of what happens when that consumer is handed a different
string. The pane gains a `content elsewhere` row naming each region and
stating, in the envelope's own words, that the offsets describe the span and
the regions are published separately because they overlap and nest.

## g) What the prediction set got right and wrong

Frozen before any run, `tasks/reviews/hard-batch-frozen-predictions.md`:

| filing | predicted | actual |
|---|---|---|
| Intel FY2024 | collapse onto the trailing index | **right** |
| Bridgecrest ABS | should refuse; will not | **right**, and the refusal shipped |
| Simon FY2024 | duplicate covers, transposed spans | **wrong** — dual registrant is handled, `success`, 92.2%; the real defect was item 16 |
| Berkshire FY2024 | letter-spaced headings break normalization | **wrong** — 97.6% coverage; the real defect was Part III |
| MetLife FY2024 | size and table density | **wrong** — `success`, 98.7%, 0.6 s; the real defect was item 16 |
| Citigroup | boundary bleed at 7/7A/8 | **wrong**, and understated — total collapse, coverage 0.0000 |
| Bank of America FY2024 | differential test vs Citi | `success`, 98.8%, no defect found — and NOT overfit to Citi, since Citi is the one that collapsed |

Four of seven predictions were wrong, and three of those four were wrong
because they predicted a *size* failure on a pipeline whose real failures are
all failures of *typographic assumption*. That is the finding the sweep
bought, and it is worth more than the fixes.

## h) Two held-out cases were burned, and both burns are declared

`evals/heldout/README.md`'s rule is that re-running does not burn a case;
**influence** does. Both burns are of that kind and both are recorded in the
moved case files themselves.

* **`c-2025`** — burned by influence. Its outcome (coverage 0.0000) drove the
  Citi extension of the resolver in §a. Moved to
  `evals/adversarial/c-2025-cross-reference-index.json`. Its four `min_chars`
  checks are kept **verbatim and red**, as `cvx-2015-internal-pointer.json`
  keeps its two: they assert content inside `start`/`end`, which §a rules
  impossible for this shape rather than merely unbuilt. Ordering stated
  plainly: the pre-fix numbers were measured before the fix, but this was a
  directed sweep and not a milestone run, so no report was committed between
  the two. What is committed is the post-fix held-out report and this record.
* **`spg-2019`** — burned by the rarer route: the fix made a frozen label
  *wrong*. `min_chars: 16 >= 100`, authored 2026-08-17 and never run, was
  cleared only because the §d bug was inflating item 16's span. SPG FY2019's
  item 16 body is the word "None."; no floor above ~35 is satisfiable.
  Adjudicated: the pipeline is right, the label is wrong. Moved to
  `evals/adversarial/spg-2019-item16-annex.json` with three checks that state
  what is true and would catch the bug's return.

The held-out set is now four cases. Two replacement filings are owed at the
next expansion, per that README's budget rule.

## i) What is NOT built, and why

1. **Resolving `cvx-2015`'s "page FS-1"** — the internal-pointer class ADR-034
   §e2 declined and ADR-038 adjudicated. That is a pointer inside one item's
   *body*, not a filing-wide index, and it names a section label rather than a
   page ladder rung. Different instrument, unchanged decision.
2. **Attributing the trailing annex to item 15** (§d). One guess is enough.
3. **A fifth status for "answered elsewhere in this document"**. `extracted`
   plus `evidence.cross_reference` plus a fired `low_item_coverage` already
   says it, and the contract's four statuses are load-bearing for consumers.
4. **Moving `doc_status` off `ambiguous`** for a resolved filing (§a).
