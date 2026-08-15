# 001 — Task 2 planning: prompt record

## Purpose

The planning prompt used before any implementation — the input side of this
record pair. What it produced, what the human constrained, and what got
corrected live in `002-task2-planning-outcome.md`; the
Assumption → Eval contradiction → Correction chain lives there too, so this
file carries none (single source of truth).

## Human decisions before prompting

1. Evaluation must be designed before implementation.
2. The auditor must be independent from the implementation agent.
3. Reach a legitimate B-level baseline first, then harden toward A-level.
4. Assignment requirements (`prompts/`, frontend, README, analysis report,
   public deployment) are part of the repo design from the beginning.

## Outcome

Executed 2026-08-15. Produced the planning batch: `docs/` design docs,
contract v2 (+ ADR-001..003), the `extraction-auditor` agent, the
`case-authoring` skill, and the first methodology audit — see `002` for the
full record.

## Prompt (verbatim)

You are responsible for planning the implementation of **Task 2: SEC 10-K Item-level Structured Extraction** for the Whaleforce AI Coding Test.

Do **not** start implementing the extraction system yet.

Your first job is to design the problem, engineering methodology, repository structure, evaluation strategy, agent workflow, and execution plan so that subsequent implementation can proceed systematically.

## 0. Read the assignment first

Read the provided Whaleforce AI Coding Test assignment in full before making any plan.

Treat the assignment as the authoritative source of requirements.

In particular, preserve and explicitly account for all common requirements, including:

- AI-assisted development workflow
- public Git repository with meaningful commit history
- publicly accessible frontend for every submitted task
- root-level `prompts/` directory containing important AI prompts
- README covering setup, design decisions, and where AI contributed
- analysis of runtime performance, cost, scalability, and correctness verification
- only public or self-created materials

For Task 2 specifically, the system must:

- accept raw SEC 10-K filings
- extract individual Items so they can be consumed independently
- handle substantial filing-format variance
- provide an evaluation set created by us
- expose results through a browser frontend
- expose extraction confidence and/or failure cases
- identify filings/companies that work well
- identify difficult, unreliable, or unsupported cases with concrete examples
- survive held-out filings chosen by the evaluator

The assignment explicitly values:

- robustness under format variance
- correctness verification without relying on public ground truth
- edge-case handling
- cost discipline
- runtime/scalability analysis
- honest failure reporting
- high-quality AI collaboration

Optimize the project for those criteria rather than simply maximizing feature count.

---

# 1. Define the problem precisely

Before proposing architecture, write a precise problem definition.

Clarify:

### Inputs
Examples:

- SEC filing URL
- accession number
- raw HTML
- downloaded filing document

Determine which should be supported in v1 and which are non-goals.

### Outputs

Define the structured output contract for an extracted Item.

Consider fields such as:

- item identifier
- canonical item name
- detected heading
- extracted text/content
- source offsets or DOM references
- extraction method
- confidence
- warnings
- validation results

Do not choose these fields blindly; explain why each field helps correctness, inspectability, evaluation, or downstream consumption.

### Supported scope

Define what counts as a supported 10-K.

Explicitly consider:

- standard 10-K
- 10-K/A
- older filings
- modern inline XBRL filings
- HTML filings
- plain-text filings
- unusual/malformed filings
- filings containing exhibits or multiple documents

Separate:

- required v1 support
- stretch support
- explicitly unsupported cases

---

# 2. Build a failure taxonomy before implementation

Identify realistic ways Item extraction can fail.

At minimum investigate:

- Table of Contents headings mistaken for actual Item headings
- repeated Item headings
- inconsistent heading capitalization
- punctuation variants
- HTML nesting differences
- headings inside tables
- inline headings embedded in paragraphs
- malformed HTML
- missing Items
- intentionally omitted Items
- Item numbering ambiguity
- Item 1 vs Item 1A vs Item 1B vs Item 1C
- Item 7 vs Item 7A
- cross-references containing Item names
- page headers/footers
- multiple filing documents
- old SEC formatting conventions
- modern inline XBRL markup
- very large filings
- unexpected ordering
- duplicate content
- false-success cases where plausible-looking output is actually wrong

