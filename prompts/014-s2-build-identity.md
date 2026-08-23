# 013 — S2: build identity, and the row that refuses its own title (2026-08-22)

The deployed inspector's status line read `build unknown`
(`curl -s https://whaleforce-sec10k.zeabur.app/api/meta` →
`{"git_sha":"unknown", …}`), so nobody opening the one instance strangers
actually use could tell which build they were looking at. Ruling:
[ADR-028](../specs/decisions/ADR-028-build-identity.md).

## The prompt decisions that mattered

- **The ledger row is titled "Set `GIT_SHA` on Zeabur" and then forbids doing
  that.** Its own Contents cell says *"prefer build-time injection over a manual
  env var — a hand-set sha goes stale on every redeploy, and a lying build label
  is worse than `build unknown`."* Following the title would have taken ten
  seconds in a dashboard and produced a label that describes a build which no
  longer exists — strictly worse than `unknown`, which at least tells a reviewer
  to go look elsewhere. The row was written by someone who had already thought
  past their own title, and the useful discipline is reading the whole cell
  before acting on the heading.

- **"A lying label is worse than none" is a *ruling*, and rulings decide
  precedence.** The one genuinely debatable design choice — does the
  build-injected file outrank the documented `GIT_SHA` override, or the other
  way round? — is settled by that sentence and not by taste. A human-set value
  cannot know it has gone stale; a build-written one is current by
  construction. So the file wins, and `GIT_SHA` is not dropped: it still answers
  on every host where no build wrote a file.

- **The 2026-08-17 console check was right and its conclusion was wrong.**
  "No auto-injected sha to borrow" was measured against the *runtime*
  environment. `ZEABUR_GIT_COMMIT_SHA` exists, but the docs are explicit that
  these variables *"only appear during the build phase"*. The whole task turned
  on noticing that a true observation had been generalised one phase too far —
  the value has to be carried into the image, not read at request time.

- **"What does the build hand us when nothing goes wrong for a human?"** The
  spec's honesty requirement was not about operator error. `printf %s "$FOO" >
  BUILD_SHA` with `FOO` unset writes an *empty file*, not no file, and a builder
  that never expands the variable writes the literal `$ZEABUR_GIT_COMMIT_SHA`.
  Both produce a lying status line with nobody making a mistake anywhere, which
  is what made validation part of the ruling rather than an implementation
  detail.

## Assumption → Eval contradiction → Correction

- **Assumed:** reading `BUILD_SHA` back at runtime is the whole fix — the build
  writes a sha, the app reports it.
- **Eval said:** `build-identity`, run against exactly that naive file-first
  resolver, 12 failures. Ten values a build can produce with no human error
  became build labels, truncated to twelve characters and served as identity:
  `'$ZEABUR_GIT'`, `'${ZEABUR_GIT'`, `'a1b2c3d4-dir'`, `'HEAD'`, `'main'`,
  `'latest'`, `'zzzzzzz'`, a 41-hex near-miss, and a value with a space in it.
- **Corrected:** `SHA_RE = [0-9a-f]{7,40}` applied to what the build actually
  wrote, not to what it was supposed to write, and the ruling written into
  ADR-028 §d rather than left in the code.

- **Assumed:** the check belongs in `src/repo_hygiene/eval_adapter.py` as a text
  pin over `app.py`, the shape S3 and S8 established, because ADR-003's CI jobs
  install nothing and `import fastapi` fails there outright.
- **Eval said:** the re-falsification run. Of six mutations that break build
  identity, a text pin over `app.py` can see exactly one (M6, the private
  resolver). Relaxing `SHA_RE` (M3, 10 failures), flipping the precedence (M4),
  and making `build_sha` ignore the file (M5, 6 failures) are all invisible to
  any check that only reads source as strings — the same lesson PR #27 R5/R6
  paid for once already.
- **Corrected:** the resolver moved out of `app.py` into
  `src/sec10k/web/build_id.py`, stdlib-only and fastapi-free, the convention
  `view.py` and `capabilities.py` already follow for this reason. The case now
  *executes* it. Only what genuinely cannot be executed — the Zeabur build —
  stays a text pin.

- **Assumed:** with the resolver green under `--suite invariant` and `--suite
  fast`, and six mutations re-falsifying it, the implementation was done.
- **Eval said:** the pre-commit gate blocked the commit — `build-identity`, 18
  failures (16 temp-directory assertions plus the two blank-`GIT_SHA` ones;
  `evals/report/20260822-161040-fast.json`, score 80/81), on code that was green
  in every run before it. `git rev-parse`
  honours `GIT_DIR` from the environment, git *sets* `GIT_DIR` while running a
  hook, and the resolver had been handed an `environ` it only used to look up
  `GIT_SHA` — so the git subprocess still inherited the ambient one and answered
  with the repo's HEAD from a temp directory that is not a repository. Every
  `NOT_A_SHA` value "resolved" to `17d43fc`.
- **Corrected:** the resolver, not the test — but only halfway, and the review
  caught the other half (PR #31 R2). Threading `environ` into the subprocess
  closes the leak for callers that pass one; `/api/meta` passes none, so the
  deployed path still inherited `GIT_DIR` byte-for-byte as the deleted
  `_git_sha` had, and no case could go red on it. **A fix verified only on the
  path the test drives is not a fix**, and the write-up saying otherwise was the
  more expensive error: it would have closed the finding. The resolver now
  strips `GIT_DIR`/`GIT_WORK_TREE`/`GIT_COMMON_DIR` inside `_rev_parse`, on
  every path including the default, and `build-identity` asserts it with
  `GIT_DIR` set in both a handed-in environ and the ambient one (ADR-028 §e).

- **Assumed:** validation belongs on the injected file, because that is where a
  build writes text nobody typed. `GIT_SHA` is a human override — if an operator
  sets it, they meant it.
- **Eval said:** PR #31 R1. `GIT_SHA=latest` → `latest`; `main` → `main`;
  `a1b2c3d4-dirty` → `a1b2c3d4-dir`; `$ZEABUR_GIT_COMMIT_SHA` → `$ZEABUR_GIT_`.
  The same ten strings the case already rejected from the file sailed through the
  override, and the case *pinned that passthrough as correct*. Worse, the ADR's
  own ruling sentence already said validation applies "at any of those steps" —
  the code contradicted the decision it shipped with.
- **Corrected:** one `_sha()` gate, applied at every source. The ruling is about
  the **value**, not its provenance: where a lie enters from does not make it
  true. And the override is not the exotic path — the ledger row is titled "Set
  `GIT_SHA` on Zeabur", so it is precisely where an operator types `latest`.

- **Assumed:** the worst case if a build-time assumption is wrong is `unknown`,
  so §g could enumerate three assumptions and generalise.
- **Eval said:** PR #31 R5 and R9, neither reproducible against Zeabur, both
  demonstrable in what they claim. `sh -uc 'printf %s "$ZEABUR_GIT_COMMIT_SHA" >
  BUILD_SHA'` exits **127** writing nothing, and **1** in a non-writable
  directory — as a build layer that aborts the image build, which is not a
  worse status line but a missing deploy. And a cached build layer freezes
  `BUILD_SHA` at a *valid* previous sha, which `SHA_RE` accepts and no
  validation can ever detect.
