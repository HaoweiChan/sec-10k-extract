# 027 — the curated hard-filing sweep, and what a frozen prediction set is worth (2026-08-28)

An external model (GPT) curated eight recent 10-K filings chosen to break
*specific assumptions* rather than to be large, ranked by expected information
gain, and prescribed a method: freeze a prediction per filing — expected item
set and statuses, first/last anchors for items 1/7/8/15, exclusion anchors,
expected `doc_status`, and the validator most likely to fire — **before**
running it. The owner's instruction was to make the extractor handle them by
whatever means ("escalation mode is fine, token cost is not a constraint") and
to confirm the deployed Zeabur build works.

Outcome: [ADR-042](../specs/decisions/ADR-042-cross-reference-index.md), four
defects fixed, two held-out cases burned and declared, and **$0.00 spent** —
the paid tier was not merely unused, it was *switched off* for the one document
shape where it had previously been billed.

## The prompt decisions that mattered

- **Freeze the predictions, then count the misses out loud.** Four of seven
  predictions were wrong, and three of those four were wrong the same way:
  they predicted a SIZE or MEMORY failure (13.8 MB MetLife, 12.9 MB BofA,
  11.2 MB Simon) on a pipeline whose real failures are all failures of
  *typographic assumption*. MetLife, BofA and Simon each returned `success` at
  92–99% coverage in under a second. The prediction set earned its keep by
  being wrong in a legible direction, and ADR-042 §g publishes the scoreboard
  rather than only the fixes. A prediction set that is quietly revised after
  the run is not an instrument.

- **The exclusion anchor that failed was reported, not swapped.** The frozen
  Intel prediction said `Form 10-K Cross-Reference Index` must not appear
  inside any resolved region. It failed on item 8 — because Intel prints a
  mini table of contents at the head of its financial statements that names
  the index. The phrase occurs four times and only the fourth is the index.
  The anchor was a bad instrument, not a finding about the fix, and
  `intc-2025-cross-reference-index.json` says so in those words before naming
  its replacement (`Item Number Item`, which occurs exactly once).

- **Refuse to move the spans, when the contract says the spans cannot move.**
  The tempting version of the Intel fix assigns the index's page ranges to
  `start`/`end` and reports a filing that reads beautifully. It is not
  available: Intel's item 3 is pages 102–105, *inside* item 8's 56–108,
  because Intel answers Legal Proceedings in Note 19; Citi's item 7A is
  threaded through item 8. INV-S1 requires non-overlapping ordered spans, so
  no correct answer for these filings can be a span assignment. The regions
  go to `evidence.cross_reference` — the shape ADR-031 already chose for the
  footnote case — and `doc_status` stays `ambiguous` with `low_item_coverage`
  still fired. That last part was the actual decision: the demo looks worse
  and the envelope stays true.

- **Answer deterministically what a paid model failed twice to answer.**
  ADR-036 §k records two escalation attempts on `intc-2025`, the second billed
  $0.997760, both returning `empty_completion` with zero items resolved. The
  owner's instruction explicitly permitted spending. The filing's own
  cross-reference index and its own printed page numbers answered it at $0.00,
  so ADR-042 §e *suppresses* the paid trigger on any filing whose index
  resolved. "Token cost is not a constraint" is a licence to try harder, not
  an argument for spending where a cheaper answer is also the better one.

- **Citi was the finding, and it was found by disobeying a size intuition.**
  Held out since 2026-08-26 and predicted as a boundary-bleed risk, it was
  measured at coverage **0.0000** — zero candidates in 1,163,303 characters,
  worse than Intel — because its index writes `1. Business 4–36` and the
  string `Item 1A` appears nowhere in the document. The generalization from
  one filing (Intel: index at the tail, `Item N.` rows, a `Pages` keyword) to
  two (Citi: index at the front, bare `N.` rows, a page COLUMN) is most of
  `src/sec10k/xref.py`'s difficulty, and none of it was visible from Intel.

- **Declare the burns, including the one that flatters the pipeline.**
  `c-2025` burned by ordinary influence. `spg-2019` burned the other way: the
  trailing-annex clip made its frozen `min_chars: 16 >= 100` label WRONG,
  because SPG FY2019's item 16 body is the word "None." and the floor had only
  ever been cleared by the bug inflating the span with 23 KB of exhibit index.
  Relabelling it is influence even though the pipeline is the party in the
  right, so it left the held-out set too. Two replacement filings are owed.

- **A hygiene check that fires on a correct span is a hygiene bug.**
  `boundary_hygiene` read every span back with `HEADING_RE` and called 11
  correct Citi spans broken, because Citi writes no `Item`. Its own comment
  says it must read the heading "with the SAME regex that produced the
  offset"; the producer for those spans is `xref.ENTRY_RE`. The fix applies
  the check's stated rule rather than adding an exemption to it.

## What was NOT done

No vision rung, no LLM call of any kind, no new dependency, and no attempt to
attribute the trailing exhibit index to Item 15 — one guess per defect is
enough, and `unattributed_content` already reports the residue honestly.
