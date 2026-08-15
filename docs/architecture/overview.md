# Architecture overview — sec10k extraction pipeline

**Descriptive, not normative.** The binding artifacts are
`specs/001-sec10k-contract.md` and `specs/000-invariants.md`, enforced by eval
cases; this doc explains the intended mechanism so a reader (or auditor) can
predict behavior and challenge it. Where this doc and reality diverge,
spec-drift flags it and this doc gets fixed.

Design posture: deterministic code first, LLM last (`cost-discipline` skill);
all-stdlib at B (ADR-003); simplest strategy that survives the seven known
traps in `sec10k-domain`. Numeric thresholds below are **PROVISIONAL** — set
empirically at T4/T5 against eval outcomes and recorded in an ADR.

Planned layout: `src/sec10k/extract.py` (orchestration + assembly),
`normalize.py` (selection + normalization), `segment.py` (candidates + filter +
boundaries + status), `validate.py` (validation + confidence). Four files.

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
10-Q→unsupported case.

**3. Normalization** — deterministic plain text. Stdlib `HTMLParser` subclass:
block-level tags emit `\n`, inline tags (including all `ix:*`) emit nothing,
`script`/`style` skipped, `html.unescape`, nbsp→space, 3+ newlines collapsed.
Plain-text era: newline normalization passthrough. Page furniture deliberately
**stays in the text** (removing it risks verbatim provenance and determinism) —
it is filtered at candidate level instead. Failure modes: word-joining at block
boundaries, entity mess. Trace: input/output lengths, tag stats. Eval:
`verbatim` (INV-S2); a determinism + word-joining spike runs before this layer
is trusted (T3).

**4. Candidate detection** — every plausible item heading, with features.
Line-anchored, case-insensitive pattern on `Item <code>` where the code must be
canonical **and era-valid**; features per candidate: offset, line length,
trailing-title similarity to the canonical title (`difflib`), uppercase ratio,
proximity to a PART marker. A lenient tier (mid-line matches) is consulted
*only* for expected items that strict matching missed — the lenient tier can
never add surprise items. Failure modes: unseen punctuation variants, inline
headings missed. Trace: full candidate list with features. Eval: presence
recall on golden cases.

**5. TOC / false-candidate filter** — reject non-headings. (a) TOC cluster:
many candidates tightly spaced near the document start form a cluster → drop it
(cluster size / position / gap thresholds provisional, set in T4, recorded in
trace and an ADR). The dropped cluster is not discarded: it is **parsed as the
filing's self-declared item manifest** and handed to layer 8 — the trap doubles
as a checklist. (b) Prose references: mid-sentence position, "of Regulation"
suffix, "see / in / under" prefix → reject. Failure modes: TOC not near the
start, two TOCs, a genuine heading caught inside the cluster. Trace: **every
rejection with its reason** — the core observability requirement. Eval:
`min_chars` + `text_not_contains` (the TOC trap is `aapl-2025-content`).

**6. Boundary resolution** — one span per item. Greedy ordered assignment over
the era's expected sequence: walk expected order, accept the earliest surviving
candidate after the previous accepted boundary; span runs from heading start to
the next accepted heading start (last item → end of the 10-K body). Disorder
and duplicate survivors are handled by construction. Failure modes: wrong
duplicate picked, last-item tail swallowing signatures/exhibit index. Trace:
accepted/rejected per code with reason. Eval: `no_overlap_ordered` (INV-S1),
boundary anchors.

**7. Status classification** — a status for every item in the era's expected
set. No accepted heading → `missing`; heading with a short body (stub
threshold provisional) → keyword scan: "incorporated by reference" →
`incorporated_by_reference`; "not applicable"/"none"/"[reserved]" → `omitted`;
otherwise stays `extracted` at low confidence. Failure modes: IBR paragraph
longer than the stub threshold, keyword false hits. Trace: classification +
matched keyword. Eval: status-asserting checks (INV-S4).

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
residual-failure data exists; ADR-004 will choose then, sized to what actually
fails. Candidate noted for the record only: an LLM returning **verbatim anchor
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
