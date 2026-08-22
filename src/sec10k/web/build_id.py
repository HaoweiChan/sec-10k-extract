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


def build_sha(root=ROOT):
    """The sha this build injected, or None if it did not inject a real one."""
    try:
        text = (Path(root) / BUILD_SHA_FILE).read_text().strip()
    except OSError:
        return None
    return text[:12] if SHA_RE.fullmatch(text) else None


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

    `environ` is the environment the whole resolution happens in, the git call
    included. That is not pedantry: `git rev-parse` honours `GIT_DIR` from the
    environment and will happily answer from a repo that is not `root` at all.
    Measured — this function's own eval case went red the first time it ran
    inside the pre-commit hook, which sets `GIT_DIR`, reporting the repo's HEAD
    while pointed at a temp directory that was not a repository.
    """
    environ = os.environ if environ is None else environ
    injected = build_sha(root)
    if injected:
        return injected
    env = (environ.get("GIT_SHA") or "").strip()
    if env:
        return env[:12]
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, env=dict(environ),
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"
