# ADR-036 — D11: the model tier ships, but only behind the D8 document-level trigger, and it is never trusted without a deterministic re-check

Date: 2026-08-26. Status: accepted, **with one part of its acceptance criteria
UNRUN and said so in §k**. **Supersedes
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

**Ruling**: four decisions. (1) The ladder is `deterministic → llm_localize (small model, unattributed text only) → llm_extract (large model, whole document)`, entered **only** when `low_item_coverage` fires, opt-in behind `escalate=True`, and no rung's answer is used until `escalate.verify` re-derives its offsets against the deterministic output (bounds, `SPAN_FLOOR`, INV-S1 ordering, and a `SIM_FLOOR` heading match). (2) **Text-less / scanned filings stay OUT of scope** and the README row is re-affirmed, so **no vision rung is built** (§e). (3) The envelope publishes a `routing` record and two new `method` values, and the inspector renders both. (4) With no `ANTHROPIC_API_KEY` the slow path **refuses loudly** — a `routing` outcome of `unavailable` plus an `escalation_unavailable` warning — and never degrades silently.
**Because**: measured over all 43 dev filing fixtures, `low_item_coverage` fires on **1 of 43 (0.0233), and on 0 of 28 real EDGAR filings**, so the ladder's default cost is exactly $0.00 and the whole dev corpus escalates for an estimated $0.056; the item-level `item_span_near_empty` fires on 12 of 43 (9 of 28 real) and is deliberately NOT the trigger, because escalating on it would spend money on the A2 class ADR-034 §e2 declined and put the dev escalation rate at 27.9%.
**Enforced by**: `evals/adversarial/escalation-trigger-quiet.json` and `evals/adversarial/escalation-no-credential.json` (fast + invariant), `evals/adversarial/ui-routing-provenance.json` + `evals/adversarial/ui-routing-provenance-regression.json` (its 7-failure mutation fixture `evals/fixtures/repo_hygiene/routing-strip-missing.html`), `evals/adversarial/escalation-seam-offline.json`, `src/sec10k/escalate.py::_demo`, `src/sec10k/llm.py::_demo`, `src/sec10k/web/view.py::_demo`, `src/sec10k/eval_adapter.py::_routing_shape` + the `routing` / `escalation_invariant` check types. Red-first record with its sha: `tasks/reviews/d11-red-first.txt`. Measurement: `tasks/reviews/d11_trigger_scan.py`.

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
| Therefore no fallback ships | **No longer true**, and this is the whole change | Two things arrived after 2026-08-19 that ADR-020 could not have measured: the 2026-08-24 demo, where two real filings (Intel, Citigroup) collapsed onto cross-reference index rows and were reported at `conf 0.95`; and D8's `low_item_coverage`, a **measured, document-level, zero-false-positive** signal for exactly that shape. ADR-020's argument was "no fallback ships *unconditionally*, because there is no gap worth the money". The gap is now identified, and — critically — so is a trigger that costs nothing on 42 of 43 dev documents. |

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
   │     … `low_item_coverage` in warnings?  no → STOP. This is 42/43 dev documents.
   ▼
rung 1   llm_localize         claude-haiku-4-5, input = the largest UNATTRIBUTED
   │                          region only, capped at 60,000 chars
   │     … verify() accepts the answer?      yes → STOP.
   ▼
rung 2   llm_extract          claude-opus-5, input = the whole normalized text
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

1. the code must be an item of this document — a rung may not invent one;
2. `0 <= start < end <= len(normalized_text)` (INV-S2);
3. `end - start >= SPAN_FLOOR` (1,500) — resolving a stub to another stub is
   not a resolution, and `SPAN_FLOOR` is the constant D8 already measured for
   precisely this question (ADR-035 §b1);
4. the item list, **after substitution**, is still disjoint and in ascending
   offset order — the same property `no_overlap_ordered` asserts (INV-S1);
5. the span must open with something that reads like this item's heading, by
   the same `title_similarity` / `SIM_FLOOR` cut `find_candidates` uses to
   accept a heading in the first place.

