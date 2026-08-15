# sec-10k-extract

Item-level structured extraction of SEC 10-K filings — split a raw filing
(iXBRL, legacy HTML, or 1990s plain-text submission) into independently
consumable Items 1–16 with explicit status and honest confidence.

Built on [groundwork](https://github.com/HaoweiChan/groundwork), an eval-first
scaffold: correctness here has no public ground truth, so it is encoded as
executable invariants and golden/adversarial cases instead of prose specs.

## Status

Eval layer expanded (T2), pipeline not yet implemented — all cases
deliberately red: 17 cases (15 golden + shallow-tier, 3 adversarial) across
13 fixtures spanning 1993–2026: plain-text multi-document, 10-K405, mid-era
HTML, modern iXBRL, a 12MB financial, a shell company, a 10-Q refusal probe,
and a hand-degraded malformed-HTML corruption. Key contracts:
`specs/001-sec10k-contract.md` (v2 envelope, offset-verbatim rule),
`specs/000-invariants.md` (INV-0–S4, all invariant-suite-backed),
`specs/decisions/ADR-004/005` (pointer & trivial-body status rulings),
`.claude/skills/sec10k-domain/` (taxonomy eras + 10 known traps). A minimal
FastAPI deploy spike (`src/sec10k/web/`) wraps the stub for Zeabur.

Sections to come as the pipeline lands: how to run, frontend URL,
works-well / fails-honestly lists, performance & cost analysis.

---

## The template underneath

**An eval-first project scaffold for the agent era.**

Most of the code in a groundwork project will be written, reviewed, and
maintained by AI agents. What survives agent handoffs is not tribal knowledge
or session memory — it is architecture, executable checks, and enforcement.
groundwork is the ground those agents stand on: for problems with no public
ground truth (extraction, agents, pipelines, anything where "correct" is a
judgment call), you lay your own ground — the eval set.

## The idea

Prose specs like "the output must be correct" are unfalsifiable, and an agent
told "please be careful" will drift. groundwork replaces both:

- **The eval set IS the spec.** Correctness lives in executable invariants and
  golden/adversarial cases, not in requirement documents. If a property isn't
  backed by a case that can go red, it doesn't exist.
- **Advice doesn't bind agents; enforcement does.** CLAUDE.md is advice. Hooks
  are law. Anything that must never happen is enforced by a hook that blocks,
  not a sentence that asks.

## Architecture — four layers, no overlap

Each layer answers one question. Nothing appears in two layers.

| Layer | Lives in | Answers | Binding? |
|---|---|---|---|
| **Facts** | `CLAUDE.md` | What is invariantly true here? (structure, commands, hard rules) | advisory |
| **Knowledge** | `.claude/skills/` | How do we do X well? (loaded on demand, zero resident context) | advisory |
| **Execution** | `.claude/agents/` | Who checks the work? (fresh-context subagents, no author bias) | advisory |
| **Enforcement** | `.claude/hooks/` + `.githooks/` | What can never happen? | **blocking** |

The common failure mode this prevents: writing enforcement-layer intent
("never commit a regression") into the facts layer, where it is a polite
suggestion an agent can talk itself past.

### The enforcement loop in practice

- Every `src/` edit → PostToolUse hook runs the **invariant suite** (absolute,
  100% required). A failure is fed straight back to the editing agent as an
  error it must fix — no human in the loop.
- Every commit → pre-commit hook runs the **fast suite** against
  `.eval-baseline.json`. A score below baseline blocks the commit. The
  baseline moves only by explicit decision, recorded in an ADR.
- Every session end → the session's prompts are dumped to `prompts/raw/`,
  so the AI-collaboration record builds itself.

### The execution layer in practice

Four standing subagents, all evidence-only (they may not fix anything):

- `cold-reviewer` — cold-reads new code without the author's reasoning; its
  deliverable is the three most likely *silent* failure inputs.
- `eval-adversary` — attacks the gaps in the eval set with real-world inputs;
  its findings become adversarial cases verbatim.
- `spec-drift` — audits gaps between what the repo says (invariants, contracts,
  ADRs, docs) and what the code does; flags decorative invariants first.
- `extraction-auditor` — audits extraction outputs and the eval methodology
  itself; in output mode it is deliberately blind to the authors' reasoning
  and confidence derivation rules.

## Repo map

```
CLAUDE.md            facts layer — working rules, < 150 lines (AGENTS.md symlinks here)
.claude/settings.json  hooks registration + plugin wiring (ponytail auto-installs)
.claude/skills/      sec10k-domain · case-authoring · eval-protocol · failure-triage · cost-discipline · graphify (vendored)
.claude/agents/      cold-reviewer · eval-adversary · spec-drift · extraction-auditor
.claude/hooks/       post-edit invariant runner · session prompt logger
.githooks/           pre-commit eval gate
specs/               ONLY three kinds: invariants · output contracts · ADRs (why, not what)
docs/                durable design docs — product · evals · architecture (descriptive; specs/ binds)
evals/run.py         stdlib-only runner — defines the case + adapter contract
evals/golden/        hand-verified cases (provenance recorded per case)
evals/adversarial/   inputs that broke, or are designed to break, the pipeline
evals/fixtures/      committed public EDGAR filings + provenance README
evals/report/        every run's scored output, committed — the progress narrative
prompts/             AI-collaboration record: auto-dumped raw/ + curated correction chains
src/<task>/          implementations — each exposes eval_adapter.py to the runner
src/sec10k/web/      FastAPI service (deploy spike now, inspector UI at T7)
pyproject.toml       web-service deps only (fastapi/uvicorn) + zbpack.json/requirements.txt for Zeabur
```

## Using this template

```bash
git clone <this-repo> my-project && cd my-project
git config core.hooksPath .githooks   # enable the pre-commit eval gate
python3 -m evals.run --suite fast     # sanity: runner works (no cases yet)
```

Opening the repo in Claude Code auto-prompts to install the **ponytail** plugin
(lazy-first coding discipline); **graphify** (codebase knowledge graphs) is
vendored as a project skill. The harness itself is Python-stdlib-only; the
extraction pipeline is stdlib-only by ADR-003; the only third-party deps are
the web service's fastapi/uvicorn, declared in the root `pyproject.toml`
because the deploy platform reads them there.

To add a task: `src/<task>/eval_adapter.py` exposing
`run_case(case) -> {"passed": bool, ...}`, a domain skill, a contract spec,
and cases tagged `"task": "<task>"`. Details in `CLAUDE.md`.

Projects that outgrow the eval harness can delete `evals/` — every hook
degrades gracefully to a no-op.

## If you are an agent entering this repo

1. Read `CLAUDE.md` in full — it is short on purpose.
2. Run `python3 -m evals.run --suite fast` to see the current ground state.
3. Before changing behavior: write the failing case first, watch it fail.
4. Before claiming done: fast suite ≥ baseline, invariant suite at 100%.
5. When you hit a judgment call about what "correct" means — that is an ADR,
   not a code comment. Write it down in `specs/decisions/`.

## Per-feature loop

```
failing eval case → implement (invariant hook watching) → cold review
→ findings become adversarial cases → eval gate green → commit
```

Design rationale for the whole approach: `specs/decisions/ADR-000`.
