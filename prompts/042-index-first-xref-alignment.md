# Index-first cross-reference alignment

## Request

Repair nontraditional 10-K filings whose Item content is located through a
Table of Contents or Form 10-K Cross-Reference Index. The solution must remain
general, use the existing LangGraph flow, and avoid issuer/year offsets.

## Outcome

Page ranges remain deterministic candidate evidence, but their starts now
advance within the first mapped printed page to the actual section heading.
Exact mapped titles win; a stricter semantic fallback handles legitimate title
variants without accepting nearby unrelated captions. Existing LangGraph
residual routing receives these aligned candidates unchanged; its prompt and
cache identity are deliberately preserved so offline CI remains reproducible.

Five synthetic cases cover preceding-page prose, duplicate running headings,
dense pages, wrapped index titles, and semantic title variants. Existing Citi
and Intel fixtures are used only for regression execution; no new filing or
held-out offsets are added.
