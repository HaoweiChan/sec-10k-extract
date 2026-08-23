# ADR-030 — D3: a non-last span dominating the document is detected, and any single-span dominance escalates `doc_status`

Date: 2026-08-23. Status: accepted. Implements D3 — the successor ADR-019 §d
named for the retired span-coverage row, and class 1 of the T5-5 debt row
(ADR-027 §e). Sanctioned exception to the T8 feature freeze (`tasks/TODO.md`,
**Freeze guard**), on the pattern [ADR-020](ADR-020-fallback-not-justified.md)
established for T12 and [ADR-026](ADR-026-boilerplate-chrome-exclusion.md) /
[ADR-029](ADR-029-structured-tables-annotation.md) applied for S6/S7. Amends
ADR-008 (the validator count and `AMBIGUOUS_CODES` size, in place), ADR-016
(its warning-code table gains a row) and ADR-019 §d (the "named here, not
built" sentence gets a dated note). Meets ADR-020 §e condition 2 — see §g.

**Ruling**: a new layer-8 validator, `item_dominates`, fires when any span other than the last one exceeds `ITEM_MAX = 0.55` of `normalized_text`; it joins `AMBIGUOUS_CODES`, so a single span holding most of the document escalates `doc_status` to `ambiguous` whether it sits first, in the middle, or (already, via `last_item_dominates` at `LAST_ITEM_MAX = 0.50`) last. `last_item_dominates` keeps its code, its threshold and its cases; the two checks share one loop and are disjoint by construction.
**Because**: `last_item_dominates` inspects only the last span, so ADR-015 §0's Target FY2002 failure — item 4 at 81% of the document, not the last span — reported plain `success`; measured over every committed fixture, the largest non-last span of a real filing is 0.5336 (jnj-2016's Item 8, the financial statements, `success`) and the smallest that must fire is 0.5723 (items-stripped's Item 4), an empty band whose midpoint is 0.55 and whose two edges are pinned; at that threshold the false-positive set on every committed real filing, dev and held-out, is empty, and ADR-013's cost asymmetry (a false `ambiguous` is a report a consumer can inspect, a false `success` on a swallowed document is the silent failure the battery exists for) decides the escalation.
**Enforced by**: `evals/adversarial/interior-span-dominates.json` (fast + invariant; red at `origin/main` `dc3f8f0`), the two band pins `evals/adversarial/jnj-bare-headings.json` (`warning_absent item_dominates`) and `evals/adversarial/items-stripped-escalation.json` (`warning_present item_dominates item 4`), `src/sec10k/validate.py::_demo` (the layer echo), `evals/fixtures/interior-span-dominates/` + `evals/fixtures/README.md` row + `evals/bench.py::SYNTHETIC`.

---

## a) Why this is a sanctioned exception and not scope creep

The freeze guard says a post-T8 capability is scope creep "no matter how good
it looks". Adding a validator IS a capability — ADR-015 §5 and the Debt row
both said so and declined to build it for exactly that reason. It is in scope
now for the three reasons ADR-026 §a gave, re-checked:

1. **The human asked for it in writing, on the record** — the D3 row of
   `tasks/TODO.md` (2026-08-23) promotes the Debt row that ADR-019 §d had
   "named as the real candidate for the first post-freeze exception, not
   built", and demands an ADR before any code. This document is that ADR.
2. **ADR-020/026/029 set the shape: a post-freeze capability gets a written
   ruling with its cost named, whichever way it goes.** ADR-020's "NOT
   JUSTIFIED" was an allowed outcome here too; §b is the measurement that
   decides it, and it rules IN — with the thinnest margin in the battery named
   in §b3 rather than smoothed.
3. **It changes no existing behaviour on any committed real filing.** §e is
   the measured blast radius: on 46 of the 47 committed documents (dev +
   held-out) not one status, confidence or `doc_status` moves — one of the
   46, the synthetic items-stripped, gains a warning and nothing else; the
   47th is the new fixture, which did not exist before.

## b) The measurement

Instrument: `extract_items` at `origin/main` `dc3f8f0` over every committed
fixture directory (41 dev, of which 37 carry spans — 26 real filings and 11
self-created derivatives; the other 4 are refusals) and, **read-only, reported
separately and not tuned on**, the 5 held-out filings. For each document: the
largest span whose item is NOT the last extracted span, as a fraction of
`normalized_text`; the last span's fraction for comparison; and the ratio of
the largest span to the second-largest (for §b2). Every span is
`status == "extracted"` — IBR pointer spans stay out of the content-shape
validators (ADR-011), here as everywhere in the battery.

### b1. Dev corpus, every span-bearing fixture, sorted by the non-last maximum

| fixture | `doc_status` | largest non-last span | fraction | last span | fraction |
|---|---|---|---|---|---|
| items-stripped (synthetic) | ambiguous | 4 | **0.5723** | 15 | 0.0203 |
| jnj-2016 | success | 8 | **0.5336** | 16 | 0.0005 |
| axp-2008 | success_with_warning | 1 | 0.4927 | 15 | 0.0021 |
| wfc-2008 | success_with_warning | 1 | 0.4859 | 15 | 0.0153 |
| bac-2006 | success | 7 | 0.4731 | 15 | 0.0016 |
| gs-2002 | success | 1 | 0.4557 | 15 | 0.1478 |
| cat-2023 | success | 8 | 0.4275 | 16 | 0.0002 |
| ko-1997 | success_with_warning | 1 | 0.4251 | 14 | 0.1190 |
| ba-2003 | success | 8 | 0.4127 | 15 | 0.0230 |
| textron-2001 | success_with_warning | 1 | 0.3818 | 14 | 0.1892 |
| msft-2013 | success | 8 | 0.3581 | 15 | 0.0175 |
| intc-2002 | success | 8 | 0.3360 | 15 | 0.0145 |
| aapl-2025 | success | 1A | 0.3285 | 16 | 0.0003 |
| heading-unnumbered (synthetic) | ambiguous | 15 | 0.3164 | 16 | 0.0001 |
| nvda-2024 | success | 15 | 0.3164 | 16 | 0.0001 |
| nike-2006 | success | 8 | 0.3160 | 15 | 0.0323 |
| sandston-2021 | success_with_warning | 1A | 0.3078 | 15 | 0.0398 |
| fy2021-item9c (synthetic) | success_with_warning | 1A | 0.3075 | 15 | 0.0397 |
| wmt-2010 | success | 1 | 0.2857 | 15 | 0.0963 |
| sgrp-2019 | success | 8 | 0.2749 | 15 | 0.0102 |
| spaced-letter-heading (synthetic) | success | 8 | 0.2749 | 15 | 0.0102 |
| spans-transposed (synthetic) | success_with_warning | 1A | 0.2745 | 15 | 0.0102 |
| spatz-2014 | success_with_warning | 1A | 0.2434 | 15 | 0.0632 |
| toc-titled (synthetic) | success | 8 | 0.2311 | 15 | 0.0203 |
| malformed-html (synthetic) | ambiguous | 8 | 0.2310 | 15 | 0.0203 |
| comma-cover-2016 (synthetic) | success | 8 | 0.2310 | 15 | 0.0203 |
| caps-cover-2016 (synthetic) | success | 8 | 0.2310 | 15 | 0.0203 |
| premier-pacific-2016 | success | 8 | 0.2310 | 15 | 0.0203 |
| ibm-1997 | success_with_warning | 1 | 0.2071 | 14 | 0.1658 |
| ibr-security-holders (synthetic) | success_with_warning | 1 | 0.2071 | 14 | 0.1657 |
| cvx-2015 | success_with_warning | 1 | 0.1986 | 15 | 0.0045 |
| reac-2015 | success_with_warning | 1 | 0.1833 | 15 | 0.0148 |
| tgt-2002 | success_with_warning | 4 | 0.1666 | 15 | 0.1708 |
| xom-2021 | ambiguous | 2 | 0.1416 | 16 | **0.7063** |
| ge-1994 | success_with_warning | 1 | 0.1294 | 14 | 0.0286 |
| ibr-pointer-first (synthetic) | success_with_warning | 1 | 0.1294 | 14 | 0.0286 |
| jpm-2024 | ambiguous | 1A | 0.1124 | 15 | **0.8328** |

Four fixtures carry no span and are not in the table: `aapl-2026-10q`,
`amended-cover-2021`, `ksb-2007` (all `unsupported`) and `truncated-download`
(`failed`).

### b1-held-out. Read-only — reported, not tuned on

| fixture | `doc_status` | largest non-last span | fraction | last span | fraction |
|---|---|---|---|---|---|
| mrk-1995 | success | 1 | 0.5274 | 14 | 0.0945 |
| cost-2022 | success | 8 | 0.4254 | 16 | 0.0003 |
| csco-2016 | success | 8 | 0.3746 | 15 | 0.0025 |
| pgr-2023 | success | 1A | 0.3693 | 16 | 0.0006 |
| spg-2019 | success | 8 | 0.3518 | 16 | 0.0334 |

No held-out document crosses 0.55. `mrk-1995` at 0.5274 is the closest and
sits below the dev corpus's own legitimate maximum (0.5336); whether that 1995
Item 1 is a correct span or a bleed is **not adjudicated here** — reading the
filing to decide would burn the fixture (`evals/heldout/README.md`). The
threshold is the dev band's midpoint and no held-out value enters its
derivation; the five numbers were printed by the same instrument run and are
reported so a reader can check that none crosses it.

### b2. What the numbers say, and the two signals they reject

**There is no clean gap between "legitimate" and "defective" at
`LAST_ITEM_MAX`'s 0.50.** Real filings legitimately put up to 53% of the
document into one interior item: jnj-2016's Item 8 is the audited financial
statements, bounded by the filer's own Item 8 and Item 9 headings (pages
34–86 of the filing), and its case asserts `success`. Seven real filings sit
between 0.41 and 0.53 — banks' MD&A (bac-2006 item 7), IBR-heavy filers whose
Item 1 is the only substantive body (wfc-2008, ko-1997, gs-2002, axp-2008),
ba-2003 and cat-2023's Item 8. A threshold of 0.50 would escalate jnj-2016 to
`ambiguous` — a false positive on a correct extraction, which ADR-008's F7
policy forbids. So `LAST_ITEM_MAX` cannot simply be applied to every span,
and the non-last check needs its own constant.

