# 013 — S2: build identity, and the row that refuses its own title (2026-08-22)

The deployed inspector's status line read `build unknown`
(`curl -s https://whaleforce-sec10k.zeabur.app/api/meta` →
`{"git_sha":"unknown", …}`), so nobody opening the one instance strangers
actually use could tell which build they were looking at. Ruling:
[ADR-027](../specs/decisions/ADR-027-build-identity.md).

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
  ADR-027 §d rather than left in the code.

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
- **Eval said:** the pre-commit gate blocked the commit — `build-identity`, 16
  failures, on code that was green in every run before it. `git rev-parse`
  honours `GIT_DIR` from the environment, git *sets* `GIT_DIR` while running a
  hook, and the resolver had been handed an `environ` it only used to look up
  `GIT_SHA` — so the git subprocess still inherited the ambient one and answered
  with the repo's HEAD from a temp directory that is not a repository. Every
  `NOT_A_SHA` value "resolved" to `17d43fc`.
- **Corrected:** the resolver, not the test. An inherited `GIT_DIR` in the
  container would equally make `/api/meta` report a stranger repo's sha, so
  `git_sha(root, environ)` now resolves entirely within `environ`, git call
  included (ADR-027 §e). The case's temp-dir assertions run with `PATH` and
  nothing else; only the local-dev assertion, the one that is *supposed* to find
  a repository, uses the real environment. The gate caught this on the very
  commit that introduced it, which is the whole argument for the hook.

- **Assumed:** `tasks/TODO.md`'s `SOURCE_CACHE` debt row, that its `ponytail:`
  marker is "the only one in the repo".
- **Eval said:** `grep -rn "ponytail:" src/` — four, in `boilerplate.py:56`,
  `web/app.py:47`, `repo_hygiene/eval_adapter.py:698` and a docstring-form one
  in `repo_hygiene/css_contrast.py:9`.
- **Corrected:** the parenthetical, plus three line references in the same row
  that this task's own edit to `app.py` had just moved.

- **Assumed:** `boilerplate.py`'s deleted max-line-length gate is justified by a
  corpus claim ("no line over 35 chars passes the other three gates anywhere in
  the corpus") that nothing re-opens when the corpus changes — the rot risk a
  debt audit flagged.
- **Eval said:** re-measured over all 39 fixtures, the ceiling is still exactly
  35 — `jpm-2024`'s `'JPMorgan Chase & Co./2024 Form 10-K'`, with every other
  fixture topping out at 17 (`'Table of Contents'`). The premise holds.
- **Corrected:** the reasoning stays; a trigger clause was added naming what
  re-opens it — a fixture whose detected chrome runs longer than 35 chars *and*
  whose long run is a false positive, since a long TRUE chrome line is the case
  the original comment already decided.
