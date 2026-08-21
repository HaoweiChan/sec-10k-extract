# ADR-025 — A history line every run, a full report only when it earns its keep, and the uncited-dump prune

Date: 2026-08-21. Status: accepted.

**Ruling**: `evals/run.py` appends one `evals/report/history.jsonl` line on every run; a full per-case `evals/report/<ts>-<suite>.json` is written only for `--report`, `--suite all`, a `--dir` held-out run, or a red run; 165 uncited routine-gate dumps are pruned, lossless because every one was backfilled into `history.jsonl` first.
**Because**: 188 report files / 18 MB on `main`, only 19 ever cited as a report of record anywhere outside `evals/report/`; every PR diff since T1 carries the other 169 as pure weight, and their only residual value — the score/pass time series — needs one line, not a full case dump.
**Enforced by**: `evals/run.py` (write policy), `src/repo_hygiene/eval_adapter.py::check_report_citations` (`report-citations-resolve`, invariant)

---

## Context

`evals/report/` is committed by design (README.md, `docs/evals/evaluation-strategy.md`
§"Audit trail") — the raw record backing every number in `docs/analysis-report.md`
and the ADRs that cite a specific run. That design was never wrong; what grew
wrong was the write policy underneath it. `evals/run.py` wrote a full
`{"suite", "score", "git_sha", "results": [...], "debt": [...]}` dump on
**every** invocation by default (`--no-report` was opt-out, not opt-in), and
the repo's own gates (`.githooks/pre-commit`, `.github/workflows/ci.yml`'s
`invariant-eval`/`fast-eval`) already worked around this by passing
`--no-report` on every routine run — the flag existed specifically because
the default was wrong for the common case. What never had a workaround was
everything upstream of the gates: T1–T14's iteration, PR review rounds,
manual `--suite all` sweeps — each one a full dump, most never opted out.

Counted directly: 188 files, 18.0 MB, on `main` at `f525dee`. Grepped for
citations outside `evals/report/` itself (`docs/`, `specs/`, `tasks/`,
`README.md`, `src/`, case files under `evals/golden|adversarial|heldout`,
`prompts/`, `.github/`): **19** are ever named — as a run of record in an ADR,
an audited "watched red first" report, or the input a metric quotes. The
other 169 are routine gate exhaust: green `fast`/`invariant` runs, superseded
`all` sweeps mid-round. Every PR that touches `evals/report/` carries whatever
of those 169 the round produced, and none of that diff is ever read again.

## Decision

### 1. `evals/run.py` write policy

- **Every run appends one line to `evals/report/history.jsonl`**, shared
  schema: `ts, suite, sha, dirty, passed, total, score, wall_s, cost_usd,
  report`. Extra keys (`debt_count`; `dir` on `--dir` runs) follow, shared
  keys never renamed. `cost_usd` is a flat `0.0` — metric 10 / ADR-020
  already established this pipeline has no paid dependency, so it is a
  reported fact, not a per-run measurement gap.
- **A full report is written only when it earns its keep**: `--report`
  (new flag, explicit ask), `--suite all` (already the full-sweep suite),
  a `--dir` held-out run (unchanged from before — never traceless, per
  `docs/evals/evaluation-strategy.md`), `--update-baseline` (a baseline
  move is a decision, ADR-012, worth its own evidence), or the run is
  **red** — any scored case failed, or the score fell below the recorded
  baseline. `[DEBT]` cases stay unscored and never make a run red on their
  own, matching `evals/run.py`'s existing debt semantics.
- **`--no-report` is now the narrow case, not the default**: it suppresses
  the full report even on red, for the one caller that genuinely cannot
  afford a report file on every invocation — `.claude/hooks/post-edit-invariant.sh`,
  which runs the invariant suite after every `src/` edit during a session.
  It never suppresses the history line, and it is still ignored on `--dir`
  runs (unchanged).
- **`.githooks/pre-commit`** drops `--no-report`: a routine green commit
  gets its history line only; a blocked (red) commit gets a full report to
  debug from, for free.