Group failures into a taxonomy.

For every failure category, identify:

1. how it could be detected,
2. how it could be mitigated,
3. how it should appear in evaluation,
4. whether the system should recover, lower confidence, or explicitly fail.

Pay special attention to **silent failures**.

---

# 3. Design the evaluation methodology BEFORE designing the final algorithm

Evaluation is a first-class deliverable.

Do not let the implementation agent define its own success criteria after seeing results.

Create an independent evaluation strategy.

## Evaluation dataset

Propose a deliberately diverse set of filings rather than random samples.

Stratify across dimensions such as:

- filing year / era
- company
- filing size
- HTML structure
- industry
- standard vs unusual formatting
- easy vs deliberately difficult examples

Define:

- development set
- validation/evaluation set
- local held-out set

The implementation workflow must avoid repeatedly tuning against the local held-out set.

Explain how many filings are appropriate for the B-level baseline and what should be expanded when pushing toward A-level.

## Ground truth

The assignment specifically asks how correctness can be verified without public ground truth.

Design a realistic ground-truth process.

Consider combinations of:

- human annotation
- heading/boundary annotation
- dual-pass review
- structural invariants
- independent extraction approaches
- sampling-based manual audit

Do not assume an external Item extraction dataset exists.

## Metrics

Define useful metrics for more than just "success/failure".

Consider:

- Item presence recall
- Item identification accuracy
- heading detection precision/recall
- boundary accuracy
- boundary overlap / IoU
- content completeness
- false-positive extraction rate
- missing-item detection
- silent-failure rate
- document-level success rate
- Item-level success rate
- confidence calibration
- latency
- deterministic processing rate
- LLM fallback rate
- cost per filing

For each metric, specify:

- what it measures
- why it matters
- how it is calculated
- what failure it can reveal

Do not invent arbitrary target thresholds without justification. If initial targets are proposed, mark them explicitly as provisional and explain how they should be revised after baseline measurements.

---

# 4. Create an independent Auditor subagent

Design a dedicated subagent named approximately:

`extraction-auditor`

The auditor must be meaningfully independent from the implementation agent.

Its responsibilities should include:

- inspecting evaluation methodology
- looking for evaluation leakage
- inspecting extracted Items
- challenging confidence estimates
- detecting silent failures
- finding cases where metrics can be gamed
- sampling outputs for manual verification
- comparing extraction against source filing evidence
- identifying missing failure categories
- producing failure reports
- recommending new adversarial eval cases

The auditor should NOT primarily implement the extraction algorithm.

Prefer read-only access unless write access to specific evaluation artifacts is justified.

Define:

- its system instructions
- tools it needs
- tools it should not have
- when it should run
- what artifacts it produces
- how disagreements between implementation metrics and auditor findings are handled

Consider whether it should have access to the implementation plan before auditing, and discuss the tradeoff.

---

# 5. Define the system architecture

After defining evaluation, propose the extraction architecture.

Prefer a layered design instead of immediately sending entire filings to an LLM.

Evaluate an architecture similar to:

SEC filing acquisition
→ document selection
→ normalization
→ candidate heading detection
→ TOC / false-candidate filtering
→ Item boundary resolution
→ structural validation
→ confidence scoring
→ fallback strategy
→ structured output

For every layer specify:

- responsibilities
- likely implementation strategy
- failure modes
- observability
- tests
- evaluation signals

Explicitly compare:

### deterministic approaches
vs
### heuristic/scoring approaches
vs
### LLM-assisted fallback

Discuss tradeoffs in:

- reliability
- latency
- cost
- explainability
- scalability
- brittleness

LLM usage should be justified rather than assumed.

---

# 6. Design confidence and failure semantics

Do not return meaningless arbitrary confidence scores such as `0.97`.

Define what confidence represents.

Explore whether confidence can be based on observable evidence such as:

- heading match quality
- DOM semantics
- ordering consistency
- candidate ambiguity
- agreement between multiple extraction methods
- expected Item sequence
- boundary evidence
- validation failures
- auditor or secondary-model disagreement

