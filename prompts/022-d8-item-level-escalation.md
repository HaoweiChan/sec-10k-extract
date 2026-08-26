# 022 — D8: the item-level half of the escalation rule, and three interviewer gaps ruled (2026-08-26)

ADR-019 §e closed with "document-level and item-level honesty are separate
properties here, and today only the first is defended by an escalation rule";
ADR-031 §i listed the per-item near-empty validator as NOT built. The
2026-08-24 demo turned that documented gap into a live failure — Intel and
Citigroup 10-Ks shown at `conf 0.95` while visibly wrong — and the
postmortem's §8 addendum widened D8 from "make the number honest" to three
explicit rulings: (a) a doc-level coverage field with an escalation threshold,
(b) what the consumer receives when a validator hits an item, (c) whether the
iXBRL numeric cross-check is worth building. Ruling:
[ADR-035](../specs/decisions/ADR-035-item-level-escalation.md). "Declined with
its cost named" was an allowed outcome for all three; two ruled in, (c) ruled
out with four measurements behind it.

## The prompt decisions that mattered

- **Let the census pick the item set, not the intuition.** The held-out
  README's own suggestion — a 2,000-char floor on Item 1 — is the right
  instinct and the wrong scope: applied to all 23 codes it fires on 27 of 27
  Item 1Bs saying "None.", on 23 of 27 Item 6s saying "[Reserved]", and on 6
  Item 1As whose entire lawful answer is "Not required for smaller reporting
  companies". Only items 1, 7 and 8 have an empty band, so only those three
  get the floor. The census is printed in full in ADR-035 §b1 (all 14 spans
  under the gap, with what each one says) precisely so a reader can disagree
  with the ruling on the evidence rather than on the summary.

- **Separate what the demo conflated: a stub item and a stub document.** They
  need different codes because they need different escalation policies. One
  pointer item is a fact about that item — escalating it would take Chevron,
  GE, Coca-Cola, NVIDIA and six more real filings to `ambiguous` and cap
  perfectly good items at 0.75, which is exactly the crying-wolf validator
  ADR-008's F7 policy forbids. A document whose items hold 3% of it is a
  verdict on the document, and it escalates. Two codes, two constants, two
  bands, one of which is deliberately non-escalating.

- **Say what the warning does NOT claim.** ADR-019 §e records a standing
  disagreement — the auditor's blind sample called a `cvx-2015` pointer
  CORRECT — and a new status value would settle it by fiat in a contract enum
  consumers switch on. `item_span_near_empty` asserts only "this span is too
  short to be this item's content", which both sides of that disagreement
  accept, and `review_required` gives the consumer the signal without
  overloading `status`. The interviewer's `needs_review` field, recorded in
  postmortem §8 as a praised mechanism that does not exist, exists now.

- **Decline (c) with numbers.** The iXBRL cross-check is a genuinely good idea
  that this corpus cannot support: 8 of 39 span-bearing dev documents carry
  any `ix:nonFraction` fact, every txt-era and pre-2020 filing reads zero, and
  relating a fact to a span needs the raw-to-normalized offset map ADR-026 §a
  refused. On the two demo filings it is redundant (intc-2025) or vacuous
  (c-2025, zero spans). The ADR names the filing that would reopen it rather
  than leaving "maybe later" as the ruling.

- **Held-out is measured, never tuned on.** Both bands come from dev values
  only, and both constants were fixed before the held-out table was read. The
  measurement is reported (ADR-035 §b4, §f2) because the D8 row demands blast
  radius on every fixture; `intc-2025` and `c-2025` were not read, not
  adjudicated, and no case label of theirs was consulted. `mrk-1995` and
  `pgr-2023` items 7/8 fire and are explicitly NOT adjudicated — reading them
  to decide would burn them, the same call ADR-030 §b1-held-out made about
  `mrk-1995`'s 0.5274.

## Assumption → Eval contradiction → Correction

- **Assumed:** a per-item span floor would leave every real dev filing alone,
  the way ADR-030's `ITEM_MAX` did — one new fixture moves, nothing else.
- **Eval said:** `nvda-2024-shallow` goes RED — `doc_status 'success' !=
  'success_with_warning'`. NVIDIA FY2024 answers Item 8 in 209 chars, and the
  statements it points at are inside **Item 15's** span (audit report at
  offset 230,451; item 15 is 230,364–338,303, established by offset
  containment on the pipeline's own output).
- **Corrected:** not the threshold — the ruling. NVIDIA is a fourth,
  unenumerated member of ADR-019 §e's internal-pointer class, and its
  warning-free `success` was the overclaim. The case becomes the real-filing
  pointer pin, the exact-`success` audit pin moves to `cat-2023-shallow`
  (which is genuinely clean and 2 orders of magnitude clear of the floor), and
  ADR-035 §e2 records the swap with the offsets behind it.

- **Assumed:** the D8 row's other option — coupling `unattributed_content` to
  the items whose spans abut the unattributed region — was a plausible
  alternative worth measuring against the floor.
- **Eval said:** it is structurally incapable of naming the right item.
  `unattributed_content` measures preamble + tail, so the abutting spans are
  by construction the FIRST and the LAST — measured over the 12 documents the
  floor fires on, the first span is item 1 on all 12 and the last is item
  14/15/16 on all 12. The coupling names a flagged item on 1 of 12, and
  nothing at all on the eleven real pointer filings.
- **Corrected:** rejected in ADR-035 §b3 as a rule about item ORDER rather
  than item content, with the 1-of-12 count, instead of being left as an
  unexplored "and/or" in the ledger row.

- **Assumed:** a synthetic stub-collapse fixture would need `no_empty_success`
  to be tightened too, since that check is named for this failure mode.
- **Eval said:** `no_empty_success` PASSES on the synthetic — 1,003 spanned
  chars against `NO_EMPTY_SUCCESS_FLOOR` 1,000, clearing it by three
  characters, the same way held-out `intc-2025` clears it by 727.
- **Corrected:** the floor is NOT moved (it is a different constant with a
  different band, and moving it inside this PR would be an unmeasured change);
  the case asserts `no_empty_success` anyway so the three-character miss stays
  visible on the record, and `low_item_coverage` is what actually catches the
  shape.

- **Assumed:** the threshold mutations would each show their band edge going
  red, the way ADR-030 §f's did.
- **Eval said:** two of the five mutations reported PASS on the first run —
  the `COVERAGE_MIN` ones, whose replacement string is the same byte length as
  the original, written inside the same wall-clock second as the previous
  mutation. Python invalidates a `.pyc` on `(int(mtime), size)`, so the
  mutated source was never imported.
- **Corrected:** the mutation harness drops `src/sec10k/__pycache__` between
  runs. Both edges then went red as expected, and the near-miss is worth
  recording: a mutation test that silently does not mutate reports exactly the
  same "PASS" as a threshold that is genuinely unpinned.
