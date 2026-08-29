# ADR-046 — systematic escalation publishes verified alternative regions

Date: 2026-08-29

Status: accepted

Amends ADR-036 and the escalation portion of `specs/001-sec10k-contract.md`.

**Ruling**: replaces ADR-036 §b's all-or-nothing rule: classify fired work as `replace_primary`, `alternative_evidence`, or `deterministic_resolved`; accepted primary deltas each re-derive INV-S1, and bounded `{start,end,title|reference}` alternative regions are verbatim item annotations that may overlap/nest and never move primary offsets.
**Because**: page-index and missing-heading shapes cannot honestly be one ordered primary span; bounds alone are not evidence, and a rejected sibling must not erase a separately verified item.
**Enforced by**: `d21-*.json`, `escalate._demo`, and `envelope_shape`; every routing record has the backend-authored, fixed `classify → plan → route → verify → decide` flow. The bounded vision seam selects at most two alternative-region annotations only when their relative source resolves against the validated original `https://www.sec.gov/Archives/…` document URL to an `https://www.sec.gov/Archives/…` common image resource (`gif/jpeg/jpg/png/webp`). Uploads and fixtures have no such base and visibly skip; blank/query-only/non-image, unsafe, and off-origin URLs are rejected. It sends OpenRouter multimodal content only after text-offset verification, using the shared budget/cache and a committed-catalogue image-input model; strict `confirm` / `reject` / null gates only the inspected items' alternatives, never unrelated text-verified siblings, and cannot create offsets or bypass text verification. Cached test verdicts are labelled as such. Fast/invariant stay $0. Full-page OCR/rendering remain residuals.

---
