# ADR-036 — D11: the model tier ships, but only behind the D8 document-level trigger, and it is never trusted without a deterministic re-check

Date: 2026-08-26. Status: accepted, **with one part of its acceptance criteria
UNRUN and said so in §k**. **§h2 lock 4 (the `X-Escalation-Token` door) is
SUPERSEDED 2026-08-28 by [ADR-041](ADR-041-escalation-open-by-default.md)**:
the paid tier is open to every request and the process `Budget` is the only
money bound; locks 1–3 stand. **AMENDED 2026-08-27 in the PR #58 round-1 repair**:
the provider swapped from the Anthropic Messages API to OpenRouter on owner
instruction (§h1, and every dollar figure in §d is recomputed on OpenRouter's
published pricing); the deployed inspector gained three independent locks before
a credential lands on it (§h2) — **amended again 2026-08-27 on owner
instruction, "make it default on, remove the button": the escalate control is
gone, the deployed service escalates on every request, Lock 1 is INVERTED into
an operator off-switch and Locks 2/3 are untouched; `extract_items`' own
`escalate=False` default is deliberately NOT changed, and the exposure this
creates on an unauthenticated endpoint is stated in §h2 rather than
softened**; `verify` gained the span-status guard the
reviewer's HIGH finding named and its all-or-nothing claim was made true (§b);
and §c1/§c3/§d4 are corrected where their cited evidence did not match the
source. Each correction is marked in place. **Supersedes
[ADR-020](ADR-020-fallback-not-justified.md)**, whose ruling — "no LLM fallback
ships; `method: llm_fallback` stays in the contract enum, unemitted, and the
pipeline stays stdlib-only at $0.00 cost" — is now wrong in its first clause
and still right in its last two on every document the trigger leaves quiet.
Implements D11, the last row of the demo-remediation track. Depends on
[ADR-035](ADR-035-item-level-escalation.md) (D8) for its sensor and takes
[ADR-034](ADR-034-pointer-and-fanout-rulings.md)'s (D9) two "subsumed by D11"
rulings into scope. Amends `specs/001-sec10k-contract.md` (one new optional
envelope key, two new `method` values), `README.md` (the scope row is
RE-AFFIRMED, not moved — §e). Narrative:
`docs/evals/audits/2026-08-25-demo-intel-citi-postmortem.md` §7.

