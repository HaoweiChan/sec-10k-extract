# Project working rules

Eval-first repo, built on **groundwork**. Tasks live under `src/<task>/`.
**The eval set IS the spec.** groundwork targets problems where requirements
are clear but correctness is hard to define up front — so correctness is encoded
as executable invariants and metrics, not prose. Architecture rationale lives in
README.md; this file is the working contract.

## Toolchain

- **ponytail** plugin is enabled repo-wide via `.claude/settings.json` — laziest
  working solution, stdlib first, shortest diff. Applies to all code here.
- **graphify** is vendored as a project skill — use `/graphify` for architecture
  and file-relationship questions; once `graphify-out/` exists, treat such
  questions as graphify queries first.

## Layout

```
.claude/skills/    domain + process knowledge, loaded on demand
.claude/agents/    cold-reviewer / eval-adversary / spec-drift / extraction-auditor
docs/              durable design docs (product, evals, architecture) — descriptive; specs/ binds
tasks/TODO.md      milestone ledger — status + per-milestone Validation gates (ADR-009)
.claude/hooks/     enforcement — the only layer that can actually block
.githooks/         pre-commit eval gate (installed via core.hooksPath)
specs/             ONLY: 000-invariants.md, per-task contracts, decisions/ADR-*.md
evals/golden/      hand-labeled cases (JSON, one per case)
evals/adversarial/ cases known or designed to break the pipeline
evals/fixtures/    committed EDGAR filings, provenance in its README
evals/report/      every run's output, committed to git
prompts/           AI-collaboration record (auto-dumped raw/ + curated files)
src/<task>/        implementation + eval_adapter.py per task
```

## Gate

The objective pass/fail for this repo. pr-loop, the hooks, and any reviewer
run exactly these, in order:

```bash
python3 -m evals.run --suite invariant   # pass: 100%
python3 -m evals.run --suite fast        # pass: score >= .eval-baseline.json
```

## Commands

```bash
python3 -m evals.run --suite fast              # quick gate suite
python3 -m evals.run --suite invariant         # must-always-hold assertions
python3 -m evals.run --suite all               # everything, writes report
python3 -m evals.run --suite fast --dir evals/heldout  # held-out run (milestones only; always writes report)
python3 -m evals.run --suite fast --update-baseline   # deliberate baseline move
```

## Hard rules

1. **Never edit `.eval-baseline.json` by hand** and never `--update-baseline` just to
   make the pre-commit gate pass. A baseline move is a decision — record why in an ADR.
2. **Every new failure becomes a case** in `evals/adversarial/` before it is fixed.
   Watch the new case fail first; an eval you've never seen red proves nothing.
3. **specs/ holds only three kinds of files**: invariants, output contracts, ADRs.
   No plans there, ever. Task state lives in exactly one file — `tasks/TODO.md`,
   milestone-level only (ADR-009). Micro-tasks stay in the session. Every ledger
   row names its Validation gate, and a gate that has not run is written
   **`UNRUN`** in Status rather than omitted.
4. **No mocked results.** If a live dependency is unreachable, fail loudly; never
   fabricate output to make a run look green.
5. Commits go through the pre-commit eval gate. `--no-verify` is for emergencies
   and must be explained in the commit message.
6. **Preserve material AI decisions.** If an AI interaction materially changes
   architecture, evaluation methodology, failure handling, an output contract, or
   another major implementation decision, preserve the key prompt and outcome in
   `prompts/`. Do not curate routine coding, formatting, or trivial debugging
   interactions. Raw transcripts may be auto-dumped; `prompts/` curated records
   should capture decisions worth reviewing.
7. **Commits are consolidated milestones.** The assignment evaluators read the
   history. Commit only settled, coherent progress — no micro-commits, and no
   quick fix-commit chasing the commit it patches. Verify the batch first
   (re-read the diff, run the relevant audits); a defect found in an unpushed
   commit is amended into it, and once pushed, the fix rides the next
   consolidated commit with its own honest message.

## Per-feature loop

1. Plan mode → ADR + new invariant/eval cases (eval first)
2. Watch the new cases fail
3. Implement (PostToolUse hook keeps running the invariant suite)
4. `cold-reviewer` subagent cold-reads → its findings become adversarial cases
5. New cases into the eval set → back to 3
6. Eval gate green → commit

## Adding a task

1. `src/<task>/` with an `eval_adapter.py` exposing `run_case(case) -> {"passed": bool, ...}`
2. A domain-knowledge skill in `.claude/skills/<task>-domain/`
3. A contract spec `specs/0NN-<task>-contract.md`
4. Golden + adversarial cases tagged with `"task": "<task>"`