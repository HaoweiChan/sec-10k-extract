# 018 — D4: the cross-item footnote the freeze deferred, built as narrowly as the census allows (2026-08-23)

`ba-2003-asterisk-ibr` sat in the unscored `debt` suite from 2026-08-17: Boeing
FY2003 marks Items 5, 10, 11, 13 and 14 with a bare `*` and says once, in a
footnote inside item 14's body, that they are incorporated by reference to the
proxy statement. Items 11 and 13 have whitespace bodies and read `extracted`
0.95 over 34 and 59 chars — the silent-failure shape this repo exists to hunt —
and the triage note said why it was not fixed: cross-item resolution is a
capability, and the T8 freeze forbids one. The D4 row promoted it with the
deliverables written in: a census first, then the rule, the marker set, where
the footnote may sit, what the IBR span points at under ADR-011, what is not
claimed. Ruling: [ADR-031](../specs/decisions/ADR-031-footnote-marker-ibr.md).

## The prompt decisions that mattered

- **Census before rule, with a WIDE net, so the marker set is measured and not
  invented.** The orchestrator's instruction was explicit — "measure what
  actually occurs, do not invent a set" — and the scan searched headings for
  `*`, `**`, daggers, `(1)`, `(a)`, `[1]`. The answer is five headings in 47
  documents, all one filing, all `*`. The rule therefore claims asterisk runs
  only, exactly matched (the same filing uses `**`/`***` as table-footnote
  markers), and names daggers and numerals as not built rather than
  "supported".

- **Both halves of the convention are necessary, and the corpus proves it.**
  The footnote-side scan found THREE marker-led paragraphs naming items and an
  external document, not one: ba-2003's footnote and wmt-2010's exhibit-index
  note ("*13 Portions of our Annual Report to Shareholders … incorporated by
  reference in Items 1, 2, 3, 5, 6, 7, 7A, 8 and 9A"), plus the latter's
  ADR-030 derivative. wmt-2010 has no marked heading and no empty body; its
  nine items are correctly classified by their own bodies. A rule keyed on the
  footnote alone would have re-judged nine correct items; a rule keyed on the
  marker alone would flip ba-2003 items 5 and 10, which carry real content.
  So the rule is the conjunction — marker on the heading, empty body, footnote
  with the same marker naming the code and both pointer signals — and the case
  pins every leg (items 5/10 stay `extracted` 0.95; item 14 stays IBR by its
  body).

- **The span ruling was forced by an invariant, not chosen by taste.** ADR-011
  says an IBR span points at the pointer sentence; here that sentence lives
  inside item 14's span and INV-S1 forbids overlap. The smallest honest design
  keeps the item's own heading line as the span (the marker is what a reader
  sees) and publishes the footnote's offsets at `evidence.footnote` — which the
  contract already declares implementation-owned, so it is not a contract
  change, though the IBR offsets paragraph is narrowed and says so. The
  rejected alternative (point the span at the footnote: overlap, or a clipped /
  discontiguous item 14, or a new span-kind) is written down with the
  invariants each variant would break.

- **Make the evidence falsifiable before claiming it.** A design that puts
  offsets in `evidence` is unverifiable until a check reads them. The adapter's
  `text_contains` gained an `evidence` key that anchors the slice at
  `evidence[key]` and fails when the key is absent; the self-check proves both
  directions, and the third mutation (evidence key dropped) goes red on exactly
  those two anchors and nothing else.

- **Position: anywhere, and say why that is the fewer-parameter rule.** The one
  instance sits after all five headings, in a different Part from item 5,
  inside another item's span — "same Part" is false on the only data point,
  "after the heading" is true on it. A position constraint would be a second
  parameter fitted to one point (the thing ADR-030 §b2 rejected); the
  same-marker + same-code + two-signal conjunction is what bounds the
  false-positive surface, and the census shows that surface is one paragraph
  in 1,547 marker-led lines.

- **No new confidence constant.** The footnote carries the same two signals a
  body pointer must, plus the item's number; the difference is location, not
  strength. A lower tier would be a pre-data number with no band (one filing,
  two items). `BASE_IBR` 0.85, pinned; the trigger for revisiting is the first
  fixture on which the rule is wrong.

## Assumption → Eval contradiction → Correction

- Assumed: the triage note's description — items 11/13's bodies are "heading
  and page furniture".
- Eval said: the inspect run — both bodies are whitespace only; the page
  furniture (`121` / `Table of Contents`) sits at the END of item 10's span.
- Corrected: the rule's empty-body test is exact (`body.strip() == ""`), the
  case's provenance and ADR-031 §b1 say so, and the furniture-only body is
  named as a not-decided ceiling at the function rather than guessed at.

- Assumed: a mutation that restores a file by `cp` is a clean re-run.
- Eval said: after the `INTERNAL_REF_RE` mutation (same byte length as
  `EXTERNAL_DOC_RE`) and a same-second restore, the case stayed red on the
  restored tree — Python's `.pyc` keyed on (mtime-seconds, size) was stale.
- Corrected: `__pycache__` cleared, every mutation re-run with `python3 -B`,
  and the ADR's mutation table is from those runs; the first contaminated
  reading of mutation 3 (full red set) was replaced by the true one (the two
  evidence anchors only).

- Assumed: no committed case read item 13's confidence on ba-2003.
- Eval said: `era-label-ba-2003` pinned it at 0.95 (`item 13 confidence 0.85
  != 0.95` on the first fast run).
- Corrected: the pin moves to 0.85 with a dated provenance note — the check's
  purpose (the era label must not move the confidence) is intact, items 12/15
  stay 0.95, and ADR-031 §g lists it as the one asserted value that changed.