**Ruling**: four decisions. (1) The ladder is `deterministic → llm_localize (small model, the largest unattributed region, capped at `LOCALIZE_WINDOW`) → llm_extract (large model, the document capped at `EXTRACT_WINDOW`)` — BOTH rungs' inputs are bounded, so one call's price is bounded on arbitrary input, entered **only** when `low_item_coverage` fires, opt-in behind `escalate=True`, and no rung's answer is used until `escalate.verify` re-derives its offsets against the deterministic output (bounds, `SPAN_FLOOR`, INV-S1 ordering, and a `SIM_FLOOR` heading match). (2) **Text-less / scanned filings stay OUT of scope** and the README row is re-affirmed, so **no vision rung is built** (§e). (3) The envelope publishes a `routing` record and two new `method` values, and the inspector renders both. (4) With no `OPENROUTER_API_KEY` the slow path **refuses loudly** — a `routing` outcome of `unavailable` plus an `escalation_unavailable` warning — and never degrades silently.
**Because**: measured over all 44 dev filing fixtures, `low_item_coverage` fires on **2 of 44 (0.0455), and on 1 of 29 real EDGAR filings**, so the ladder's default cost is exactly $0.00 and the whole dev corpus escalates for an estimated $1.3440 (derived, `tasks/reviews/d11_sweep_cost.py`; the $0.056 this header carried until 2026-08-27 was the pre-OpenRouter figure and is withdrawn — PR #58 R20). **Both figures moved on 2026-08-27 when the live exam burned `intc-2025` and its fixture moved to the dev side (`evals/heldout/README.md`, Burn 2026-08-27): the trigger now fires on a REAL filing and not only on the synthetic, which is stronger evidence, and the sweep is 21× more expensive because that filing is 517,976 chars.** The item-level `item_span_near_empty` fires on 13 of 44 (10 of 29 real) and is deliberately NOT the trigger, because escalating on it would spend money on the A2 class ADR-034 §e2 declined and put the dev escalation rate at 27.9%.
**Enforced by**: `evals/adversarial/escalation-trigger-quiet.json` and `evals/adversarial/escalation-no-credential.json` (fast + invariant), `evals/adversarial/ui-routing-provenance.json` + `evals/adversarial/ui-routing-provenance-regression.json` (its 11-failure mutation fixture `evals/fixtures/repo_hygiene/routing-strip-missing.html`), `evals/adversarial/escalation-seam-offline.json`, `src/sec10k/escalate.py::_demo`, `src/sec10k/llm.py::_demo`, `src/sec10k/web/view.py::_demo`, `evals/adversarial/escalation-verify-guards.json` (PR #58 R1/R2/R7 — the first case that reaches `verify` at all), `src/sec10k/eval_adapter.py::_routing_shape` + the `routing` / `escalation_invariant` / `verify_guards` check types, and `.github/workflows/ci.yml`'s unit-tests job, which runs both `_demo`s (PR #58 R3: before it did, every guard in this ADR was deletable with the gate 100% green). Red-first record with its sha: `tasks/reviews/d11-red-first.txt`. Measurement: `tasks/reviews/d11_trigger_scan.py` (§c's census) and `tasks/reviews/d11_sweep_cost.py` (§d's dollars, derived from that census and the committed price record rather than retyped — PR #58 R8), plus `evals/adversarial/ui-escalation-locks.json` with its two mutation fixtures — `escalation-locks-removed.py` (the locks deleted, PR #58 R9) and `escalation-locks-evaded.py` (every name and shape intact and both locks defeated by three one-token edits, PR #58 R18) — which bind §h2's locks.

---

## a) What ADR-020 ruled, what has changed, and what has not

ADR-020 (2026-08-19) ruled an LLM fallback NOT JUSTIFIED and gave two reasons.
Both are re-checked here rather than waved away, because a superseding ADR that
does not re-check its predecessor's evidence is just a reversal with a
footnote.

| ADR-020's reason | Still true? | What changed |
|---|---|---|
| Six of seven residual-failure classes are **precision** failures a recall-only fallback cannot reach | **Still true, and this ADR does not claim otherwise.** The ladder is a recall mechanism; it moves spans into unattributed text and cannot fix a span that is in the wrong place for a precision reason. | Nothing. §i names what this ladder does not reach. |
| The one real recall gap (`axp-2008`, 4 of 768 items) closes deterministically at $0 | **Still true.** | Nothing — and ADR-034 §e3 already ruled the `axp-2008` fan-out "subsumed by D11" on the escalation-ladder principle, which is exactly what this document builds. |
| Therefore no fallback ships | **No longer true**, and this is the whole change | Two things arrived after 2026-08-19 that ADR-020 could not have measured: the 2026-08-24 demo, where two real filings (Intel, Citigroup) collapsed onto cross-reference index rows and were reported at `conf 0.95`; and D8's `low_item_coverage`, a **measured, document-level, zero-false-positive** signal for exactly that shape. ADR-020's argument was "no fallback ships *unconditionally*, because there is no gap worth the money". The gap is now identified, and — critically — so is a trigger that costs nothing on 42 of 44 dev documents. |

**What ADR-020 got right, and this ADR keeps.** The escalation-ladder
principle: the deterministic pipeline is the default and the only path on a
clean filing; a paid tier is a **triggered** capability, never an
unconditional one; and `$0.00` remains the honest published cost of a run in
which nothing escalated. Every one of those survives.

**Where ADR-020 must now be read with a correction.** Its §b table row 7 and
its headline sentence — "the pipeline stays stdlib-only at $0.00 cost" — are
true only of the default path from this commit on. The pipeline is still
stdlib-only in the sense that matters to CI (§h: `requirements.txt` is
unchanged, no `pip install` runs, the gate loads no network module), but it
now contains an HTTP client, and a caller who passes `escalate=True` on a
collapsed document can be billed.

## b) The ladder, and the property that makes it safe to ship

```
rung 0   deterministic        always, $0, unchanged
   │     … `low_item_coverage` in warnings?  no → STOP. This is 42/44 dev documents.
   ▼
rung 1   llm_localize         openai/gpt-5-mini, input = the largest UNATTRIBUTED
   │                          region only, capped at 60,000 chars
   │     … verify() accepts the answer?      yes → STOP.
   ▼
rung 2   llm_extract          anthropic/claude-opus-5, normalized text capped
                              at EXTRACT_WINDOW = 1,250,000 chars
         … verify() accepts?  no → the deterministic spans stand, and the
                                   envelope says the ladder resolved nothing.
```

Both paid rungs answer the **same question** — "for these item codes, where in
this text is the content?" — and return the same artifact: a JSON map from item
code to a `[start, end]` offset pair, or `null`. They differ only in cost class
and in how much of the document they are shown. That is what makes the ladder
cost-proportionate rather than decorative: the cheap rung is asked first and
sees only the text no item claimed, which is the premise of the whole
escalation; the expensive rung is asked only when the cheap one fails and is
the only one that pays to read the whole filing.

**Neither rung is trusted.** `escalate.verify` re-derives every offset before
it is used, and a proposal that fails any check is discarded with the rejection
published in the routing record:

1. the code must be an item of this document, and one this tier was actually
   asked about — a rung may not invent an item or resolve one nobody asked
   about (the second half was claimed but not implemented until PR #58 R7);
2. **that item must carry a span at all.** `missing` and `omitted` items have
   null offsets by contract, and `meta.coverage` sums every item with a
   non-null start — so resolving one both publishes a malformed envelope and
   inflates the exact number the D8 trigger thresholds on. Added 2026-08-27
   (PR #58 R1, HIGH): measured on the reviewer's repro, one resolved `missing`
   item moved a document's coverage from 0.0030 to 0.6142. `c-2025`, one of
   the two held-out exam filings, is 21 `missing` + 2 `omitted`, so the first
   live run would have hit this. `envelope_shape` now asserts the contract's
   null-span rule too, so the guard binds every producer and not just this one;
3. `0 <= start < end <= len(normalized_text)` (INV-S2);
4. `end - start >= SPAN_FLOOR` (1,500) — resolving a stub to another stub is
   not a resolution, and `SPAN_FLOOR` is the constant D8 already measured for
   precisely this question (ADR-035 §b1);
5. the item list, **after substitution**, is still disjoint and in ascending
   offset order — the same property `no_overlap_ordered` asserts (INV-S1);
6. the span must open with something that reads like this item's heading, by
   the same `title_similarity` / `SIM_FLOOR` cut `find_candidates` uses to
   accept a heading in the first place.

Check 6 is the one that matters most and the one to attack. It means a
hallucinated offset does not merely have to be plausible — it has to land on
real heading text that the deterministic segmenter would itself have accepted
had it looked there. `escalate._demo` pins the hallucination shape directly: a
long, in-bounds, correctly-ordered span pointing at the document's tail is
rejected on similarity, not on luck.

**All-or-nothing.** Either every proposed span survives or none is used.
Stricter than necessary, and deliberate: the ordering check is a property of
the item list as a whole, and partial application makes the failure mode "some
items moved and the ordering held by accident". Carried with its upgrade path
in a `ponytail:` comment in `verify`'s docstring.

> **Correction, 2026-08-27 (PR #58 R2).** This paragraph was FALSE when first
> published. The loop `continue`d past each failing entry and returned the
> survivors; only an ordering failure discarded the whole proposal, and every
> mixed proposal `_demo` happened to construct tripped ordering as a side
> effect, so the property had never once been watched. The reviewer's repro is
> in `tasks/reviews/pr58-r1-red.txt`. **The claim was kept and the code was
> changed to match it** — on this paragraph's own rationale, which is right —
> and `evals/adversarial/escalation-verify-guards.json` now pins both
> directions: a mixed proposal is discarded entirely, and a *null* sibling
> ("I could not locate item 8") is not a rejection and does not discard the
> survivor.

**What a resolved item looks like.** Its `start`/`end` move, its `method`
becomes `llm_localize` or `llm_extract`, its `heading_text` becomes `null` (the
new span does not open with the heading the segmenter matched, and `verbatim`
reads that field), and `evidence.deterministic` holds the offsets, method,
heading and title similarity the $0 path had published. The fast path's answer
is never destroyed.

## c) The trigger — re-derived, not cited, and one disagreement to report

Instrument: `tasks/reviews/d11_trigger_scan.py`, which runs `extract_items` at
default flags over every filing under `evals/fixtures` and reports, per
document: normalized chars, published `meta.coverage`, `doc_status`, whether
each D8 code fired, and — for every `item_span_near_empty` hit — the item's
**whole span in full**, so the adjudication below is checkable rather than
assertable. 43 filing documents (28 real EDGAR downloads, 15 self-created);
`evals/fixtures/repo_hygiene/` is excluded as not-a-filing and named as such in
the scan. **No held-out fixture is read** — the burn rule
(`evals/heldout/README.md`) governs, D11 still has its exam, and the numbers
ADR-035 §b4 already published are cited rather than re-measured.

### c1. The two candidate triggers, measured

| code | fires on | of all 44 | of 29 real filings |
|---|---|---|---|
| `low_item_coverage` (doc-level, escalating, ADR-035 §d) | `xref-index-collapse`, `intc-2025` | **2/44 = 0.0455** | **1/29 = 0.0345** |
| `item_span_near_empty` (item-level, non-escalating, ADR-035 §c) | 13 fixtures, 20 item hits | 13/44 = 0.2955 | 10/29 = 0.3448 |

**Re-derived 2026-08-27** after the live exam burned `intc-2025` and moved its
fixture to the dev side. The previous figures — 1/43 and 0/28 for the doc-level
code — were correct for a corpus that did not contain a real collapsed filing.
It does now, and §c2's admission below is the paragraph most changed by it.

The 13: `cvx-2015`(7,8), `fy2021-item9c`(8), `ge-1994`(8), `ibr-pointer-first`(8),
`intc-2025`(1,7,8), `jpm-2024`(7,8), `ko-1997`(8), `nvda-2024`(8), `reac-2015`(8),
`sandston-2021`(8), `spatz-2014`(8), `xom-2021`(7,8),
`xref-index-collapse`(1,7,8).

**Ruling: `TRIGGER_CODES = ("low_item_coverage",)`.** The router escalates on
the document-level code and not on the item-level one. Three reasons, in order
of weight:

1. **ADR-035 §c already ruled it**, and the router inherits rather than
   re-decides: "one pointer item is a fact about that item, not a verdict on
   the document." A code that deliberately does not escalate `doc_status`
   should not escalate to a paid tier either.
2. **The cost budget the D11 ledger row itself imposes.** The row requires
   "dev escalation rate stays near zero so the default cost stays $0". 1/29 on
   real filings is near zero. 10/29 is not.
3. **It would spend money on a class nobody has ruled is broken.** Stated
   precisely, because the first version of this paragraph over-claimed and the
   reviewer caught it (PR #58 R5). Of the nine real filings
   `item_span_near_empty` hits, exactly **four** — `cvx-2015`, `jpm-2024`,
   `ge-1994`, `spatz-2014` — are members of the A2 set `ADR-034` §d1
   enumerates and §e2 DECLINED. (A2's fifth member, `bac-2006`, does not fire
   at all.) The other five — `xom-2021`, `ko-1997`, `nvda-2024`, `reac-2015`,
   `sandston-2021` — **were never in D9's scope and are an unruled population,
   not a declined one.** So the accurate statement is: four filings belong to a
   class D9 declined, and five belong to no ruling at all. Neither group is
   agreed to be defective, and building a paid capability to fix something not
   agreed to be broken is the shape ADR-026 §a's test exists to catch.
   Correspondingly, ADR-034's reason for declining A2 is not that two reads
   disagreed about items 7 and 8 — its §e2 says in terms that the auditor's
   blind sample adjudicated `cvx-2015` item **6** CORRECT and that "items 7
   and 8 were never independently adjudicated". The flag reaches items 1/7/8
   and never item 6. **Unadjudicated, not disagreed**, wherever this document
   says otherwise.

`item_span_near_empty` is not ignored: `trigger.items` carries every item it
flagged, and that list is what the rungs are asked about **once
`low_item_coverage` has escalated the document**. It is a hint, not a trigger.

### c2. Precision and recall, with the positive set stated honestly

**`low_item_coverage` — the router's actual sensor.**
Positive prediction: 1 document. Adjudication: `xref-index-collapse` has
coverage 0.0303 and its items 1, 7 and 8 are the bare heading lines
`"Item 1. Business."` (18 chars), `"Item 7. Management's Discussion…"` (95) and
`"Item 8. Financial Statements…"` (53) — a collapse by construction. **Precision
1/1 = 1.000.** Recall needs the misses, so the near-miss band is printed rather
than asserted empty: the only dev documents with coverage below 0.35 are
`ge-1994` (0.2306), its derivative `ibr-pointer-first` (0.2306) and `cvx-2015`
(0.2718), none of which is a collapse — `ge-1994` is a txt-era Exhibit-13 filer
and `cvx-2015`'s item 1 is 82,907 chars of real Business prose. **Recall
1/1 = 1.000.**

**And now the sentence that matters more than either number.** As first
published, the dev positive set had **size one and was synthetic**. A precision
and recall of 1.000 over n=1 is not evidence of generalization; it is evidence
that the one case the fixture was built for is caught. **Amended 2026-08-27:
the set is now size TWO and one of them is a real EDGAR filing** — `intc-2025`,
burned by the live exam and moved to the dev side, fires the code at coverage
0.0033 and is a genuine post-2019 reorg collapse rather than a fixture built to
trip a threshold. That is a real strengthening of this sensor's evidence, and it
was bought with the exam: the same move leaves D11 with one held-out filing.
n=2 is still not generalization. The real evidence for this sensor would be
the held-out run, which is **UNRUN** (§k). Anyone reading "precision 1.000"
here without reading this paragraph has been misled by the number, and the
number is published only because the ledger row asks for it.

**`item_span_near_empty` — not the trigger, measured anyway** because ADR-034's
falsifier turns on it (§c3) and because it selects the items the rungs are
pointed at. All 17 firing spans are printed in full by the scan and every one
of them is a pointer sentence, a cross-reference row or a bare heading line —
**precision 17/17 = 1.000** at the item level. For recall, the seven item-1/7/8
spans in `[SPAN_FLOOR, 4000)` — the shortest the floor let through — are
`tgt-2002`·1 (2,094), `spatz-2014`·1 (2,955), `fy2021-item9c`·1 and
`sandston-2021`·1 (3,164), `sgrp-2019`·7 and its two derivatives (3,763). Six
of the seven are unambiguous prose. **`tgt-2002` item 1 is the one contested
adjudication and it is contested here rather than glossed**: its first ~530
characters are a list of incorporation-by-reference page pointers ("The first
paragraph of Fourth Quarter Results, Page 19; Analysis of Financial Condition,
Page 20-21; …"), after which roughly 1,560 characters of genuine Item 1 content
follow — incorporation state, employee counts, a Competition section, an
Available Information section. Adjudicated **substantive**, so recall is
**17/17 = 1.000**; a reader who calls that span a pointer gets **17/18 =
0.944**. Both readings are published because the choice between them is a
judgement about one document, not a fact the instrument settles. ADR-035 §b1
describes the same span as "real Business prose in a near-pure-pointer
document", which understates the hybrid shape; that is a correction to the
description, not to the threshold, and it is carried as debt rather than acted
on here.

### c3. ADR-034's A2 falsifier: tripped, and adjudicated

ADR-034 §e2 declined A2 partly because "the D8 trigger is measured silent on
all five filings", and its own falsifier table says A2 becomes *subsumed* if
"the D8 trigger, once built, fires on any of the five A2 filings". Measured
here: `item_span_near_empty` fires on **four of the five** — `cvx-2015`(7,8),
`jpm-2024`(7,8), `ge-1994`(8), `spatz-2014`(8); only `bac-2006` is silent. The
falsifier is **tripped**, confirming the open debt row added at the PR #57
merge cross-check.

**Adjudication.** The falsifier is written against "the D8 trigger" as if D8
shipped one. It shipped two, with opposite escalation semantics, and the
sentence generalises a measurement of item 1 alone. Read against the code that
D11 actually routes on — `low_item_coverage` — the original claim holds: it is
silent on all five. Read against D8's item-level code, it does not. So:

* **A2 is not reachable by this ladder as built**, because the ladder does not
  route on the item-level code, for the three reasons in §c1.
* **"Declined" stands, and its stated reason is amended — twice.** The correct
  reason is not "nothing reaches it" (something does) and not "two reads
  disagree" (they did not; PR #58 R5). It is: **what reaches those items is a
  non-escalating item-level flag over spans that were never independently
  adjudicated at all, and D11 declines to spend money resolving a question
  nobody has answered.** ADR-034 §e2 is explicit — its blind sample adjudicated
  `cvx-2015` item **6**, not 7 or 8, and records that 7 and 8 "were never
  independently adjudicated". That is a weaker reason than D9 published and a
  weaker one than this ADR first published; saying so twice over is the point
  of this paragraph.
* **What would change it**, stated as its own falsifier: an adjudication that
  settles whether a pointer-bodied item 7/8 inside a well-extracted filing is a
  defect — which, per the paragraph above, would be the FIRST such adjudication
  rather than a tie-break between two existing ones. If it is, A2 becomes a one-line change here (`TRIGGER_CODES` gains
  `item_span_near_empty`) whose measured price is in §d4 — and that is the
  whole reason the price is published.

## d) Cost — one measured input, one ESTIMATE clearly labelled

**The measured half.** The escalation rate is measured, deterministic and $0:
**2 of 44 dev documents, 1 of 29 real filings** (re-derived 2026-08-28, PR #61
R14; `tasks/reviews/d11-trigger-scan.txt`). This paragraph said 1 of 43 and 0
of 28 until then, contradicting §c1's own table two hundred lines above it,
which had been re-derived on 2026-08-27 and this one had not. Both now come
from the same run of the same script.

**The estimated half, and why it is an estimate.** Nothing here has been
billed. Token counts come from a **4 characters ≈ 1 token** proxy over
`normalized_text`, not from a tokenizer call. Every figure below is therefore
an ESTIMATE and is labelled one everywhere it appears, including in this ADR's
own headline. `llm.call` records the response's own `usage` and computes `usd`
from it, so the first live run replaces every estimate with a measurement, in
the routing record, without a code change.

**Where the prices come from (recomputed 2026-08-27, PR #58 + owner
instruction).** Not from a table in this document and not from a constant in
the code. `GET https://openrouter.ai/api/v1/models` was fetched
unauthenticated on **2026-08-27**, and the two rungs' records are committed
verbatim at `tasks/reviews/2026-08-27-openrouter-models.json`, with the
sha256 of the full 417-model response as a **fetch receipt** — the hashed
response is not committed and OpenRouter's catalogue mutates, so that digest
records which fetch the two records were pruned from; it is not something a
reader can reproduce (PR #58 R16). What a reader can check is everything
downstream, and the reviewer did:
`llm.usd()` reads that file and **raises** on a slug it does not carry, so
there is no stale constant to fall back to:

| rung | OpenRouter slug | input $/MTok | output $/MTok | context |
|---|---|---|---|---|
| 1 `llm_localize` | `openai/gpt-5-mini` | 0.25 | 2.00 | 400,000 |
| 2 `llm_extract` | `anthropic/claude-opus-5` | 5.00 | 25.00 | 1,000,000 |

Rung 2 is deliberately the **same model** the pre-swap version costed, so every
figure below moves for exactly one reason: rung 1 got 4× cheaper on input.
Rung 1's slug is a judgement call, and the honest form of it is: the verifier
makes a wrong answer safe but not free, so a rung 1 that always fails is pure
waste. `openai/gpt-5-mini` is the cheapest tier plausibly competent at exact
offset arithmetic over a 60,000-char window, and **whether it actually is** is
one of the things the first live run exists to find out (§k). Its slug is one
constant in `escalate.RUNGS`.

### d1. Per-document estimate

**Every figure in this section is now DERIVED, not typed.**
`tasks/reviews/d11_sweep_cost.py` reads the character counts from the same §c1
census, the prices from the committed OpenRouter record, and prints these
tables; its output is committed at `tasks/reviews/d11-sweep-cost.txt`. That
exists because §d4's total was published wrong in two consecutive rounds
(PR #58 R4, then R8) and the cause was not the model — which reproduces every
figure below to the published digit — but five hand-typed character counts,
`reac-2015`'s wrong by 3.3×. A number a human retypes is a number that will be
wrong again.

| document | chars | rung 1 (`gpt-5-mini`) | rung 2 (`claude-opus-5`) | full ladder |
|---|---|---|---|---|
| `xref-index-collapse` | 33,061 | ~$0.0061 | ~$0.2161 | ~$0.2222 |
| `intc-2025` (the real collapse, burned in) | 517,976 | ~$0.0077 | ~$1.1141 | ~$1.1218 |
| median span-bearing dev filing | 108,893 | ~$0.0077 | ~$0.3565 | ~$0.3642 |
| `bac-2006` (2nd largest) | 705,848 | ~$0.0077 | ~$1.4620 | ~$1.4697 |
| `jpm-2024` (largest) | 1,213,284 | ~$0.0077 | ~$2.4017 | ~$2.4094 |

**Every figure in this table went UP on 2026-08-27, twice, and both times the
exam is the reason.** First: output was estimated at a guessed 150 tokens per
call, and the run showed reasoning tokens are billed as output — rung 2 spent
its entire 2,048-token allowance thinking and emitted nothing (§h4) — so output
is now priced at each rung's own `max_tokens` **ceiling**, 2,048 for rung 1 and
6,144 for rung 2 including its 4,096-token reasoning budget.

Second, and larger: **the chars-per-token proxy was wrong, per model, in both
directions** (§h5). It was a retyped `4` for both rungs. Measured against four
billed responses it is 3.0740 / 2.7395 for `anthropic/claude-opus-5` — so `4`
understated rung 2's tokens by up to **1.46×** — and 5.4195 / 4.2663 for
`openai/gpt-5-mini`, where it overstated. The proxy is now derived per model
from `tasks/reviews/2026-08-27-token-ratio.json` as the MINIMUM observed value
floored to 1 dp (2.7 and 4.2), minimum because fewer chars per token means more
tokens means more money, so it is the end that cannot understate. Both changes
push every figure the same way: up. The arithmetic, once, so the rest
re-derives: rung 2 on the median filing is `min(108893, 1250000)/2.7 + 250 =
40,580` input tokens at $5.00/MTok = $0.202900, plus a 6,144-token output
ceiling at $25.00/MTok = $0.153600, = **$0.3565**.

### d2. Per-corpus estimate

A full `escalate=True` sweep of all 44 dev filings costs an estimated
**$1.3440** — `intc-2025` at $1.1218 plus `xref-index-collapse` at $0.2222,
because the other 42 stop at rung 0. A default-flag sweep costs **$0.00**,
measured, not estimated: no tier is reachable.

Before 2026-08-27 this figure was **$0.0488** over 43 documents, when the only
escalating document was a 33,061-char synthetic and the token proxy was wrong.
The burn moved a 517,976-char real filing onto the dev side and the corrected
proxy raised every per-document price; together the sweep rose 27×. Nothing
about the trigger changed; the corpus and the arithmetic did.

### d3. Where the budget does not hold, said plainly

`Budget` checks the dollar ceiling against what has **already** been spent, not
against what the next call is projected to cost, so one call can overshoot
`max_usd` by its own price. The measured worst case on the dev corpus is
`jpm-2024`'s rung 2 at an estimated $1.5216 against a $1.00 default. The call
budget (`max_calls`) is a hard ceiling and is not affected. Carried as debt
with its upgrade path, in a `ponytail:` comment on `Budget.take` and a row in
the ledger.

**And a correction about what a `Budget` bounds at all (PR #58 R6).** Its
docstring said "per-run" and this section read as if $1.00 were a ceiling on a
sweep. It is not: a `Budget` bounds the calls and dollars charged through THAT
INSTANCE, and `extract_items` with no `budget=` creates one per DOCUMENT. A
caller sweeping many documents must pass one `Budget` to every call to get a
per-sweep ceiling; the web layer now does exactly that with a single
process-wide instance (§h2). The docstring says this in full.

### d4. The price of the trigger this ADR did NOT choose

Published because §c3's falsifier turns on it. **This figure has been wrong
twice — $3.4/~60× in the first version (PR #58 R4), $4.2252/86.7× in the second
(PR #58 R8) — and both times because the per-document character counts were
retyped by hand rather than read from the census.** It is now derived by
`tasks/reviews/d11_sweep_cost.py` and pasted from its committed output, and the
derivation reproduces the reviewer's independent figure exactly.

Routing on `item_span_near_empty` as well would escalate **13 of 44** dev
documents for an estimated **$9.6754 per sweep against the chosen trigger's
$1.3440 — 7.2×**. `bac-2006` is **not** among the thirteen (§c3: it is silent),
and the script asserts that rather than trusting it. Per document, largest
first: `jpm-2024` $2.4094, `intc-2025` $1.1218, `cvx-2015` $0.9358, `xom-2021`
$0.8827, `ibr-pointer-first` $0.8343, `ge-1994` $0.8343, `nvda-2024` $0.7943,
`fy2021-item9c` $0.3524, `sandston-2021` $0.3523, `ko-1997` $0.3426,
`reac-2015` $0.3101, `spatz-2014` $0.2833, `xref-index-collapse` $0.2222.

**This ratio has now moved twice, and the second move goes AGAINST the ruling.**
It was published as $3.4/~60× (wrong), corrected to $4.5656/93.6× (right for its
corpus), and is now **7.2×** — because the burn put a large real collapsed
filing on the escalating side of the comparison, so the narrow trigger's own
sweep is no longer nearly free. The cost gap between the two triggers is an
order of magnitude smaller than this section claimed a day ago. **The ruling
stands, and its cost argument is now much weaker**: §c1's other two reasons —
ADR-035 §c already ruled the item-level code non-escalating, and the class it
would reach is one nobody has adjudicated as broken (§c3) — are doing most of
the work. Saying so is the point of re-deriving a number instead of restating
it.

## e) Ruling on text-less / scanned inputs — OUT of scope, and the README row is re-affirmed

The D11 ledger row requires this to be an explicit decision either way, because
it moves a README scope boundary. **It does not move: `README.md`'s "Out of
scope by design" row — which names "scanned/image/PDF filings" — stands
unchanged, and no vision rung is built.** Four reasons, strongest first.

1. **The router is structurally downstream of the refusal.** A text-less input
   normalizes to under `COLLAPSE_FLOOR` and returns a `failed` envelope with
   `normalization_collapse` **before any item exists** — before `expected`,
   before `validate`, before `meta.coverage`. There is no item span, so
   `low_item_coverage` cannot fire, so the trigger cannot fire, so escalation
   is unreachable. Measured: 4 of 44 dev documents refuse before any item
   exists (`aapl-2026-10q`, `amended-cover-2021`, `ksb-2007` as `unsupported`;
   `truncated-download` as `failed`). Admitting scanned input is therefore not
   "add a rung" — it is "make a refusal into a trigger", which is a different
   and much larger change.
2. **It would break the cost budget the same ledger row imposes.** If a
   refusal became a candidate for a paid OCR-class pass, then every truncated
   download, every mis-fetched page and every non-10-K form would be a
   candidate too — the classes are indistinguishable at the point of refusal,
   which is exactly why the contract tests collapse *before* form identity.
   The escalation rate stops being 1/29 and becomes "however many bad inputs
   arrive", which is unbounded and adversary-controlled.
3. **The corpus has zero instances.** 0 of 44 dev filings and 0 of 7 held-out
   filings are text-less (the held-out figure from ADR-035 §b4's published
   table, not from a new read). EDGAR has required machine-readable HTML or
   text since 1996. A capability with no committed instance cannot be evaluated
   here at all.
4. **Its price is the highest in the ladder and its yield the lowest.** Full
   character recovery over a scanned filing is an image-per-page vision pass —
   the most expensive call available — bought for documents that, per (3), the
   corpus does not contain.

**What this costs, stated rather than hidden.** A genuinely scanned 10-K — a
pre-1996 paper filing, some foreign private issuers, a photocopied exhibit —
stays refused. The refusal is honest and names its reason, which is the
ADR-024 pattern for 10-K/A. **This is a real capability gap and it is a
decision, not an oversight.** What would change it: a committed fixture of a
text-less 10-K plus a decision that the refusal path may escalate, which is a
milestone of its own.

**And therefore no vision rung.** The D11 row's middle rung was specified as a
"vision verifier" that renders the filing and localizes the miss. Under the
owner's own 2026-08-25 correction the ladder is failure-class-conditional:
vision-as-verifier presumes text exists but spans are wrong, and
vision-as-extractor is for input with no text. Ruling (1) removes the second
branch from scope. For the first, the localization question — "where in this
document is item 8's real content?" — is answered from the normalized text and
its offsets, which is what the rung must return anyway; pixels would add a
rendering step and answer the same question less precisely, since a rendered
page cannot name a character offset.

**A second, independent reason, which is a constraint and not an argument, and
is recorded so this ruling is not read as purely principled.** There is no
stdlib HTML renderer. Rendering a filing needs a headless browser or a PDF
engine — a new dependency, which `requirements.txt` and a CI job that runs no
`pip install` forbid (ADR-003). Had reason 1 gone the other way, this
constraint would still have blocked the rung in this pass, and the honest
outcome would have been "declared, not built". **The interviewer-facing claim
"cost-proportionate escalation with visual backing" is therefore only half
delivered: the escalation is built and instrumented, the visual backing is
not.** Carried as debt with its dependency named.

## f) Blast radius — `origin/main` (5a44758) vs this branch

Instrument: `evals/snapshot.py`, the committed byte-identity harness (ADR-026
§d, ADR-033 §d, ADR-035 §f), run against an `origin/main` checkout and against
this tree, then diffed key by key.

```
origin/main   dev: 58 files  sha256=58364186aff9dad3f7443de4b5447ae3a7894e76fc01ad1592fd03a4b4479d0f
              heldout: 7 files  sha256=f80025699bc34f06af6ea0fb3457106593ec858c4d89d4144870e339b00e191a
task/D11      dev: 61 files  sha256=d011ead7c65f7bf9bbe5fdd6f43feeab8c8c4ef29bc657457fc815ad89f2bb39
              heldout: 7 files  sha256=f80025699bc34f06af6ea0fb3457106593ec858c4d89d4144870e339b00e191a
```

> **The `task/D11` line is re-run on the commit this PR ships, not on an
> earlier one (PR #58 R10).** The first published value was taken before the
> round-1 repair edited two mutation fixtures, so a reader re-deriving it got a
> different number — which defeats the entire point of a section whose claim is
> "re-runnable". Re-taken after the last fixture change in this branch, and
> re-taken again in the round-3 repair, which added a third mutation fixture
> (`escalation-locks-evaded.py`) and edited a fourth. Shipping a digest known
> to be one commit stale is how R10 arose; doing it inside the commit that
> closes R10's siblings would be the same mistake one level deeper.

**The held-out sha is byte-identical.** So is every filing document in dev.
The dev sha moves for two reasons, both of which are files rather than
behaviour:

* three new files, `evals/fixtures/repo_hygiene/routing-strip-missing.html`,
  `escalation-locks-removed.py` and `escalation-locks-evaded.py` — the mutation
  fixtures for the two new `repo_hygiene` checks, which the snapshot harness
  sweeps because it sweeps everything under `evals/fixtures`;
* three edited files, `repo_hygiene/boilerplate-checkbox-default-on.html`,
  `boilerplate-wire-values.html` and `boilerplate-wire-values.py` — the ADR-026
  wire mutation fixtures, whose *text* was edited so their correct hops carry
  the new pinned spelling (§g2). Only `sha` and `norm_chars` move on each; all
  three still report `unsupported`, and none of them is a filing.

**0 of 43 filing documents differ in any field the harness reads** — no
`normalized_text` sha, no offset, no `status`, no `method`, no `confidence`, no
`doc_status`, no warning, no envelope key.

**One field the harness cannot see, stated rather than left implicit.**
`snapshot.py`'s digest does not read `meta.extractor_version`, and that
constant moves (`0.9.0-d8` → `0.9.1-d11`). It is the one field of the
default-flag envelope that is not byte-identical, exactly as it moved for D8.
Everything else is.

## g) What changed, and the pins that moved with it

### g1. New

`src/sec10k/llm.py` (the only module that can talk to a paid API: credential,
budget, cache, pricing — rewritten for OpenRouter 2026-08-27, §h1),
`tasks/reviews/2026-08-27-openrouter-models.json` (the committed pricing
source `llm.usd()` reads), `src/sec10k/escalate.py` (trigger, windows, verify,
apply, route), `tasks/reviews/d11_trigger_scan.py` (§c's instrument), five eval
cases, one mutation fixture, two `repo_hygiene` checks (`escalation_seam`,
`routing_provenance`), three `sec10k` check types (`routing`,
`escalation_invariant`, `verify_guards`), `_routing_shape` and the
missing/omitted null-span rule in `envelope_shape`, and two `ci.yml` lines that
make this ADR's two `_demo`s enforcement rather than a claim (PR #58 R3).

Added in the PR #58 round-2 repair: `tasks/reviews/d11_sweep_cost.py` +
`d11-sweep-cost.txt` (§d derived rather than typed, R8), a third `repo_hygiene`
check `escalation_locks` with `evals/adversarial/ui-escalation-locks.json`, its
regression case and the `escalation-locks-removed.py` fixture (§h2's locks bound
by a runnable check, R9), and `escalate.EXTRACT_WINDOW` (rung 2's input capped,
R12).

Added in the PR #58 round-3 repair, all of it binding mechanisms that earlier
rounds introduced UNBOUND — the pattern the circuit breaker fired on: the tier
record's `offset` and the strip's true range (R17), `escalation-locks-evaded.py`
+ `ui-escalation-locks-evaded.json` (R18), the `_demo` block that drives `route`
over an over-long document with a stubbed transport in place of a tautology on a
local string (R19), the `offset`/`input_chars`/`truncated` requirement in
`_routing_shape` (R17/R19), and an eighth shape in `routing-strip-missing.html`
(R19). Every one of them was proved by mutation before it was claimed —
transcripts in `tasks/reviews/pr58-r3-red.txt`.

### g2. Pins that moved because the wire moved

`check_boilerplate_plumbing`'s allow-list holds the exact expression at each
hop of the ADR-026 flag's path. Three of those hops gained the `escalate`
flag, so three pins were re-spelled and the three mutation fixtures that carry
their correct halves were re-spelled with them — the same move S9 (ADR-032)
made when `blocks=markdown` joined the same call, and the wire was re-checked
by hand rather than assumed — **and removed 2026-08-27 with the control itself (§h2's owner note); the hop below described the opt-in wire**: `#escalate` → `escalateOn()` → request body or
query string → handler → `_run` → `extract_items`. `ui-confidence-honesty`'s
banner pin moved for the same reason (the banner now also calls
`routingStrip`). **A moved pin is the one change in this diff that can hide a
regression**, so it is listed here explicitly rather than buried in a diff.

## h1) The provider is OpenRouter, not the Anthropic API (2026-08-27, owner instruction)

A real swap, not a rename. `OPENROUTER_API_KEY` replaces the Anthropic
credential everywhere including the eval adapter's credential-stripping;
`Authorization: Bearer` replaces `x-api-key`; the endpoint is
`https://openrouter.ai/api/v1/chat/completions`; the body is OpenAI-shaped
(`messages: [{role: system}, {role: user}]`) and has exactly three keys; the
response is read from `choices[0].message.content` and usage from
`usage.prompt_tokens` / `usage.completion_tokens`; the model ids are
OpenRouter slugs (§d). Two provider-shaped failure modes the previous client
did not have are handled: OpenRouter returns provider errors inside a **200**
body, and it signals a filtered completion with `finish_reason:
"content_filter"` — both raise `EscalationUnavailable` rather than yielding
empty text that would parse as an empty proposal.

**Dropped rather than mapped.** The Anthropic client sent a reasoning-effort
knob in a nested config object. OpenRouter's chat-completions surface has no
equivalent, so it is gone and its plumbing with it — mapping it onto a
different provider's different concept would have been an invented
equivalence. `llm._demo` asserts the request body's SHAPE (three keys, two
messages in order) rather than text-matching the file, so a comment cannot
satisfy the pin.

**Still no new dependency.** `requirements.txt` is unchanged; the client is
stdlib `urllib.request` + `json`. `PROMPT_VERSION` moved to
`d11.2-openrouter`, so no cached response from the old transport can be served
for a new-transport request.

## h2) The deployed inspector: four locks, because a real credential landed on it

> **AMENDED 2026-08-27 — owner decision: "make it default on, remove the
> button."** The deployed inspector now escalates on EVERY request. The
> escalate checkbox is gone from `index.html`, along with the helper that read
> it, the `/api/meta` arming round-trip that disabled it, the
> `escalation_disarmed` refusal note, and the request-level `escalate` flag on
> all three endpoints. The server decides; the client has no say.
>
> **Lock 1 is INVERTED, not removed.** `ESCALATION_ENABLED` used to ARM paid
> work (`os.environ.get("SEC10K_ESCALATION_ENABLED") == "1"`, off until
> someone opted in); it now DISARMS it — on until the operator says stop.
> **The off value is a documented falsy SET, not one literal** (PR #61 R3):
> `SEC10K_ESCALATION_ENABLED` is stripped, lowercased and tested against
> `DISARM_VALUES = ("0", "false", "no", "off")`. The first cut compared
> against `"0"` alone, which left `false`, `off`, `FALSE` and `"0 "` all
> ARMED — and those are what an operator types into a Zeabur variable, so it
> was a stop button that would be believed and would not work. **UNSET and
> EMPTY both ARM**, deliberately: that is the default-on this section exists
> to record, and `os.environ.get(VAR, "")` makes the two states identical.
> Anything not in the set arms. An off-switch costs nothing, does not contradict "default on", and
> means a runaway is stopped by an env var on the host rather than by a code
> change and a redeploy. The check that binds it moved with it: the semantics
> pin that PR #58 R18 added — the shape alone is not the property — is
> re-derived for the new direction, and `escalation_locks` now also pins that
> the `extract_items(...)` call site NAMES `ESCALATION_ENABLED` rather than
> passing a literal, because with no request flag left to AND against,
> `escalate=True` would orphan the switch while leaving it in the file looking
> authoritative. Mutation transcripts: `tasks/reviews/escalate-default-on-red.txt`.
>
> **Locks 2 and 3 are UNTOUCHED**, and they carry more weight than they did:
> the process-wide `Budget` (`SEC10K_ESCALATION_MAX_CALLS`,
> `SEC10K_ESCALATION_MAX_USD`) and `EXTRACT_WINDOW`'s input cap inside
> `escalate.route` are now the only ceilings, because nobody has to tick
> anything to spend money. The effective deployment ceiling below is unchanged.
>
> **SCOPE, stated because getting it wrong would be serious.** This is a WEB
> LAYER change only. `extract_items`' own `escalate=False` default is
> deliberately unchanged. Flipping the library default would put paid API
> calls on every `python3 -m evals.run` and in CI, destroying the $0 offline
> gate the whole eval harness depends on — and §l's falsifier "escalation is
> free by default" would go from true to meaningless.
>
> **WHAT THIS EXPOSED, and how it was closed — the two corrections in order,
> because each one falsified the sentence before it.**
>
> As first written this note said: the deployment has **no authentication and
> no rate limit**, and now no opt-in either, so **any caller can trigger paid
> work by uploading a document that collapses**. Two rounds of review found
> that claim wrong twice, and in opposite directions.
>
> **CORRECTION 1 — 2026-08-27, PR #61 R1.** No upload was needed at all.
> `intc-2025` (coverage 0.0033) and `xref-index-collapse` (0.0303) both fire
> the trigger and were both in the deployed dropdown, so one click did it, and
> `?fixture=intc-2025&run=1` did it on PAGE LOAD, because the deep link ends
> `$("#go-fx").click()`. `fixtures.DEPLOY_EXCLUDED` is a named set the
> deployment neither LISTS nor RESOLVES: `_fixture_file` refuses an excluded
> name in the same words an unknown one gets, because an exclusion that only
> shrank the menu would be cosmetic while the deep link and a hand-written
> POST both name a fixture directly. Both stay EVAL fixtures —
> `list_fixtures`/`iter_fixtures` and therefore the oracle, the bench and every
> case are untouched — and D1's invariant is re-pinned to the new relationship
> (deployed = eval corpus minus the named set) rather than edited to pass.
> Bound by `evals/adversarial/deployed-fixture-exclusion.json`; transcripts in
> `tasks/reviews/pr61-r1-red.txt`.
>
> **CORRECTION 2 — 2026-08-28, PR #61 R10, and it falsified correction 1's own
> closing sentence.** That sentence read "an upload is now the only route", and
> it was not. `POST /api/extract/url` accepts any
> `https://www.sec.gov/Archives/…` URL and reached the same `_run` with
> escalation on — and `intc-2025` is a real Intel EDGAR filing whose own
> Archives URL still billed. Excluding committed fixtures could never have
> fixed that: extracting arbitrary EDGAR URLs is the FEATURE, so every
> collapsing filing on EDGAR was a paid call for an anonymous caller. Four
> places said an upload was the only route and all four were false.
>
> **LOCK 4 — THE DOOR — WITHDRAWN 2026-08-28 by
> [ADR-041](ADR-041-escalation-open-by-default.md), the day it shipped.** The
> door was closed to every human who would actually open the deployment:
> `index.html`'s four `fetch()` calls never sent `X-Escalation-Token` and no
> field collected one, so the only interface the service advertises could not
> reach the paid tier for anyone, the owner included. ADR-041 deletes
> `gate.py`, the variable and the header, ACCEPTS R10's exposure as the price
> of a demo an interviewer can open, and leaves the process `Budget` as the
> only money bound. **The rest of this block is what lock 4 said while it
> stood, kept because a withdrawn decision with a stated reason is worth more
> than a deleted one — read it as history, not as current behaviour.**
>
> ~~**LOCK 4 — THE DOOR (owner decision, 2026-08-28: "close it at the
> door").**~~
> `src/sec10k/web/gate.py::paid_path_open` is consulted ONCE, in `_run`, which
> is the single point fixture, upload and URL converge on and the only caller
> of `extract_items` in the web layer. Escalation runs only for a request
> presenting a valid `X-Escalation-Token`; the operator's off-switch is folded
> into the same decision. **Unset is CLOSED, not open**: with no
> `SEC10K_ESCALATION_TOKEN` on the host — or one shorter than
> `MIN_TOKEN_CHARS` — the paid tier is unreachable by everyone, so a forgotten
> variable makes the demo free rather than free to bill. **Deterministic
> extraction is untouched**: it stays open, unauthenticated and $0 on all three
> routes, and when the door does not open the envelope publishes
> `escalation.reason` and the page prints it, rather than going quiet.
>
> Bound (while it stood) by `evals/adversarial/escalation-door.json`, which
> IMPORTED `gate.py` and ran the decision table rather than reading its shape —
> `gate.py` was stdlib-only for exactly that reason — plus
> `evals/adversarial/escalation-door-open.json` for the miss. **Both cases are
> replaced by `escalation-choke-point.json` / `-evaded.json` under ADR-041**,
> which keep every assertion below and drop only the header table. The choke point
> is pinned as a property, not a line: exactly one `extract_items` entrance,
> inside `_run`, escalating and billing on the SAME name. PR #61 R13 is why —
> a guard counted as one literal in one function is a guard the next endpoint
> walks around.
>
> **Dated note, 2026-08-28 (PR #61 R23, `tasks/reviews/pr61-r4.json`).** That
> sentence is true of the choke point and NOT of the call's arguments. The
> first-operand check binds `headers.get`'s arity, its object and its name, but
> not the expression around it: `(request.headers.get(gate.HEADER) or
> gate.configured_token())` satisfies all four assertions and hands an
> anonymous request the deployment secret, with invariant at a perfect 86/86.
> **The ceiling, stated rather than implied: these pins catch accidental
> regression, not a deliberate edit by someone with commit access, and no AST
> pin over `app.py` can — it imports fastapi and cannot be imported by the
> no-install CI jobs (ADR-003), so its call site is reachable only by shape.**
> The shipped door is correct and was driven against a counting listener four
> times; this is a gap in the check, not a live exposure. Carried as TD-163,
> whose upgrade path is the only thing that closes the class for real:
> exercising the call site with real calls in the CI `unit-tests` job, where
> dependencies are installable.
>
> **What the door does NOT close, stated because the previous version of this
> paragraph was the thing that went stale.** The FREE tier is still open to
> anyone: no rate limit, no request cap, a 25 MB upload ceiling, and a large
> filing costs real CPU and memory. That is a denial-of-service and
> hosting-cost surface, not a billing one, and it is `TD-162`. *[Dated note,
> 2026-08-28 (D15, ADR-040): TD-162 was promoted and closed the same day —
> the free tier now has a GLOBAL per-process request limit (token bucket,
> burst 20 / 30 per minute by default, bounded env config) at one
> `@app.middleware("http")` choke point, refusing over-limit requests with
> 429 + `Retry-After` before any endpoint body runs; the measured cost that
> sized it: one ~25 MB request ≈ 1.13 s CPU / 138 MB peak RSS. "Open to
> anyone" still holds — the limit bounds RATE, not access, and the door
> itself still deliberately carries no rate limit of its own: the token is
> that path's brake, and since D15 the shared free-tier limiter additionally
> sits in front of every extract request, token or not.]* Behind the door,
> the process `Budget` still bounds a token holder and still **resets on every
> redeploy**, so "spent" is a state a push undoes; the credit limit on the
> OpenRouter key remains the only ceiling that survives one, and should be set
> as if it were the only one. `TD-158` — auth or a rate limit on the escalating
> path — is CLOSED by this lock rather than narrowed.

PR #58 R6 and R12, and the reason they were repaired rather than disclosed: the owner is
putting a credential on a **public, unauthenticated** Zeabur deployment whose
three extract endpoints all accept an `escalate` flag, and whose only existing
limit is a 25 MB upload cap. With a key present and nothing else changed, an
anonymous caller could upload collapsed filings and drive opus-class calls
until the account ran dry — and nothing bounded aggregate spend, because
`route()` builds a fresh per-document `Budget` and no caller passed one.

**Lock 1 — a credential alone never arms paid work.** *(Superseded
2026-08-27 by the owner note above: the variable's sense is INVERTED and the
default is now ON. The reasoning below is kept because it is what makes the
off-switch a separate variable rather than a truthiness check on the key, and
that part is unchanged.)* The server refuses to
escalate unless `SEC10K_ESCALATION_ENABLED=1` is *also* set. Deliberately a
second variable rather than a truthiness check on the key: the key arrives for
its own reasons, and "a key exists" must not mean "spend it". Verified with a
key exported and the variable unset — `escalation_enabled: false`, no routing
record, `cost` all zeros.

**Lock 2 — one process-wide ceiling, not one per document.** `web.app`
constructs a single `Budget` (`SEC10K_ESCALATION_MAX_CALLS`, default 20;
`SEC10K_ESCALATION_MAX_USD`, default $5.00) and passes it to every
`extract_items` call, so the bound is on the DEPLOYMENT. Verified: with the
ceiling set to one call, request 1 attempts a tier and requests 2 and 3 come
back `outcome: "unavailable"`, `"budget spent: 1 of 1 calls used"`. It does not
reset on its own; restarting the process is the deliberate act that refills it.

**Lock 3 — both rungs' inputs are capped, so one call's price is bounded on
arbitrary input.** Added 2026-08-27 (PR #58 R12), and it is the difference
between a ceiling and a suggestion. `Budget` refuses only once spend has
*already* reached `max_usd` (§d3), so the true bound is always MAX_USD plus one
call's own price — and rung 2 used to send the WHOLE document, which on this
deployment is attacker-supplied and capped only by `MAX_BYTES` (25 MB). A
~4M-char upload was a single ~$5.00 call takeable at spent=$4.99, roughly
doubling the configured ceiling. Rung 2's input is now capped at
`EXTRACT_WINDOW = 1,250,000` chars — the largest committed dev filing rounded
up, so no dev document is truncated and no figure in §d moves — which caps one
rung-2 call at an estimated **$2.4697**.

**So the effective deployment ceiling is `SEC10K_ESCALATION_MAX_USD` + $2.4697,
i.e. $7.4697 at the default $5.00**, not $5.00. It is stated that way here
rather than as MAX_USD alone, and `tasks/reviews/d11_sweep_cost.py` prints it
so the two cannot drift. Truncation is never silent: each tier record publishes
`input_chars` and `truncated`, so a resolution over a clipped document says so.
What this still does not bound is a document whose real content sits past
1.25M chars — rung 2 cannot resolve it at all. Debt row, with the upgrade path
(cap on projected cost once the first live run supplies real token counts,
which closes §d3's overshoot in the same move).

**And the refusal is never silent, which is the whole milestone.**
*(SUPERSEDED 2026-08-27: there is no box, so there is no ticked box to ignore
and no `escalation_disarmed` message — the server stopped emitting it. What
replaced this paragraph's three pinned hops is their mirror: six ABSENT-pins
in `routing_provenance` forbidding the control, the helper, the flag on any
wire, the arming round-trip and the dead refusal note from creeping back, and
`routing-strip-missing.html`'s shape 1 is now "the control comes back, whole",
worth six of its eleven failures. `/api/meta` still publishes
`escalation_enabled` — almost always true now — so the deployment stays
inspectable without a control on the page, and the routing strip is where a
viewer learns a paid tier ran and what it cost. The original text follows.)*
An unarmed
deployment does not quietly ignore a ticked box. `/api/meta` publishes
`escalation_enabled`, the page disables the control and says why, and any
request that asked anyway comes back with an `escalation_disarmed` message
rendered above the banner. Three hops, three pinned expressions, and a
7th mutation shape in `routing-strip-missing.html` whose whole content is "the
box is offered unconditionally" — the dishonesty this row exists to remove,
wearing the costume of a working feature.

**Neither of the two `web.app` locks touches a local run**, and the third
touches every run. Corrected 2026-08-27 (PR #58 R23): this paragraph said
"neither lock" under a heading that had just become three, and the third is not
a `web.app` lock at all. Locks 1 and 2 live in `web.app`, so the eval suites,
`python3 -m src.sec10k.escalate` and a direct `extract_items(..., escalate=True)`
bypass them entirely and a developer who exports both variables gets the tier
with the default per-document budget. **Lock 3, the input cap, is applied inside
`escalate.route` and therefore applies to every one of those paths** — which is
the point: a bound that only guarded the deployment would not bound a sweep, and
`route` is the single place all callers pass through.

**What is still not bounded**, said plainly: there is no authentication and no
rate limit on the deployment, so an anonymous caller can still consume the
process budget — denying the capability to everyone else — and can still cost
CPU. The locks bound *spend*, which is the irreversible resource; availability
is not bounded and is a debt row. *[Dated note, 2026-08-28 (D15, ADR-040):
that debt row, `TD-162`, is now closed — a global per-process token bucket on
every `/api/extract/*` request bounds the arrival rate (and with it CPU and,
behind the door, how fast a token holder can consume the process budget);
"no authentication" still holds, and one hammering client can still exhaust
the SHARED bucket for everyone on the instance until the window refills —
that ceiling is recorded, with the sizing and the per-IP rejection, in
ADR-040 §b.]* **Widened 2026-08-27 by the owner note at
the top of this section**: with the opt-in removed, that caller no longer has
to find or tick anything, and the process budget they consume refills on every
redeploy. **Narrowed the same day (PR #61 R1)**: they must now bring their own
document, because the two committed fixtures that fire the trigger are neither
listed nor resolvable on the deployment. The credit limit on the OpenRouter key is the brake that does not.

## h4) The exam ran, was billed, and broke the client (2026-08-27)

The first held-out run this repo has ever paid for. `intc-2025`,
`escalate=True`, **$0.899858 over 2 calls**, `resolved: []`.

The deterministic half was right — coverage 0.0033, `doc_status` `ambiguous`,
items 1/7/8 flagged, D8's trigger fired. Rung 1 was right too: valid JSON
`{"1": null, "7": null, "8": null}`, honestly reporting it could not locate
those items in its window. **Rung 2 was the bug**: `completion_tokens: 2048` —
exactly the `max_tokens` sent — with empty content, which reached `json.loads`
as an unexplained `JSONDecodeError`.

**Root cause, from OpenRouter's documentation and not from inference.** It
documents a `reasoning` request parameter taking `effort` OR `max_tokens`, and
states that **for Anthropic models `max_tokens` must be strictly higher than
the reasoning budget to ensure there are tokens available for the final
response after thinking**. We sent 2,048 and no reasoning budget to a reasoning
model; the allowance went entirely to thinking. This also corrects §h1, which
claimed OpenRouter's chat-completions surface "has no equivalent" of a
reasoning knob — it has one, and not sending it is what cost $0.90.

**Three changes.** (1) The split is now EXPLICIT and per rung:
`MAX_TOKENS` (2,048) is the answer, `REASONING_TOKENS` (4,096) is the thinking,
and a reasoning rung is called with their sum plus
`reasoning: {"max_tokens": …}`. `openai/gpt-5-mini` is deliberately left
unchanged — it answered correctly at 842 output tokens with no reasoning budget,
and altering a rung that demonstrably works, on provider behaviour this repo
cannot test without spending, is the unverified change this PR has been burned
by repeatedly. (2) The client RECORDS `finish_reason` and `max_tokens` in the
cached record. OpenRouter normalizes `finish_reason` to
tool_calls/stop/length/content_filter/error, and `length` is the documented
signal that the limit was reached — so an exhausted allowance is **detectable**
rather than reconstructed from arithmetic, which is how this one had to be
diagnosed. (3) An empty completion is its own routing outcome,
`empty_completion`, carrying the numbers that identify it, recorded with its
COST — a call that was billed and produced nothing must still report as billed.

**MEASURED 2026-08-28 (D17 deliverable (b), `tasks/reviews/d17-intc-measurement.txt` RUN 2): change (1) does NOT achieve its purpose on `intc-2025`, and this paragraph's inference was wrong.** The fixed ladder was run against the same filing with a real credential: rung 2 was billed **$0.997760** and returned `empty_completion` AGAIN — `finish_reason: length`, `output_tokens: 6144` of `max_tokens: 6144`, `reasoning: {"max_tokens": 4096}`, empty text. OpenRouter's documented rule is satisfied (6,144 > 4,096) and the failure reproduces identically, so tripling the allowance moved the failure rather than removing it, and "raising the answer allowance is nearly free" is true of the PRICE and false of the OUTCOME. Changes (2) and (3) are vindicated in the same run and are the only reason this is legible rather than another unexplained `JSONDecodeError`. The residual is carried as **TD-165**; the response is committed to `evals/cache/llm/` so the finding replays at $0.00. **Amended again 2026-08-28**: change (2)'s principle is now applied to the field this run needed and did not have. `_normalize` was dropping `usage.completion_tokens_details.reasoning_tokens` — the ONLY field separating "the cap was not enforced and thinking consumed the allowance" from "it was, and the answer was truncated", which `finish_reason: length` reports identically. It is now recorded (`None` when the provider omits it, never `0`) and pinned in `llm.py::_demo`, so the next paid attempt is diagnostic rather than a repeat. TD-165 carries the pre-declared stop rule: one further paid attempt at most, only once a run carries that field, and a second all-thinking result rules the A1 collapse class out of this ladder's reach in an ADR rather than buying a third ceiling.

**On cost, the counter-intuitive part.** Of the $0.895360, only **$0.0512** was
output; **$0.844160** was input, paid whatever came back. So raising the answer
allowance is nearly free, and *not* raising it means paying the input for a
guaranteed empty answer. The cost-discipline move here is UP. Every §d figure
was re-derived on the new ceilings and all of them rose.

**What this did NOT establish.** `escalate.verify` has still never met a real
model answer. The exam tested the transport and found it broken before the
trust boundary was reached — so §b's five checks remain unexercised against
anything a model actually produced, and §k's list is unchanged on that point.
The evidence is kept as `evals/adversarial/escalation-empty-completion.json`,
which replays the exact cached payload at $0.

**The burn.** Fixing the client is shipping code in response to a held-out
outcome, so `intc-2025` is burned and moved to the dev side; the owner ruled
the burn is taken rather than argued around, and declined a second amendment to
the rule. `evals/heldout/README.md`, Burn 2026-08-27, carries the accounting.
**D11's surviving exam is one filing.**

## h5) The token proxy was wrong, per model, in both directions (2026-08-27)

Every dollar figure this ADR publishes is derived through a chars-per-token
proxy, and nothing checked that proxy against reality until the two held-out
exam runs billed four real responses. It was a retyped `4` for both rungs.

| model | measured chars/token | what `4` did |
|---|---|---|
| `anthropic/claude-opus-5` | 3.0740 (`intc-2025`), 2.7395 (`c-2025`) | **UNDERSTATED tokens by up to 1.46×** |
| `openai/gpt-5-mini` | 5.4195 (`intc-2025`), 4.2663 (`c-2025`) | overstated them |

**It is not one multiplier — it is per model, and the two rungs err in opposite
directions.** Both of the orchestrator's data points happened to be rung 2,
which is why the error first looked like a single 1.46× correction.

The understatement is the one that cost money. §h2 published a worst-case single
call of **$1.5675** while a real `c-2025` rung-2 call on a *larger* input had
already been billed **$2.12163**; the per-document `Budget` of $1.00 was
overshot to $2.13 — which is the disclosed "ceiling plus one call's own price"
behaviour of §d3, except that the disclosed price was wrong.

**The correction.** `chars_per_token(model)` in `tasks/reviews/d11_sweep_cost.py`
reads `tasks/reviews/2026-08-27-token-ratio.json` and returns the **minimum**
observed value for that model, floored to 1 dp — 2.7 and 4.2. Minimum, because
fewer chars per token means more tokens for the same text, so it is the end that
cannot understate a price. No number is retyped anywhere;
`evals/adversarial/token-proxy-bound.json` pins the function against the record,
in the conservative direction only, and refuses to pass if any rung's model has
no sample.

**How thin this is, said rather than implied.** Two samples per model. Both
documents are SEC filings in HTML-derived normalized text, so nothing here says
what the ratio would be on another corpus. One of the four is derived from the
code path rather than measured, and its only effect is to *lower* the bound —
it can make costs more conservative, never less. OpenRouter documents no
tokenizer endpoint (checked 2026-08-27): token counts come back only as a
byproduct of a billed completion, so a proxy is unavoidable and can only be
measured and bounded. This is a bound, not an estimate, precisely because two
points cannot support an estimate.

**`EXTRACT_WINDOW` is kept at 1,250,000 on a premise that has changed.** It was
chosen when the bound it produced was believed to be $1.5675; the corrected
proxy puts it at $2.4697. It is not re-tuned to chase the old figure, because
that figure was never the requirement — "bounded on arbitrary input" was, and it
still is — and shrinking it to ~844,000 chars would truncate `jpm-2024`, giving
up the property that justified the number to preserve a number that was wrong.
The levers for a smaller ceiling are the documented ones: lower
`SEC10K_ESCALATION_MAX_USD`, or build §d3's projected-cost pre-check. Both are
the operator's call.

## h3) The seam — the gate stays offline and $0, and it is measured

`requirements.txt` is unchanged (`fastapi`, `uvicorn`). No `pip install` runs
in CI. The client is stdlib `urllib.request` + `json`, not the `anthropic` SDK,
because the pipeline and the eval harness must stay importable with zero
third-party packages (ADR-003).

`escalate.route` imports `llm` **inside the function**, so importing the
extractor loads no network module. `escalation_seam` checks this **dynamically**
— a subprocess imports `src.sec10k.extract`, `src.sec10k.eval_adapter`,
`src.sec10k.escalate` and `evals.run`, then reports `sys.modules`; any of
`urllib.request`, `urllib.error`, `http.client`, `socket`, `ssl`, `requests`,
`httpx`, `anthropic`, `openai` in that set fails. A static read of import
statements could not see a transitive one, which is why it is measured. Two
vacuity guards: `llm.py` must exist and must itself import `urllib.request`,
and nothing under `src/` or `evals/` may import `llm` at module scope — hoisting
that one line is the edit that would break the seam while every other check
stayed green.

Belt and braces on the money: `src/sec10k/eval_adapter.run_case` removes
`OPENROUTER_API_KEY` from the environment for the whole of every sec10k case,
restoring it after. So a case declaring `escalate: true` behaves identically on
a machine with a credential and one without, and the `fast` suite makes zero
paid calls **by construction** rather than by convention (cost-discipline
rule 4). `evals/bench.py`'s own no-network AST self-check is untouched.

Caching (cost-discipline rule 2): every response is keyed on
`sha256(PROMPT_VERSION, model, system, user, max_tokens)` under
`evals/cache/llm/`, checked **before** the budget and before the credential, so
a re-run of a live eval costs $0 and needs no key. `PROMPT_VERSION` is part of
the key, so a reworded prompt cannot be answered from an old response. The
cache directory is committed (with a README) rather than ignored, so a future
`full` suite is reproducible offline — it is empty today because nothing has
been called.

## i) Routing is user-visible, never silent

**The envelope.** `routing` is an optional key on the ADR-026 terms — present
exactly when `escalate=True` — carrying `trigger` (fired, codes, the flagged
items, the trigger warning's own message), `tiers` (one record per rung
attempted: tier, model, items, outcome ∈ `resolved`|`rejected`|`unparseable`|
`unavailable`, its cost, whether it came from cache, and — on a rejection —
`verify`'s reasons in full), `resolved`, and the summed `cost`. Three
consistency properties `envelope_shape` **re-derives rather than trusts**: the
record's cost is the sum of its tiers' costs; the envelope's top-level `cost`
equals it; and `resolved` names exactly the items whose `method` is an
escalation method. A published price a consumer cannot re-derive is the
undisclosed-cost failure this milestone exists to close, and the PR #57 R1
lesson — a hard-coded `meta.coverage` passing every band pin — is why these are
recomputed.

**Per item.** The tier rides the existing `method` field the sidebar and the
pane header already print as `via …`, and `evidence.deterministic` holds what
the $0 path said. `envelope_shape` refuses an item claiming an escalation
method on an envelope with no routing record.

**The inspector.** A banner strip (`routingStrip`) prints the doc-level record,
distinguishing three states that are genuinely different: no record at all
(escalation was never asked for), a record with `fired: false` (asked for, and
the deterministic answer needed no help — this is the $0 claim, on screen), and
a fired trigger with each tier's outcome, its error verbatim when it has one,
and the money. The pane's evidence list gains a `tier` row naming the method
and what it replaced. The `escalate` checkbox ships **unchecked** (a paid tier
is never the default) and **not disabled** (a wire nobody can reach is not a
capability) — the pair `ui-boilerplate-wire-values` had to add for ADR-026's
flag after a mutation passed with the box permanently off.

**What the UI pins do and do not prove.** They are TEXT PINS over one file, and
`check_confidence_honesty`'s docstring — written after two rounds of that pin
being falsified inside review — applies here word for word. A green
`ui-routing-provenance` asserts the pinned expressions are present and unique
in `index.html`. It does not assert a browser renders them, and no static read
of one file could. **There is no browser walk backing this row**, unlike D7 and
D10, because the state worth looking at — a document that actually escalated —
cannot be produced without a credential.

## j) Smaller rulings, each because someone will ask

* **`llm_fallback` stays declared and unemitted.** It was ADR-020's name for
  the unconditional fallback that never shipped. Reusing it for a triggered
  tier would make an old consumer's switch mean something it never meant. Two
  new values instead.
* **`status` does not change on a resolved item.** ADR-004/005 answer "what did
  the filing do with this item", and a tier moving a span does not change that
  answer. The same reasoning ADR-035 §e gave for not adding a fifth status.
* **The ladder stops at the first `EscalationUnavailable`.** With no credential
  there is no point asking rung 2; the routing record shows one tier attempted
  and says why. A `rejected` or `unparseable` answer does continue to the next
  rung — that is a rung failing, not the ladder being unavailable.
* **No reasoning-effort knob is sent at all.** The Anthropic client this
  replaced set one; OpenRouter's chat-completions surface has no equivalent, so
  it was dropped with the transport rather than mapped onto a different
  provider's different concept (§h1). `llm._body` returns exactly
  `{model, max_tokens, messages}`, and `llm._demo` asserts that shape. Amended
  2026-08-27 — this bullet previously published the dropped knob as a live
  ruling, contradicting §h1 in the same document (PR #58 R11).
* **The item-level hint is the flagged set, and falls back to every spanned
  item** when `low_item_coverage` fired with no `item_span_near_empty` beside
  it — possible on a document whose items are all short but none of them 1/7/8.
* **The dev escalation proxies are `xref-index-collapse` (A1) and the
  `cvx-2015`/`jpm-2024` pointer class** (as the ledger row directs). No
  synthetic reorg fixture was needed: `xref-index-collapse` already is the
  collapse shape, red-first at D8.

## k) What is NOT done, and must not be read as done

**THE HELD-OUT EXAM RAN ON BOTH FILINGS AND THE LADDER RESCUED NEITHER.
D11's acceptance criterion — "the slow path completes the D6 filings it never
trained against" — is NOT MET.** Stated flatly because softening it would be
the dishonesty this whole milestone is about.

| | cost | outcome |
|---|---|---|
| `intc-2025`, 2026-08-27 | $0.899858, 2 calls | `resolved: []`. Rung 2 returned empty content: the CLIENT was broken (§h4). Burned by the fix it exposed. |
| `c-2025`, 2026-08-27 | $2.125834, 2 calls | `resolved: []`. Rung 1 `rejected`; rung 2 **worked** and returned parseable `{"7A": null}` — an honest "cannot locate". Not burned. |

**$3.025692 of real money, and no item resolved on either filing.**

**RE-RUN 2026-08-28 AGAINST THE FIXED LADDER (D17 deliverable (b)), and the
answer is still no.** `intc-2025` was run again with the §h4 fix in place:
rung 1 replayed from cache at $0.00 and still localizes nothing; rung 2 was
billed **$0.997760** and returned `empty_completion` a SECOND time, on the
tripled allowance the fix introduced (§h4's dated note carries the numbers).
Running total **$4.023452 of real money, still no item resolved on any
held-out filing.** D11's acceptance stays NOT MET, and the rung-2 half of
hole 2 below is now MEASURED rather than outstanding: the ladder does not
merely go untested on this filing, it demonstrably fails on it. The residual
design question is TD-165. `escalate.verify` STILL has not been handed a real
bad answer — no answer arrived — so that hole is untouched by this run, and
D17 (a) closed it against synthetic bad answers only.

What the exam DID prove, which is not nothing:

* **D8's trigger fired correctly on both unseen filings** — `intc-2025`
  coverage 0.0033, `c-2025` coverage 0.0 — which is the sensor §c is about,
  working on documents it had never seen.
* **Rung 1 answered honestly and cheaply on both** ($0.004498, $0.004204),
  returning `null` for items it could not locate rather than inventing spans.
  That is the behaviour §b's prompt asks for and it is the cheap rung's whole
  job.
* **The transport works after the §h4 fix**, confirmed by a real call:
  `c-2025`'s rung 2 came back parseable with `finish_reason: "stop"`, outcome
  `rejected` and not `unparseable`.

And what it did NOT prove, which is the important half: **`verify` was never
handed a bad answer to reject.** Both models said "I cannot locate this"; neither
returned a wrong span. So §b's five checks — the trust boundary this design
rests on — remain untested against a real adversarial response. The ladder's
safety property is still only proven against constructed proposals.

`intc-2025` is now on the dev side (`evals/heldout/README.md`, Burn
2026-08-27), so **D11's surviving exam is `c-2025`, and it has now been spent
too — though not burned: the owner ruled its outcome fixes nothing.** The
paragraph below is the position as it stood before either run.

**The D11 ledger row defines success on held-out
— "the slow path completes the D6 filings it never trained against". That run
has not happened and cannot: `OPENROUTER_API_KEY` is not set in this
environment, and repo rule 4 forbids fabricating the result. The exam is
therefore **intact and unspent**, which is the one good thing about this
column being empty. `intc-2025` and `c-2025` were not read, not adjudicated and
not iterated against; the only held-out numbers in this document are the ones
ADR-035 §b4 already published, cited under the 2026-08-26 amendment that a
ruling citing an outcome is not influence.

**Four live calls have now been made across two exam runs, $3.025692 in total,
and they changed nothing about the trust boundary.** Every dollar figure is still an estimate (§d), now re-derived
on measured ceilings. No `verify()` has ever been run against a real model's
answer — only against
`_demo`'s constructed proposals, which test the checker and say nothing about
how often a real answer passes it. **`SIM_FLOOR` on check 6 (§b's numbering, which
`verify`'s docstring matches) may prove far too strict in practice**, in which case every escalation returns `rejected` and the
ladder is an expensive no-op; that is the single most likely way this design
fails, it is not detectable without a credential, and it is why the rejection
reasons are published in full.

**No browser walk** (§i). **No vision rung** (§e). **A2 remains unreached**
(§c3). **The `Budget` dollar ceiling can be overshot by one call's own price**
(§d3). **Rung 1's slug is a judgement, not a measurement** — whether
`openai/gpt-5-mini` can actually do exact offset arithmetic over a 60,000-char
window is unknown, and if it cannot then rung 1 is pure waste that always
escalates to rung 2 (§d). **The deployment has no authentication and no rate
limit** — the §h2 locks bound spend, not availability (§h2's closing
paragraph) — **and as of 2026-08-27 it also escalates by default, so any
caller can trigger paid work with one upload and no opt-in** (§h2's owner
note; the process budget is the bound and a redeploy refills it).

> **Amendment, 2026-08-28 (D17).** The two holes this section opens are now
> narrower, and one is closed. **(a) The trust boundary is exercised by a
> committed adversarial battery**: `evals/adversarial/escalation-verify-battery.json`
> (17 sub-cases against xom-2021's real items — out-of-bounds, sub-`SPAN_FLOOR`,
> wrong-region and mid-paragraph offsets, INV-S1 overlaps between existing and
> proposed siblings, malformed shapes, mixed-proposal all-or-nothing, with the
> item list deep-compared byte-untouched after every sub-case) and
> `evals/adversarial/escalation-route-parse.json` (6 crafted transport texts
> through `route`'s real parse path), both fast+invariant, red-first with an
> 8-mutation matrix (`tasks/reviews/d17-red-first.txt`). One **genuine gap**
> was found and fixed in the same PR: JSON booleans — `isinstance(True, int)`
> is True, so `[true, N]` passed §b check 3's shape test and was ACCEPTED
> whenever the coerced `[1, N]` verified, and `route`'s `int()` coercion
> laundered the bool into a plausible offset before `verify` ever saw it.
> Both entry points now reject booleans; floats and digit strings were probed
> and ruled benign coercion, recorded rather than "fixed". This closes the
> "only constructed proposals" half of the hole; whether a REAL model's
> answer ever passes `verify` still needs a credential.
> **(b) The intc-2025 measurement was attempted against the fixed ladder**
> (`tasks/reviews/d17-intc-measurement.txt`, runner `d17_intc_measurement.py`,
> hard $5.00 pre-call cost gate built per §d3 and self-checked): rung 1
> replayed its committed real response from cache at $0 — the cache hit
> itself proving §h4 changed nothing about rung 1's request — and still
> localizes nothing; rung 2's post-fix request is a new cache key and needs a
> live call, and the run recorded the loud refusal: **still unmeasured —
> credential absent in the delivery environment, refused loudly, $0.000000
> spent, envelope untouched.** The one open question of this section is now
> exactly one billed call wide (projected $1.114685 by the committed
> price/proxy records).

## l) Falsifiers

| Ruling | What would falsify it | How to check | Cost of the check |
|---|---|---|---|
| `low_item_coverage` is the right trigger | it fires on a real filing that is NOT collapsed (a false positive), or a held-out collapse does not fire it | re-run `tasks/reviews/d11_trigger_scan.py` after any fixture expansion; the held-out run when a credential exists | $0 / one exam |
| The ladder is worth its price | the held-out run shows rung 2 resolving nothing that rung 1 did not, or `verify` rejecting every real answer | the held-out run, reading `routing.tiers[*].outcome` and `rejections` | one exam + ~$0.2 |
| Scanned input stays out of scope | a committed text-less 10-K fixture appears, or a user brings one | `d11_trigger_scan.py`'s "refused before any item exists" line, plus the fixtures README | $0 |
| Escalation is free by default — the LIBRARY default, `extract_items(path)`; the DEPLOYED service has escalated by default since 2026-08-27 (§h2) and is not free | any default-flag run reports a non-zero `cost`; or the web layer's default-on leaks into `extract_items`' own signature | `evals/snapshot.py`, and the `escalation-trigger-quiet` case's `usd: 0.0` | $0 |
| The gate stays offline | any network module appears in a gate import | `escalation-seam-offline`, every run | $0 |
| A model cannot move a span it should not | a fabricated offset passes `verify` | attack `escalate._demo`'s proposals; the live run's `rejections` list | $0 |
| A2 stays declined | someone adjudicates the pointer-bodied-item-7/8 class as a defect | a decision, not a measurement | §d4's $9.6754/sweep, 7.2× (derived by `tasks/reviews/d11_sweep_cost.py`) |
