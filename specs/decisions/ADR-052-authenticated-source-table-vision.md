# ADR-052 — authenticated raster verdicts verify, never author, table fidelity

Date: 2026-08-30

Status: accepted

**Ruling**: a verified key may sample one selected public source table as a PNG and compare it with the exact cached deterministic Markdown candidate; only confirm is verified.
**Because**: table DOM text alone cannot prove visual column fidelity.
**Enforced by**: `d27-high-assurance`'s cached multimodal verdict and no-key checks.

---

## Decision

The deterministic table renderer remains the only author of Markdown. When a
viewer has first verified the existing escalation key, the inspector samples
one substantive table in the selected source region. The browser rasterizes
that table's DOM cell rectangles and text to a PNG, then sends the PNG plus
the exact DOM text and SHA-256. The server caps both, verifies the hash, and
matches the text to that run's cached normalized table and its deterministic
Markdown candidate before it calls the configured vision-capable model.

The model can return only `confirm`, `reject`, or `null`. A confirm validates
that deterministic candidate against the raster; reject or null leaves it
visibly partial. No
verdict creates Markdown, offsets, spans, or new filing evidence. No key,
invalid key, cache miss, malformed PNG/hash, or source mismatch makes a model
call or incurs cost.

## Why

Image tags in a filing are not a page or table rendering. Duke's FY2024 filing
uses TD multi-row headers and printed-page chrome, so text-only prompting could
not honestly validate visual table fidelity. A browser-native canvas is the
smallest dependency-free raster path, while the existing gate, Budget, cache,
and strict verdict parser retain the paid-path boundary.

## Enforcement

`d27-high-assurance` pins the grouped TD header, narrow page-adjacent chrome
rule, default UI, collapsed trace, exposed raster control, and zero-call
unauthenticated verifier. The endpoint independently binds token, table text,
hash, PNG signature, and byte caps before `vision_table_verify` can spend.