**The band that does exist is (0.5336, 0.5723)** — jnj-2016's Item 8 below,
items-stripped's Item 4 above (eight headings stripped; the span swallowed
them; that fixture is already `ambiguous` through
`expected_items_mostly_missing`, which is why it can pin the edge but not
prove the policy, §c). Midpoint 0.553 → **`ITEM_MAX = 0.55`**, the
convention `LAST_ITEM_MAX` follows. The historical defect this is for sits
far above: Target FY2002's item 4 was 26,861 of 33,196 chars = 0.809 (ADR-015
§0; fixed upstream by the echo rule, it reads 0.1666 today, row `tgt-2002`).

Two alternative signals were measured and **rejected**, ADR-008's
"rejected after measuring" pattern:

- **Dominance relative to the next-largest span** (largest ÷ second-largest
  extracted span). items-stripped reads 5.15 — but so do legitimate filings:
  wfc-2008 6.95, cvx-2015 5.76, mrk-1995 5.58 (held-out), ko-1997 3.57, and
  the two last-span defects jpm-2024 7.41 / xom-2021 4.99. A filer whose
  other items are pointers has one big span and many stubs by design; the
  ratio cannot tell that from a bleed. No separation — rejected.
- **An absolute + relative rule** (fraction > 0.50 AND ratio > 3). Fires on
  exactly one committed document (items-stripped, 0.57 / 5.15) and on none of
  the legitimate ones (jnj 2.49, wfc 0.49 / 6.95) — but it is a two-parameter
  rule fitted to one synthetic point, with no measured band for the second
  parameter. A threshold the corpus cannot pin from both sides is the
  `vacuous_coverage` finding ADR-027 §c closed, re-opened — rejected.

