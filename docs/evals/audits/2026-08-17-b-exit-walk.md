# B-exit checklist walk — 2026-08-17

The line-by-line walk of `docs/product/milestones.md` §"B-level exit checklist",
the T8 validation gate. Run at git `ca98481` (+ uncommitted ledger edits only).
Fresh evidence generated for this walk: `--suite all` re-run →
`evals/report/20260817-022651-all.json`, **27/27 = 1.000, +1 enumerated debt
(unscored)**; the deployed instance and the Zeabur console were independently
verified in this session (browser-driven, not from memory).

Checkboxes in `milestones.md` stay unticked on purpose — that file is durable
criteria, "not where we are" (its own header), and ADR-009 puts status in
exactly one place. This document is the walk; `tasks/TODO.md` T8 carries the
verdict.

| # | Line | Verdict | Evidence |
|---|------|---------|----------|
| 1 | Three format eras handled; txt stop-loss honored | **green** | txt: ge-1994 / ibm-1997 / textron-2001 green; HTML: msft-2013 / nike-2006 et al.; iXBRL: aapl-2025 / jpm-2024 / nvda-2024 / cat-2023. Stop-loss **declined** in ADR-007 §2, so the "if demoted" clause is moot and `ge-1994-oldformat` is green, not debt. The transitional boundary (gs-2002) is the one known exception, handled under line 2 |
| 2 | Goldens green; adversarial green or enumerated debt with triage | **green** | `20260817-022651-all.json`: 27/27 = 1.000. Exactly one debt: `gs-2002-transitional-numbering`, unscored, `[DEBT] STILL RED — era-model-limitation`, triaged in ADR-013 and re-triaged in `2026-08-17-h2-heldout.md` |
| 3 | Eval set ≈12–15 filings, deep + shallow, era-stratified | **green** | 22 fixture dirs, 1993–2026: deep tier 4 filings (aapl-2025, jpm-2024, msft-2013, textron-2001 — content+structure pairs), shallow tier 6, plus 12 adversarial fixtures (real filings + self-created corruptions). Provenance: `evals/fixtures/README.md` |
| 4 | Every invariant backed by an invariant-tagged case; ge-1994 retagged | **green** | invariant suite 10/10. Spec "Enforced by" map, all backers tagged `"invariant"`: INV-0 → aapl-2025-structure; S1 → aapl-2025-structure, ibr-pointer-first, toc-titled; S2 → aapl-2025-structure; S3, S4 → ge-1994-oldformat (era-set `item_present` with explicit statuses + `item_absent` for era-invalid codes — the S4 semantics, verified in the case JSON this walk); S5 → ixbrl-hidden-metadata. ge-1994-oldformat carries the promised retag. Nit, cosmetic: the case JSON names INV-S3 but not S4; the S4 assignment lives in the spec's Enforced-by line |
| 5 | Held-out authored frozen pre-frontend, run twice, reports committed pre-fix | **green** | G3 frozen (tag-strip verification, predictions pre-registered). H1 at T7 exit: 1/5, report alone in a72d8f7. H2 at T8: 5/5, report alone in 004c5f1, triage ca98481. Burn/refresh turned twice: jnj-2016 → csco-2016, gs-2002 → pgr-2023 |
| 6 | Contract v2 envelope; ADR-001..003 | **green** | ADRs on disk; envelope (`doc_status`/items/counts/trace/meta/warnings) observed in production responses during this session's browser verification |
| 7 | Zeabur inspector: 3 input modes, badges, banner, trace | **green** | Verified against the deployed instance this session: fixture (aapl-2025: success, 18 extracted + 5 IBR), upload guards (415/400/404), live EDGAR URL on an out-of-eval-set filing (AAPL FY2024: success, 19 extracted + 4 IBR, zero warnings). Console: service Running at HEAD (ca98481), domain provisioned, logs clean — an internet scanner probing `/.env` variants got straight 404s |
| 8 | README: run, decisions, AI, works-well + difficult lists | **green** | Sections present: Run it / Key design decisions / What works well / What is difficult, unreliable, or unsupported / Performance, cost, scalability / Where AI helped (45ce49f). Caveat, S1-gated: the frontend's link to these lists 404s for strangers while the repo is private |
| 9 | Analysis report v1 with measured numbers | **green** | be92d69: correctness §1 + metrics verbatim, held-out §2, runtime §3 (p50 0.041 s / p95 0.249 s, both populations explained), cost §4, scalability §5, weaknesses §6 |
| 10 | ≥3 curated prompt records; pre-B auditor audit committed | **green** | 5 curated records (`prompts/001–005`); `audits/2026-08-16-preb-audit.md` + disposition (31b07c3, 2ca4c4e) |
| 11 | Baseline armed via `--update-baseline` with its ADR | **green** | ADR-012; `.eval-baseline.json` = `{"fast": 1.0}`; CI jobs each proven red before trusted (G2) |

## Verdict

**11/11 green — T8 closes; the B-freeze is formal.** Three honest annotations,
none blocking: the gs-2002 transitional debt (enumerated, triaged, unscored);
the cosmetic S4 naming nit in line 4; the private-repo 404 on the README links
(line 8), which is S1's job to clear.

Also observed during the console check, for the record: `GIT_SHA` is absent
from the service's variables (S2 confirmed from the inside — and a manually
set value would go stale on every redeploy, so prefer a build-time injection
when doing S2); an unused `PASSWORD` variable sits on the service, read by
nothing in `src/`.
