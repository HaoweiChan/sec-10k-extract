# Architecture overview — sec10k extraction pipeline

**Descriptive, not normative.** The binding artifacts are
`specs/001-sec10k-contract.md` and `specs/000-invariants.md`, enforced by eval
cases; this doc explains the intended mechanism so a reader (or auditor) can
predict behavior and challenge it. Where this doc and reality diverge,
spec-drift flags it and this doc gets fixed.

Design posture: deterministic code first, LLM last (`cost-discipline` skill);
all-stdlib at B (ADR-003); simplest strategy that survives the known traps
catalogued in `sec10k-domain` (ten and counting). Numeric thresholds below are **PROVISIONAL** — set
empirically at T4/T5 against eval outcomes and recorded in an ADR.

Planned layout: `src/sec10k/extract.py` (orchestration + assembly),
`normalize.py` (selection + normalization), `segment.py` (candidates + filter +
boundaries + status), `validate.py` (validation + confidence). Four files.
Built so far (T4): `extract.py` + `normalize.py` + `segment.py` — layers 1–7
and 11. Layers 8–9 (validation battery, calibrated confidence) are T5, so a
standing `validation_not_implemented` warning caps every filing at
`success_with_warning`; nothing claims a clean `success` before it has been
validated.

## Pipeline layers

Each layer: responsibility → strategy → main failure modes → what the `trace`
records → eval signal.

**1. Acquisition** (web service, never the extractor) — upload/save, or EDGAR
URL fetch with declared User-Agent, size cap, sha256. Fails loudly on network
errors. Trace: source, sha256, byte count. Tested at the service level, not by
eval cases.

**2. Document selection** — find the 10-K body, classify the form. If
`<DOCUMENT>` blocks exist: pick `<TYPE>10-K` or `10-K405`; else treat the whole
file as the document; cover-page "FORM 10-K" sniff; nothing matches →
`doc_status: unsupported`. Failure modes: exhibit chosen, wrong form accepted.
Trace: block count, chosen type + offsets. Eval: `ge-1994-oldformat`,
10-Q→unsupported case. **Built (T3)**: `<DOCUMENT>` blocks are present in 7 of
13 fixtures — including four `.htm` primary documents, not just the txt-era
submissions — so both paths are load-bearing. `<TYPE>` (EDGAR-validated) wins
when present and the cover sniff becomes a second opinion that warns on
disagreement rather than refusing; the sniff is confined to the first 3,000
chars because a 10-Q always cites its own prior 10-K further down. 10-K/A and
10-KSB are refused, not best-effort parsed.