### b3. The margin, stated

`ITEM_MAX` sits **1.03×** above the worst real filing (0.55 / 0.5336). That is
the thinnest margin in the battery — `MISSING_MAX` is 1.25× (ADR-027 §c),
`UNATTRIBUTED_MAX` 1.37×, `LAST_ITEM_MAX` 2.6× — and it is stated at the
constant in `validate.py`. The honest consequence: an unseen filer whose Item
7 or 8 runs to 56% of the document will read `ambiguous` with every item
capped at 0.75. On the 31 real filings this repo has measured (26 dev + 5
held-out) none does; the widest legitimate interior span seen is 0.5336. The
cost of that false positive, when it comes, is §c's argument.

## c) The escalation policy — `item_dominates` joins `AMBIGUOUS_CODES`

The question ADR-019 §d left open: should single-span dominance escalate
`doc_status` regardless of position, or only when it is the last span?

**Ruling: it escalates.** Three reasons, in order of weight:

1. **ADR-013's cost asymmetry.** A false `ambiguous` is a conservative
   report a consumer can inspect — every item is still extracted and
   addressable, capped at 0.75 (ADR-027 §a). A false `success` (Target FY2002
   read plain `success`, no warning at all) or `success_with_warning` on a
   document where one span holds 64% and four items are silently inside it is
   exactly the silent failure the battery exists to prevent, and the contract
   invites consumers to threshold on `doc_status`.
