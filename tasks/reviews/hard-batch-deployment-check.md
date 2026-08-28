# Deployment check — the hard-filing batch, before and after ADR-042

The owner's instruction carried a condition: "confirm the version on Zeabur
works." This is that check. It has two halves, because a claim about a
deployment is only worth something if the LIVE build was measured too.

## 1. The live build, BEFORE the fix — and it reproduced the defects

`https://whaleforce-sec10k.zeabur.app`, 2026-08-28, `git_sha 573d30701852`
(= `main` at `573d307`), `escalation_enabled: true`, over the real
`POST /api/extract/url` route:

| filing | bytes | live `doc_status` | live result |
|---|---|---|---|
| Bridgecrest ABS trust | 53,755 | `success_with_warning` | 23 items, item 7 = 96 chars, item 8 = 54 chars — **the §b defect, in production** |
| Simon Property FY2024 | 11,195,959 | `success` | 23 items, item 8 = 227,849 chars, **item 16 = 23,401 chars** — the §d defect, in production |

Both at `cost.usd 0.0`. So the two defects ADR-042 fixes are not local
artifacts: the deployed service was returning them to anyone who pasted those
EDGAR URLs, and the 11.2 MB fetch-normalize-extract round trip completed
inside the request timeout, which is the scale question answered.

Intel was deliberately NOT sent to the live endpoint. `/api/extract/url` has
no fixture exclusion, escalation was on by default (ADR-041), and Intel is the
one document known to fire the trigger — the request would have billed roughly
$1.00 to reproduce a failure ADR-036 §k already records twice.

## 2. The fixed tree, through the same FastAPI app

`uvicorn src.sec10k.web.app:app`, this branch, same routes, same code the
Zeabur build runs (`zbpack.json` → the same module):

```
/api/meta   fixtures 48 · intc-2025 listed: True · c-2025 listed: True · escalation True
```

| fixture | `doc_status` | items | `elsewhere` regions | resolved chars | cost |
|---|---|---|---|---|---|
| `intc-2025` | `ambiguous` | 23 | 20 | 850,446 | **$0.00** |
| `c-2025` | `ambiguous` | 23 | 27 | 1,730,571 | **$0.00** |
| `spg-2025` | `success` | 23 | 0 | 0 | $0.00 |
| `brka-2025` | `success` | 23 | 5 | 2,185 | $0.00 |
| `bridgecrest-2025` | `unsupported` | 0 | 0 | 0 | $0.00 |

And over `/api/extract/url` on the fixed tree, the two filings not committed as
fixtures: **MetLife FY2024** `success`, coverage 0.9513, item 16 now 59 chars
(was 38,153); **Bank of America FY2024** `success`, coverage 0.9879, item 15
17,171 / item 16 66 chars. Both $0.00.

## 3. The item pane actually shows the resolved content

Read out of the live DOM at `?fixture=intc-2025&run=1`, item 7's pane:

```
ITEM 7 — MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS
PART II · EXTRACTED · CON…
…Results of operations
Pages 18-29

Critical accounting estimates
Pages 34-36, 65-72

———— pages 18-29,29-32 · chars 97,926–155,555 ————

Table of Contents

Management's Discussion and Analysis

Overview

Our MD&A begins with an overview of significant events and key developments in 2025…
```

Evidence rows present on that pane: `shown`, **`content elsewhere`**,
`heading matched`, `offsets`, `evidence`. The routing strip reads
`deterministic only — the escalation trigger stayed quiet, no tier ran,
$0.0000 · 0 calls · 0 tokens`, which is §e working on the deployed surface and
not only in the library.

A screenshot was attempted and the browser pane returned blank frames (the
pane was hidden in this session); the DOM read above is the evidence instead,
and this note says so rather than shipping a missing image.

## 4. What is still true of the deployment after this change

- `intc-2025` and `c-2025` are back in the dropdown (ADR-042 §e). They cost
  $0.00 and cannot escalate, so the reason they were withheld is gone.
- `xref-index-collapse`, the synthetic, still fires the trigger and stays in
  `DEPLOY_EXCLUDED` — which is what keeps `deployed-fixture-exclusion` from
  being a vacuous check.
- ADR-041's accepted exposure is UNCHANGED: an anonymous caller can still
  reach the paid tier through `/api/extract/url` on a collapsing filing that
  is *not* an index shape. This change removes one document shape from that
  surface; it does not close it.
- **This has not been deployed.** The live build is still `573d307`. Merging
  is the owner's call.