- **Corrected:** the first is engineered out (`${VAR:-}` + `|| true`, re-measured
  at exit 0); the second is named in §g as a failure mode that does **not** fail
  closed, because it cannot be engineered out from this side. That is what makes
  the gate's wording load-bearing rather than decorative: the sha must **MOVE**
  across two redeploys, not merely exist. A generalisation ("the failure mode is
  the honest one") is a claim about a set — it takes one member to be false.

- **Assumed:** `tasks/TODO.md`'s `SOURCE_CACHE` debt row, that its `ponytail:`
  marker is "the only one in the repo".
- **Eval said:** `grep -rn "ponytail:" src/` — four, in `boilerplate.py:56`,
  `web/app.py:47`, `repo_hygiene/eval_adapter.py:699` and a docstring-form one
  in `repo_hygiene/css_contrast.py:9`.
- **Corrected:** the parenthetical, plus three line references in the same row
  that this task's own edit to `app.py` had just moved.

- **Assumed:** `boilerplate.py`'s deleted max-line-length gate is justified by a
  corpus claim ("no line over 35 chars passes the other three gates anywhere in
  the corpus") that nothing re-opens when the corpus changes — the rot risk a
  debt audit flagged.
- **Eval said:** re-measured over the 38 measurable fixtures (39 directories,
  one of which — `repo_hygiene` — is not a filing), the ceiling is still exactly
  35 — `jpm-2024`'s `'JPMorgan Chase & Co./2024 Form 10-K'`, with every other
  fixture topping out at 17 (`'Table of Contents'`). The premise holds.
  *(Dated: "38 measurable (39 directories)" was the S2 working tree; the
  merged tree already had 41 directories / 40 filings (PR #31 R14). Re-measured
  2026-08-23, D2, over every fixture `evals.oracle.iter_fixtures` yields: 41,
  ceiling still 35 on `jpm-2024`, next 17. The `boilerplate.py` comment now
  carries the walk instead of a count; this record keeps its own.)*
- **Corrected:** the reasoning stays; a trigger clause was added naming what
  re-opens it — a line passing the three repeat gates at more than 35 chars
  *and* turning out to be a false positive, since a long TRUE chrome line is the
  case the original comment already decided.
- **And corrected again, by review (PR #31 R6):** the first wording said
  "detected chrome", which is a *wider* population than the one measured.
  `edgar_chrome` is matched by SGML shape rather than repetition and reaches 127
  chars on `ge-1994` and `ibr-pointer-first` — so the trigger's own condition was
  already satisfied by six committed fixtures and could never fire as news. A
  trigger is only worth writing if the corpus does not already trip it; the
  measurement and the clause now name the same population.