2. **The measured false-positive set is empty.** At 0.55 no committed real
   filing, dev or held-out, fires (§b1 / §b1-held-out). The ADR-008 argument
   that kept `unattributed_content` OUT of `AMBIGUOUS_CODES` — "for IBR-heavy
   filings that shape is normal" — does not apply: no class of committed
   filing has an interior span above 0.5336. Were the policy "warn only", the
   measured cost of escalating would still be zero today; the benefit is the
   Target shape.
3. **Consistency with the last span.** `last_item_dominates` has escalated
   since ADR-008. One span holding most of the document is the same claim
   about the document wherever the span sits; a policy that escalates it at
   position N and not at position N−1 is a policy about where the bleed
   happened to land, not about whether the document was resolved.

**Which documents flip, and the cap (ADR-027 §a).** Exactly one committed
document changes `doc_status`: the new fixture `interior-span-dominates`,
`success_with_warning → ambiguous`, all 16 span-carrying items capped
0.95/0.85 → 0.75 (items 1A/1B/2/3 are `missing` at 0.40, below the cap,
untouched). items-stripped already read `ambiguous` (via
`expected_items_mostly_missing`) with every item already capped, so its new
`item_dominates` warning moves no number: item 4 is `min(0.75, 0.95 − 0.15)
= 0.75` before and after. No real filing flips.