- **CI**: `invariant-eval` drops `--no-report` for the same reason.
  `fast-eval` — the same command the pre-commit hook runs, on `main` at
  head — is designated the **report-of-record run** and now passes
  `--report` explicitly, so a full report keeps landing on every green
  push to `main` even though the new default wouldn't write one. This is
  the direct answer to "does anything rely on a report existing after a
  green run": nothing in the repo *reads* CI's own copy (CI is an
  ephemeral checkout with no push step — its report never reaches `main`
  either way), but the convention that "a report exists for the commit at
  head" is a human one (whoever moves a milestone forward runs
  `--suite all` or `--report` and commits its output alongside the
  code, same as before this ADR), and `--report` on `fast-eval` keeps the
  automated half of that convention exercised and true.

### 2. The `-dirty` / `dirty` disagreement, closed at the source

`git_sha()`'s dirty check (`git status --porcelain -uno`) already special-cased
one problem: every run drops an *untracked* file into `evals/report/`, so
without `-uno` the second run in a session always saw its own prior output and
stamped `-dirty` on identical code. `history.jsonl` reopens exactly that hole
one file later: once it's committed, it is a **tracked** file this same run is
about to append a line to, and `-uno` does not exempt modified tracked files.
Left alone, every run after the first commit of `history.jsonl` would report
`-dirty` on an otherwise-clean tree, and the report's `git_sha` field and the
history line's `sha`/`dirty` fields would silently disagree about whether the
run was clean the moment `history.jsonl` had one entry.

Fixed in the one place dirty is decided — `git_sha()`'s status call gets a
negative pathspec, `-- . ':!evals/report/history.jsonl'` — and the history
line's `sha`/`dirty` are derived by splitting `git_sha()`'s own return value
(`sha, dirty = (s[:-6], True) if s.endswith("-dirty") else (s, False)`), not
computed separately. One dirty check, two callers reading the same string:
they cannot drift apart again by construction.

**Verified** (working tree fully committed, two runs back to back):

```
$ python3 -m evals.run --suite invariant
...
$ tail -2 evals/report/history.jsonl
{"ts": "...", "suite": "invariant", "sha": "<7-hex>", "dirty": false, ...}
{"ts": "...", "suite": "invariant", "sha": "<7-hex>", "dirty": false, ...}
```

Both runs report `dirty: false` and a bare 7-hex `sha`, no `-dirty` suffix —
the second run does not see the first run's own `history.jsonl` append as
tree dirt. (Exact output captured in the PR body, since it depends on the
commit this ADR lands in.)

### 3. The prune

**CITED** = every `evals/report/<ts>-(fast|invariant|all|bench|oracle).json`
named outside `evals/report/`, git-grepped across `docs/`, `specs/`, `tasks/`,
`README.md`, `src/`, `evals/golden`, `evals/adversarial`, `evals/heldout`,
`prompts/`, `.github/`: **19 files**. (`graphify-out/manifest.json` also
mentions 28 more of these paths, but as a generated file-hash index over the
whole tree — every committed file gets an entry there, cited or not — not as
a report-of-record citation; it was excluded from CITED. It is regenerated by
`/graphify` and unaffected by the prune either way.)

**Non-prunable regardless of citation** (per this ADR's own scope, and none
of it uncited-but-borderline in practice): `*-bench.json` (6, `evals/bench.py`,
governed by ADR-021), `*-oracle.json` (1, `evals/oracle.py`, ADR-019/ADR-021
precedent), `pr-loop-ledger.jsonl` (the pr-loop round ledger, not a suite
report at all), anything under `evals/heldout/` (none of *those* live in
`evals/report/`, but the rule is stated for clarity — held-out fixtures/cases
are governed by their own burn-rule ADRs, not this one).

**Prune candidates** = UNCITED `*-fast.json` / `*-invariant.json` /
`*-all.json` only: **165 files**.

- CITED: 19
- UNCITED (all types): 168 (165 candidates + 3 uncited-but-non-prunable bench
  runs, kept anyway)
- Candidates (uncited, prunable type): 165