**3. Normalization** — deterministic plain text. Stdlib `HTMLParser` subclass:
block-level tags emit `\n`, inline tags (including all `ix:*`) emit nothing,
`script`/`style` skipped, `html.unescape`, nbsp→space, 3+ newlines collapsed.
Plain-text era: newline normalization passthrough. Page furniture deliberately
**stays in the text** (removing it risks verbatim provenance and determinism) —
it is filtered at candidate level instead. Failure modes: word-joining at block
boundaries, entity mess. Trace: input/output lengths. Eval:
`verbatim` (INV-S2); a determinism + word-joining spike runs before this layer
is trusted (T3). **Built (T3)**, with two rulings the spike forced (ADR-006):
`ix:header`/`ix:hidden` are skipped like `script`/`style` (INV-S5 — their
character data was 15.4% of JPM 2024's text, ahead of the cover page), and a
newline is era-dependent — collapsed inside HTML text chunks at parse time
(where it is a filer's 80-column source wrap), preserved in txt-era filings
(where it is the document's own layout). Measured: 13/13 fixtures
deterministic, 40/40 eval anchors survive, 492 ms for the 12.8 MB JPM filing.

**4. Candidate detection** — every plausible item heading, with features.
Line-anchored, case-insensitive pattern on `Item <code>` where the code must be
canonical **and era-valid**; features per candidate: offset, title text,
similarity to the canonical title (`difflib` over era aliases), uppercase flag.
A lenient tier (mid-line matches) is consulted *only* for expected items that
strict matching missed — the lenient tier can never add surprise items.
Failure modes: unseen punctuation variants, inline headings missed. Trace:
candidate count plus every rejection. Eval: presence recall on golden cases.
**Built (T4)**: strict line-anchored matching only — the lenient tier is
deliberately NOT built (ADR-007). Strict matching finds every expected heading
in all 13 fixtures, and the one heading it cannot find (corrupted markup in
`malformed-html`) should surface as `missing`, not be rescued by a looser
pattern. The expected item set comes from the period-of-report date, resolved
from the SGML header, the iXBRL `dei` fact, or the cover page — all three are
needed to cover 13 of 13.

**5. TOC / false-candidate filter** — reject non-headings. (a) TOC cluster:
inside a dense run of ≥5 distinct codes, a candidate whose own code recurs
later in the document is an index entry → drop it (ADR-007 — per-candidate
recurrence, not density alone: real Part III one-liners sit as close as 43
chars apart). The dropped cluster is not discarded: it is **parsed as the
filing's self-declared item manifest** and handed to layer 8 — the trap doubles
as a checklist. (b) Prose references: mid-sentence position, "of Regulation"
suffix, "see / in / under" prefix → reject. Failure modes: TOC not near the
start, two TOCs, a genuine heading caught inside the cluster. Trace: **every
rejection with its reason** — the core observability requirement. Eval:
`min_chars` + `text_not_contains` (the TOC trap is `aapl-2025-content`; its
hard, titled-TOC form is `toc-titled`). **Built (T4)**: measured, the
load-bearing rule is simpler than predicted — a real heading carries its title
on the same line, which kills every real fixture's TOC *and* MSFT 2013's 42
running `Item 8` page headers in one move. The cluster rule only matters when
TOC entries are titled, which is why it needed a fixture of its own. (b) needs
no separate rule so far: line-anchoring plus the canonical-code filter already
rejects every prose reference in the set — GE 1994's "Item 405 of Regulation
S-K" and IBM 1997's "ITEM 601 OF" parse as codes 40/60 and are not canonical.

**6. Boundary resolution** — one span per item. Greedy ordered assignment over
the era's expected sequence: walk expected order, accept the earliest surviving
candidate after the previous accepted boundary; span runs from heading start to
the next accepted heading start (last item → end of the 10-K body). Disorder
and duplicate survivors are handled by construction. Failure modes: wrong
duplicate picked, last-item tail swallowing signatures/exhibit index. Trace:
accepted/rejected per code with reason. Eval: `no_overlap_ordered` (INV-S1),
boundary anchors. **Built (T4)** as described, with trap 8 handled by stopping
the last item at the signature block — verified on the txt-era and shell
fixtures, whose tails begin exactly at `SIGNATURES` (GE 1994's inline 280K-char
annual report is excluded, 75.8% of that document). Measured boundary hygiene:
every extracted span in all 13 fixtures starts with its own heading, 0
mismatches.

**7. Status classification** — a status for every item in the era's expected
set, per ADR-004/ADR-005: heading present → `extracted`, however trivial the
body ("[Reserved]", "None." — triviality is flagged by length and validators,
not status); heading present with a short pointer-only body naming a
*different document* (keyword scan, stub threshold provisional) →
`incorporated_by_reference`; heading absent where era/filer rules permit the
absence (optional Item 16, SRC 7A relief) → `omitted`; heading absent where
the era expects it → `missing`. Failure modes: IBR paragraph longer than the
stub threshold, keyword false hits, era-relief rules misjudged. Trace:
classification + matched keyword. Eval: status-asserting checks (INV-S4).
**Built (T4)** per ADR-004/005, with one ruling ADR-007 records: phrase
matching runs on a whitespace-flattened copy of the body, because fixed-width
txt filings wrap the very phrases the rules depend on ("definitive
proxy\nstatement") — that alone mis-classified 5 items across GE 1994 and
Textron 2001. The "stub threshold" above turned out not to exist: measured, IBR
bodies (93–1,875 chars) and extracted bodies overlap completely in length, so
shape decides — is the first sentence a pointer, and does it name a different
document.

**8. Structural validation** — the false-success net: a battery of
**label-free** validators modeled on how a human sanity-checks an extraction.
Because they need no annotations, they run on *every* filing — including
held-out ones the eval set has never seen; this is where robustness beyond the
labeled fixtures comes from. Core checks: expected-set completeness,
order/overlap re-check, coverage ratio (extracted-span sum ÷ body length),
sequence completeness. The battery (all thresholds/priors provisional —
measured from eval-set distributions at T5, ADR-recorded):

- **TOC manifest cross-check** — the parsed TOC cluster from layer 5 is the
  filing's self-declared item manifest; compare it against the extracted set.
  A mismatch is a strong, free warning.
- **Gap analysis** — text between consecutive spans should be near-empty
  (page furniture, PART markers). A large unassigned gap means missed content
  and *localizes* it — the complement of the coverage ratio.
- **Boundary hygiene** — each span starts exactly with its matched heading,
  ends at sentence/paragraph punctuation (not mid-sentence), and the next
  accepted heading sits immediately after its end.
- **Part-region consistency** — PART markers must fall between the right items
  (e.g. "PART II" between Items 4 and 5); each item inside its declared Part's
  region.
- **Rank-order length sanity** — relative, not absolute: Item 8 typically
  longest, 1A ≫ 1B, 9B tiny. Rank checks survive where absolute bands break
  (shell company vs mega-cap).
- **Numeric density** — digit/`$`/`%` ratio per item: Item 8 extreme, 1A
  near-zero. A cheap mislabel detector.
- **Keyword fingerprints** — small per-item vocabulary priors ("risk" /
  "adversely affect" density for 1A, "litigation" for 3, "internal control
  over financial reporting" for 9A, "compensation" for 11) scoring whether a
  span *reads like* its label; includes negative fingerprints (risk-language
  density inside Item 1 = bleed, generalizing the single-phrase
  `text_not_contains`).
- **Dual-method boundary agreement** — boundaries derived independently from
  headings (layer 6) and from TOC anchors are compared; agreement raises
  confidence, disagreement → `ambiguous`. The strongest form of
  multiple-ways-to-verify, nearly free once the TOC is parsed.

Signals are chosen for independence — shape, content, structure, agreement —
not volume (word count + paragraph count + char count is one signal three
times). Policy per taxonomy F7: every validator is itself a false-positive
source (financials, shells, smaller reporting companies all violate "typical"
priors), so validators emit warnings and move confidence; only TOC-manifest
mismatch, gap analysis, and dual-method disagreement may push `doc_status` to
`ambiguous`, and none hard-fails a run alone. Failure modes: priors wrong for
atypical filers. Trace: each validator with pass/fail and measured values.
Eval: feeds `doc_status`/warning cases.

**9. Confidence scoring** — see below.

**10. Fallback (A-level, design deferred)** — no concrete design until T8
residual-failure data exists; a dedicated ADR will choose then, sized to what
actually fails. Candidate noted for the record only: an LLM returning **verbatim anchor
quotes** that we re-locate to offsets (preserves INV-S2 by construction —
invented quotes fail relocation and become explicit failures), cached by
content-hash + prompt-version, budget-capped, `full` suite only.

**11. Assembly** — derive `doc_status`, attach trace/timings/meta, emit the
contract-v2 envelope.

## Confidence semantics

Evidence-derived and interpretable; never a vibes number.

**Committed structure**: a tiered base score by heading-match quality
(strict + title match > strict with weak title > lenient), minus additive
penalties for recorded evidence flags — a competing surviving candidate for the
same code, a boundary closed by end-of-document, length outside the prior band,
each relevant validation warning. Coarse rounding, clamped away from 0 and 1 —
no fake precision. Every input to the score is recorded in the item's
`evidence{}`, so an auditor can recompute or dispute it.

**Committed ordering for non-extracted statuses** (most→least confident):
keyword-evidenced IBR/omitted > missing with zero candidates at any tier >
length-inferred classification > missing because all candidates were rejected.

**All numeric values are PROVISIONAL placeholders** — set empirically in T5
against eval outcomes, recorded in an ADR. At A-level: bucket dev + held-out
items by score, measure empirical accuracy per bucket, publish the table in the
analysis report, and remap scores through it (a lookup, not a model).

## Doc-status derivation (fixed rule order, thresholds provisional)

1. Exception / unusable input / normalization collapse → `failed`
2. Form detection says non-10-K / no 10-K document found → `unsupported`
3. Unresolved duplicate candidates for an expected item, or low coverage
   ratio → `ambiguous`
4. All expected items statused but any warning emitted → `success_with_warning`
5. Otherwise → `success` — deliberately hard to earn.

## Deterministic vs heuristic vs LLM

| | Deterministic (regex/parse) | Heuristic (tiers, clusters, priors) | LLM |
|---|---|---|---|
| Reliability | high on covered patterns, zero on uncovered | degrades gracefully | highest variance coverage |
| Latency | ~0 | ~0 | 1–10 s/call |
| Cost | 0 | 0 | real, per call |
| Explainability | total | good — features recorded in trace | weak; must be caged |
| Scalability | linear | linear | rate/budget-bound |
| Brittleness | brittle to unseen variance | tunable against evals | prompt/model drift |

Ladder order per `cost-discipline`: each stage sees only what the previous
stage couldn't handle, and **per-stage hit-rate is logged** — that number is
what justifies or kills each stage in the analysis report. LLM usage is a
conclusion from residual-failure data, not an assumption.

## Observability

The `trace` answers, for any filing: what document was selected; what
candidates were found; which were rejected and why; which boundaries won;
which validations passed/failed with values; whether fallback ran; what moved
confidence. Structured decisions and evidence only — no model chain-of-thought.
Consumers: the frontend debug panel, the extraction-auditor, developers, and
the analysis report (timings/cost aggregation).