**Mutation proof** (this branch, all cases green at the shipped values):
removing `"item_dominates"` from `AMBIGUOUS_CODES` → `interior-span-dominates`
RED: `doc_status 'success_with_warning' != 'ambiguous'`, `item 1 confidence
0.8 > 0.75`. The policy has a case that turns red if it is reverted
(ADR-016's rule), and the case pins the cause, not only the consequence:
`warning_absent` on `expected_items_mostly_missing` (4 of 20 missing = 0.20,
under `MISSING_MAX` — the same fraction axp-2008 loses and must not escalate
on), on `toc_manifest_mismatch` (the source has no contents page; its
`toc_manifest` is empty at `origin/main`) and on `last_item_dominates` (the
last span is 9.6%) closes every other route to `ambiguous`.

## d) What `last_item_dominates` becomes — kept, not renamed, not merged

`last_item_dominates` keeps its code (a contract code, pinned by
`jpm-2024-structure`, `xom-2021-shallow` present and `textron-2001-structure`
absent — renaming it would be a contract change with no gain), its threshold
(`LAST_ITEM_MAX = 0.50`, band (0.1892, 0.7063), ADR-027 §c) and its message.
The two checks now share one loop over the extracted spans in `validate.py`
§3/3b: the last span is judged against `LAST_ITEM_MAX` and emits
`last_item_dominates`; every other span is judged against `ITEM_MAX` and
emits `item_dominates`. Disjoint by construction — no span can carry both
codes, and no document can carry both warnings (two spans above 0.50 and
0.55 would sum past 1.0).

Why not one constant for both: the two distributions are different measured
facts. The last item (the exhibit list, or Item 14 pre-2003) is legitimately
small — the largest real one is textron-2001's 0.1892 — so its threshold has
a wide band and a 2.6× margin; an interior item (Item 1 of an IBR-heavy
filer, Item 7/8 of a bank) is legitimately up to 0.5336, so its threshold
has a four-point band and a 1.03× margin. A shared 0.55 would happen to sit
inside both bands on today's corpus, but it would move a published constant
(ADR-008, ADR-027 §c) for tidiness rather than for a measurement, and it
would hide the fact that the two checks are defending different margins.
Two constants, two comments, both pinned.

## e) Blast radius — main `dc3f8f0` vs this branch, all 47 committed documents

Instrument: a scratch snapshot of `extract_items` (every item's status,
confidence, offsets and `method`; every warning `(code, item)`;
`doc_status`) over `evals/fixtures` (42 directories with the new one) and
`evals/heldout/fixtures` (5), run against both trees and diffed.

| fixture | what changed | clause |
|---|---|---|
| `interior-span-dominates` (NEW) | `success_with_warning → ambiguous`; `item_dominates` on item 1; 16 span items capped to 0.75 | §c (the case; red at main) |
| `items-stripped` | `+ item_dominates` on item 4; **no** status, confidence or `doc_status` change | §b2 (band upper edge; the pin in `items-stripped-escalation`) |
| every other dev fixture (40) | identical in every field the snapshot reads | — |
| every held-out fixture (5) | identical | — |

No golden's asserted value changes. No offset moves anywhere (the validator
reads spans, it does not produce them). `normalized_text` is untouched.
Table fidelity unchanged: `cells 1.0000 (400/400), rows 1.0000 (31/31)`.
`extractor_version` → `0.8.0-d3`: `doc_status` on a dominated document is not
comparable across the bump.

## f) Threshold pins and the red line

| constant | value | measured empty band (low fixture, high fixture) | pins | mutation → red line |
|---|---|---|---|---|
| `ITEM_MAX` | 0.55 | (0.5336 jnj-2016 item 8, 0.5723 items-stripped item 4) | `jnj-bare-headings` `warning_absent item_dominates`; `items-stripped-escalation` `warning_present item_dominates item 4` | 0.53: jnj RED `unexpected warning 'item_dominates': item 8 is 53% of the document`, `doc_status 'ambiguous' not in ['success', 'success_with_warning']`, `item 13 confidence 0.75 != 0.85`; 0.58: items-stripped RED `expected warning 'item_dominates', got ['expected_item_missing', 'expected_items_mostly_missing']` |

`interior-span-dominates` (item 1 at 0.6387) stays green at both mutated
values — it is not a band edge, it is the policy's proof; the edges are the
two committed fixtures that already existed.

**Red at `origin/main` `dc3f8f0`** (cases added, pipeline at main, the new
fixture present):
`interior-span-dominates`: `doc_status 'success_with_warning' != 'ambiguous'`
· `expected warning 'item_dominates', got ['expected_item_missing']` · `item 1
confidence 0.95 > 0.75`. `items-stripped-escalation`: `expected warning
'item_dominates', got ['expected_item_missing', 'expected_items_mostly_missing']`.
`jnj-bare-headings`: green at main (a pin for a code that did not yet exist
cannot be red; it is red under the 0.53 mutation above). Layer echo in
`validate._demo`: a non-last span of 5,000 chars beside a 23-char last span
fires `item_dominates` on item 1 and not `last_item_dominates`; and
`"item_dominates" in AMBIGUOUS_CODES` is asserted there.

