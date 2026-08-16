# Held-out set — frozen, not run

**Do not run these to see how they do.** They exist to estimate generalization
once, at a milestone, and a casual run spends that. The rules are in
`docs/evals/evaluation-strategy.md`; this file is the inventory and the
provenance.

Why this is structural and not honour-system:

- `evals/run.py` `CASE_DIRS` covers `golden/` and `adversarial/` only, so
  `--suite fast|all` **cannot** reach this directory. Reaching it takes an
  explicit `--dir evals/heldout`.
- `--dir` runs ignore `--no-report`: the runner writes a report with the git
  SHA embedded, every time. A held-out run cannot be traceless.
- Reports are committed **before** any fix, so run-before-fix ordering is
  provable from history rather than asserted.

## Burn rule

A case is burned the moment its labeled outcome influences implementation — a
fix, a threshold, a new case written because of it. **Re-running does not burn
it; influence does.** A burned case goes through `failure-triage`, moves to
`evals/adversarial/`, and is replaced with a fresh filing at the next
expansion. Budget 2 spare filings per milestone for that cycle.

## Authoring discipline

Every case here was verified by an **independent tag-strip regex scan that
imports nothing from `src/`**. The extractor has never been invoked on any of
these files. Where a case records a prediction about how the pipeline will
behave — GS 2002's transitional numbering, Costco's em-dash separators, Exxon's
missing Item 6 — that prediction is written into the provenance *before* the
first run, so it cannot be retrofitted afterwards.

## Inventory

| Fixture | Source | Accession | Filed | Period end | Stratum | Bytes |
|---|---|---|---|---|---|---|
| `ko-1997/filing.txt` | sec.gov/Archives/edgar/data/21344/0000021344-98-000004.txt | 0000021344-98-000004 | 1998-03-09 | 1997-12-31 | pre-2001 txt, beverage; first cohort required to carry Item 7A; ALL-CAPS cover date from a real filer | 377,407 |
| `pgr-2023/filing.htm` | sec.gov/Archives/edgar/data/80661/000008066124000007/pgr-20231231.htm | 0000080661-24-000007 | 2024-02-26 | 2023-12-31 | iXBRL, **fire/marine/casualty insurance** — restores the financial-sector coverage. Sits 16 days past the Item 1C era boundary, and its cover carries a **floating comma** (`December 31 , 2023`). Replaces `gs-2002`, burned 2026-08-17 | 1,474,219 |
| `csco-2016/filing.htm` | sec.gov/Archives/edgar/data/858877/000085887716000117/csco-2016730x10k.htm | 0000858877-16-000117 | 2016-09-08 | 2016-07-30 | mid-2010s HTML, computer-communications equipment; 52/53-week FY ending in **July**. Replaces `jnj-2016`, burned by H1 | 4,476,127 |
| `xom-2021/filing.htm` | sec.gov/Archives/edgar/data/34088/000003408822000011/xom-20211231.htm | 0000034088-22-000011 | 2022-02-23 | 2021-12-31 | large iXBRL, energy; the calendar-FY2021 cohort ADR-010 moved the 9C boundary to reach; drops Item 6 entirely | 6,159,522 |
| `cost-2022/filing.htm` | sec.gov/Archives/edgar/data/909832/000090983222000021/cost-20220828.htm | 0000909832-22-000021 | 2022-10-05 | 2022-08-28 | iXBRL, retail, **August** FY end; separates every item code from its title with an **em dash**, a heading shape no dev fixture contains | 1,861,894 |

Re-fetch pattern, same as `evals/fixtures/README.md`:

```bash
curl -H "User-Agent: Haowei Chan hwchan42@gmail.com" <url> -o <dest>
```

## Disjointness from the dev set

No filer appears in both sets. Sector coverage added here that `evals/fixtures/`
does not have at all: beverage, brokerage, computer-communications equipment,
petroleum, retail warehouse. Fiscal-year ends added: November, July
(52/53-week), August — every dev fixture ends in December, June, May or
September.

(Pharmaceutical and the January 52/53-week year end left this set with
`jnj-2016` when H1 burned it; both now live in `evals/fixtures/`, so the
coverage is not lost, it moved to the dev side.)

## Run history

| Run | Date | Score | Outcome |
|---|---|---|---|
| **H1** | 2026-08-16 | **1/5** | `evals/report/20260816-225101-fast.json`, triaged in `docs/evals/audits/2026-08-16-h1-heldout-triage.md`. Two real extractor findings, four labels the author got wrong. `jnj-2016` burned and promoted to `evals/adversarial/`; `gs-2002`, `ko-1997` and `xom-2021` label-corrected from their source documents. |

After H1 the set is no longer pristine: `cost-2022` is the only case never
observed failing, and three carry corrected labels. H1 is the only clean
generalization estimate those three will ever provide, and later runs on them
measure regression, not generalization. `csco-2016` is fresh.

**H1b, 2026-08-16, 4/5** — re-run after the ADR-013 fixes. Read it carefully,
because the number flatters the result: of the four passes only `cost-2022`
(clean in H1) and `csco-2016` (fresh, never observed) are generalization
evidence. `ko-1997` and `xom-2021` pass because their labels were corrected,
which measures the correction, not the extractor. The single failure,
`gs-2002`, is the era-model limitation ADR-013 deliberately declined to fix and
is enumerated debt, not a surprise. The honest one-line summary is: **one fresh
unseen filing, 4.5 MB and never observed, passed on the first attempt** — and
even that is a presence-and-status result, not a boundary one: `csco-2016` and
`cost-2022` carry no anchors and no length bands, so a TOC-collapsed extraction
would clear them (pre-B audit finding 4).

**Burn, 2026-08-17** — `gs-2002` moved to `evals/adversarial/` as enumerated
debt. It had been run twice, its failure mode is published in four documents,
and ADR-013's decision *not* to fix the era model was taken with its outcome in
hand; the burn rule names "a threshold choice" as burning, and a documented
decision to decline a fix is at least as much influence. Counting it in a
held-out denominator would have overstated that denominator. Replaced by
`pgr-2023`, which carries two predictions recorded before its first run.
