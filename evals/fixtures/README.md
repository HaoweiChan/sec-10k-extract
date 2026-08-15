# Fixtures

Public EDGAR documents, fetched with a declared User-Agent per SEC
fair-access policy. Re-fetch command pattern:

```bash
curl -H "User-Agent: Haowei Chan hwchan42@gmail.com" <url> -o <dest>
```

| Fixture | Source | Accession | Filed | Format | Bytes |
|---|---|---|---|---|---|
| `aapl-2025/filing.htm` | sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm | 0000320193-25-000079 | 2025-10-31 | iXBRL (2019+ era) | 1,520,208 |
| `ge-1994/filing.txt` | sec.gov/Archives/edgar/data/40545/0000040545-94-000003.txt | 0000040545-94-000003 | 1994-03-11 (10-K for FY1993) | plain-text full submission (1993–2001 era) | 430,539 |
| `msft-2013/filing.htm` | sec.gov/Archives/edgar/data/789019/000119312513310206/d527745d10k.htm | 0001193125-13-310206 | 2013-07-30 | legacy HTML (2001–2019 era), mid-era deep-tier pick | 1,776,947 |
| `jpm-2024/filing.htm` | sec.gov/Archives/edgar/data/19617/000001961725000270/jpm-20241231.htm | 0000019617-25-000270 | 2025-02-14 | iXBRL, large financial-sector deep-tier pick (~12MB) | 12,849,180 |
| `textron-2001/filing.txt` | sec.gov/Archives/edgar/data/217346/000095013502001340/b42129tie10-k405.txt | 0000950135-02-001340 | 2002-03-14 | plain-text, form type literally 10-K405, early-2000s deep-tier pick | 69,521 |
| `sandston-2021/filing.htm` | sec.gov/Archives/edgar/data/892832/000141057822000504/sdon-20211231x10k.htm | 0001410578-22-000504 | 2022-03-25 | iXBRL, shallow-tier shell-company stratum | 799,426 |
| `premier-pacific-2016/filing.htm` | sec.gov/Archives/edgar/data/1589919/000112785517000104/ppci10k123116.htm | 0001127855-17-000104 | 2017-04-17 | HTML, shallow-tier SRC 7A-relief stratum | 642,332 |
| `ibm-1997/filing.txt` | sec.gov/Archives/edgar/data/51143/0001047469-98-012291.txt | 0001047469-98-012291 | 1998-03-30 | plain-text full submission, form type 10-K405, shallow-tier late-1990s stratum | 344,714 |
| `nike-2006/filing.htm` | sec.gov/Archives/edgar/data/320187/000119312506156152/d10k.htm | 0001193125-06-156152 | 2006-07-28 | legacy HTML, shallow-tier mid-2000s stratum | 1,198,942 |
| `nvda-2024/filing.htm` | sec.gov/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm | 0001045810-24-000029 | 2024-02-21 | iXBRL, shallow-tier 2021+/9C/Reserved stratum | 2,085,566 |
| `cat-2023/filing.htm` | sec.gov/Archives/edgar/data/18230/000001823024000009/cat-20231231.htm | 0000018230-24-000009 | 2024-02-16 | iXBRL, shallow-tier modern-industrial stratum | 5,687,600 |
| `aapl-2026-10q/filing.htm` | sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm | 0000320193-26-000020 | 2026-07-31 | iXBRL Form 10-Q (not a 10-K), adversarial `10q-unsupported` fixture | 1,018,210 |
| `toc-titled/filing.htm` | SELF-CREATED — copy of `premier-pacific-2016/filing.htm` with its table-of-contents rows merged into single cells, so every TOC entry becomes a titled, single-line pseudo-heading (see `evals/adversarial/toc-titled.json` provenance for the exact regex, the 43 merged row boundaries, and the measured 0.842–0.943 similarity scores). Supplies the hard form of trap 1, which no real fixture in this set exercises. | n/a (not an EDGAR filing) | n/a | mutated HTML, adversarial `toc-titled` fixture | 628,096 |
| `heading-unnumbered/filing.htm` | SELF-CREATED — copy of `nvda-2024/filing.htm` with the seven characters `Item 8.` deleted from the Item 8 body heading, leaving the title, markup and content intact (see `evals/adversarial/heading-unnumbered.json`). A title-only heading is a real filer style, not damage, which makes this the silent-failure case: the output looks clean and only the filing's own contents page reveals the gap. | n/a (not an EDGAR filing) | n/a | mutated iXBRL, adversarial `heading-unnumbered` fixture | 2,085,553 |
| `malformed-html/filing.htm` | SELF-CREATED — hand-degraded copy of `premier-pacific-2016/filing.htm` (see `evals/adversarial/malformed-html.json` provenance for the exact mutations: 15 of 46 `</font>` closing tags removed, one `<div style="...">` tag truncated mid-attribute at the Item 1A heading, one `&#160;` entity garbled at the Item 8 heading) | n/a (not an EDGAR filing) | n/a | hand-degraded HTML, adversarial `malformed-html` fixture | 642,150 |
