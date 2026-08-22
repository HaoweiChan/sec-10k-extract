# ADR-027 — S2: build identity is injected at build time, and never lies

Date: 2026-08-22. Status: accepted. Implements S2.

**Ruling**: `/api/meta`'s `git_sha` resolves in one fixed order — the build-injected `BUILD_SHA` file, then the `GIT_SHA` env var, then `git rev-parse --short HEAD`, then the literal `"unknown"` — and a value that is not `[0-9a-f]{7,40}` is not a build identity at any of those steps. `BUILD_SHA` is written by `zbpack.json`'s `build_command` from Zeabur's build-phase `ZEABUR_GIT_COMMIT_SHA` and is never committed.
**Because**: the S2 row's own ruling is that "a lying build label is worse than `build unknown`", so every way a build can hand the runtime a non-sha — an empty file, an unexpanded `$ZEABUR_GIT_COMMIT_SHA`, a branch name — has to resolve to `unknown` rather than be rendered as a build identity; and only the build knows its sha is current, so nothing a human set can outrank it.
**Enforced by**: `evals/adversarial/build-identity.json` (`invariant` + `fast`), which calls `src/sec10k/web/build_id.py` for real and pins the `build_command`, the `.gitignore` line and `/api/meta`'s call site.

---

## a. The defect, and why the row's obvious fix was refused

`https://whaleforce-sec10k.zeabur.app/api/meta` returned `{"git_sha":"unknown", …}`
— a reviewer opening the one instance strangers actually use could not tell
which build they were looking at (C6).

The row is named "Set `GIT_SHA` on Zeabur", and that is exactly the fix it goes
on to refuse:

> Prefer build-time injection over a manual env var — a hand-set sha goes stale
> on every redeploy, and a lying build label is worse than `build unknown`.

A dashboard variable is set once and then silently describes a build that no
longer exists. That is strictly worse than `unknown`: `unknown` tells a
reviewer to go look elsewhere, while a stale sha tells them to stop looking.
So the env var is kept as an override for hosts that have neither a build hook
nor a `.git` (it is documented, and dropping it silently would be its own
defect), but it is not the mechanism.

## b. Where the sha comes from

Zeabur exposes `ZEABUR_GIT_COMMIT_SHA`, and the console check on 2026-08-17
that found "no auto-injected sha to borrow" was looking at the wrong phase —
the docs are explicit that *"these variables will only appear during the build
phase of the Git service"*. It is not readable at request time, which is why
the value has to be carried into the image rather than read from the
environment:

```json
"build_command": "printf %s \"$ZEABUR_GIT_COMMIT_SHA\" > BUILD_SHA"
```

`printf %s`, not `echo`: `echo` appends a newline that only happens to be
harmless here, and `printf` with no format string cannot be handed a value
starting with `-`. `start_command` is deliberately untouched — the committed
one already serves a live deployment, and changing it risks that for no gain
in this task.

The file is gitignored. A committed `BUILD_SHA` **is** the stale hand-set label
this ADR refuses, one directory over, so its absence has to resolve to the
honest fallback rather than to whatever was last checked in.

## c. The precedence order, and why it is that way

| | source | why it sits here |
|---|---|---|
| 1 | `BUILD_SHA` | written by the build that produced this image, so it is current by construction and no human has to remember it |
| 2 | `GIT_SHA` | the documented manual override, for a host with neither a build hook nor a `.git`. It loses to (1) because a human-set value cannot know it has gone stale, and the build-written one always does |
| 3 | `git rev-parse --short HEAD` | local development, where a working checkout is the most direct answer available |
| 4 | `"unknown"` | said out loud rather than guessed |

The file outranking the env var is the one debatable step, and it is the step
the row's ruling decides: an override that can go stale must not shadow a
source that cannot. `GIT_SHA` is not dropped — it still answers everywhere no
build wrote a file, which is every host except this one.

## d. Why validation is part of the ruling and not an implementation detail

`printf %s "$FOO" > BUILD_SHA` with `FOO` unset writes an **empty file**, not
no file. A resolver that reads the file back without asking what is in it
turns that into an empty build label, and turns a builder that never expanded
the variable into a status line reading `build $ZEABUR_GIT_COMMIT_SHA`. Both
are the lie the row forbids, arrived at with no human error anywhere.

So `SHA_RE = [0-9a-f]{7,40}` is the gate, and it is applied to what the build
wrote, not to what we hoped it wrote. Everything else — empty, whitespace, the
unexpanded literal in either spelling, `unknown`, `HEAD`, `main`, a `-dirty`
suffix, a 41-hex-digit near-miss — is `unknown`. Measured, in the naive
file-first implementation before the gate was added: ten of those values
became build labels, including `'$ZEABUR_GIT'` and `'a1b2c3d4-dir'`, truncated
to twelve characters and served as if they identified a build.

## e. The environment is part of the question, not context

`git rev-parse` honours `GIT_DIR` from the environment and will answer from a
repository that is not the directory it was pointed at. This was not
theoretical: `build-identity`'s first run inside the pre-commit hook — which
git runs with `GIT_DIR` set — reported 16 failures on an implementation that
was green everywhere else, because the resolver returned the repo's HEAD while
pointed at a temp directory that is not a repository at all.

The same leak reaches production: a `GIT_DIR` inherited by the container makes
`/api/meta` report a sha from whatever repository that variable names. So
`git_sha(root, environ)` resolves *entirely* within `environ`, the git call
included. The check that caught it is the eval gate itself, on the commit that
introduced it.

## f. Why the resolver moved out of `app.py`

It was `app.py::_git_sha`, and `app.py` imports fastapi, which ADR-003's
dependency-free CI jobs cannot import at all. A check confined to reading
`app.py` as text could only ever pin the resolver's *spelling*; this repo
already measured what that is worth (PR #27 R5/R6 — six severed wires that
answered every question about themselves correctly).

`src/sec10k/web/build_id.py` is stdlib-only and imports no fastapi, the same
convention `view.py` and `capabilities.py` already follow for the same reason,
so `evals/adversarial/build-identity.json` executes the real resolver against
every value a build can produce. What genuinely cannot be executed — a Zeabur
build — is pinned as text instead: the `build_command` whole (a check that
merely *asks* whether it mentions the variable is answerable by a command that
writes the wrong thing), the `.gitignore` line, `BUILD_SHA` not being tracked,
and `/api/meta` calling the shared resolver rather than growing a second copy.

## g. What this ADR does not establish

That Zeabur's builder sets `ZEABUR_GIT_COMMIT_SHA`, runs `build_command` in
the directory the runtime later serves from, and carries the written file into
the run image. No agent can run a Zeabur build, and none of that is claimed
here. The failure mode if any of it is false is the honest one and not a
regression: `BUILD_SHA` is absent or empty, the resolver rejects it, and
`/api/meta` reports `unknown` exactly as it does today. The S2 gate —
"`/api/meta` reports a real sha **that tracks redeploys**" — is confirmed by
curling `/api/meta` after the merge and again after a second redeploy, and
stays `UNRUN` in the ledger until then.