Design how confidence could eventually be calibrated against empirical evaluation results.

Also define explicit statuses such as:

- success
- success_with_warning
- ambiguous
- unsupported
- failed

The frontend should make these distinctions inspectable.

---

# 7. Design the repository as an AI-native engineering environment

Create a repo structure that supports Claude Code and potentially Codex.

Do not put everything into one giant `CLAUDE.md`.

Use repository-local documentation with clear responsibilities.

Consider something approximately like:

```text
/
├── CLAUDE.md
├── AGENTS.md
├── README.md
├── prompts/
├── docs/
│   ├── product/
│   ├── architecture/
│   ├── specs/
│   ├── plans/
│   │   ├── active/
│   │   └── completed/
│   └── evals/
├── tasks/
│   ├── TODO.md
│   └── completed/
├── .claude/
│   ├── agents/
│   └── skills/
├── src/
├── tests/
└── evals/
```

You may improve this structure if justified.

Define the role of:

- `CLAUDE.md`
- `AGENTS.md`
- `README.md`
- `prompts/`
- specs
- implementation plans
- task tracker
- architecture decision records if needed
- evaluation datasets/results

Avoid duplicated sources of truth.

---

# 8. Design Skills

Propose only Skills that encode reusable workflows.

Candidates include:

- `create-spec`
- `plan-feature`
- `execute-task`
- `run-eval`
- `audit-extraction`
- `debug-eval-failure`
- `review-change`
- `finish-task`

For each Skill describe:

- when it should be invoked
- expected inputs
- procedure
- expected outputs
- files it may update

Do not create Skills that are just vague personas such as "senior Python engineer".

---

# 9. Design subagents

Keep the number of subagents intentionally small.

Evaluate whether we need:

### Researcher
For investigating SEC filing structure, repository code, or known failure patterns.

### Evaluator
For running evaluation and clustering failures.

### Extraction Auditor
For independent correctness auditing and adversarial review.

### Reviewer
For spec compliance, architecture regression, test coverage, and silent-failure review.

Avoid building a fake organization of many overlapping agents.

For every proposed subagent specify:

- responsibility
- context isolation benefit
- tool permissions
- write permissions
- triggering conditions
- output contract

Explain why the task should be a subagent rather than a Skill.

---

# 10. Define specs and implementation plans

Break Task 2 into durable feature specs.

For example:

```text
001-filing-acquisition
002-document-normalization
003-heading-candidates
004-item-boundary-resolution
005-structural-validation
006-confidence-scoring
007-evaluation-framework
008-web-frontend
009-observability
```

These names are examples only.

Improve the decomposition if appropriate.

Each spec should eventually contain:

- Goal
- User-visible behavior
- Requirements
- Non-goals
- Failure modes
- Acceptance criteria
- Open questions

Separate durable specs from temporary implementation plans.

Plans should describe HOW a particular implementation iteration will satisfy a spec.

---

# 11. Define the task system

Create a simple `tasks/TODO.md` methodology.

The task tracker should act as a scheduler, not a knowledge base.

Each task should have enough information to resolve its context, for example:

```text
T012 — Implement TOC candidate filtering

priority:
status:
spec:
plan:
dependencies:
validation:
owner/agent:
```

Avoid copying architecture and requirements into the TODO file.

Tasks should link back to their specs/plans.

---

# 12. Plan B-level first, then A-level hardening

We intend to first reach a legitimate B-level implementation, then use remaining engineering time to push Task 2 toward A-level quality.

Define both milestones separately.

## Task 2 B-level

Specify the minimum complete system that deserves to be called B-level rather than a happy-path prototype.

It must still satisfy all mandatory assignment submission requirements.

Define:

- supported input scope
- extraction capabilities
- evaluation size/depth
- frontend capabilities
- required documentation
- minimum failure handling
- required deployment state

## Task 2 A-level hardening

Do NOT define A as "more features".

Define improvements primarily in terms of evidence quality and engineering depth:

