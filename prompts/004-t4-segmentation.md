# 004 — T4: segmentation, and four things the data corrected

## Purpose

T4 built layers 4–7 (candidates → TOC filter → boundaries → status) and took
the eval set from 3/19 to 19/20. Curated per hard rule 6: the mechanism that
shipped is not the one the architecture doc predicted, and three of the four
corrections came from measurement rather than from a failing case.

## The prompt

> continue on task 4

Same shape as T3 — the scope came from `milestones.md` ("candidates + TOC
filter + boundaries + status classification → `aapl-2025-*` and `ge-1994`
green (the TOC trap dying is the single most important green in this repo)")
and the design constraints came from dumping real candidates before writing
any of it, which that milestone's appendix explicitly asks for.

## Measure first, then design

Every design decision below came from one spike: dump every `Item N` line-match
in all 13 fixtures and look at what is actually there. It immediately produced
two facts no amount of reasoning would have:

- **MSFT 2013 repeats a bare `Item 8` on every page of its financial
  statements** — 42 occurrences, plus 24 of `Item 7` and 12 of `Item 1`. Trap 6
  (page furniture) was catalogued as a txt-era problem; it is alive and worse
  in the HTML era.
- **Every real fixture's TOC puts the item code and its title in separate
  table cells**, so TOC entries normalize to a bare `Item 1.` with the title on
  the next line.

Those two facts share one discriminator — *a real heading carries its title on
the same line* — which is why the shipped filter is a single cheap rule where
the architecture doc predicted a feature vector (line length, uppercase ratio,
PART proximity).

## Assumption → Eval contradiction → Correction

- Assumed: the TOC-cluster filter would be the thing that beats the TOC trap.
- Eval said: it never fired. Not once, on any of 12 fixtures — the same-line
  rule had already killed every TOC for free. The repo's most-cited trap was
  guarded by code no case had ever exercised.
- Corrected: built `evals/adversarial/toc-titled.json` — premier-pacific with
  its TOC rows merged into single cells, so 20 TOC entries score 0.842–0.943
  similarity and only the cluster rule can separate them.

- Assumed: with that fixture written, the cluster filter would pass it.
- Eval said: it failed. The rule required *every* code in a dense run to recur
  later; a TOC sits close enough to the body it indexes that the run swallowed
  the first real body heading, whose code does not recur — so the test failed
  on that one candidate and rescued the entire TOC.
- Corrected: recurrence is judged per candidate. The case caught a real bug in
  its first run, which is the whole argument for writing it.

- Assumed: `POINTER_MAX = 2000` and `SIM_FLOOR = 0.45` were reasonable, and I
  wrote both into code comments as "measured".
- Eval said: they were not measured, they were invented — and measuring them
  killed one. IBR bodies span 93–1,875 chars while 106 of 191 extracted bodies
  fall in the same range, so the length cutoff separated nothing. The
  similarity band was 0.141–0.593, not the 0.30/0.62 the comment claimed.
- Corrected: length cutoff deleted (shape decides); floor moved to the measured
  midpoint. Willy's "no pre-data magic numbers" directive is not satisfied by
  *labelling* a number measured — ADR-007 now carries the real distributions.

- Assumed: status classification could match phrases against item bodies.
- Eval said: 5 items across GE 1994 and Textron 2001 came back `extracted`
  that should have been `incorporated_by_reference`, and the first diagnosis
  (bad `EXTERNAL_DOC_RE`) was wrong — two different regexes were failing for
  one reason: fixed-width txt filings wrap the exact phrases the rules depend
  on (`definitive proxy\nstatement`, `incorporated by\nreference`).
- Corrected: classification runs on a whitespace-flattened copy of the body;
  offsets never do. One fix, both symptoms — the same root-cause-not-symptom
  discipline that ADR-006 ruling 2 came from.

## Not built, on purpose

The lenient candidate tier the architecture describes. Strict line-anchored
matching finds every expected heading in all 13 fixtures, and the single
heading it cannot find (`malformed-html`, whose Item 1A tag is corrupted)
*should* report `missing` rather than be rescued by a looser pattern — the case
allows exactly that outcome. Recorded in ADR-007 so the omission is a decision,
not a gap.

## Cost

Zero LLM calls, zero dollars. Slowest fixture (12.8 MB JPM) runs end to end in
~520 ms.
