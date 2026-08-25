# Postmortem — 2026-08-24 demo: Intel and Citigroup 10-Ks failed at conf 0.95

**What happened.** At a live demo on 2026-08-24, recent Intel (INTC) and
Citigroup (C) 10-K filings were run through the inspector. Both extractions
were visibly wrong, and the side panel showed per-item `conf 0.95` while they
were wrong. This document is the retrospective: what failed, why the number
said otherwise, what the repo already knew, and what work was cut from it.
The remediation milestones are ledger rows D6–D11 in `tasks/TODO.md`; this
file is the narrative they point back to. Nothing here is normative —
`specs/` binds. §7 records the design direction set at the interviewer
debrief later the same day, which re-scoped D6 and added D11.

## 1. The headline finding: 0.95 was not lying about what it measures

The panel number is computed in exactly one place, `score()` at
`src/sec10k/validate.py:280`. `BASE_STRICT = 0.95` is awarded on **one
input**: the matched heading string's similarity to the canonical item title
(`STRICT_SIM = 0.8`). It is not a function of span length, span content, or
coverage. Two things can pull it down:

1. Warnings that carry this item's code — only four validator codes ever do
   (`last_item_dominates` / `item_dominates`, `boundary_hygiene`,
   `numeric_density_inversion`, `keyword_fingerprint`). Document-level codes
   (`unattributed_content`, `toc_manifest_mismatch`,
   `expected_items_mostly_missing`) pass `item=None` and never touch any
   item's number.
2. The document-level `ambiguous` cap (ADR-027). `success_with_warning` does
   **not** cap anything.

So `conf 0.95` asserts precisely: *the heading text matched well, no
item-targeted validator fired, the document was not flagged ambiguous*. It is
silent on whether the span holds the right content. This is documented —
`docs/architecture/overview.md` §confidence calls the distribution "nearly
binary" (224 of 283 items at 0.95) and the scale uncalibrated, and ADR-019
states the structural gap outright: document-level and item-level honesty are
separate properties, and only the first has an escalation rule.

The demo turned that documented gap into a stakeholder-visible incident.

## 2. The two failure shapes, both previously seen

**Intel-shaped: stub collapse (ADR-015).** This repo has already been broken
by Intel once. `intc-2002` originally resolved all fifteen items to
18–490-char stubs at the very end of the file — 1,445 chars of a
309,085-char document, 0.47% — because a trailing cross-reference index made
`_toc_runs` treat the real body headings as TOC entries and drop them. Every
invariant passed; every item would have scored 0.95, because the headings it
matched were real headings — just the wrong instances. ADR-015 fixed FY2002
and closed with: "the honest statement of the risk is that the next
mis-dated item repeats this exactly." Intel's post-2019 10-Ks are the
modern maximal case: the narrative is reorganized into a non-canonical
order, mapped back to items by a "Form 10-K cross-reference index" — the
exact trap class, on a filing shape with zero fixture coverage.

**Citigroup-shaped: pointer prose (ADR-017, ADR-019 §e).** WFC FY2008 once
reported ten items as `extracted` at 0.95 over 250–360-char pointer
paragraphs. ADR-017 fixed Wells Fargo's exact phrasing; the *class* — a
large-bank filing that answers Items 7/8 with a one-sentence pointer to
pages later in the same document, the real MD&A/financials sitting unlabeled
in the tail — is open, permanently-red debt
(`evals/adversarial/cvx-2015-internal-pointer.json`; jpm-2024 items 7/8 show
the same shape, doc-level `ambiguous` but item-level still 0.95). Citigroup
files exactly this way, and C appears in no fixture, golden, adversarial, or
held-out set.

**The UI amplified both.** `doc_status` and the warnings list live in the
top banner; the side panel a viewer is actually reading shows a per-item
`conf 0.95` with no visual link back to a document-level
`success_with_warning`. During a demo, the panel is the product.

## 3. Coverage gap, stated plainly

The eval set is the spec (CLAUDE.md), and neither demo input was in it:

- Intel coverage is `intc-2002` only — 2001–2019 HTML era, pre-reorg.
- Citigroup coverage is zero. Nearest financial-sector fixtures: jpm-2024,
  wfc-2008, bac-2006, gs-2002, axp-2008.
- No fixture in the corpus exercises the post-2019 "non-canonical order +
  cross-reference index" layout at all.

Running uncovered inputs live, in front of an audience, was the process
failure; the pipeline behaved exactly as its eval set specifies.

## 4. Known-difficult filers (candidate coverage, ranked)

| Filer class | Why it breaks this pipeline | Nearest existing coverage |
|---|---|---|
| Money-center banks: C, JPM, GS, MS, BAC, WFC | Items 7/8 are pointer sentences; real MD&A/financials are hundreds of unlabeled F-pages in the tail | jpm-2024, wfc-2008 (phrasing-fixed), cvx-2015 debt case |
| Intel 2019+ | Non-canonical section order + cross-reference index; strongest known TOC-trap variant | intc-2002 (pre-reorg only) |
| Berkshire Hathaway | Minimal HTML, atypical layout, huge insurance statements | none |
| txt-era Exhibit-13 filers (GE style) | Body is one IBR sentence; content lives in the annual-report exhibit | ge-1994 (trailing-tail only) |
| AXP-style combined Part III headings | One heading names four item codes; every heading path matches one code | axp-2008 (permanently-red debt) |
| Non-canonical item codes (CAT "Item 1D") | Canonical-code filter must reject without collateral | cat-2023-shallow |
| Part III via 10-K/A | Amendment filings are refused by scope (ADR-024) | amended-cover-refused |

