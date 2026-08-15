# Fixtures

Public EDGAR documents, fetched with a declared User-Agent per SEC
fair-access policy. Re-fetch command pattern:

```bash
curl -H "User-Agent: Haowei Chan hwchan42@gmail.com" <url> -o <dest>
```

| Fixture | Source | Format |
|---|---|---|
| `aapl-2025/filing.htm` | sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm | iXBRL (2019+ era) |
| `ge-1994/filing.txt` | sec.gov/Archives/edgar/data/40545/0000040545-94-000003.txt | plain-text full submission (1993–2001 era) |
