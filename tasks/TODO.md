# Task 2 milestones — sec10k item extraction

Milestone-level only (ADR-009) — micro-tasks live in the session. Every row
names the reviewer evidence it buys (`docs/product/assignment-requirements.md`
C1–C7 / T1–T6) and the **Validation** gate it must clear to be called done.
A gate that has not run is written **`UNRUN`** in Status, never omitted — the
whole reason this file exists is that three cold-reviewer runs went missing
inside a prose clause.

**Freeze guard**: at T8 (B-freeze) the system stops taking features. Everything
after it is evidence-deepening only — `docs/product/milestones.md` ranks the
A-backlog. A new capability after the freeze is scope creep no matter how good
it looks.

| # | Milestone | Contents | Reviewer evidence | Validation | Status |
|---|-----------|----------|-------------------|------------|--------|
| T1 | Planning package | `docs/` (requirements map, problem definition, eval strategy, failure taxonomy, architecture), contract v2 + ADR-001..003, extraction-auditor agent, case-authoring skill, layer-8 validator design, curated prompt record | C1 C4 T1 | methodology audit runs and every finding is disposed before commit | **done** — bbbeb64…4bc80af; `docs/evals/audits/2026-08-15-methodology.md` |
| T2 | Eval expansion r1 + deploy spike | 17 cases red across 13 fixtures (1993–2026); harness v2 checks, per-item echo, `--dir` held-out plumbing, git SHA in reports; status rulings ADR-004/005; FastAPI + Zeabur spike with a live EDGAR fetch | T2 C3 C6 | every new case watched red before any implementation; dual-pass audit disposes all findings | **done** — e4e7b01 / 6743745 / 049a955 / 7cd7d11; `audits/2026-08-15-t2-dualpass.md` |
| T3 | Layers 2–3 — document selection + normalization | spike first (determinism + word-joining on all 13 fixtures) → ADR-006 rulings → INV-S5, `norm_contains` checks, vacuous-pass hole closed | T1 | spike findings land as red cases before the layer is built; `verbatim` partial green | **done** — ca7f1de (red) → 20067cf (3/3) · **cold-reviewer UNRUN** |
| T4 | Layers 4–7 — candidates, TOC filter, boundaries, status | ordered-candidate resolution, TOC-cluster suppression, boundary assignment, status classification; thresholds measured then ADR-007 | T1 T5 | the TOC trap case dies; txt stop-loss decided at exit, either way, in writing | **done** — 8bfc232 (19/20); ADR-007 §2 declines the stop-loss, txt era stays in scope · **cold-reviewer UNRUN** |
| T5 | Layers 8–9 — label-free validator battery + confidence + v2 envelope | 8 validators (TOC manifest cross-check, gap analysis, boundary hygiene, part-region consistency, rank-order length, numeric density, keyword fingerprints, dual-method agreement); priors from eval-set distributions, ADR-008 | robustness T5 | thresholds derived from measured distributions, never chosen ahead of data; `doc_status` cases green | **done** — 67ec058 (21/21) · **cold-reviewer UNRUN · spec-drift UNRUN** |
| T6 | Remaining goldens | mid-era HTML + large financial iXBRL goldens | T2 | green with no new code — if code is needed, it is a T4/T5 defect, not a T6 task | **done** — no commit; carried green by T4/T5, `report/20260816-010527-all.json` 1.0 @ a6ab0a5 |
| G1 | **Gate catch-up** | cold-reviewer cold-reads T3–T5 implementation; spec-drift audits specs↔code | C1 honesty | every finding becomes an adversarial case **watched red**, then fixed green (hard rule 2); zero findings is itself a reportable result | **done** — 4 red cases → ADR-010 → 25/25 fast, 8/8 invariant. Both audits ran; the spec↔code audit was dispatched to the cold-reviewer agent by mistake and ran under the spec-drift brief — remit covered, agent charter not exercised. **Open: 4 of 6 validators still unprovable, 4 adapter checks structurally cannot go red** (ADR-010 consequences) — deferred to T9 by scope decision, not closed. **Open: IBR offset recommendation awaiting sign-off** (below).** |
| G2 | **CI + armed baseline + branch protection** | one workflow (unit / invariant / fast); `--update-baseline` with its ADR; protect `main`: require PR + the 3 checks, block force-push and deletion | C2 | CI proven red on a deliberately broken commit before it is trusted; baseline non-empty so `run.py:130` can actually fire | **done (protection deferred)** — baseline armed at 1.000 (ADR-012); all three jobs each proven to exit 1 on their own deliberate break, then green on the runner (run 31936582729, 17s, no pip install). **Branch protection deliberately deferred to the G3→T7 boundary**: G3 is fixtures + frozen cases with zero behavior change, so a PR round-trip buys nothing, and locking main when implementation resumes is the honest version of the story rather than a retrofitted one. Settings agreed: require PR + the 3 checks, block force-push and deletion, no reviewer approval, admin bypass retained |
| G3 | **Held-out authoring** (frozen) | 5 shallow-tier filings + cases in `evals/heldout/`, era-stratified, disjoint from dev fixtures | T6 | authored and committed **without being run** — authoring must not leak an outcome | **done** — KO 1997 (txt, beverage), GS 2002 (transitional HTML, financial, Nov FY), JNJ 2016 (52/53-week FY ending Jan 1), XOM 2021 (the FY2021 9C cohort), COST 2022 (em-dash headings, Aug FY). Never run — verified by an independent tag-strip scan importing nothing from `src/`; isolation is structural (`CASE_DIRS` cannot reach the dir, `--dir` runs always write a report). Three predictions recorded in provenance **before** the first run so they cannot be retrofitted |
| T7 | Frontend inspector | fixture select + upload + EDGAR URL; item / status / confidence / method badges; warnings + `doc_status` banner; trace panel — on the already-proven Zeabur deploy | C3 T3 | a stranger can submit a filing, read the confidence, and understand a failure without reading the code | **todo** |
| H1 | **Held-out run #1** (T7 exit) | `--suite fast --dir evals/heldout` against the deployed system | T6 | report committed **before** any fix; burned cases triaged, promoted to adversarial, replaced | **todo** |
| T8 | B-freeze | held-out run #2, `evals/metrics.py`, `docs/analysis-report.md` v1 (measured latency/cost/scalability), README works-well + difficult/unsupported lists, pre-B extraction-auditor audit, baseline move | C5 C6 T4 T5 T6 | the B-exit checklist in `docs/product/milestones.md` is green line by line → **stop** | **todo** |
| T9+ | A-hardening | ranked backlog in `milestones.md` — eval expansion, confidence calibration, silent-failure rate, fallback (only if residual data justifies it), perf/cost numbers, taxonomy completeness | E-level markers | each item lands with its own eval evidence or it does not land | backlog |

