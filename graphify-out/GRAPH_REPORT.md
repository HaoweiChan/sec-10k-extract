# Graph Report - .  (2026-08-17)

## Corpus Check
- 159 files · ~459,151 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 458 nodes · 768 edges · 40 communities (35 shown, 5 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 102 edges (avg confidence: 0.81)
- Token cost: 455,988 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Audit Findings and Methodology|Audit Findings and Methodology]]
- [[_COMMUNITY_Extraction and Segmentation Core|Extraction and Segmentation Core]]
- [[_COMMUNITY_Eval Runner and Inspector Service|Eval Runner and Inspector Service]]
- [[_COMMUNITY_Eval Adapter Check Vocabulary|Eval Adapter Check Vocabulary]]
- [[_COMMUNITY_Graphify Pipeline Reference|Graphify Pipeline Reference]]
- [[_COMMUNITY_Normalization Layer|Normalization Layer]]
- [[_COMMUNITY_Architecture Layer Overview|Architecture Layer Overview]]
- [[_COMMUNITY_10-K Domain Traps|10-K Domain Traps]]
- [[_COMMUNITY_Cost and Eval Protocol|Cost and Eval Protocol]]
- [[_COMMUNITY_Heading Detection and Boundaries|Heading Detection and Boundaries]]
- [[_COMMUNITY_Invariants and Status ADRs|Invariants and Status ADRs]]
- [[_COMMUNITY_Measured Thresholds and Confidence|Measured Thresholds and Confidence]]
- [[_COMMUNITY_Eval-First Scaffold Decisions|Eval-First Scaffold Decisions]]
- [[_COMMUNITY_Validator Battery Measurement|Validator Battery Measurement]]
- [[_COMMUNITY_Fixture Inventory and Provenance|Fixture Inventory and Provenance]]
- [[_COMMUNITY_Review Agent Roles|Review Agent Roles]]
- [[_COMMUNITY_Failure Triage Process|Failure Triage Process]]
- [[_COMMUNITY_Span Invariants and IBR|Span Invariants and IBR]]
- [[_COMMUNITY_Normalization Rulings|Normalization Rulings]]
- [[_COMMUNITY_Inspector API and Frontend|Inspector API and Frontend]]
- [[_COMMUNITY_Case Authoring and Held-out|Case Authoring and Held-out]]
- [[_COMMUNITY_Layer 8 Validator Battery|Layer 8 Validator Battery]]
- [[_COMMUNITY_Dual-Pass Anchor Audit|Dual-Pass Anchor Audit]]
- [[_COMMUNITY_Metrics Computation|Metrics Computation]]
- [[_COMMUNITY_Output Contract v2|Output Contract v2]]
- [[_COMMUNITY_Frontend and Milestone Gates|Frontend and Milestone Gates]]
- [[_COMMUNITY_CI Eval Gate Jobs|CI Eval Gate Jobs]]
- [[_COMMUNITY_Project Working Rules|Project Working Rules]]
- [[_COMMUNITY_Silent-Success Failure Class|Silent-Success Failure Class]]
- [[_COMMUNITY_Taxonomy Era Model|Taxonomy Era Model]]
- [[_COMMUNITY_A-Track Milestones T9-T14|A-Track Milestones T9-T14]]
- [[_COMMUNITY_Ground Truth Without Data|Ground Truth Without Data]]
- [[_COMMUNITY_Post-Edit Invariant Hook|Post-Edit Invariant Hook]]
- [[_COMMUNITY_B-Freeze Guard|B-Freeze Guard]]
- [[_COMMUNITY_Repo Root Node|Repo Root Node]]
- [[_COMMUNITY_Date Regex Ruling|Date Regex Ruling]]
- [[_COMMUNITY_Repo Publication Task|Repo Publication Task]]

