# D26 — item-scoped cross-reference residual routing

Date: 2026-08-30

## Owner decision

Replace document-wide `cross_reference_index` suppression with per-item routing. Keep verified index regions as annotations and keep their primary index rows unchanged. Send only rows without verified answer evidence through the existing three-turn cached/budgeted agent loop. The UI/API must make the primary-row versus cross-reference-character distinction and the actual routing decision visible.

## Outcome preserved in this change

ADR-051 adopts `resolved_codes` and `residual_codes`; residual terminal outcomes are only `omitted` and `incorporated_by_reference`, each bound to the original index row by a deterministic verifier. Intel `intc-2025` is FY2025 (period 2025, accession filed 2026); the FY2024 filing has the same index layout, so this is not a newly regressed parser shape.
