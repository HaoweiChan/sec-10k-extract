# ADR-051 — cross-reference resolution leaves bounded residual work

Date: 2026-08-30

Status: accepted

Supersedes ADR-045's document-wide cross-reference suppression rule and qualifies ADR-046/047.

**Ruling**: cross-reference resolution is item-scoped: residual and footnote-backed disposition work uses the existing bounded loop; verified content never becomes a span-repair target, and only an empty residual/disposition set suppresses at $0.

**Because**: Intel FY2025 has a cross-reference index with some verified page regions and some rows that only say `None`, `[Reserved]`, or point to the 2026 proxy. Treating any one resolved row as proof the entire document is resolved hid both the remaining work and the decision from users.

**Enforced by**: D26 cached/offline route and UI cases; the real `intc-2025` fixture pins the 13 verified regions and unchanged primary spans while proving only its residual codes are offered to the loop.

---

## Decision

Every parsed index row publishes immutable provenance. Rows with verified page
regions are `resolved_codes`; rows with no verified region are `residual_codes`.
An explicitly marked footnote-backed disposition code may join the residual
set without discarding its local page region (Intel item 10).

The only new agent proposal is `propose_item_dispositions`, a batch map of
exactly `omitted` or `incorporated_by_reference`. The deterministic verifier
binds each proposal to the original index-row slice: `None`/`[Reserved]` for
an omission, or an exact collective/individual incorporation pointer naming
the item or its Part for IBR. It rejects wrong items/Parts, statuses, bounds,
invented prose, URLs, and inference. Terminal dispositions have null primary
offsets; the original row stays in `evidence.cross_reference_entry`.
