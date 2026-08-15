# 003 — T3: the normalization spike and what it changed

## Purpose

Records the T3 milestone (document selection + normalization) because the
spike ADR-003 mandated did not merely validate the plan — it produced three
findings that changed the architecture, the invariant set, and the eval
methodology. Curated per hard rule 6.

## The prompt

> this repo has finished till task 2, continue on task 3. refer to
> docs/product/assignment-requirements.md

Deliberately unspecific. Everything below came from the repo's own contract:
`milestones.md` defines T3 as "document selection + normalization (spike
first: determinism + word-joining on both fixtures), partial green:
`verbatim`", and ADR-003's revisit clause makes that spike a precondition for
building on stdlib `html.parser`.

## What the spike was asked to answer

ADR-003 named three questions. Two came back clean and one did not:

| Question | Result |
|---|---|
| Deterministic per input? | Yes — 13/13 fixtures, repeat runs identical |
| Fast enough? | Yes — 0.43 s for the 12.8 MB JPM filing, 2.3 s for all 13 |
| Word integrity across tag boundaries? | **No** — and two defects the question wasn't even aimed at |

The instrument mattered more than the questions. Rather than eyeballing
output, the spike re-used **the eval set's own `text_contains` anchors as the
canary**: they are authored against the ADR-003 canon by a separate SOP, so
they fail loudly whenever the normalizer and the canon disagree. 33 of 34
survived — and chasing the one that didn't found two larger problems standing
behind it.

## The three findings

1. **iXBRL context metadata is emitted as document text.** `<ix:header>`'s
   character data normalizes into a run of concatenated machine identifiers
   ahead of the cover page: 12.9 K chars on AAPL 2025, 221 K on JPM 2024 —
   15.4% of that document before the first readable word. Offsets are the
   contract's unit of provenance, so this displaces every offset in the
   filing and poisons every ratio the layer-8 validators will measure against
   document length.
2. **HTML source line-wrap survives normalization.** The dead anchor. MSFT's
   filing agent hard-wraps at ~80 columns *inside text nodes*; "Microsoft
   was\nfounded in 1975" is one sentence in every browser and two lines in
   our text. 858 occurrences in MSFT 2013, 669 in NIKE 2006, zero in every
   other HTML fixture — a filing-agent style confined to one stratum.
3. **One eval case could pass on an empty parse.** `malformed-html`'s entire
   check surface (`doc_status` allowlist including `ambiguous`, plus a
   whitelist-shaped `only_items`) is satisfied by `items: []` — so it would
   have gone green at T3 against a pipeline that extracts nothing at all.

## Decisions

- ADR-006 ruling 1: skip `ix:header`/`ix:hidden` like `script`/`style` — by
  element, not by `style="display:none"` (AAPL alone has 33 of those, mostly
  legitimate).
- ADR-006 ruling 2: **a newline means opposite things in the two format
  eras.** HTML — source formatting, collapse it, and collapse it *at parse
  time* while a source wrap is still distinguishable from a block boundary.
  Plain-text era — the newline IS the document (fixed-width layout,
  line-anchored headings), passthrough. The txt fixtures show the same
  mid-sentence-newline signature (GE 2,178, IBM 1,798) and must keep every one.
- ADR-006 ruling 3: no entity decoding on the txt path (no fixture needs it;
  `html.unescape` rewrites `&amp` without a semicolon). Held-out gap recorded
  as debt rather than pre-solved.
- INV-S5 added: `normalized_text` is the readable filing, not machine
  metadata — stated positively so it cannot be satisfied by deleting content.
- New adapter checks `norm_contains`/`norm_not_contains`. Before them nothing
  in the eval set asserted anything about the normalizer's own output.

## Assumption → Eval contradiction → Correction

- Assumed: the spike would confirm ADR-003 and be thrown away.
- Eval said: the anchor canary killed `msft-2013-content`'s
  "Microsoft was founded in 1975", and pulling that thread exposed 221 K chars
  of XBRL metadata sitting in JPM's normalized text — neither of which any
  existing case could see.
- Corrected: ADR-006 (three rulings), INV-S5, two new adversarial cases, two
  new check types. The spike became the standing cheap check for
  normalization changes rather than a throwaway.

- Assumed: a normalization defect would be caught by the item-level anchors
  that already exist.
- Eval said: it cannot be, by construction. At T3 there is no segmentation, so
  every `text_contains` check fails with "item not extracted" whether
  normalization is perfect or broken — the layer was untestable, not merely
  untested.
- Corrected: `norm_contains`/`norm_not_contains` judge `normalized_text`
  directly, and the two new cases live at that layer. Isolating the layer is
  what made "watch it fail" mean anything this milestone.

- Assumed: "watched it fail" was satisfied because all 19 cases were red
  before implementation.
- Eval said: they were red with `NotImplementedError` — which proves the
  pipeline is absent, not that a case discriminates its fix. `malformed-html`
  proved the point from the other direction: it was one check away from
  passing on an empty parse.
- Corrected: each T3 fix was disabled in turn against the finished pipeline
  and its guarding case confirmed red (hidden-metadata skip →
  `ixbrl-hidden-metadata` fails; intra-chunk collapse → `html-source-wrap`
  fails; form refusal → `10q-unsupported` fails), and `malformed-html` gained
  `expected_set_complete`, triaged `eval-bug`.

- Assumed: the three positive `norm_contains` anchors in
  `ixbrl-hidden-metadata` were belt-and-braces.
- Eval said (design review while authoring): a normalizer that dropped
  everything before the cover page, or dropped every unrecognized element,
  passes all three negative checks while destroying the document.
- Corrected: the positives are load-bearing and were chosen to pin the cut at
  both ends — one immediately after the header block, two deep in the body.

## Cost

Zero LLM calls, zero dollars. The whole T3 pipeline is deterministic stdlib;
`cost` in the envelope is structurally `{llm_calls: 0, tokens: 0, usd: 0.0}`.
