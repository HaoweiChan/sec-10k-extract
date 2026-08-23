# ADR-031 — D4: a marked, empty heading is resolved by a footnote that names the item and an external document

Date: 2026-08-23. Status: accepted. Implements D4 — the promoted Debt row
"Cross-item footnote IBR" (`tasks/TODO.md`), enumerated since 2026-08-17 as
`evals/adversarial/ba-2003-asterisk-ibr.json` in the unscored `debt` suite.
Sanctioned exception to the T8 feature freeze (`tasks/TODO.md`, **Freeze
guard**), on the pattern [ADR-020](ADR-020-fallback-not-justified.md)
established for T12 and [ADR-026](ADR-026-boilerplate-chrome-exclusion.md) /
[ADR-029](ADR-029-structured-tables-annotation.md) /
[ADR-030](ADR-030-non-last-span-dominance.md) applied for S6/S7/D3. Amends
ADR-004 (the definition of "a pointer" gains a second location), ADR-011 (what
an IBR span points at, for this one shape) and `specs/001-sec10k-contract.md`
(the IBR offsets rule), each in place with a dated note.

**Ruling**: a heading whose line ends in an asterisk run (`\*+`), over a body that is EMPTY (whitespace only), is `incorporated_by_reference` when a footnote anywhere in `normalized_text` begins with the SAME asterisk run, names that item's code in an `Items 5, 10, 11, 13 and 14`-style list, and carries both pointer signals `classify()` already demands (`IBR_RE` + `EXTERNAL_DOC_RE`). The item's span stays its own heading line (the marker is the in-span evidence); the footnote's offsets are published at `evidence.footnote = {start, end}`; confidence is the standard `BASE_IBR` 0.85; `method` is unchanged.
**Because**: Boeing FY2003 marks five items with a bare `*` and resolves it once, inside item 14's body; items 11 and 13 have whitespace bodies and read `extracted` 0.95 over 34 and 59 chars — the silent-failure shape — and no label-free validator can see an empty span. Measured over all 47 committed documents (42 dev + 5 held-out, read-only) the marked-heading convention occurs in exactly one filing and with exactly one marker, and the two conditions together (marker on the heading, empty body) are what keep the rule off the two other filings whose footnotes name items and an external document.
**Enforced by**: `evals/adversarial/ba-2003-asterisk-ibr.json` (`fast` + `invariant`; red at `origin/main` `1343bf8` as enumerated debt), `src/sec10k/segment.py::_demo` (seven `footnote_pointer` assertions), `src/sec10k/test_eval_adapter.py::test_ibr_spans_are_checked` (the `evidence` anchor), `evals/adversarial/era-label-ba-2003.json` (item 13's confidence pin, amended).

---

## a) Why this is a sanctioned exception and not scope creep

The freeze guard says a post-T8 capability is scope creep "no matter how good
it looks". Cross-item reference resolution IS a capability — the Debt row, the
case's own triage note and `docs/product/milestones.md` all said so and
declined to build it for exactly that reason. It is in scope now for the three
reasons ADR-026 §a gave, re-checked:

1. **The human asked for it in writing, on the record** — the D4 row of
   `tasks/TODO.md` (2026-08-23) promotes the Debt row and demands an ADR
   before any code, with the census, the rule, the marker set, the footnote's
   permitted position, the span ruling under ADR-011 and the not-claimed list
   named as deliverables. This document is that ADR.
2. **ADR-020/026/029/030 set the shape: a post-freeze capability gets a
   written ruling with its cost named, whichever way it goes.** "NOT
   JUSTIFIED" was an allowed outcome; §b is the measurement that decides it,
   and it rules IN — on a convention that occurs once in the corpus, which is
   why the rule is as narrow as §c makes it.
3. **It changes no existing behaviour on any committed document but the one
   it is for.** §g is the measured blast radius: of 47 documents, exactly one
   (ba-2003) changes, in exactly the two items the case names; no offset,
   warning or `doc_status` moves anywhere; table fidelity is unchanged.

## b) The census

Instrument: `extract_items` at `origin/main` `1343bf8` over every committed
fixture directory (42 dev: 38 span-bearing — 26 real filings and 12
self-created derivatives — and 4 refusals) and, **read-only, reported
separately and not tuned on**, the 5 held-out filings. Two scans per
document: (i) every accepted heading's `heading_text` for a trailing marker,
searched with the WIDE set `(\*+|†|‡|\(\d{1,2}\)|\([a-z]\)|\[\d+\])\s*$` so
the answer is what occurs, not what was guessed; (ii) every line of
`normalized_text` that BEGINS with a marker from the same wide set, then the
subset that names an item number (`\bitems?\s+\d`) and, over the paragraph
(to the next blank line, flattened), matches `EXTERNAL_DOC_RE` — the one
external-document list the pipeline has; no second list is grown.

### b1. Headings with a trailing marker — dev

| fixture | item | marker | body after the heading line | status · confidence at main | chars |
|---|---|---|---|---|---|
| ba-2003 | 5 | `*` | substantive (exchanges, holder count, a "certain information" pointer) | `extracted` · 0.95 | 587 |
| ba-2003 | 10 | `*` | substantive (codes of conduct, director and officer bios) | `extracted` · 0.95 | 14,911 |
| ba-2003 | 11 | `*` | **empty** — whitespace only | `extracted` · 0.95 | 34 |
| ba-2003 | 13 | `*` (a space before it: `Transactions *`) | **empty** — whitespace only | `extracted` · 0.95 | 59 |
| ba-2003 | 14 | `*` | the footnote itself (so the body opens with the pointer) | `incorporated_by_reference` · 0.85 | 321 |

**Five marked headings in the whole dev corpus, all in one filing, all the
same marker.** No dagger, no `**`, no `(1)`/`(a)`/`[1]` on any heading of
any other document. The earlier triage wording "heading and page furniture"
was imprecise and is corrected in the case: items 11 and 13's bodies are
whitespace only; the page furniture (`121` / `Table of Contents`) sits at the
END of item 10's span and of item 14's.

### b2. Marker-led lines — dev

| count | what |
|---|---|
| 1,547 | lines beginning with a marker from the wide set (table footnotes, exhibit-index notes, list markers) |
| 301 | …of which asterisk-led |
| 14 | …marker-led AND naming an item number |
| **3** | …AND matching `EXTERNAL_DOC_RE` over the paragraph |

The three, in full:

| fixture | offset | marker | names | `IBR_RE` | what it is | any marked heading in the document? |
|---|---|---|---|---|---|---|
| ba-2003 | 402285 | `*` | Items 5, 10, 11, 13 and 14 | yes | the Part III footnote, inside item 14's span: "* Certain information required by Items 5, 10, 11, 13 and 14 is incorporated herein by reference to the registrant's definitive proxy statement, which will be filed with the Commission within 120 days after the close of the fiscal year." (236 chars) | yes — the five in §b1 |
| wmt-2010 | 105277 | `*` (the exhibit number `*13`) | Items 1, 2, 3, 5, 6, 7, 7A, 8 and 9A | yes | an EXHIBIT-INDEX entry: "*13 Portions of our Annual Report to Shareholders … All information incorporated by reference in Items 1, 2, 3, 5, 6, 7, 7A, 8 and 9A of this Annual Report on Form 10-K from the Annual Report to Shareholders … is filed with the SEC." | **no** — none of the nine named items carries a marker, and none has an empty body (1: 31,116 chars `extracted`; 6/7/7A/8 already IBR by their own bodies, 294–552 chars; 9A 3,890 `extracted`) |
| interior-span-dominates | 105243 | `*` | same | yes | the wmt-2010 derivative (ADR-030) — the same line | no |

The other 11 marker-led item-naming lines name a regulation item ("Item 601
of Regulation S-K", "Item 5.03 of Form 8-K", "Item 15(b)") or an internal
section and match no external document; they are listed in the not-claimed
set (§i) and the rule never reaches them.

### b3. Held-out — read-only, reported, not tuned on

| | count |
|---|---|
| documents | 5 (all span-bearing) |
| headings with a trailing marker (wide set) | **0** |
| marker-led lines | 195 (24 asterisk-led) |
| …naming an item number | **0** |
| …and matching `EXTERNAL_DOC_RE` | **0** |

No held-out document has either half of the convention. Nothing here enters
the rule's derivation; the five numbers are reported so a reader can check
that the held-out set neither triggers nor contradicts it.

### b4. What the numbers say

- **The convention is real and it is rare**: one filing in 31 real ones (26
  dev + 5 held-out). A rule for it must be narrow enough that the 46 other
  documents are provably untouched (§g) and honest that it is fitted to one
  instance (§i).
- **Both halves are necessary.** wmt-2010 has the footnote half — a
  marker-led paragraph naming nine items and an external document, with
  `IBR_RE` — and no marked heading and no empty body; its nine items are
  correctly classified by their own bodies already. A rule keyed on the
  footnote alone would have re-judged nine correct items on one filing and
  its derivative; a rule keyed on the marker alone would flip ba-2003 items 5
  and 10, which carry real content. The marker on the heading AND the empty
  body AND the footnote naming the code are each load-bearing. Pinned how:
  the empty-body conjunct by the gate (remove it and items 5/10 flip, which
  the case forbids); the same-marker-run and names-THIS-code conjuncts by the
  CI self-check `segment._demo` ONLY — no corpus instance can pin them (an
  unmarked-heading mutation and a not-named mutation both flip nothing on all
  47 documents, PR #42 R2), so the gate cannot see them until a fixture
  carries a second marker or a footnote naming the wrong item.
- **The marker family is asterisk runs, exactly matched.** Only `*` occurs on
  a heading; `**` and `***` occur in the same filing as table-footnote
  markers (deliveries, debentures), which is why the heading's run and the
  footnote's run must be string-equal, not merely both asterisks. Daggers and
  numerals are not claimed — nothing in the corpus would test them.

## c) The rule

`src/sec10k/segment.py::footnote_pointer(code, heading_text, body, text)`,
called from `extract.py` only when `classify()` returned `extracted` for a
heading that was found:

1. `heading_text` ends in `MARKER_TAIL_RE = (\*+)\s*$` — else None.
2. `body.strip() == ""` — else None. The body is the span minus its heading
   line, the same `body` `classify()` read. ponytail: empty means
   whitespace-only, which is what the corpus has; a body of page furniture
   alone would not qualify, and the upgrade (a furniture strip) is named at
   the function, to be added when a fixture shows it.
3. For every line of `text` matching `FOOTNOTE_RE = ^[ \t]*(\*+)[ \t]*(?=\S)`
   whose asterisk run equals the heading's: take the paragraph to the next
   blank line (`PARA_END_RE = \n[ \t]*\n`; txt-era footnotes wrap), flatten
   whitespace, and require all three of — the item's code in the set named by
   `ITEM_LIST_RE = \bitems?\s+((?:\d{1,2}[A-D]?\b[\s,]*(?:and\s+)?)+)`
   (codes upper-cased, so `1a` matches `1A`); `IBR_RE`; `EXTERNAL_DOC_RE`.
   The first such paragraph wins; its `(start, end)` is returned.
4. `extract.py`: status becomes `incorporated_by_reference` and
   `evidence.footnote = {"start", "end"}` is added. Nothing else changes —
   not the span, not `method`, not `heading_text`.

**Where the footnote may sit — anywhere in `normalized_text`.** Measured: the
one instance sits 368,283 chars after item 5's heading, 3,255 after item
11's, in a different Part from item 5 (II vs III) and inside another item's
span. "Same Part" is therefore false on the only instance. "After the
heading" is true on it — but a rule fitted to one point should carry the
fewest parameters that point supports, and a footnote placed ABOVE the
headings it governs (a note at the head of Part III: "* Items 10–14 are
incorporated…") is the same convention; ADR-030 §b2 rejected a second
parameter the corpus could not pin for the same reason. The position-free
rule is the one with no untested constant; the same-marker + same-code +
two-signal conjunction is what bounds its false-positive surface, and §b2
shows that surface is one paragraph in 1,547 marker-led lines.

**Why not in `classify()`.** `classify` is body-only by contract ("`body` is
the span minus its heading line") and every caller and self-check depends on
that; the resolution needs the heading line and the whole document. A
separate function, called after `classify` returns `extracted`, leaves the
ADR-004/005/007/010/015/017 rulings and their assertions byte-identical and
makes the mutation in §h a one-line removal.

## d) What the IBR span points at — and the alternative rejected

ADR-011 rules that an IBR item's `start`/`end` point at "the item's own
pointer text — the sentence naming the other document", because that sentence
is the evidence a human reads. Here the sentence lives inside ANOTHER item's
span (item 14's, 402235–402556), and INV-S1 / `no_overlap_ordered` forbid two
span-carrying items from overlapping.

**Ruling: the item's span stays its own heading line** — `Item 11. Executive
Compensation*`, 34 chars; `Item 13. Certain Relationships and Related
Transactions *`, 59 chars. The marker on that line is the in-span half of the
evidence (it is what a reader sees on the page and what sends them to the
footnote). The footnote's offsets are published at `evidence.footnote`
`{start, end}` — offsets into `normalized_text`, never a second copy of the
text (the contract's no-`text`-field rule). `evidence`'s internal shape is
"implementation-owned and may evolve without an ADR"
(`specs/001-sec10k-contract.md`, Envelope fields), so adding the key is NOT a
contract change; the IBR offsets paragraph of the contract IS narrowed by
this ruling and is amended in place to say so. The eval adapter gains the one
thing needed to make the design falsifiable: an `"evidence": "footnote"` key
on any span-reading check (`text_contains`, `text_not_contains`, `min_chars`,
`max_chars` — `EVIDENCE_CHECKS`) resolves the item's offsets to
`evidence[key]` once, so containment AND extent are pinnable; the key must
exist, and every other check type REFUSES it loudly rather than silently
checking the span (PR #42 R1 — the first cut honoured it on `text_contains`
only, and a wrong footnote slice passed). `test_ibr_spans_are_checked` and
`test_evidence_key` prove both directions.

**Rejected: point the span at the footnote.** It would put the pointer
sentence where ADR-011 says it belongs — and it would overlap item 14's span
(INV-S1 violation; `no_overlap_ordered` and `verbatim`'s "span opens with its
own `heading_text`" both go red), or require clipping item 14's span around
it (a discontiguous or truncated item 14, which INV-S2 and the "no
discontiguous span" ruling of ADR-019 §f refuse), or require a second
span-kind the contract does not have. Every one of those is a larger change
than a key in `evidence`, and two of them are invariant changes. Also
rejected: a new per-item top-level field (`footnote_start`/`footnote_end`) —
a contract change for a shape that occurs once; `evidence` is the place the
contract already designates for "recomputable from each item's evidence".

**`method` is unchanged** (`heading_strict` for both items). ADR-027 §b made
`method` name the heading-match tier by the same cut that pays the confidence
base; the heading WAS found by the strict line-anchored match (similarity
1.0), and what changed is the status, whose cause is recorded in `evidence`.
A `footnote_resolved` enum value would be a contract change
(`envelope_shape` refuses values outside the enum) that splits one axis
(how the heading was found) across two; not built, and the case pins
`heading_strict` on item 11 so that a later change is a decision.

## e) Confidence — `BASE_IBR` 0.85, no new constant

The ADR-008/018 scale is an ordinal evidence encoding: status tier, title
match, warning count, document verdict. The footnote-resolved item's evidence
is the same two signals a body pointer must carry (`IBR_RE` +
`EXTERNAL_DOC_RE`) plus one the body pointer does not — the footnote names
the item BY NUMBER. The difference from a body pointer is location, not
strength. A lower tier (say 0.80) would be a pre-data constant with no
measured band: one filing, two items, no case in which the rule is wrong to
bound it from below. ADR-018 rejected exactly that kind of remap. So: 0.85,
pinned on both items; the trigger for revisiting is the first fixture on
which `footnote_pointer` resolves an item wrongly — that case, not this ADR,
would choose the number.

## f) What the validators and the structural checks see afterwards

- `no_empty_success`: the extracted total drops by 93 chars (34 + 59) on a
  document spanning ~400K; unaffected.
- `validate()`: items 11 and 13 move from `spans` (content-shape checks) to
  `hygiene_spans` only (ADR-011) — both spans open with their own heading
  (`boundary_hygiene` silent). They are not Item 8/1A and were under
  `SUBSTANTIVE_MIN`, so `numeric_density_inversion` / `keyword_fingerprint`
  never read them. `unattributed_content`: the first span is still item 1 and
  the last still item 15 — unchanged. `last_item_dominates` /
  `item_dominates`: unchanged (largest non-last span is still item 8 at
  0.4127, ADR-030 §b1). `doc_status` stays `success`; zero warnings before
  and after.
- `no_overlap_ordered` / `verbatim` / INV-S1 / INV-S2: the two spans did not
  move; the footnote lives in `evidence`, which no span invariant reads.
- The web inspector renders `evidence` generically; nothing there changes.

## g) Blast radius — main `1343bf8` vs this branch, all 47 committed documents

Instrument: a scratch snapshot of `extract_items` (every item's status,
confidence, offsets, `method`, `evidence.warnings`, `evidence.footnote`;
every warning `(code, item)`; `doc_status`) over `evals/fixtures` (42) and
`evals/heldout/fixtures` (5), run against both trees and diffed.

| fixture | what changed | clause |
|---|---|---|
| `ba-2003` item 11 | `extracted` 0.95 → `incorporated_by_reference` 0.85; offsets 399030–399064 unchanged; `method` unchanged; `+ evidence.footnote {402285, 402521}` | §c, §d, §e |
| `ba-2003` item 13 | `extracted` 0.95 → `incorporated_by_reference` 0.85; offsets 402176–402235 unchanged; `method` unchanged; `+ evidence.footnote {402285, 402521}` | §c, §d, §e |
| `ba-2003` items 5, 10, 14 and every other item | identical | §b1, §c step 2 |
| every other dev fixture (41) | identical in every field the snapshot reads | — |
| every held-out fixture (5) | identical | §b3 |

**1 document of 47; 2 items.** No offset moves anywhere. No warning, no
`doc_status` change. `normalized_text` untouched. Table fidelity unchanged:
`cells 1.0000 (400/400), rows 1.0000 (31/31)`. `extractor_version` →
`0.8.0-d4`. One case's asserted value changes: `era-label-ba-2003` pinned
item 13's confidence at 0.95 as "the era label must not move the confidence"
— the pin moves to 0.85 with a dated provenance note, its purpose intact
(items 12 and 15 stay 0.95).

## h) Red line, pins, mutations, gate

**Red at `origin/main` `1343bf8`** — `python3 -m evals.run --suite debt`:
`[DEBT] ba-2003-asterisk-ibr: STILL RED — cross-item-footnote-convention`;
failures `item 11 not incorporated_by_reference: extracted` · `item 13 not
incorporated_by_reference: extracted`. The `[DEBT]` enumeration reads 4 lines
at main and 3 on this branch (`axp-2008-combined-part-iii`,
`cvx-2015-internal-pointer`, `msft-2013-website-block` remain).

**The case now pins** (26 checks; the original five kept, twenty-one added):
items 11/13 IBR at 0.85; item 11 `method heading_strict`; item 11's span
contains `Executive Compensation*` and is ≤ 34 chars, item 13's ≤ 59 (the
span is the heading line); `evidence.footnote` on BOTH 11 and 13 carries the
footnote's first 114 chars verbatim, its last 51 (`within 120 days after the
close of the fiscal year.`) and is exactly 236 chars (`min_chars` +
`max_chars` on the evidence — head, tail and length together fix the slice
at 402285–402521, PR #42 R1); items 5 and 10 `extracted` at 0.95 (a
substantive body under the same marker is never flipped); item 14 IBR with
`definitive proxy statement` in its own span (the body path, untouched).

**Mutations** (each run on this branch with bytecode caching off, the case
re-run after restore):

| mutation | result |
|---|---|
| `extract.py`: the `footnote_pointer` call replaced by `None` | RED — `item 11 not incorporated_by_reference: extracted`, same for 13, `confidence 0.95 != 0.85` ×2, `item 11 has no evidence span 'footnote'` ×2 |
| `segment.py`: `EXTERNAL_DOC_RE` swapped for `INTERNAL_REF_RE` in the footnote test (the "non-external target" mutation) | RED — identical six lines: the proxy-statement footnote is not an internal pointer, so nothing resolves |
| `extract.py`: `evidence.footnote` never written | RED — `item 11 has no evidence span 'footnote'`, same for 13, and nothing else: the evidence checks are the only ones that see the key, and they do |
| `segment.py`: `PARA_END_RE` never matches (PR #42 R1's repro) — `footnote_pointer` returns (72070, 414197), a different `*`-led line of 342,127 chars | before R1: GREEN 19/19 (containment only). After: RED — `item 11 has 342127 chars > 236`, same for 13 |

Layer echo in `segment._demo`: positive on a wrapped txt-style footnote for
items 11 and 13 (the second with a space before its marker); None for a
non-empty body (item 10), for an unmarked heading, for a code the footnote
does not name (12), for a `**` heading against a `*` footnote, and for the
same footnote rewritten to point at "Item 7 of this Form 10-K" (ADR-004:
internal targets are not IBR).

**Gate after**: `invariant 51/51 = 1.000` (+3 enumerated debt, unscored),
`fast 99/99 = 1.000` (+3), table fidelity 400/400 · 31/31,
`.eval-baseline.json` untouched (`{"fast": 1.0}`), `segment` / `validate` /
`eval_adapter` 19/19 / `bench --self-check` ok, `--check-docs` 68 / 0
unmatched.

## i) What this ADR does NOT claim

- **Markers other than asterisk runs** — daggers, `(1)`/`(a)`/`[1]`,
  superscripts: none occurs on any committed heading (§b1), so none is built;
  the first fixture that carries one adds its marker here, with its own
  census line.
- **A marked heading over a NON-empty body** — ba-2003 items 5 and 10 stay
  `extracted` (ADR-004 shape 3; the footnote says "certain information"), and
  the case pins them. Whether a marker over a short furniture-only body
  should resolve is not decided (§c step 2's named ceiling).
- **A footnote with no item numbers, or one naming a regulation item** — the
  11 marker-led lines of §b2 that name "Item 601 of Regulation S-K", "Item
  5.03 of Form 8-K", "Item 15(b)" and the like never pass step 3 (no
  `EXTERNAL_DOC_RE`, or the named code is not the heading's); they are
  enumerated so the claim "3 of 1,547" can be re-run.
- **Ranges and prose lists** — "Items 10 through 14", "Items 10 to 14": not
  observed, not parsed; `ITEM_LIST_RE` takes comma/and lists only.
- **Sub-item references are not guarded** (PR #42 R3) — `ITEM_LIST_RE` reads
  "Item 5.03 of Form 8-K" as naming `5` and "Item 15(b)" / "Item 15(a)(3)" as
  naming `15` (axp-2008 @326904 and xom-2021 @385888 are two of §b2's 11
  non-external lines with that shape). Harmless on the corpus — none of those
  paragraphs matches `EXTERNAL_DOC_RE`, and no heading is marked — but a
  false-positive surface this list must name; a lookahead that excludes a
  dotted or parenthesised continuation is the fix when a fixture needs it,
  chosen with care because a list that ENDS a sentence ("…Items 11 and 13.")
  must still name 13.
- **A footnote that resolves to an internal target** ("* Items 11 and 13 are
  in Item 7 of this report") — ADR-004 shape 2, stays `extracted`; the
  `_demo` assertion and the `INTERNAL_REF_RE` mutation both cover it.
- **wmt-2010's exhibit-index note** — it is not a heading marker; its nine
  items are classified by their own bodies and the rule does not look at it
  (§b2, §b4). The `cvx-2015` internal pointer and the `axp-2008` combined
  heading stay in the Debt table, untouched.
- **The per-item near-empty-success validator is NOT built** (PR #42 R4) —
  the debt triage's "second half": a label-free layer-8 check that flags an
  `extracted` span that is near-empty for an item whose canonical content
  cannot be trivial. `no_empty_success` is document-total only, and nothing
  in the battery reads a single span's emptiness; ba-2003 items 11/13 are
  caught by THIS rule's resolution, not by a validator. Carried as a Debt row
  (`Origin: PR #42 R2/R3/R4`).
- **Held-out** — no threshold or pattern was tuned on it; §b3 is a read-only
  report showing it carries neither half of the convention.
- **That the rule generalises beyond the one filing it is fitted to** — it is
  a narrow conjunction whose false-positive surface on the corpus is one
  paragraph; the second real instance, when a fixture brings one, is the
  test, and if it breaks the rule the case that breaks it chooses the repair.

## Verification

`--suite invariant` 51/51 = 1.000 (+3 enumerated debt, unscored);
`--suite fast` 99/99 = 1.000 (+3); table fidelity cells 400/400, rows 31/31.
`.eval-baseline.json` untouched (`{"fast": 1.0}`, matches). No
`--update-baseline`, no `--no-verify`. Held-out run not performed (nothing was
tuned on it; §b3 is a read-only measurement).