Check 5 is the one that matters most and the one to attack. It means a
hallucinated offset does not merely have to be plausible — it has to land on
real heading text that the deterministic segmenter would itself have accepted
had it looked there. `escalate._demo` pins the hallucination shape directly: a
long, in-bounds, correctly-ordered span pointing at the document's tail is
rejected on similarity, not on luck.

**All-or-nothing.** Either every proposed span survives or none is used.
Stricter than necessary, and deliberate: checks 4 and 5 are properties of the
item list as a whole, and partial application makes the failure mode "some
items moved and the ordering held by accident". Carried with its upgrade path
in a `ponytail:` comment in `verify`'s docstring.

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

| code | fires on | of all 43 | of 28 real filings |
|---|---|---|---|
| `low_item_coverage` (doc-level, escalating, ADR-035 §d) | `xref-index-collapse` | **1/43 = 0.0233** | **0/28 = 0.0000** |
| `item_span_near_empty` (item-level, non-escalating, ADR-035 §c) | 12 fixtures, 17 item hits | 12/43 = 0.2791 | 9/28 = 0.3214 |

The 12: `cvx-2015`(7,8), `fy2021-item9c`(8), `ge-1994`(8), `ibr-pointer-first`(8),
`jpm-2024`(7,8), `ko-1997`(8), `nvda-2024`(8), `reac-2015`(8),
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
   "dev escalation rate stays near zero so the default cost stays $0". 0/28 on
   real filings is near zero. 9/28 is not.
3. **It would spend money on a class ADR-034 §e2 DECLINED.** The nine real
   filings `item_span_near_empty` hits are the A2 class — a few pointer-bodied
   items inside an otherwise well-extracted filing — which D9 declined
   precisely because "two independent reads still disagree that it is a
   defect". Building a paid capability to fix something not agreed to be
   broken is the shape ADR-026 §a's test exists to catch.

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

**And now the sentence that matters more than either number.** The dev
positive set has **size one and is synthetic**. A precision and recall of 1.000
over n=1 is not evidence of generalization; it is evidence that the one case
the fixture was built for is caught. The real evidence for this sensor would be
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
* **"Declined" stands, and its stated reason is amended.** The correct reason
  is not "nothing reaches it" — something does — but "what reaches it is a
  non-escalating item-level flag whose class two independent reads still
  disagree is a defect, and D11 declines to spend money resolving a
  disagreement." That is a weaker reason than D9 published, and saying so is
  the point of this paragraph.
* **What would change it**, stated as its own falsifier: an adjudication that
  settles whether a pointer-bodied item 7/8 inside a well-extracted filing is a
  defect. If it is, A2 becomes a one-line change here (`TRIGGER_CODES` gains
  `item_span_near_empty`) whose measured price is in §d4 — and that is the
  whole reason the price is published.

## d) Cost — one measured input, one ESTIMATE clearly labelled

**The measured half.** The escalation rate is measured, deterministic and $0:
1 of 43 dev documents, 0 of 28 real filings.

**The estimated half, and why it is an estimate.** Nothing here has been
billed. Token counts come from a **4 characters ≈ 1 token** proxy over
`normalized_text`, not from `count_tokens` — which is itself an API call this
pass may not make — and prices are the 2026-06-24 table in `llm.PRICES`. Every
figure below is therefore an ESTIMATE and is labelled one everywhere it
appears, including in this ADR's own headline. `llm.call` records the
response's own `usage` and computes `usd` from it, so the first live run
replaces every estimate with a measurement, in the routing record, without a
code change.

### d1. Per-document estimate

| document | chars | rung 1 (haiku-4-5) | rung 2 (opus-5) | full ladder |
|---|---|---|---|---|
| `xref-index-collapse` (the only dev document that escalates) | 33,061 | ~$0.0093 | ~$0.0463 | **~$0.056** |
| median span-bearing dev filing | 102,529 | ~$0.0160 | ~$0.1332 | ~$0.149 |
| `bac-2006` (2nd largest) | 705,848 | ~$0.0160 | ~$0.8873 | ~$0.903 |
| `jpm-2024` (largest) | 1,213,284 | ~$0.0160 | ~$1.5216 | ~$1.538 |