## 5. What was already on file vs. what was new

Already documented before the demo: the uncalibrated near-binary confidence
scale (overview.md), the item-level escalation gap (ADR-019), the
internal-pointer debt class (ADR-019 §e, cvx-2015), the era-table silent
failure point (ADR-015), the partial silent-failure sample (README, 109 of
490), and the per-item near-empty validator named as unbuilt (ADR-031 §i).
The cheapest known catch is recorded in `evals/heldout/README.md`: a
2,000-char floor on Item 1 would have caught the Intel shape instantly —
`min_chars` exists only as an eval assertion, never as a runtime validator.

New information from the demo: (a) the modern-Intel layout is a live input
users will actually try, not a hypothetical; (b) the side-panel presentation
converts a documented limitation into a trust incident; (c) the demo path
(live EDGAR URL, uncovered filer) has no preflight gate.

## 6. Remediation (ledger rows D6–D9)

Ordered by cost-to-catch, honoring the T8 freeze (a new capability needs its
own ADR as a sanctioned exception — D3/D4 are the precedent):

1. **D7 — inspector confidence honesty (display-only).** Surface
   `doc_status` and any item-targeted warnings beside the per-item number; a
   warned document never shows a naked 0.95. No pipeline change.
2. **D6 — the hard set, held out.** Re-scoped by §7: recent INTC and C
   filings are authored as **held-out** cases (isolation, burn rule per
   `evals/heldout/README.md`), not dev fixtures — they are the exam the D11
   slow path must pass without training on them. Baseline deterministic run
   recorded; both are expected to fail it.
3. **D8 — item-level escalation rule (ADR required).** A layer-8 validator
   that carries the item code — per-item span floor and/or
   unattributed-coverage coupling — so the existing warning penalty pulls
   0.95 down on stub and pointer spans. This is the missing half ADR-019
   names, and per §7 it doubles as the escalation trigger D11 routes on.
4. **D9 — decision row.** With D6 evidence in hand, decide whether
   internal-pointer resolution (ADR-019 §e) and combined-heading fan-out
   (axp-2008; ADR-020 calls it the deterministic $0 fix) are promoted from
   debt, declined, or subsumed by the D11 slow tier — each outcome with its
   cost comparison cited.
5. **D11 — tiered escalation (ADR required, supersedes ADR-020).** See §7.

**Process rule going forward:** no live-demo input outside the eval set. A
demo preflight is one extraction run read for `doc_status` and warnings
before anyone screen-shares it.

## 7. Addendum — design direction from the interviewer debrief (2026-08-25)

Discussed with the interviewer after this postmortem was first drafted, and
adopted as the track's direction by the owner:

**Fast-slow tiered extraction ("thinking fast and slow").** The
deterministic, model-less pipeline stays the default — it is free, and on
clean filings it is correct. When it is out of its depth, the system
escalates instead of shipping a confident wrong answer: first to a **vision
verifier** — render the filing and let a vision model give visual backing or
contradiction ("Intel's Item 1 is blank on screen; the real content is on
these pages") as a cheap localizing hint, not an extraction — then, only if
still unresolved, to a **model-based extractor** that is allowed to spend
whatever the document takes. Normal operation costs $0; hard documents get
everything.

The ladder is **failure-class-conditional, not fixed** (owner correction,
same day): vision-as-verifier presumes text exists in the document but the
spans landed wrong — the Intel and Citi shapes. When the input has no
extractable text at all (a scanned or image-based document), there is
nothing to verify and vision-as-extractor — OCR-class full character
recovery — IS the slow path. The router picks by failure class: empty or
garbage `normalized_text` escalates straight to vision extraction;
text-present-but-spans-wrong tries the cheap hint first. Such text-less
inputs are refused as out of scope today (README); admitting them is a
scope expansion D11's ADR must rule on explicitly.

Four consequences the ledger now encodes:

- **The trigger is the prerequisite, and the demo is the proof.** A router
  needs a reliable "the fast path is stuck" signal, and §1 shows today's
  pipeline has none — 0.95 on a blank extraction means it cannot tell. D8
  is therefore not just confidence honesty; it is D11's sensor, and D11 is
  sequenced behind it. Trigger precision/recall on the dev corpus becomes
  ADR evidence: fire too rarely and the demo repeats, too often and the
  cost story collapses.
- **ADR-020 is revisited, not overturned silently.** Its NOT JUSTIFIED
  ruling was data-gated: on the then-measured corpus there was no real
  recall gap a fallback could close. The demo filings and the D6 held-out
  set are precisely the new data. D11's ADR must supersede ADR-020 with
  measured escalation rate and per-document cost (the cost-discipline skill
  binds), and the deterministic-fix-first preference ADR-020 recorded gets
  re-argued in D9 against the slow tier's measured cost.
- **Intel and Citi live in held-out.** The owner's placement call: the two
  filings the slow path exists to complete are the ones it must never
  train on. Development iterates on dev proxies (the cvx-2015/jpm-2024
  pointer class; a synthetic cross-reference-index fixture if needed);
  generalization is claimed only from the held-out run, under the existing
  isolation and burn rules.
- **Routing is user-visible, never silent.** The demo's trust damage came
  from the UI asserting more than the pipeline knew; a slow tier that
  escalates invisibly would recreate that in reverse. The envelope records
  which tier produced each item — extending the per-item `method` field the
  inspector already renders as "via ..." — plus a document-level routing
  record (trigger fired or not, tiers attempted, per-tier outcome and
  cost), and the inspector displays both, pinned by a red-first UI case.
