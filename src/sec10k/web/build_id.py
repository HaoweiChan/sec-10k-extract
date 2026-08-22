"""Build identity for the inspector's status line (`/api/meta`). Ruling: ADR-027.

Pure stdlib, no fastapi import, so the repo_hygiene eval adapter can import
and exercise it for real — same convention as view.py and capabilities.py.
Checked by `evals/adversarial/build-identity.json`; there is deliberately no
`_demo()` here, because that case already calls every branch below and a
second copy of the same assertions is a second thing to drift.
"""
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# Written during the BUILD, read at runtime, never committed (.gitignore) —
# a checked-in sha is stale the moment it lands. zbpack.json's `build_command`
# is what writes it; Zeabur exposes ZEABUR_GIT_COMMIT_SHA in the build phase
# only, which is why the value has to be carried into the image as a file
# rather than read from the environment at request time.
BUILD_SHA_FILE = "BUILD_SHA"

# The only shape a build label may have. Everything a build can hand us that
# is NOT this — the empty file `printf %s "$FOO"` writes when FOO is unset, an
# unexpanded `$ZEABUR_GIT_COMMIT_SHA`, a branch name, a `-dirty` suffix — is a
# claim we cannot stand behind, and `unknown` is the honest answer. The S2
# ruling: a lying build label is worse than `build unknown`.
SHA_RE = re.compile(r"[0-9a-f]{7,40}")

# Location variables exist to point git at a repository OTHER than the one you
# are standing in — the opposite of the question this module asks. Scrubbed on
# every path, not just the ones a caller remembers to scrub: `/api/meta` calls
# `git_sha(ROOT)` with no environ at all (PR #31 R2), and an inherited GIT_DIR
# there would serve a stranger repository's sha as this build's identity.
GIT_LOCATION_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR")


def _sha(value):
    """`value` cut to 12 chars if it IS a build identity, else None.

    One rule, applied at every source. The ruling is about the VALUE, not
    about where it came from: `latest`, `main`, an unexpanded
    `$ZEABUR_GIT_COMMIT_SHA` and a `-dirty` suffix are equally not a build
    identity whether a build wrote them into the file or an operator typed
    them into the `GIT_SHA` box (PR #31 R1 — all four were served as labels).
    """
    value = (value or "").strip()
    return value[:12] if SHA_RE.fullmatch(value) else None


def build_sha(root=ROOT):
    """The sha this build injected, or None if it did not inject a real one."""
    try:
        return _sha((Path(root) / BUILD_SHA_FILE).read_text())
    except OSError:
        return None


def git_sha(root=ROOT, environ=None):
    """Build identity for the status line, most-trustworthy source first:

    1. `BUILD_SHA` — written by the build that produced this image, so it is
       current by construction and needs no human to remember it.
    2. `GIT_SHA` — the documented manual override, for a host with neither a
       build hook nor a .git. It outranks nothing above it: a human-set value
       cannot know it has gone stale, and the build-written one always does.
    3. `git rev-parse` — local development, where a working checkout is the
       most direct answer there is.
    4. `"unknown"` — said out loud rather than guessed.

    Every step is gated by `_sha`, so no source can promote a non-sha to a
    build label; and `git rev-parse` is asked about `root` specifically, with
    the git location variables stripped from its environment. That is not
    pedantry: those variables answer about a DIFFERENT repository, and this
    function's own eval case caught it the first time it ran inside the
    pre-commit hook, which sets `GIT_DIR` — the resolver reported the repo's
    HEAD while pointed at a temp directory that was not a repository at all.
    An inherited `GIT_DIR` in a container does the same thing to `/api/meta`.
    """
    environ = os.environ if environ is None else environ
    return (build_sha(root)
            or _sha(environ.get("GIT_SHA"))
            or _sha(_rev_parse(root, environ))
            or "unknown")


def _rev_parse(root, environ):
    """`root`'s own short HEAD, or None. Never raises — an absent git, an
    unreadable directory or a non-repository are all just "no answer"."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root,
            env={k: v for k, v in environ.items() if k not in GIT_LOCATION_VARS},
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout
    except Exception:
        return None