- broader/adversarial evaluation
- stronger failure taxonomy
- lower silent-failure rate
- confidence calibration
- layered fallback strategies
- stronger auditor process
- error analysis
- performance measurements
- cost analysis
- scalability analysis
- explicit tradeoff documentation

Clearly identify which improvements provide the highest marginal evaluation value.

---

# 13. Plan frontend requirements

The frontend is not only a demo.

It should make the system inspectable.

Design views for:

- choosing or submitting a filing
- extracted Item navigation
- source evidence
- confidence
- warnings
- extraction method
- failure states
- timing
- possibly cost
- debug/audit information where useful

Avoid wasting excessive engineering time on visual polish.

Prioritize evaluator usability and inspectability.

---

# 14. Plan observability

Design structured execution traces.

For each filing, we should be able to answer:

- what document was selected?
- what candidate headings were found?
- which candidates were rejected and why?
- which boundaries were selected?
- which validations passed/failed?
- whether fallback was invoked?
- why confidence changed?
- what failed?

This information should be usable by:

- developers
- evaluator
- auditor subagent
- frontend

Do not expose internal chain-of-thought. Use structured decisions, evidence, and diagnostics.

---

# 15. Preserve AI collaboration evidence

Because the assignment explicitly evaluates AI collaboration quality:

Design a `prompts/` strategy from the beginning.

Decide what prompts should be saved.

Examples:

- initial architecture planning
- evaluation design
- difficult failure debugging
- auditor prompts
- major implementation prompts
- major review prompts

Do not dump every trivial interaction.

Create a naming convention and lightweight metadata format if useful.

The goal is for a reviewer to understand:

- what AI was asked to do
- what human decisions constrained it
- how outputs were evaluated
- how plans changed after failures

---

# 16. Commit strategy

Because commit history will be inspected, propose a development commit strategy.

Avoid both:

- one giant final commit
- artificial meaningless micro-commits

Commits should reflect coherent engineering milestones.

Include examples of likely commit boundaries.

---

# 17. Produce the planning artifacts

After completing the analysis, create or propose the following artifacts.

Do not implement the production extraction pipeline yet unless needed for minimal exploratory spikes.

Required planning outputs:

1. `docs/product/assignment-requirements.md`
   - faithful extraction of assignment requirements
   - distinguish mandatory requirements from our design choices

2. `docs/product/task2-problem-definition.md`

3. `docs/evals/evaluation-strategy.md`

4. `docs/evals/failure-taxonomy.md`

5. `docs/architecture/overview.md`

6. `docs/specs/`
   - initial spec decomposition

7. `docs/plans/active/task2-b-baseline.md`

8. `docs/plans/active/task2-a-hardening.md`

9. `tasks/TODO.md`

10. proposed `.claude/agents/extraction-auditor.md`

11. proposed other subagents only if justified

12. proposed `.claude/skills/` structure

13. root-level `prompts/` strategy

14. a short document describing B-level exit criteria and A-level hardening priorities

---

# 18. Final review before implementation

Before considering planning complete, perform a self-review and then use the independent auditor/reviewer perspective to challenge the plan.

Explicitly answer:

1. Are all assignment requirements represented somewhere in the repo plan?
2. Could we accidentally satisfy our metrics while extracting the wrong content?
3. Where are silent failures most likely?
4. Is our eval set likely to overfit our implementation?
5. Which parts of the design are unnecessary overengineering?
6. Which parts are currently under-specified?
7. What are the three highest-risk technical unknowns?
8. What exploratory spikes should happen before committing to architecture?
9. What is the shortest path to a legitimate B-level submission?
10. After B-level, what three investments have the highest probability of moving the work toward A-level?

If an assignment requirement conflicts with any proposal in this prompt, **the assignment wins**.

Do not optimize for blindly following this prompt. Treat it as planning guidance, challenge weak assumptions, and document important disagreements.

At the end, give me:

- proposed repository tree
- spec list
- subagent list
- skill list
- B-level milestone
- A-level hardening plan
- prioritized task list
- major risks
- unresolved decisions

Then stop and wait for implementation instructions.