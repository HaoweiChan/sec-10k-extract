# Assignment requirements — Whaleforce AI Coding Test, Task 2

Faithful extraction of the assignment (EN/ZH, 2026 update). **Mandatory** = imposed
by the assignment; **choice** = our design decision, revisable without violating
anything. Every mandatory row names where this repo satisfies it — this table is
the coverage map that `spec-drift` and methodology audits check against.

## Common requirements

| # | Requirement | Kind | Satisfied by |
|---|---|---|---|
| C1 | AI-assisted workflow; how AI was used to reason, implement, evaluate, iterate | mandatory | `prompts/` (raw + curated), README "where AI helped" section |
| C2 | Public git repo; commit history reflects the real development process | mandatory | commit strategy in [milestones.md](milestones.md) — eval-first red→green pairs, no squashed story |
| C3 | Publicly accessible web frontend per task; not API-only; operable from a browser | mandatory | FastAPI + vanilla JS inspector on Zeabur (T7); views specified in [task2-problem-definition.md](task2-problem-definition.md) |
| C4 | Root `prompts/` folder with key prompts — they will read them | mandatory | `prompts/` with curation rules in `prompts/README.md`; CLAUDE.md hard rule 6 |
| C5 | README: how to run, key design decisions, where AI helped | mandatory | README rewrite at T8 |
| C6 | Analysis report: runtime performance, cost, scalability, correctness verification | mandatory | `docs/analysis-report.md` (T8), written from committed `evals/report/` logs — measured, not guessed |
| C7 | Public or self-created material only | mandatory | EDGAR filings with provenance in `evals/fixtures/README.md`; adversarial corruptions self-created; OSS cross-check tools only as dev instruments |

## Task 2 requirements

| # | Requirement | Kind | Satisfied by |
|---|---|---|---|
| T1 | Extract individual Items from raw 10-K filings so they are independently consumable | mandatory | `specs/001-sec10k-contract.md` (offset-based items) |
| T2 | Self-built eval set verifying reliability | mandatory | `evals/` golden + adversarial (+ heldout at T2); [evaluation-strategy.md](../evals/evaluation-strategy.md) |
| T3 | Frontend: submit **or** select filings, inspect extracted items, understand confidence / failure cases | mandatory | fixture-select + upload + URL modes; item/confidence/warning/trace views |
| T4 | List filings/companies that work well, with examples | mandatory | README + frontend page (T8) |
| T5 | List filings/companies that are difficult/unreliable/unsupported, with concrete failure cases | mandatory | same — fed by adversarial debt + audit findings |
| T6 | Survives their held-out filings against the deployed system | external test | upload path first-class; explicit `unsupported`/`failed` statuses; held-out discipline in evaluation-strategy.md |

**What they grade** (their words): robustness under format variance → [failure-taxonomy.md](../evals/failure-taxonomy.md) + architecture layers; self-verification without public ground truth → evaluation-strategy "ground truth" section; edge-case handling → adversarial suite; cost discipline → `cost-discipline` skill + cost metrics; perf/scalability/correctness analysis → analysis report.

**Rubric**: A = eval depth, layered tradeoffs, concrete perf/cost/scalability analysis, honest failure modes, high-quality prompt records. B = basic functionality, surface-level eval/analysis. C = happy path only. Our plan: legitimate B first, then A-hardening that is evidence-deepening, not feature-adding (milestones.md).

## Our design choices (not mandated)

Eval-first groundwork conventions; deterministic-first pipeline with LLM deferred
until residual-failure data exists; anchor-based ground truth; FastAPI on Zeabur;
stdlib-only parsing at B. Each recorded in `specs/decisions/`.