## Open decision — IBR offsets (G1, awaiting sign-off)

The contract says non-`extracted` items carry null offsets; the code emits real
offsets for `incorporated_by_reference`, and eval anchors were **deleted** from
`textron-2001-content` to match the spec — coverage lost to a stale spec line.

Investigated, recommendation: **amend the contract, not the code.** `validate()`
builds its span map from `status == "extracted"` only, and the adapter's
`no_overlap_ordered` / `verbatim` do the same, so an IBR span is invisible to
all six validators and both structural checks — which is exactly what let
`ibr-pointer-first` disown 4,805 chars in silence. Nulling the offsets would
also cost the T7 inspector the pointer sentence itself, the evidence a human
uses to confirm an IBR claim; `heading_text` alone cannot show it.

So: keep pointer-text offsets for `incorporated_by_reference`, keep null for
`missing`/`omitted`, **and extend INV-S1 and boundary hygiene to cover IBR
spans** so a misclassification is loud rather than silent. Restore the deleted
Textron anchors. Not implemented — it changes a binding invariant.

Exit criteria + A-ranking: `docs/product/milestones.md` ·
Methodology: `docs/evals/evaluation-strategy.md` ·
Architecture: `docs/architecture/overview.md` ·
Ledger rationale: `specs/decisions/ADR-009-milestone-ledger.md`
