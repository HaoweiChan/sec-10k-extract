# Frozen predictions — GPT's hard-filing batch

Written **before** any of these six was run through `extract_items`, except
`intc-2025`, which is a committed fixture whose collapse is already recorded
(ADR-036 §k, D17). Timestamp: 2026-08-28, worktree
`claude/gpt-difficult-10k-samples-579d78`, tree at `573d307`.

The prediction is the instrument. Anything below that turns out wrong is a
finding about our model of the pipeline, not something to quietly edit.

| # | filing | predicted `doc_status` | predicted failure | most likely validator to fire |
|---|---|---|---|---|
| 1 | Intel FY2024 (`intc-2025`) | `ambiguous` | **known**: only Item headings in the document are in the trailing *Form 10-K Cross-Reference Index*; all 23 spans land there, 0.3% coverage | `low_item_coverage` (fires), `unattributed_content`, `item_span_near_empty` ×3 |
| 2 | Citigroup FY2024 (`c-2025`) | `success` or `success_with_warning` | held-out, 15 MB; risk is Item 7/7A/8 boundary bleed into the 200-page financial section | `item_span_near_empty` / tail bleed |
| 3 | Berkshire FY2024 | `success_with_warning` | letter-spaced headings (`Par t I`, `Busines s`) defeat heading normalization → some items `missing` | `low_item_coverage` if the split is systematic; otherwise per-item `missing` |
| 4 | Simon Property FY2024 | `success_with_warning` or `ambiguous` | two registrants (SPG Inc. + SPG L.P.) → duplicate Item headings; second set wins or spans transpose | `spans_transposed` / `duplicate heading` / `non_last_span_dominance` |
| 5 | MetLife FY2024 | `success_with_warning` | 13.8 MB, dense tables; boundary risk at 7/7A/8, memory/time risk on normalization | `item_span_near_empty` on 7A; runtime, not a validator |
| 6 | Bridgecrest ABS Trust 2024-1 | **`unsupported`** | ABS trust files a 10-K that has none of Items 1–16; correct behaviour is refusal, NOT a plausible-looking item set | form/era detection must refuse; if it instead emits items, that is the finding |

## Anchors (Items 1, 7, 8, 15), predicted

- **Intel**: Item 1 should start at the business narrative (~page 3), not at the
  index line `Item 1. Business:` near offset 514,391. Exclusion anchor for
  Item 1: the string `Form 10-K Cross-Reference Index` must NOT be inside it.
  Item 7 = MD&A pages 18–36; Item 8 = pages 56–108; Item 15 = pages 110–115.
- **Berkshire**: Item 1 ends before `Item 1A. Risk Factors`; Item 8 covers the
  consolidated financial statements; exclusion anchor: the Chairman's letter
  is not part of Item 1.
- **Simon**: Item 15's span must not swallow the L.P. financial statements as
  a second copy of Item 8.
- **Bridgecrest**: no anchors — there should be no spans at all.

## Information gain

Intel, Simon and the ABS trust test three *different* assumptions
(items-are-headings, one-registrant-per-document, every-10-K-has-Items-1-16).
The rest mostly test size.