**Gate after**: `invariant 50/50 = 1.000`, `fast 98/98 = 1.000` (+4 enumerated
debt, unscored), table fidelity 400/400 · 31/31, `.eval-baseline.json`
untouched (`{"fast": 1.0}`), `validate` / `eval_adapter` 18/18 / `metrics` /
`bench` self-checks ok, `--check-docs` 68 / 0 unmatched.

## g) Consequences, and what this ADR does NOT claim

- **T5-5 class 1 is closed** ("a 4-5-of-21 missing filing sits under
  MISSING_MAX with an interior span swallowing the rest"): the new fixture is
  exactly that shape (4 of 20 = 0.20 under `MISSING_MAX`, item 1 at 0.6387)
  and it now escalates. Classes 2 and 3 are **not** closed: class 2 (the
  `EXEC_OFFICERS_RE` clip opening an interior gap no validator measures) is a
  gap, not a dominance — the clipped item gets *smaller* — and ADR-019 §d's
  structural argument that the EO clip is the only interior-gap source
  stands; class 3 (a txt filing with no contents page disabling
  `toc_manifest_mismatch`) is the absence of a signal, and the new fixture
  shows the battery still escalating such a document through this route —
  useful, but not a cure for a missing manifest. The T5-5 Debt row is
  re-filed for classes 2/3 only.
- **ADR-020 §e condition 2 is met in mechanism, not in effect.** It reads:
  *If the escalation-policy successor named in ADR-019 §d ships and gives
  non-last span dominance a doc-level signal, rows 4 and 5 acquire a trigger
  they lack today, and "should the fallback fire on it" becomes live.* The
  signal ships here. On the two rows it names it is silent: cvx-2015's
  largest non-last span is 0.1986 and msft-2013's 0.3581 (§b1), both far
  under `ITEM_MAX`, so neither document acquires a firing trigger today.
  ADR-020 says any met condition "reopens T12 with its own ADR"; that ADR is
  not this one — recorded as a Debt row (`Origin: D3`).
- **Not claimed**: that this validator would have caught Intel FY2002
  (ADR-015 §0's other failure — every item a stub, 0.47% covered; that is
  `unattributed_content`'s shape, which fired, non-escalating, and stays as
  ADR-008 ruled it); that a span *mis-assigned* rather than over-extended is
  visible (ADR-013's blind spot — proportion measures size, not
  correctness); that the 1.03× margin holds beyond the 31 real filings
  measured; that `mrk-1995`'s 0.5274 is correct or wrong (not adjudicated,
  §b1-held-out); any change to the interior-gap half of the retired row
  (ADR-019 §d's EO-clip accounting is untouched); any threshold chosen on
  held-out data (the held-out table enters no derivation; it is reported so
  the reader can see none of the five crosses the threshold).
- ADR-008's validator count reads eight (`grep -c 'warn("'
  src/sec10k/validate.py` → 8) and `AMBIGUOUS_CODES` four
  (`len(AMBIGUOUS_CODES)` → 4); both amended in place with this ADR's marker.
  README's "only three may escalate" sentence is corrected to four, with the
  same command behind it.
- The bench artifact of record (ADR-021, `20260823-185707`, n=41) predates the
  new fixture and is not re-run here — D2 re-ran it today; `SYNTHETIC` names
  the fixture so n reads 42 at the next refresh, which `--self-check` will
  count.

## Verification

`--suite invariant` 50/50 = 1.000 (+4 enumerated debt, unscored);
`--suite fast` 98/98 = 1.000 (+4 enumerated debt, unscored); table fidelity
cells 400/400, rows 31/31. `.eval-baseline.json` untouched (`{"fast": 1.0}`,
matches). No `--update-baseline`, no `--no-verify`. Held-out run not performed
(no threshold was tuned on it; §b1-held-out is a read-only measurement).
