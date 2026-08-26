"""The ONLY module in this repo that can talk to a paid API (ADR-036, D11).

Nothing on the gate path imports it. `src/sec10k/escalate.py` imports it
INSIDE the one function that spends money, so `python3 -m evals.run` never
pulls `urllib` in at all — the property is asserted dynamically by
`repo_hygiene`'s `escalation_seam` check, which imports the extractor in a
subprocess and reads `sys.modules`.

Written on stdlib `urllib.request` + `json` and NOT on the `anthropic` SDK, by
constraint, not by preference: `requirements.txt` is `fastapi` + `uvicorn`,
CI runs no `pip install` at all (ADR-003), and the extraction pipeline and the
eval harness must stay importable with zero third-party packages. That is the
documented exception to "use the official SDK" — a raw-HTTP client because the
project cannot take the dependency.

Three properties this module exists to guarantee, all of them ADR-036 rulings:

1. **No credential, no output.** `ANTHROPIC_API_KEY` is read from the
   environment and nowhere else. When it is absent every call raises
   `EscalationUnavailable` before a socket is opened. It is never defaulted,
   never prompted for, never logged, and never written to the cache key.
2. **No unbudgeted spend.** Every call goes through a `Budget`, which counts
   calls and dollars and raises `BudgetExceeded` rather than continuing
   (cost-discipline rule 3). `Budget(max_calls=0)` is a hard offline mode.
3. **Re-running is free.** Every response is cached under a content hash of
   everything that could change it — model, prompt version, system, user,
   max_tokens, effort (cost-discipline rule 2). A second run of the same eval
   costs $0.

Self-check: python3 -m src.sec10k.llm
"""
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

API_VERSION = "2023-06-01"
DEFAULT_BASE_URL = "https://api.anthropic.com"
# bumped whenever a prompt in escalate.py changes: it is part of the cache key,
# so a reworded prompt cannot silently be answered from an old response.
PROMPT_VERSION = "d11.1"

# USD per 1M tokens, (input, output). Cached from the Anthropic pricing table
# 2026-06-24 and used ONLY to turn a response's own reported token counts into
# the `usd` figure the routing record publishes. A stale price makes the
# published cost wrong, which is why it is a named constant with a date rather
# than a literal inside a formula.
PRICES = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

CACHE_DIR = Path(os.environ.get("SEC10K_LLM_CACHE") or (ROOT / "evals" / "cache" / "llm"))


class EscalationUnavailable(RuntimeError):
    """The slow path cannot run: no credential, or the API refused/failed.

    Raised, never swallowed into a fabricated answer. `escalate.route` catches
    exactly this class and records it verbatim in the routing record and as a
    doc-level warning, which is the "fail loudly and refuse" half of repo rule
    4 — the fast path's result still stands, and nothing claims a tier ran.
    """


class BudgetExceeded(EscalationUnavailable):
    """The run's call or dollar budget is spent. A subclass because a caller
    that already handles "the slow path could not run" handles this too."""


def usd(model, input_tokens, output_tokens):
    """Cost of one response in dollars, from its own reported token counts."""
    if model not in PRICES:
        raise KeyError(f"no price on record for model {model!r} — refusing to "
                       "publish a cost figure this module cannot compute")
    cin, cout = PRICES[model]
    return round((input_tokens * cin + output_tokens * cout) / 1_000_000, 6)


class Budget:
    """A per-run ceiling on paid work, enforced BEFORE the call (cost-discipline
    rule 3). `max_calls=0` is the offline mode the eval suites run under."""

    def __init__(self, max_calls=2, max_usd=1.00):
        self.max_calls = max_calls
        self.max_usd = max_usd
        self.calls = 0
        self.tokens = 0
        self.spent = 0.0

    def take(self):
        # ponytail: the dollar ceiling is checked against what has ALREADY been
        # spent, not against what this call is projected to cost, so one call
        # can overshoot `max_usd` by its own price — measured worst case on the
        # dev corpus is jpm-2024's rung 2 at an estimated $1.52 against a $1.00
        # default (ADR-036 §d3). Upgrade path when it matters: estimate input
        # tokens from len(user)/4 and refuse before the call. Not built here
        # because the estimate is the very thing the first live run exists to
        # replace, and a wrong pre-check refuses work that would have been
        # affordable. Carried as debt, not hidden.
        if self.calls >= self.max_calls:
            raise BudgetExceeded(
                f"run budget spent: {self.calls} of {self.max_calls} calls used")
        if self.spent >= self.max_usd:
            raise BudgetExceeded(
                f"run budget spent: ${self.spent:.4f} of ${self.max_usd:.2f}")
        self.calls += 1

    def charge(self, dollars, tokens):
        self.spent = round(self.spent + dollars, 6)
        self.tokens += tokens

    def as_dict(self):
        return {"llm_calls": self.calls, "tokens": self.tokens,
                "usd": round(self.spent, 6)}