## God Nodes (most connected - your core abstractions)
1. `eval_check()` - 20 edges
2. `extract_items()` - 18 edges
3. `Architecture overview — sec10k pipeline` - 16 edges
4. `Evaluation strategy — sec10k` - 15 edges
5. `Analysis report v1 (B-freeze)` - 14 edges
6. `Fixture inventory and provenance` - 14 edges
7. `graphify pipeline` - 13 edges
8. `Layer 8 — Label-free validator battery` - 13 edges
9. `Failure taxonomy` - 13 edges
10. `Held-out set — frozen inventory` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Real inputs over synthetic corruption` --semantically_similar_to--> `Held-out discipline`  [INFERRED] [semantically similar]
  .claude/agents/eval-adversary.md → README.md
- `Metric gaming check` --semantically_similar_to--> `Checks structurally incapable of failing`  [INFERRED] [semantically similar]
  .claude/agents/extraction-auditor.md → README.md
- `Label-free validator battery` --semantically_similar_to--> `Shallow-tier case`  [INFERRED] [semantically similar]
  README.md → .claude/skills/case-authoring/SKILL.md
- `doc_status and refusal to guess` --semantically_similar_to--> `Five failure classes`  [INFERRED] [semantically similar]
  README.md → .claude/skills/failure-triage/SKILL.md
- `Graph health check` --semantically_similar_to--> `Label-free validator battery`  [INFERRED] [semantically similar]
  .claude/skills/graphify/SKILL.md → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Separation of independent review roles** — _claude_agents_cold_reviewer_cold_reviewer, _claude_agents_eval_adversary_eval_adversary, _claude_agents_extraction_auditor_extraction_auditor, _claude_agents_spec_drift_spec_drift, readme_separation_of_roles [EXTRACTED 1.00]
- **The eval gate: suites, baseline, CI, hooks** — _claude_skills_eval_protocol_skill_invariant_suite, _claude_skills_eval_protocol_skill_fast_suite, _claude_skills_eval_protocol_skill_baseline_discipline, _github_workflows_ci_eval_gate, claude_hook_enforcement_layer [INFERRED 0.95]
- **10-K item-boundary trap family** — _claude_skills_sec10k_domain_skill_toc_trap, _claude_skills_sec10k_domain_skill_regulation_reference_trap, _claude_skills_sec10k_domain_skill_trailing_exhibit_tail, _claude_skills_sec10k_domain_skill_internal_pointer_items, _claude_skills_sec10k_domain_skill_noncanonical_headings [EXTRACTED 1.00]
- **Eleven-layer sec10k extraction pipeline** — docs_architecture_overview_acquisition, docs_architecture_overview_document_selection, docs_architecture_overview_normalization, docs_architecture_overview_candidate_detection, docs_architecture_overview_toc_false_candidate_filter, docs_architecture_overview_boundary_resolution, docs_architecture_overview_status_classification, docs_architecture_overview_structural_validation, docs_architecture_overview_confidence_scoring, docs_architecture_overview_fallback, docs_architecture_overview_assembly [EXTRACTED 1.00]
- **Held-out burn/refresh generalization cycle** — evals_heldout_readme_burn_rule, evals_heldout_readme_structural_isolation, docs_evals_audits_2026_08_16_h1_heldout_triage, docs_evals_audits_2026_08_17_h2_heldout, docs_evals_evaluation_strategy_audit_trail, docs_analysis_report_generalization_evidence [EXTRACTED 1.00]
- **Correctness verification without public ground truth** — docs_evals_evaluation_strategy_ground_truth_without_public_data, docs_evals_evaluation_strategy_boundary_anchors, docs_architecture_overview_structural_validation, docs_evals_audits_2026_08_15_methodology, docs_analysis_report_silent_failure_rate [EXTRACTED 1.00]
- **The repo's recurring "a check that cannot fail" defect class** — specs_decisions_adr_009_milestone_ledger_unobservable_gate, specs_decisions_adr_012_arm_the_baseline_check_that_cannot_fail, specs_decisions_adr_005_trivial_body_status_unreachable_status, specs_000_invariants_decorative_invariant, specs_decisions_adr_010_g1_corrections_collapse_before_form [INFERRED 0.85]
- **Item status semantics decided across ADR-004/005/011 and the contract** — specs_001_sec10k_contract_item_status, specs_decisions_adr_004_pointer_item_status_pointer_shapes, specs_decisions_adr_005_trivial_body_status_omitted_vs_missing, specs_decisions_adr_011_ibr_offsets, specs_decisions_adr_010_g1_corrections_ibr_remainder_max [EXTRACTED 1.00]
- **Heading detection: same-line rule, similarity floor, TOC cluster, next-line promotion** — specs_decisions_adr_007_segmentation_thresholds_same_line_rule, specs_decisions_adr_007_segmentation_thresholds_sim_floor, specs_decisions_adr_007_segmentation_thresholds_toc_cluster_filter, specs_decisions_adr_013_heading_shape_and_escalation_next_line_title, specs_decisions_adr_014_t9_tranche1_rulings_item4_reserved_window [EXTRACTED 1.00]

## Communities (40 total, 5 thin omitted)

### Community 0 - "Audit Findings and Methodology"
Cohesion: 0.08
Nodes (51): Analysis report v1 (B-freeze), Era table as single point of silent failure, Generalization evidence is two filings, Silent-failure rate (metric 6), Checks that cannot fail by construction, Methodology audit (pre-implementation), Leakage-impossible-by-ordering (author cases before pipeline), Finding: INV-S4 has no enforcing check (+43 more)

### Community 1 - "Extraction and Segmentation Core"
Cohesion: 0.09
Nodes (36): _envelope(), extract_items(), _item(), 10-K item-level extraction. Contract: specs/001-sec10k-contract.md.  Layers 1-9, Extract items from a 10-K filing.      Returns {"normalized_text": str, "doc_sta, assign_boundaries(), classify(), _demo() (+28 more)

### Community 2 - "Eval Runner and Inspector Service"
Cohesion: 0.09
Nodes (29): git_sha(), load_cases(), main(), run_case(), Path, Request, api_meta(), edgar_check() (+21 more)

### Community 3 - "Eval Adapter Check Vocabulary"
Cohesion: 0.16
Nodes (23): eval_check(), item_text(), Eval adapter for sec10k — owns the check vocabulary and item registry.  Case sha, Judge a single check against a result dict.      Returns None on pass, else a fa, run_case(), item(), Self-check for the eval check vocabulary itself — NOT an eval run.  Feeds hand-b, ADR-011: incorporated_by_reference carries pointer-text offsets, so the     stru (+15 more)

### Community 4 - "Graphify Pipeline Reference"
Cohesion: 0.12
Nodes (25): /graphify add URL ingestion, --watch auto-rebuild, Neo4j / FalkorDB Cypher export, graphify MCP server export, Discrete confidence rubric, Deterministic node ID format, Verbatim source_file rule, graphify extraction subagent prompt (+17 more)

### Community 5 - "Normalization Layer"
Cohesion: 0.12
Nodes (19): HTMLParser, _demo(), format_era(), normalize(), _parse_date(), period_end(), _Plain, Layers 2-3: document selection + normalization.  Mechanism: docs/architecture/ov (+11 more)

### Community 6 - "Architecture Layer Overview"
Cohesion: 0.17
Nodes (18): Deterministic coverage / structurally $0 cost, Scalability projection (18.9 MB/s, pure function), Architecture overview — sec10k pipeline, Layer 1 — Acquisition, Layer 11 — Assembly, Deterministic → heuristic → LLM ladder, Layer 2 — Document selection, Layer 10 — Deferred LLM fallback (+10 more)

### Community 7 - "10-K Domain Traps"
Cohesion: 0.18
Nodes (15): eval-adversary agent, Real inputs over synthetic corruption, Format eras (txt / HTML / iXBRL), Incorporation by reference, Internal-pointer items, Item taxonomy by era, Wild non-canonical item headings, Regulation and cross-reference traps (+7 more)

### Community 8 - "Cost and Eval Protocol"
Cohesion: 0.18
Nodes (14): Content-hash external call cache, Cost discipline, Escalation ladder (regex to big model), Enforced per-run budget, Baseline discipline, Eval protocol, fast suite (pre-commit gate), full suite (slow/paid cases) (+6 more)

### Community 9 - "Heading Detection and Boundaries"
Cohesion: 0.23
Nodes (12): Layer 6 — Boundary resolution, Same-line title heading discriminator, Layer 7 — Status classification, Layer 5 — TOC / false-candidate filter, ADR-005 omitted-vs-missing status ruling, Finding 1: JNJ markup inverts the heading discriminator, F1 — False-positive headings, F3 — Absence and status ambiguity (+4 more)

### Community 10 - "Invariants and Status ADRs"
Cohesion: 0.17
Nodes (12): 000 — Invariants, An invariant without a backing eval case is decorative drift, ADR-004: Status semantics for pointer-shaped items, Three pointer shapes (external / internal same-document / mixed), The extractor reports what the filing labels, verbatim, ADR-005: Status semantics — trivial bodies and absent headings, A contract status with no eval representation is decorative, ADR-007: T4 segmentation — measured thresholds and era rulings (+4 more)

### Community 11 - "Measured Thresholds and Confidence"
Cohesion: 0.17
Nodes (12): confidence field (uncalibrated, pinned by cases), A validator that cries wolf is a defect, not noise (taxonomy F7), Ruling 4: the form cross-check compares families, not strings, No pre-data magic numbers — constants measured after the mechanism works, SIM_FLOOR = 0.37 title-similarity threshold, TOC-cluster filter (per-candidate recurrence, TOC_CLUSTER_MIN = 5), Confidence model (layer 9) — base by heading quality, WARN_PENALTY, Kept validators with measured thresholds (+4 more)

### Community 12 - "Eval-First Scaffold Decisions"
Cohesion: 0.17
Nodes (12): ADR-000: Eval-first scaffold instead of spec-driven development, The eval set is the spec, Hooks are law, CLAUDE.md is advice, ADR-001: Adapting the Task 2 planning prompt to scaffold conventions, Normative specs vs executable enforcement vs descriptive architecture, ADR-009: A milestone ledger, and why hard rule 3 had to bend, A gate nobody can observe is indistinguishable from a gate that passed, UNRUN status marker for judgment gates (+4 more)

### Community 13 - "Validator Battery Measurement"
Cohesion: 0.22
Nodes (11): Last-item tail bleed weakness, Layer 9 — Confidence scoring, Pre-B-freeze audit, Clean bills verified independently, Finding 1: confidence ordering is inverted where it varies, No pre-data magic numbers (all numerics PROVISIONAL), Measure first, then design, 005 — T5 validator battery record (+3 more)

### Community 14 - "Fixture Inventory and Provenance"
Cohesion: 0.29
Nodes (11): F5 — Format and parse hazards, Fixture inventory and provenance, Fixture heading-unnumbered (silent-failure shape), Fixture jpm-2024 (12.8 MB financial iXBRL), Fixture malformed-html (hand-degraded), Fixture msft-2013 (mid-era HTML, source wraps), Self-created fixture provenance discipline, Fixture toc-titled (self-created TOC trap) (+3 more)

### Community 15 - "Review Agent Roles"
Cohesion: 0.27
Nodes (10): cold-reviewer agent, Silent wrongness (vs. crashes), Confidence miscalibration hunt, extraction-auditor agent, Metric gaming check, Output audit mode, Decorative invariant, spec-drift agent (+2 more)

### Community 16 - "Failure Triage Process"
Cohesion: 0.20
Nodes (10): Standing disagreement is a spec-ambiguity, Watch it fail first, Five failure classes, Failure triage SOP, Minimal repro becomes the case, Triage smell checks, Per-feature loop, Contract-v2 output envelope (+2 more)

### Community 17 - "Span Invariants and IBR"
Cohesion: 0.29
Nodes (10): INV-S1: span-carrying item ranges non-overlapping and in document order, INV-S2: extracted item text is a verbatim slice of normalized_text, INV-S4: expected items are never silently absent, Item status enum (extracted / missing / incorporated_by_reference / omitted), Offsets are into normalized_text, never the raw file, omitted vs missing: both mean no heading, era rules decide which, ADR-011: IBR items carry offsets and are checked like any other span, The pointer text is the human-checkable evidence for an IBR claim (+2 more)

### Community 18 - "Normalization Rulings"
Cohesion: 0.22
Nodes (10): INV-S5: normalized_text is the readable filing, not machine metadata, ADR-003: Stdlib-only parsing and normalization at B-level, Normalization canon (entity decoding, whitespace collapse, NBSP), Dead-anchor bug class, Revisit clause: a tolerant parser only after a real red case defeats stdlib, ADR-006: Normalization rulings from the T3 spike, Ruling 1: ix:header / ix:hidden subtrees are skipped entirely, Ruling 2: a newline means opposite things in HTML vs txt eras (+2 more)

### Community 19 - "Inspector API and Frontend"
Cohesion: 0.22
Nodes (8): POST /api/extract/{fixture,upload,url}, GET /api/meta (git_sha + fixtures), boot(), call(), esc(), render(), VIEW / SEL shared view state, S2 — Set GIT_SHA on Zeabur

### Community 20 - "Case Authoring and Held-out"
Cohesion: 0.32
Nodes (8): Dual-pass anchor verification, Held-out leakage check, Methodology audit mode, Boundary anchors, Case authoring SOP, Deep-tier golden case, Held-out case and burn semantics, TOC trap

### Community 21 - "Layer 8 Validator Battery"
Cohesion: 0.25
Nodes (8): Boundary hygiene validator, doc_status derivation rule order, Dual-method boundary agreement (deferred), Keyword fingerprint validator, Layer 8 — Label-free validator battery, TOC manifest cross-check validator, Finding 1b: warning volume cannot escalate doc_status, TOC manifest cross-check could not fire

### Community 22 - "Dual-Pass Anchor Audit"
Cohesion: 0.32
Nodes (8): Layer 4 — Candidate detection, Layer 3 — Normalization, T2 dual-pass audit, Finding: five dead ASCII anchors, ADR-003 normalization canon (entities → Unicode), F2 — Heading variance, A newline means opposite things in the two eras, Whitespace-flattened body for status phrase matching

### Community 23 - "Metrics Computation"
Cohesion: 0.50
Nodes (7): compute(), load_cases(), main(), _rate(), Metrics over a committed eval report — the numbers the analysis report quotes., render(), _self_check()

### Community 24 - "Output Contract v2"
Cohesion: 0.25
Nodes (8): 001 — sec10k output contract (v2), doc_status derivation order, Refusal semantics: unsupported/failed never emit a best-effort parse, ADR-002: Output contract v2 — document envelope + item evidence, Escalation policy — AMBIGUOUS_CODES, Ruling 4: collapse is diagnosed before form identity, Each CI job deliberately broken and its exit code observed, Ruling 2: MISSING_MAX = 0.25 → expected_items_mostly_missing

### Community 25 - "Frontend and Milestone Gates"
Cohesion: 0.25
Nodes (8): method enum (heading_strict / heading_lenient / status_keyword / llm_fallback), Same-line heading rule (title on the heading's own line), ADR-013: Next-line heading titles; missing items escalate by proportion, sec10k inspector frontend (index.html), G2 — CI + armed baseline + branch protection, G3 — Held-out authoring (frozen, never run), H1 — Held-out run #1 (1/5), T7 — Frontend inspector (deployed to Zeabur)

### Community 26 - "CI Eval Gate Jobs"
Cohesion: 0.29
Nodes (7): Shallow-tier case, invariant suite, eval-gate CI workflow, invariant-eval job, unit-tests job, Hooks as the only blocking layer, Stdlib-only parsing (ADR-003)

### Community 27 - "Project Working Rules"
Cohesion: 0.40
Nodes (6): AGENTS.md working rules, Adding a task recipe, The eval set IS the spec, Project working rules (CLAUDE.md), scaffold eval-first scaffold, sec-10k-extract

### Community 28 - "Silent-Success Failure Class"
Cohesion: 0.33
Nodes (6): INV-0: pipeline never reports success with empty output, ADR-010: Four corrections the G1 audits forced, The silent-success failure class (wrong output reported as success), T11 — A3 silent-failure rate, T12 — A4 fallback stage (conditional, gated on T11 data), T13 — A5 perf/cost/scalability numbers

### Community 29 - "Taxonomy Era Model"
Cohesion: 0.47
Nodes (6): INV-S3: only canonical item codes valid for the filing's taxonomy era, Era model — expected item sets keyed on period-of-report date, The era table is a single point of silent failure (enumerated debt), Ruling 2: Item 9C boundary at date(2021, 10, 1), Item 4 "Reserved" era window (2010-02-28 → 2011-12-15), T14 — A6 taxonomy completeness + 10-K/A stretch

### Community 30 - "A-Track Milestones T9-T14"
Cohesion: 0.33
Nodes (6): ADR-014: T9 tranche-1 rulings — Item 4 Reserved window, ordinal rejoin, Instrument-vs-pipeline discipline, G1 — Gate catch-up (cold-reviewer + spec-drift), H2 — Held-out run #2 (5/5), T10 — A2 confidence calibration, T9 — A1 eval expansion r2

### Community 31 - "Ground Truth Without Data"
Cohesion: 0.40
Nodes (5): Boundary anchors with recorded occurrence counts, Ground truth without public data, Residual gap: anchors test containment, not boundaries, Fixture aapl-2025 (iXBRL deep tier), Eval anchors reused as the normalizer canary

## Ambiguous Edges - Review These
- `eval-adversary agent` → `10-K filing anatomy (sec10k-domain)`  [AMBIGUOUS]
  .claude/agents/eval-adversary.md · relation: conceptually_related_to

## Knowledge Gaps
- **30 isolated node(s):** `post-edit-invariant.sh script`, `sec10k-extract`, `Enforced per-run budget`, `--cluster-only rerun`, `Neo4j / FalkorDB Cypher export` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `eval-adversary agent` and `10-K filing anatomy (sec10k-domain)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `extract_items()` connect `Extraction and Segmentation Core` to `Eval Runner and Inspector Service`, `Eval Adapter Check Vocabulary`, `Normalization Layer`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `eval_check()` connect `Eval Adapter Check Vocabulary` to `Extraction and Segmentation Core`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `ADR-010: Four corrections the G1 audits forced` connect `Silent-Success Failure Class` to `Invariants and Status ADRs`, `Measured Thresholds and Confidence`, `Eval-First Scaffold Decisions`, `Span Invariants and IBR`, `A-Track Milestones T9-T14`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **What connects `post-edit-invariant.sh script`, `Metrics over a committed eval report — the numbers the analysis report quotes.`, `sec10k-extract` to the rest of the system?**
  _87 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Audit Findings and Methodology` be split into smaller, more focused modules?**
  _Cohesion score 0.07686274509803921 - nodes in this community are weakly interconnected._
- **Should `Extraction and Segmentation Core` be split into smaller, more focused modules?**
  _Cohesion score 0.0931174089068826 - nodes in this community are weakly interconnected._