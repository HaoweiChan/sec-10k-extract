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
| `gs-2002/filing.htm` | sec.gov/Archives/edgar/data/886982/000095012303002099/y83718e10vk.htm | 0000950123-03-002099 | 2003-02-27 | 2002-11-29 | 2001–2004 transitional HTML, financial, **November** FY end; uses post-SOX numbering (14 = Controls, 15 = Exhibits) ahead of the 2003-08-14 effective date | 395,754 |
| `jnj-2016/filing.htm` | sec.gov/Archives/edgar/data/200406/000020040617000006/form10-k20170101.htm | 0000200406-17-000006 | 2017-02-27 | 2017-01-01 | mid-2010s HTML, pharmaceutical; 52/53-week FY whose period end falls in the *next* calendar year | 3,500,076 |
| `xom-2021/filing.htm` | sec.gov/Archives/edgar/data/34088/000003408822000011/xom-20211231.htm | 0000034088-22-000011 | 2022-02-23 | 2021-12-31 | large iXBRL, energy; the calendar-FY2021 cohort ADR-010 moved the 9C boundary to reach; drops Item 6 entirely | 6,159,522 |
| `cost-2022/filing.htm` | sec.gov/Archives/edgar/data/909832/000090983222000021/cost-20220828.htm | 0000909832-22-000021 | 2022-10-05 | 2022-08-28 | iXBRL, retail, **August** FY end; separates every item code from its title with an **em dash**, a heading shape no dev fixture contains | 1,861,894 |

Re-fetch pattern, same as `evals/fixtures/README.md`:

```bash
curl -H "User-Agent: Haowei Chan hwchan42@gmail.com" <url> -o <dest>
```

## Disjointness from the dev set

No filer appears in both sets. Sector coverage added here that `evals/fixtures/`
does not have at all: beverage, brokerage, pharmaceutical, petroleum, retail
warehouse. Fiscal-year ends added: November, January (52/53-week), August —
every dev fixture ends in December, June, May or September.