**Backfill before delete**: every one of the 180 `*-fast.json` /
`*-invariant.json` / `*-all.json` reports on `main` — cited and uncited alike
— was read and turned into one `history.jsonl` line, sorted by the run's own
timestamp, before any file was removed. `bench`/`oracle` reports were not
backfilled into `history.jsonl`: they are a different instrument's output
(`evals/bench.py`/`evals/oracle.py`), share none of `evals/run.py`'s
`suite`/`score`/`passed` schema, and fabricating those fields to fit the
row shape would violate hard rule 4 (no mocked results) for zero benefit —
they are never pruned, so nothing about them needs recovering from a line.
Pre-ADR-025 history rows carry `"wall_s": null` (not recorded at the time)
and `"report": null` for pruned ones — `.report` names the file only where it
still exists on disk, matching this run's schema exactly. The prune is
therefore lossless for the pass/fail/score time series, and traceable to the
exact input it summarizes: `report` in each row is either a real, present
filename or an honest `null`.

**Deleted**: `git rm` on the 165 candidates, listed in the PR diff. **Pre-prune
commit**: `f525dee7cff049a0d860350353f2fb3e603aa21f` (`main` at the point this
branch forked) — every deleted file is byte-identical there, so
`git show f525dee7cff049a0d860350353f2fb3e603aa21f:evals/report/<name>`
recovers any of them.

**Sizes**: `evals/report/` — 189 tracked files / 18.0 MB before → 25 tracked
files (22 kept reports + `history.jsonl` + `pr-loop-ledger.jsonl` +
`.gitkeep`) / 1.7 MB after.

### 4. `report-citations-resolve`, watched red first

`src/repo_hygiene/eval_adapter.py` (already backing `adr-header-and-index`,
same file, same no-input-needed pattern) gained `check_report_citations()`:
scans the same CITE_SCAN locations this ADR's own CITED count used, and fails
if any `evals/report/<ts>-*.json` cited there is missing on disk. Wired to a
new case, `evals/golden/report-citations-resolve.json`
(`"input": {"checks": ["report_citations"]}`), invariant + fast — a future
prune (or an ADR edited to cite a report that got deleted) breaks the build
instead of rotting into a dead link. `adr-header-and-index.json` was updated
to declare its checks explicitly (`["adr_headers", "adr_index"]`) now that
the adapter dispatches by name instead of always running everything.

Watched red: temporarily renamed `evals/report/20260819-014559-oracle.json`
(cited by ADR-019) out of the way and ran `--suite invariant` —
`[FAIL] report-citations-resolve`, `13/14 = 0.929`, `INVARIANT VIOLATION`.
Restored the file, reran: `14/14 = 1.000`.

## Alternatives rejected

- **Keep writing a full report every run, gzip old ones.** Doesn't touch the
  actual problem — every PR diff still carries a compressed dump nobody
  reads, and the eval-first repo's own hard rule against traceless runs
  argues for *fewer, meaningful* records, not smaller meaningless ones.
- **Delete uncited reports outright, no backfill.** Loses the time series
  ADR-021's cost/perf framing and any future "how has `fast` trended"
  question would need — the actual ask (GW-008) is explicit that this must
  stay lossless.
- **Time-box retention (keep last N days) instead of a citation gate.**
  Would have pruned reports still cited by ADR-018/019/020/021 (all from
  2026-08-16 through 2026-08-20, well inside any reasonable window) purely
  by age, breaking exactly the links this ADR's own invariant now protects.
  Citation is the correct predicate; age is not.

## Consequences

- Routine `fast`/`invariant` runs — pre-commit, CI, the PostToolUse hook —
  now cost one JSON line, not a multi-KB dump. `evals/report/` stops growing
  by default; it grows again only on `--suite all`, a held-out run, a
  baseline move, or an actual red run — the cases worth keeping.
- `evals/metrics.py`'s own report picker
  (`sorted((ROOT/"evals"/"report").glob("*-all.json"))[-1]`) is unaffected:
  `--suite all` still always writes a full report, so "the newest `all`
  report" keeps meaning what it always meant.
- `evals/bench.py`'s `from evals.run import git_sha` import is untouched —
  `git_sha()` keeps its existing signature and `-dirty`-suffixed string
  return; only its internal status call gained the `history.jsonl` exclusion,
  invisible to every existing caller.
- A future citation of a report that gets pruned or renamed is now a build
  failure (`report-citations-resolve`), not a silent dead link discovered
  by a reader months later.