def _cache_key(model, system, user, max_tokens, effort):
    blob = json.dumps([PROMPT_VERSION, model, system, user, max_tokens, effort],
                      sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(blob).hexdigest()


def _credential():
    """The key, from the environment and nowhere else.

    Not defaulted, not read from a file, not prompted for. An empty or
    whitespace-only value is treated as absent — an exported-but-empty
    variable is the shape a half-finished `export` leaves behind, and taking
    it as a credential would turn a loud refusal into a 401.
    """
    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise EscalationUnavailable(
            "ANTHROPIC_API_KEY is not set — the slow path refuses rather than "
            "degrading. The deterministic result above stands on its own; no "
            "tier ran and nothing was inferred.")
    return key


def call(model, system, user, max_tokens, budget, effort="low", timeout=120):
    """One Messages API request. Returns {"text", "usage", "usd", "cached"}.

    Cache first (free, and does not touch the budget or the credential), then
    budget, then credential, then the socket — in that order, so the cheapest
    refusal wins and a cached eval run needs no key at all.
    """
    key_hash = _cache_key(model, system, user, max_tokens, effort)
    hit = CACHE_DIR / f"{key_hash}.json"
    if hit.exists():
        got = json.loads(hit.read_text())
        return {**got, "cached": True}

    budget.take()
    api_key = _credential()
    body = {
        "model": model,
        "max_tokens": max_tokens,
        # `effort` replaces the removed `budget_tokens` on this model family;
        # sending `budget_tokens` to Opus 5 / Haiku 4.5 is a 400.
        "output_config": {"effort": effort},
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    base = os.environ.get("ANTHROPIC_BASE_URL") or DEFAULT_BASE_URL
    req = urllib.request.Request(
        base.rstrip("/") + "/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json",
                 "anthropic-version": API_VERSION,
                 "x-api-key": api_key},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # the body may carry the API's own error message; the KEY may not
        # appear in it, and does not — it travelled in a header we do not echo
        detail = e.read().decode("utf-8", "replace")[:400]
        raise EscalationUnavailable(f"API returned HTTP {e.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise EscalationUnavailable(f"API unreachable: {e}") from None

    if payload.get("stop_reason") == "refusal":
        raise EscalationUnavailable(
            f"model refused: {(payload.get('stop_details') or {}).get('category')}")
    text = "".join(b.get("text", "") for b in payload.get("content", [])
                   if b.get("type") == "text")
    u = payload.get("usage") or {}
    got = {
        "text": text,
        "usage": {"input_tokens": u.get("input_tokens", 0),
                  "output_tokens": u.get("output_tokens", 0)},
        "usd": usd(model, u.get("input_tokens", 0), u.get("output_tokens", 0)),
        "model": model,
    }
    budget.charge(got["usd"], sum(got["usage"].values()))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    hit.write_text(json.dumps(got, indent=1, sort_keys=True))
    return {**got, "cached": False}


def _demo():
    """The three properties above, each as an assertion that fails if the
    property breaks. No network, no key, no fabricated response."""
    import tempfile

    # 1. no credential -> refusal, raised before anything else happens
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        with tempfile.TemporaryDirectory() as td:
            global CACHE_DIR
            real_cache, CACHE_DIR = CACHE_DIR, Path(td)
            b = Budget(max_calls=5)
            try:
                call("claude-haiku-4-5", "s", "u", 64, b)
                raise AssertionError("a keyless call must refuse, not proceed")
            except EscalationUnavailable as e:
                assert "ANTHROPIC_API_KEY" in str(e), e
            # the budget is decremented BEFORE the credential check, so a
            # keyless run cannot loop forever pretending it never tried
            assert b.calls == 1, b.calls

            # an exported-but-empty variable is not a credential
            os.environ["ANTHROPIC_API_KEY"] = "   "
            try:
                call("claude-haiku-4-5", "s", "u", 64, Budget())
                raise AssertionError("an empty key must refuse")
            except EscalationUnavailable:
                pass
            del os.environ["ANTHROPIC_API_KEY"]

            # 2. a zero budget refuses before the credential is even read
            try:
                call("claude-opus-5", "s", "u", 64, Budget(max_calls=0))
                raise AssertionError("a zero budget must refuse")
            except BudgetExceeded as e:
                assert "budget spent" in str(e), e
            assert isinstance(BudgetExceeded("x"), EscalationUnavailable)

            # 3. a cached response is served without budget or credential.
            #    Written here through the cache's own key function — this is
            #    the CACHE being tested, not a fabricated API result: nothing
            #    downstream of this file ever sees it.
            k = _cache_key("claude-opus-5", "s", "u", 64, "low")
            (CACHE_DIR / f"{k}.json").write_text(json.dumps(
                {"text": "{}", "usage": {"input_tokens": 1, "output_tokens": 1},
                 "usd": 0.00003, "model": "claude-opus-5"}))
            zero = Budget(max_calls=0)
            got = call("claude-opus-5", "s", "u", 64, zero)
            assert got["cached"] is True and zero.calls == 0
            # ...and a different prompt is a different key, so a reworded
            # prompt can never be answered from the old response
            try:
                call("claude-opus-5", "s", "u2", 64, Budget(max_calls=0))
                raise AssertionError("a different prompt must miss the cache")
            except BudgetExceeded:
                pass
            CACHE_DIR = real_cache
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved

    # pricing arithmetic, and the refusal to invent a price
    assert usd("claude-opus-5", 1_000_000, 1_000_000) == 30.0
    assert usd("claude-haiku-4-5", 200_000, 0) == 0.2
    try:
        usd("gpt-not-a-model", 1, 1)
        raise AssertionError("an unpriced model must not yield a cost figure")
    except KeyError:
        pass

    b = Budget(max_calls=1, max_usd=0.10)
    b.take(); b.charge(0.02, 500)
    assert b.as_dict() == {"llm_calls": 1, "tokens": 500, "usd": 0.02}
    try:
        b.take()
        raise AssertionError("a spent call budget must refuse")
    except BudgetExceeded:
        pass
    print("[llm self-check] ok")


if __name__ == "__main__":
    _demo()