Rung 1's price is flat above 60,000 chars because `LOCALIZE_WINDOW` caps what
it is shown — which is the point of having a cheap rung at all.

### d2. Per-corpus estimate

A full `escalate=True` sweep of all 43 dev filings costs an estimated
**$0.056**, because 42 of them stop at rung 0. A default-flag sweep costs
**$0.00**, measured, not estimated: no tier is reachable.

### d3. Where the budget does not hold, said plainly

`Budget` checks the dollar ceiling against what has **already** been spent, not
against what the next call is projected to cost, so one call can overshoot
`max_usd` by its own price. The measured worst case on the dev corpus is
`jpm-2024`'s rung 2 at an estimated $1.52 against a $1.00 default. The call
budget (`max_calls`, default 2) is a hard ceiling and is not affected. Carried
as debt with its upgrade path, in a `ponytail:` comment on `Budget.take` and a
row in the ledger.

### d4. The price of the trigger this ADR did NOT choose

Published because §c3's falsifier turns on it: routing on
`item_span_near_empty` as well would escalate 12 of 43 dev documents, including
`jpm-2024` and `bac-2006`, for an estimated **$3.4 per dev sweep** — roughly
60× the chosen trigger — to resolve a class ADR-034 declined. That number is
the argument.

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
   is unreachable. Measured: 4 of 43 dev documents refuse before any item
   exists (`aapl-2026-10q`, `amended-cover-2021`, `ksb-2007` as `unsupported`;
   `truncated-download` as `failed`). Admitting scanned input is therefore not
   "add a rung" — it is "make a refusal into a trigger", which is a different
   and much larger change.
2. **It would break the cost budget the same ledger row imposes.** If a
   refusal became a candidate for a paid OCR-class pass, then every truncated
   download, every mis-fetched page and every non-10-K form would be a
   candidate too — the classes are indistinguishable at the point of refusal,
   which is exactly why the contract tests collapse *before* form identity.
   The escalation rate stops being 0/28 and becomes "however many bad inputs
   arrive", which is unbounded and adversary-controlled.
3. **The corpus has zero instances.** 0 of 43 dev filings and 0 of 7 held-out
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
task/D11      dev: 59 files  sha256=c6678a8b7b82e6ae74021b45ef6e12825ff0b2fb101ee3cb3b2082bc71fe4b77
              heldout: 7 files  sha256=f80025699bc34f06af6ea0fb3457106593ec858c4d89d4144870e339b00e191a
```

**The held-out sha is byte-identical.** So is every filing document in dev.
The dev sha moves for two reasons, both of which are files rather than
behaviour:

* one new file, `evals/fixtures/repo_hygiene/routing-strip-missing.html` — the
  mutation fixture for the new UI check, which the snapshot harness sweeps
  because it sweeps everything under `evals/fixtures`;
* three edited files, `repo_hygiene/boilerplate-checkbox-default-on.html`,
  `boilerplate-wire-values.html` and `boilerplate-wire-values.py` — the ADR-026
  wire mutation fixtures, whose *text* I edited so their correct hops carry the
  new pinned spelling (§g2). Only `sha` and `norm_chars` move on each; all
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
budget, cache, pricing), `src/sec10k/escalate.py` (trigger, windows, verify,
apply, route), `tasks/reviews/d11_trigger_scan.py` (§c's instrument), five eval
cases, one mutation fixture, two `repo_hygiene` checks (`escalation_seam`,
`routing_provenance`), two `sec10k` check types (`routing`,
`escalation_invariant`), `_routing_shape` in `envelope_shape`.

### g2. Pins that moved because the wire moved

`check_boilerplate_plumbing`'s allow-list holds the exact expression at each
hop of the ADR-026 flag's path. Three of those hops gained the `escalate`
flag, so three pins were re-spelled and the three mutation fixtures that carry
their correct halves were re-spelled with them — the same move S9 (ADR-032)
made when `blocks=markdown` joined the same call, and the wire was re-checked
by hand rather than assumed: `#escalate` → `escalateOn()` → request body or
query string → handler → `_run` → `extract_items`. `ui-confidence-honesty`'s
banner pin moved for the same reason (the banner now also calls
`routingStrip`). **A moved pin is the one change in this diff that can hide a
regression**, so it is listed here explicitly rather than buried in a diff.

