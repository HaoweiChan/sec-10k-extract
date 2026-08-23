# ADR-028 — S2: build identity is injected at build time, and never lies

Date: 2026-08-22. Status: accepted. Implements S2.

Renumbered 027 -> 028 on 2026-08-22 when `origin/main` merged first with its own
ADR-027 (ambiguity caps confidence, PR #32 / T5). All four PR #31 review
artifacts — `tasks/reviews/pr31-r1.json`, `pr31-r2.json`,
`pr31-r1-resolution.json` (which also cites `ADR-027-build-identity.md §e` and
`prompts/013-s2-build-identity.md`, the prompt record renumbered to `014` in the
same merge) and `pr31-r2-resolution.json` (R12 "Matches ADR-027 §g") — still
cite this file as ADR-027 because that is what it was called when those rounds
reviewed it; they are the record of a review, not of the tree, and are left as
written per this repo's supersede-don't-retro-edit convention. A bare `ADR-027`
in any of them means THIS file (list completed 2026-08-23, L1, PR #31 R15).

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
"build_command": "printf %s \"${ZEABUR_GIT_COMMIT_SHA:-}\" > BUILD_SHA || true"
```

`printf %s`, not `echo`: `echo` appends a newline that only happens to be
harmless here, and `printf` with no format string cannot be handed a value
starting with `-`. `start_command` is deliberately untouched — the committed
one already serves a live deployment, and changing it risks that for no gain
in this task.

**The command must not be able to fail the build**, which the first version
could (PR #31 R5). Measured: `sh -uc 'printf %s "$ZEABUR_GIT_COMMIT_SHA" >
BUILD_SHA'` exits **127** and writes nothing — a builder that runs the step
under `set -u` — and in a non-writable working directory the same command
exits **1**. A container builder runs such a step as a layer whose non-zero
exit aborts the image build, and a deploy that does not exist is not "worse
than `build unknown`" on any axis this ADR reasons about; it is a different
and larger failure. `${VAR:-}` covers the first, `|| true` the second, and
both were re-measured at exit 0 with an empty `BUILD_SHA` — which the resolver
then rejects, landing on `unknown`. The failure stays inside the status line,
where this ADR can reason about it.

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
git runs with `GIT_DIR` set — reported **18** failures on an implementation
that was green everywhere else (16 temp-directory assertions plus the two
blank-`GIT_SHA` ones; `evals/report/20260822-161040-fast.json`, score 80/81),
because the resolver returned the repo's HEAD while pointed at a temp
directory that is not a repository at all.

The same leak reaches production: a `GIT_DIR` inherited by the container makes
`/api/meta` report a sha from whatever repository that variable names.

The first fix was half of one, and PR #31 R2 caught it: passing `environ`
through to the subprocess closes the leak only for callers that pass an
explicit `environ`, and `/api/meta` passes none — it calls `git_sha(ROOT)`,
falls back to `os.environ`, and inherited exactly what the deleted
`app.py::_git_sha` had. The deployed path was byte-for-byte as leaky as the
code it replaced, and no case could go red on it. So the strip happens inside
the resolver, on every path including the default one, and `build-identity`
asserts it with `GIT_DIR` set both in a handed-in environ and in the ambient
one — the second being `/api/meta`'s exact call shape.

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
here. Those three all fail **closed**: `BUILD_SHA` is absent or empty, the
resolver rejects it, and `/api/meta` reports `unknown` exactly as it does
today.

Two more failure modes do not fail closed, and the earlier version of this
section generalised over them (PR #31 R5, R9):

1. **The build step aborts the build.** Addressed in §b rather than tolerated —
   the command is now unable to exit non-zero.
2. **The builder caches the `build_command` layer across commits.** Then
   `BUILD_SHA` holds a valid 7–40 hex sha *from the previous build*, `SHA_RE`
   accepts it because it is a real sha, and `/api/meta` serves a stale label
   indistinguishable from a current one. That is the "real but frozen" outcome
   the S2 row calls worse than `build unknown`, and **no validation can detect
   it** — a sha cannot be interrogated about which build wrote it. It is not
   reproducible offline and is not claimed either way here.

Which is exactly why the S2 gate is worded as it is — "`/api/meta` reports a
real sha **that tracks redeploys**". A sha that merely *exists* would pass a
weaker reading of that gate while frozen by a cached layer. The check is
`curl -s .../api/meta` after the merge **and again after a second redeploy**,
with the requirement that the value **MOVE**; it stays `UNRUN` in the ledger
until both observations exist.
