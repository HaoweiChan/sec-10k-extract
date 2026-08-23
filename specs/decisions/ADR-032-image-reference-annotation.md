# ADR-032 — S10: image REFERENCES are reported as opt-in point offsets into an unchanged `normalized_text`; fetching the image BYTES is ruled out of S10, and no image bytes are committed

Date: 2026-08-23. Status: accepted. Implements S10. Sanctioned exception to the
T8 feature freeze (`tasks/TODO.md`, **Freeze guard**), on the pattern
[ADR-020](ADR-020-fallback-not-justified.md) established for T12 and applied by
[ADR-026](ADR-026-boilerplate-chrome-exclusion.md) (S6),
[ADR-029](ADR-029-structured-tables-annotation.md) (S7) and
[ADR-030](ADR-030-non-last-span-dominance.md) (D3).

**Ruling**: the S10 capability ships as its **offline half only**. `extract_items(path, images=True)` adds one envelope key, `images` — a list of `{offset, src, alt, width, height}` records, one per HTML `<img>`, in document order; `offset` is a **point** into `normalized_text` (an image emits no text, so it has no span), which is byte-identical with the flag on and off, as are every item offset, `doc_status` and `warnings`. The item an image falls in is **derived from offsets**, never stored, exactly as ADR-029 derives an item's tables. The **fetch half is ruled OUT of S10** — no network call, no cache, no inspector route — and **no image bytes are committed as fixtures**; §c names the cost of that ruling in both directions.
**Because**: the bytes are not in the fixtures — every one of the 53 `<img>` in the committed corpus is an external reference to a sibling document in its EDGAR accession, none is an inline `data:` URI — so the only half of "extract the images" that can be gated offline, by the eval set that is this repo's spec, is the reference. Recording it costs the text run nothing it does not already have (the position counter is already there and the recorder never emits), moves no offset anywhere, and makes "on and off are identical" true by construction; fetching, by contrast, buys a network dependency, a cache, and an eval case that either hits EDGAR on every run or is mocked — and hard rule 4 forbids the second.
**Enforced by**: `evals/golden/bac-2006-images.json`, `evals/golden/xom-2021-images.json`, `evals/golden/jpm-2024-images.json`, `evals/adversarial/images-refusal-path.json`, `evals/adversarial/images-in-table-cell.json` (fast) and `evals/adversarial/images-offsets-invariant.json` (invariant + fast); `src/sec10k/eval_adapter.py` (`image`, `images_sane`, `offsets_invariant_under_images`, and `envelope_shape`'s `_images_shape`); `src/sec10k/normalize.py::_demo` and `src/sec10k/test_eval_adapter.py::test_image_checks` — see §g.

---

## a. Why this is a sanctioned exception and not scope creep

The freeze guard says a post-T8 capability is scope creep "no matter how good
it looks". S10 is in scope for the three reasons ADR-026 §a gave for S6 and
ADR-029 §a re-checked for S7, each re-checked again here rather than inherited:

1. **The human asked for it in writing, on the record** — the S10 row of
   `tasks/TODO.md`, 2026-08-23, which also demanded "its own ADR before any
   code". This document is that ADR; the code in this PR was written to it.
2. **ADR-020/026/029/030 set the shape: a post-freeze capability gets a
   written ruling with its cost named**, whichever way it goes. This one is
   ruled IN for the reference half and **OUT for the fetch half**, and both
   costs are measured — §f for what shipped, §c for what did not.
3. **It changes no existing behaviour.** With the flag off — every existing
   caller, every existing eval case, the web inspector — not one byte of any
   envelope moves. §d proves it two ways: a main-vs-HEAD snapshot over all 54
   committed dev fixture files and all 5 held-out ones is byte-identical, and
   the equality is asserted on every run by `images-offsets-invariant`
   (invariant suite).

What would have made it scope creep — rendering placeholders into
`normalized_text`, or shipping a network fetcher whose only eval case is a
mock — is refused in §c and §e.

## b. What is recorded, and what is not

### b1. The record (`src/sec10k/normalize.py::_Plain`, `normalize(..., images=True)`)

The existing one-pass HTML walk already visits every `<img>`: it is neither a
`BLOCK_TAG` nor a `CELL_TAG`, so today it emits nothing and is forgotten. With
`images=True` the same walk notes, against the running length of the text it is
emitting, **where** each `<img>` sits and what its attributes say. It never
emits anything extra: the recorder reads the position counter, it does not
write to the text — the identical rule ADR-029 §b1 states for tables, and the
reason the two annotations compose in one pass (§b4).

One record per `<img>`, wherever it sits, including inside a table cell — but
see §b2a for what an in-cell offset does and does not mean:

| field | meaning |
|---|---|
| `offset` | a **point** into `normalized_text`, where the image sits in the reading order. Not a span: an `<img>` emits no text, so there is nothing to bound. Two adjacent images therefore share an offset, and that is the correct answer, not a collision (§b2) |
| `src` | the `src` attribute verbatim, entity-decoded by `html.parser`; `null` when the tag has none |
| `alt` | the `alt` attribute verbatim, entity-decoded; `null` when the tag has none (4 of the corpus's 53, all in cvx-2015). Reported as the filer wrote it and never improved — 5 of bac-2006's say only "LOGO", 3 of jpm-2024's are bare Workiva asset ids |
| `width`, `height` | the declared pixel size as an int, or `null`. The `width=`/`height=` attribute first, then a `width:Npx` / `height:Npx` declaration in `style`. **0 of the corpus's 53 images carry the attribute form and 40 carry the style form**, so recording only the attribute would have shipped a field that is `null` on every committed filing — a field no case could pin, which is the untestable-code-path sin ADR-010 named. Anything that is not a whole POSITIVE number of pixels answers `null` rather than a wrong number: a non-pixel unit (`50%`, `auto`), a zero (`width="0"`, the classic spacer gif) and a fractional declaration (`0.75px`, `1.5px`). The last two were PR #44 R2: they returned 0 and 1, and 0 is a value `_images_shape` and specs/001 ("positive int") both refuse, so the extractor could emit an envelope its own contract rejects. 0 of the 53 committed images trigger it; `normalize.py::_demo` is the whole guard |

Offsets are recorded pre-`_tidy` and moved by the **same** `_sub_map` machinery
ADR-029 §b1 introduced for table marks — the marks-carrying path calls
`rx.sub(repl, text)` on the identical pattern and replacement, so the text
cannot differ from the marks-free path. Nothing is tightened afterwards
(there is no span to tighten) and nothing is dropped: every `<img>` in the
document is a reference a reader would otherwise lose in silence, including
one with no `src` at all.

An `<img>` inside `SKIP_TAGS` (`<title>`, `ix:header`, `ix:hidden`, `script`,
`style`) is **not** recorded — those are machine metadata by INV-S5, and an
image inside them is not part of the readable filing. No committed fixture has
one; `normalize.py::_demo` pins it synthetically.

### b2. Document order is non-decreasing, not strictly increasing

xom-2021's cover signature block holds three adjacent `<img>` elements
separated by 216 bytes of markup each; that markup emits only whitespace, which
ADR-003's canon collapses, so all three report **offset 232186**. Four such
coincident pairs exist in the corpus. This is the correct answer — an image
occupies no characters, so two images between the same two words are at the
same place — and both the contract shape (`_images_shape`) and the case
(`xom-2021-images`) pin it, so an implementation cannot "fix" it by nudging
offsets apart. Nudging would be a text edit by another name.

### b2a. An in-cell image is usually OUTSIDE its table's recorded span

Corrected 2026-08-24 after PR #44 R1, which falsified the unconditional claim
§b1 first made. An image offset is a **reading-order point**. A table's
`start`/`end` and every cell's span are tightened to the table's **visible
text** (ADR-029 §b1) and an image contributes none, and an empty cell is
additionally clamped into its table's tightened span. The two therefore do not
nest in general:

- an image in a cell that **carries text** lands inside that cell's span;
- an image in a **text-empty** cell does not sit at any text, and if it
  precedes (or follows) all of the table's visible text the clamp puts every
  empty cell at the tightened boundary while the image stays where it was —
  outside the table span entirely.

**The corpus is entirely the second case.** 10 of the 53 `<img>` sit inside
`<table>` markup (cvx-2015 4 of 4, xom-2021 3 of 9, bac-2006 2 of 5, ba-2003
1 of 3) and **0 of 53 image offsets fall inside any recorded table or cell
span** — because a filer who typesets a graphic in a table gives it a cell of
its own, with no text in it. The named instance is the **xom-2021 cover
signature block**: g7/g8/g9 each have their own `<td colspan="3">` in the
leading rows of one table, all three report offset **232186**, and the table
is recorded at **(232188, 232373)** with every empty cell clamped to 232188 —
the images sit two characters before the table starts. bac-2006 does the same
at 391006 against a table at (391008, 391112).

This is not a defect and is not worked around: pulling the table span back to
swallow the images would break ADR-029's rule that a table span is tight to
its text, and moving the image offset would make it something other than where
the image is. It is a relationship that has to be **asserted rather than
assumed**, which is what the `image` check's `in_table` key and
`evals/adversarial/images-in-table-cell.json` now do, on the real xom-2021
images rather than on a synthetic cell built so it cannot expose the case.

### b3. No derived-view module, and no stored containing item

ADR-029 shipped `src/sec10k/tables.py` because a table record needs real
derivation: a grid, a Markdown rendering, colspan expansion. **An image record
needs none** — its fields *are* the answer. So S10 ships no `images.py`, by
ruling and not by omission. The two views a consumer wants are one expression
each, and they are written here so they are not reinvented five times:

- the images inside an item's `[start, end)`:
  `[im for im in env["images"] if start <= im["offset"] < end]`
- the item an image falls in: the item whose span holds `im["offset"]`, `None`
  when no span does (a cover-page image, or any image on a refusal envelope,
  which carries no items at all).

The containing item is **derived, never stored** — the same rule that keeps
item text out of the envelope (INV-S2) and a cell string out of a table record
(ADR-029 §b2). It is derived by the eval adapter's `image` check, which is
where the goldens' hand-labeled `item` values are compared, and it inherits
whatever quality the item spans have — see §e.

### b4. Opt-in, not always-on; and it composes with `tables`

`extract_items(path, images=False)` is the default and `normalize()` without
the flag is the pre-S10 code path plus a no-op branch. Ruled opt-in on the same
rule as ADR-026 and ADR-029, for consistency of the envelope contract rather
than for size: the annotation is small (§f), but "the key exists only when the
caller asked" is the contract these three capabilities share, and `[]` means
"asked, found none", which is a different answer from the key being absent. On
a refusal envelope (`unsupported`/`failed`) it is carried when asked, because
the images were normalized before the refusal was decided
(`images-refusal-path`).

`tables=True` and `images=True` are independent and may be passed together;
they share one `_Plain` pass and one `_tidy` marks map, so asking for both
costs one walk, not two, and neither changes what the other records
(`normalize.py::_demo`).

## c. The fetch half — ruled OUT of S10, with the cost named both ways

The S10 row separates two halves and demands a ruling on each. The reference
half ships (§b). **The fetch half does not ship.** No `src` is resolved against
an EDGAR accession index, nothing is downloaded, nothing is cached, and the
inspector gains no image route.

**What it would cost to ship it.** The `groundwork:cost-discipline` skill's
rules are the frame, and three of them bite:

- *Rule 4, "`fast` suite makes zero paid calls; paid/live cases are tagged
  `full` only, and their cached responses are committed so `full` is
  reproducible offline."* The cached response for an image is **the image
  bytes**. So "commit the cached response" and "commit an image fixture" are
  the same act, and a committed image joins the benchmark corpus — the S3
  upload-fixture ruling, and ADR-021 §b8's populations, which every published
  perf figure is derived from. The 53 images of this corpus are jpgs sized
  from 85×65 to 684×400; at even 60 KB each that is roughly 3 MB of binary
  added to a repository whose entire fixture corpus is text, and every figure
  derived from "the fixtures" would need restating to say which population it
  means.
- *Rule 2, "every external call is cached."* A cache is a directory, a key
  scheme, an eviction story and a staleness story. The inspector already has a
  process-local source cache with a `ponytail:` marker and an open debt row
  against it; adding a second, differently-shaped cache beside it is the
  refactor that row is waiting for, not a thing to bolt on inside S10.
- *Hard rule 4, "no mocked results — if a live dependency is unreachable, fail
  loudly."* A live-fetch case in the `full` suite is therefore a case that goes
  red when EDGAR is slow, rate-limits (10 req/s, declared User-Agent), or
  renames an accession path. That is the honest design and it is also a
  standing source of red runs that say nothing about this repository's code.

**What ruling it out costs.** Exactly this: a consumer gets the reference and
must resolve it themselves. The resolution is not hidden from them — `src` is a
relative filename inside the same EDGAR accession as the filing, so
`https://www.sec.gov/Archives/edgar/data/<cik>/<accession-no-dashes>/<src>` is
the whole rule, and it is written down here so that not shipping it is a
decision a reader can act on rather than a gap. No committed fixture can show
an image, and the inspector shows nothing where an image sits. That is the
whole of the loss, and it is what a Debt row (Origin: S10) records.

**Whether any image bytes are committed as fixtures: no.** Ruled here, as the
S10 row demands. Nothing in this PR adds a binary file. The corpus stays text,
ADR-021's populations do not move, and §f3 says so with the number on it.

## d. Offset invariance — the equality, asserted and measured

As ADR-026 §d and ADR-029 §d: `normalized_text`, `items`, `warnings`,
`doc_status` are identical with `images` on and off, the key is present on
exactly one side, and this is **asserted on every run** by
`offsets_invariant_under_images` in `images-offsets-invariant` (xom-2021,
invariant suite) and in `images-refusal-path` (aapl-2026-10q, the refusal
path).

Measured 2026-08-23 over **all 54 committed dev fixture files and all 5
held-out fixtures**: a snapshot of (normalized-text sha256, `norm_chars`,
`doc_status`, `warnings`, the sorted envelope key list, and every item's
`item`/`status`/`start`/`end`/`confidence`/`method`/`heading_text`) at
`origin/main` and at this branch's HEAD, **default flags**, is byte-identical
— the two JSON files compare equal byte for byte (`cmp`). Measured **twice**,
because `origin/main` moved mid-task when PR #42 (D4, ADR-031) merged:

| base | dev sha256 | held-out sha256 |
|---|---|---|
| 3e16f70, the branch point | `e7072435…a9b6aaf7` | `51de5a11…04957f3f` |
| c13aa5c, after merging D4 in | `19168a6e…30e9223a` | `51de5a11…04957f3f` |

The dev digest differs between the two rows because **D4** changed two
`ba-2003` item statuses; it is identical across `origin/main` and HEAD within
each row, which is the only comparison this section claims. Every published
normalized-length figure, every ADR-021 bench number
and every committed case anchor therefore stands unchanged. The script is
committed as `evals/snapshot.py` — it takes a tree root and writes the
snapshot, so the comparison is re-runnable rather than a claim, and it is
written for any capability flag rather than for this one (S9 will want it).

Also asserted on every run: every record's offset in bounds and in
non-decreasing order, every field of the declared type
(`_images_shape`, reached from both `envelope_shape` and `images_sane`, so a
record that is not in the contract shape is red on **any** case that asks for
images, not only on one that labels an image).

## e. What is NOT claimed

Ruled out honestly; each out-of-scope item someone might want is a Debt row in
`tasks/TODO.md` with `Origin: S10`.

| shape | ruling |
|---|---|
| fetching the bytes, caching them, serving them in the inspector | **out**, by ruling — §c, with the cost named both ways. Debt |
| committing image bytes as fixtures | **out**, by ruling — §c. Debt only in the sense that the fetch row subsumes it |
| classifying an image (chart / signature / logo) | **out**. The S10 row allows it only "if the ADR finds a zero-cost signal", and there is none that is honest: the *filer's own* `alt` carries it when they bothered (jpm-2024: "Jamie Dimon Signature.jpg", "pwclogoa24.jpg") and carries nothing when they did not (the same filing's "1036", "21625", "7161"), while bac-2006 says only "LOGO" on all five and xom-2021 repeats the filename on all nine. A classifier trained on that would be right on the images that already say what they are. The record carries `alt`, `src`, `width` and `height`; the consumer decides — the same ruling, for the same reason, as ADR-029 §e's refusal to call a table "data" or "layout" |
| CSS background images, `<object>`, `<embed>`, inline `<svg>`, `<picture>`/`srcset` | **out**: `<img>` only. Zero of any of them carry document graphics in the committed corpus. An `<svg>` chart in a future filing would be missed silently, which is INV-0's class of defect; recorded as Debt rather than guessed at |
| `data:` URIs | **recorded, not decoded**: a `data:` `src` is reported verbatim like any other. Zero in the corpus (all 53 srcs are relative filenames), so the path is exercised only by reasoning, not by a fixture. It is also the one shape where the bytes ARE in the fixture, and §c's ruling means nothing decodes them |
| the containing item's correctness | **derived, and only as good as the spans.** Containment is computed from item offsets, so on a filing whose segmentation is wrong the containment is wrong in exactly the same way. xom-2021 and jpm-2024 both fire `last_item_dominates`, so all 9 and all 14 of their images fall in one over-long span (Item 16, Item 15); bac-2006 is `success` with clean spans and its images split across Items 7 and 8, which is why **bac-2006-images is the case that proves containment discriminates** and the other two do not. Debt |
| rendering a Markdown image placeholder | **out of S10, deliberately — it is S9's** (§i). S10 ships no renderer at all, so there is nothing for S9 to collide with |
| txt-era images | **out**: `normalize()` answers `[]` for the txt era. The 7 txt fixtures contain no `<img>` and 1990s ASCII submissions cannot carry one |
| deduplicating repeated images | **out**: a `src` that appears twice is two records. Within a fixture no `src` repeats in the committed corpus; across it, three do (nvda-2024 and its synthetic derivative heading-unnumbered share two), which is why the `image` check has an `index` key even though nothing needs it today |

## f. Cost, measured

Measured 2026-08-23 on this tree, median of 3 runs per fixture:

| | measured |
|---|---|
| Wall-clock, `images=True` vs default, over the **15** image-carrying fixtures | median **1.083×**, range **1.063× – 1.135×** |
| Wall-clock on HTML fixtures with **zero** images (msft-2013, tgt-2002, wfc-2008) | **1.003× / 1.026× / 0.997×** — i.e. nothing |
| jpm-2024 (largest fixture, most images) | 0.5973 s → 0.6465 s |
| Annotation size, whole corpus | **5,477 bytes** of JSON across all 53 records |
| Annotation size, jpm-2024 | **1,549 bytes** on a 1,267,279-byte envelope — **+0.122 %** |

The ~8 % time cost is **not** proportional to the image count — it is the price
of taking the marks-carrying `_tidy` branch at all, which walks every match of
the three whitespace regexes instead of letting `re.sub` do it in C. A fixture
with zero images pays nothing because `_sub_map` returns immediately on an
empty mark list. Contrast ADR-029 §f, where `tables=True` costs +20 % time and
**+98 %** envelope bytes: images are 1/800th the payload of tables on the same
filing. That asymmetry is why §b4 justifies opt-in on contract consistency
rather than on size — the honest reason, since the size argument that carried
ADR-029 §b3 does not carry here.

### f2. What was NOT done, and why

Rendering an image placeholder into `normalized_text` — `![alt](src)`, or
`[IMAGE]` — was considered and refused outright, on ADR-029 §f2's reasoning and
with this corpus's own number on it. **On the 15 image-carrying fixtures the
first image sits at offset 17 – 359,634, median 458**, and a rewriting design
moves every offset after it: **5.08 % (jnj-2016, whose two images are in the
tail) – 100.00 % (ba-2003, whose first image is at offset 17); median
99.52 %, and 8 of the 15 above 99 %.** The annotation route moves **zero**
offsets, and §d asserts that equality on every run.

### f3. Corpus untouched

No fixture was added and no binary file was added. Every case runs against
committed filings — bac-2006, xom-2021, jpm-2024, aapl-2026-10q — so ADR-021
§b8's populations and every figure derived from them do not move. §c's ruling
that no image bytes are committed is what keeps that true.

## g. Enforcement

Six cases, plus the module and adapter self-checks. Every case was **red at
`origin/main` (3e16f70)** — `unknown check type 'image'` /
`'images_sane'` / `'offsets_invariant_under_images'`, 5 FAIL rows on
`--suite fast` (98/103) and 1 on `--suite invariant` (50/51, an INVARIANT
VIOLATION) — and then red again, on **content**, under five one-line
mutations of the working implementation, so none of them passes on vocabulary
alone.

**Those five red runs are NOT in `evals/report/history.jsonl`** (PR #44 R4).
They were made in a throwaway `git archive` tree of 3e16f70 with the case
files copied in, so the runner appended its lines to that tree's copy of the
file and they were discarded with it; every history line this PR commits is
green. The time series therefore carries no trace of them, and the claim above
rests on this document plus the round-1 reviewer's independent reproduction of
the 50/51 invariant result and of four of the five mutations. The one red line
the time series *does* carry is round 2's: `20260824-000828 fast 81764f7 dirty
104/105 0.9905`, the R1 case run with ADR §b1's original claim in it (§b2a).

| case | fixture · suite | labels (`src`/`alt`/`width`/`height` hand-read from the raw HTML by an independent regex route and compared field-by-field with the shipped annotation before being written; `offset` cross-checked by the 30 characters of `normalized_text` on either side of it) |
|---|---|---|
| `bac-2006-images` | bac-2006 · fast | 5 uppercase `<IMG SRC=... ALT="LOGO">`, no style attribute so `width`/`height` null on all five; **the only case whose item labels discriminate** — Item 7 twice, Item 8 three times, on a `success` document with no warnings; two images sharing offset 391006 |
| `xom-2021-images` | xom-2021 · fast | 9 records: 6 Earnings Factor Analysis performance graphs and 3 cover signatures; **g7/g8/g9 all at offset 232186**, the coincident-offset shape (§b2) |
| `jpm-2024-images` | jpm-2024 · fast | 14 records inside a 1,213,284-char text — the scale check for `_images_shape`; every awkward `alt` in the corpus (apostrophes, spaces, bare Workiva ids), and all four image kinds the S10 row names |
| `images-offsets-invariant` | xom-2021 · **invariant** + fast | on-vs-off equality, both directions of the default-off rule, shape of all 9 records, exact count |
| `images-in-table-cell` | xom-2021 · fast | added in PR #44 round 2 for R1: the 3 signature images against the table that contains them in the raw HTML but not in its recorded span (§b2a), all 9 images' `in_table`, and the first case in the suite to run `tables=True` and `images=True` together |
| `images-refusal-path` | aapl-2026-10q · fast | `unsupported` still carries the list when asked; `item: null` — the containment derivation's no-span branch, which no other case reaches; the `found`/`imgs` name-collision class ADR-029's `tables-refusal-path` exists for |

Mutations (this working tree, 2026-08-23, each applied alone and restored):

| mutation | what went red |
|---|---|
| M1 `alt` never recorded | 4 cases, 29 `image` checks: `alt None != 'LOGO'`, `alt None != '1036'`, … The invariant case stays green — correctly: it asserts the equality and the shape, not the content |
| M2 the `style` fallback for `width`/`height` dropped (attribute only) | 3 cases, 24 checks: `width None != 500`, `width None != 671`, `width None != 36`. bac-2006 stays green, since its five images have no declared size either way — which is the measurement behind §b1's rule |
| M3 offsets not moved through the `_tidy` map (pre-tidy values shipped) | 4 cases, 29 checks: `offset 327410 != 289566`, `offset 169928 != 159291`, … |
| M4 the `images` key emitted with the flag off | `images-offsets-invariant` and `images-refusal-path`: `images OFF emitted an images key; default must change nothing`. The three goldens stay green — which is exactly why the invariant case exists |
| M5 images deduplicated by offset | `bac-2006-images` (`4 images < min 5`, `src 'g23696g52h61.jpg': 0 image(s) carry it`), `xom-2021-images` (`7 images < min 9`), `images-offsets-invariant` (`7 images < min 9`). jpm-2024 stays green: it has no coincident pair |

`src/sec10k/normalize.py::_demo` pins the synthetic shapes no fixture isolates
(a `width=`/`height=` attribute, a `50%` non-pixel size, an `<img>` with no
`src`, an `<img>` inside `<title>` that is never recorded, an `<img>` inside a
table cell that carries text landing inside that cell's span AND an image in
an image-only leading row landing outside the whole tightened table, an
`&amp;` in `alt`, and the text
being identical with the flag on and off) and is run by
`.github/workflows/ci.yml`'s unit-tests job.
`src/sec10k/test_eval_adapter.py::test_image_checks` pins the check vocabulary
itself on a synthetic envelope, including every way `_images_shape` must
refuse a record — the gate case is the eval case, the self-check is the floor
(PR #25 R1).

Gate after: at the branch point (3e16f70) `--suite invariant` **51/51** and
`--suite fast` **103/103**; after merging `origin/main` c13aa5c (PR #42, D4,
which adds one case and promotes `ba-2003-asterisk-ibr` out of debt)
`--suite invariant` **52/52** and `--suite fast` **104/104**; after PR #44
round 2 (the R1 case, +1 case with a `table` check of its own)
`--suite invariant` **52/52** and `--suite fast` **105/105**. Table fidelity
is 1.0 throughout — cells 400/400 then 427/427, rows 31/31 then 34/34, a
RATIO the baseline gates, so the new labels move the counts and not the gated
value. Every module self-check ok; `.eval-baseline.json` untouched (§h).

## h. No baseline move (hard rule 1)

S10 adds **no metric and no baseline key**. `.eval-baseline.json` is untouched
by this PR — no `--update-baseline` was run, and the file's diff is empty.

Stated because the precedent could suggest otherwise: ADR-029 §h recorded two
new metric keys, and an image-fidelity metric would be the symmetrical move.
It is not made, and the reason is the one ADR-029 §c2 gave about its own gate's
honest worth: every image label here asserts an exact match, so any such metric
would be 1.0 by construction on a green suite and would fire only together with
a case that is already red. ADR-029's metric earned its keep on **magnitude** —
"colspan lost" is a 21 % cell loss, not a binary — and an image record has no
comparable partial-credit axis: a `src` is right or wrong. Adding a key that
can only ever read 1.0 or accompany a red case would be a number in the report
that means nothing, which is what `evals/metrics.py`'s null rule exists to
prevent.

## i. Seams — S9 and the inspector

**S9 (whole-document Markdown rendering) is a parallel, independent task.** The
S10 row says the annotation is "rendered by S9 as a Markdown image
placeholder". That rendering is **S9's**, and S10 ships no renderer, so there
is nothing to collide over and no ordering dependency in either direction: S10
does not need S9 to land, and S9 needs from S10 only the `images` key, whose
shape is fixed by the contract (`specs/001-sec10k-contract.md`) and by
`_images_shape`. The placeholder S9 will want is `![alt](src)` at `offset`,
composed the way ADR-029 §b2 composes an item body with its tables — from the
record, by a consumer, not from a stored field.

Both tasks touch `_Plain`. S10's edit is one `elif` branch on `img` at the end
of `handle_starttag`'s chain plus one module-level helper (`_dim`); it adds no
tag to `BLOCK_TAGS`, changes no existing branch, and emits nothing, so it is
mergeable beside an S9 change that adds emphasis or heading recording as long
as neither rewrites the chain wholesale. If S9 lands first this ADR does not
move.

**The inspector gains nothing in S10.** "The inspector shows the image where
the placeholder sits" is the fetch half's acceptance criterion, and the fetch
half is ruled out (§c) — with no bytes there is nothing to show. A Debt row
records it.

## j. Blast radius, measured

The corpus, as the shipped annotation sees it (2026-08-23, `evals/fixtures`,
`repo_hygiene` excluded because it is the UI-check corpus and not a filing):

| measured over the 42 filing fixtures | value |
|---|---|
| Fixtures by era | **24 HTML, 11 iXBRL, 7 txt** |
| Fixtures carrying at least one `<img>` | **15 of 42** — 8 HTML, 7 iXBRL, 0 txt |
| Total `<img>` recorded | **53** |
| `src` kinds | **53 relative filenames, 0 absolute URLs, 0 `data:` URIs** — the S10 row's central claim, re-measured and confirmed: the bytes are never in the fixture |
| Records carrying an `alt` | **49 of 53**; the 4 without are all in cvx-2015 |
| Records carrying a declared pixel size | **40 of 53**, every one of them from `style`; **0 of 53** from a `width=`/`height=` attribute |
| Coincident-offset pairs (two records at one offset) | **4** |
| Share of each fixture's offsets a rewriting design would move | **5.08 % – 100.00 %, median 99.52 %** (§f2) |

**One figure in the S10 row does not reproduce, and is corrected here.** The
row says "15 of 38 HTML fixtures carry `img` tags". The count **15** is right
and its per-fixture breakdown (jpm-2024 14, xom-2021 9, bac-2006 5, cvx-2015 4,
cat-2023 4) is right to the image. The denominator is not: there are **42**
filing fixtures, of which **35** are HTML or iXBRL and 7 are txt-era, so the
ratio is 15 of 35, not 15 of 38. (ADR-029 §i1 counted 34 HTML/iXBRL of 41
filing fixtures; `interior-span-dominates` has been added since, and it is
HTML and carries one image.) The row's conclusion is unaffected in either
direction.

### j1. What this does not establish

These are **corpus-bound counts, and the corpus is 42 hand-picked filings.**
Nothing here is a claim about EDGAR. "Zero `data:` URIs" and "zero `<svg>`
charts" in particular are facts about these 35 documents, not about filings —
which is precisely why §e records the `data:` path as reachable-but-unexercised
and the `<svg>` gap as Debt rather than as an impossibility. Nor do these
figures say anything about whether the *records* are correct: that is the five
cases of §g against hand-read labels, and their worth is bounded by the
two-route agreement described in the golden files' provenance.