## h) The seam — the gate stays offline and $0, and it is measured

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
`ANTHROPIC_API_KEY` from the environment for the whole of every sec10k case,
restoring it after. So a case declaring `escalate: true` behaves identically on
a machine with a credential and one without, and the `fast` suite makes zero
paid calls **by construction** rather than by convention (cost-discipline
rule 4). `evals/bench.py`'s own no-network AST self-check is untouched.

Caching (cost-discipline rule 2): every response is keyed on
`sha256(PROMPT_VERSION, model, system, user, max_tokens, effort)` under
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
* **`effort: "low"` on both rungs.** The question is locate-by-offset, not
  reasoning; `budget_tokens` is removed on this model family and returns a 400.
* **The item-level hint is the flagged set, and falls back to every spanned
  item** when `low_item_coverage` fired with no `item_span_near_empty` beside
  it — possible on a document whose items are all short but none of them 1/7/8.
* **The dev escalation proxies are `xref-index-collapse` (A1) and the
  `cvx-2015`/`jpm-2024` pointer class** (as the ledger row directs). No
  synthetic reorg fixture was needed: `xref-index-collapse` already is the
  collapse shape, red-first at D8.

## k) What is NOT done, and must not be read as done

**The held-out exam is UNRUN.** The D11 ledger row defines success on held-out
— "the slow path completes the D6 filings it never trained against". That run
has not happened and cannot: `ANTHROPIC_API_KEY` is not set in this
environment, and repo rule 4 forbids fabricating the result. The exam is
therefore **intact and unspent**, which is the one good thing about this
column being empty. `intc-2025` and `c-2025` were not read, not adjudicated and
not iterated against; the only held-out numbers in this document are the ones
ADR-035 §b4 already published, cited under the 2026-08-26 amendment that a
ruling citing an outcome is not influence.

**No live call has ever been made.** Every dollar figure is an estimate (§d).
No `verify()` has ever been run against a real model's answer — only against
`_demo`'s constructed proposals, which test the checker and say nothing about
how often a real answer passes it. **`SIM_FLOOR` on check 5 may prove far too
strict in practice**, in which case every escalation returns `rejected` and the
ladder is an expensive no-op; that is the single most likely way this design
fails, it is not detectable without a credential, and it is why the rejection
reasons are published in full.

**No browser walk** (§i). **No vision rung** (§e). **A2 remains unreached**
(§c3). **The `Budget` dollar ceiling can be overshot by one call's own price**
(§d3).

## l) Falsifiers

| Ruling | What would falsify it | How to check | Cost of the check |
|---|---|---|---|
| `low_item_coverage` is the right trigger | it fires on a real filing that is NOT collapsed (a false positive), or a held-out collapse does not fire it | re-run `tasks/reviews/d11_trigger_scan.py` after any fixture expansion; the held-out run when a credential exists | $0 / one exam |
| The ladder is worth its price | the held-out run shows rung 2 resolving nothing that rung 1 did not, or `verify` rejecting every real answer | the held-out run, reading `routing.tiers[*].outcome` and `rejections` | one exam + ~$0.2 |
| Scanned input stays out of scope | a committed text-less 10-K fixture appears, or a user brings one | `d11_trigger_scan.py`'s "refused before any item exists" line, plus the fixtures README | $0 |
| Escalation is free by default | any default-flag run reports a non-zero `cost` | `evals/snapshot.py`, and the `escalation-trigger-quiet` case's `usd: 0.0` | $0 |
| The gate stays offline | any network module appears in a gate import | `escalation-seam-offline`, every run | $0 |
| A model cannot move a span it should not | a fabricated offset passes `verify` | attack `escalate._demo`'s proposals; the live run's `rejections` list | $0 |
| A2 stays declined | someone adjudicates the pointer-bodied-item-7/8 class as a defect | a decision, not a measurement | §d4's $3.4/sweep |
