"""The ONLY module in this repo that can talk to a paid API (ADR-036, D11).

Provider: **OpenRouter** (`https://openrouter.ai/api/v1/chat/completions`),
owner instruction 2026-08-27. The Anthropic Messages API client this replaced
is gone, not renamed: the auth header, the request body, the response shape,
the model ids and the pricing source all changed (ADR-036 §h1).

Nothing on the gate path imports this module. `src/sec10k/escalate.py` imports
it INSIDE the one function that spends money, so `python3 -m evals.run` never
pulls `urllib` in at all — asserted dynamically by `repo_hygiene`'s
`escalation_seam` check, which imports the extractor in a subprocess and reads
`sys.modules`.

Written on stdlib `urllib.request` + `json` and NOT on a vendor SDK, by
constraint: `requirements.txt` is `fastapi` + `uvicorn`, CI runs no
`pip install` at all (ADR-003), and the pipeline and eval harness must stay
importable with zero third-party packages.

Four properties this module exists to guarantee, all of them ADR-036 rulings:

1. **No credential, no output.** `OPENROUTER_API_KEY` is read from the
   environment and nowhere else. When it is absent every call raises
   `EscalationUnavailable` before a socket is opened. Never defaulted, never
   prompted for, never logged, never part of a cache key.
2. **No unbudgeted spend.** Every call goes through a `Budget` (cost-discipline
   rule 3). `Budget(max_calls=0)` is a hard offline mode. Read `Budget`'s own
   docstring for what its ceiling does and does NOT bound — PR #58 R6.
3. **Re-running is free.** Every response is cached under a content hash of
   everything that could change it (cost-discipline rule 2).
4. **No invented price.** `usd()` reads per-token pricing out of the committed
   OpenRouter catalogue record and raises on a slug that is not in it. There is
   no hand-maintained price table to go stale (PR #58, owner instruction).

Self-check: python3 -m src.sec10k.llm   (wired into CI's unit-tests job — PR #58 R3)
"""
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
# bumped whenever a prompt in escalate.py or the request shape changes: it is
# part of the cache key, so a reworded prompt — or a different provider's
# request body — cannot be answered from an old response.
PROMPT_VERSION = "d11.2-openrouter"

# The two rungs, as OpenRouter SLUGS. Not guessed: both are present verbatim in
# the committed catalogue record below, and `usd()` refuses a slug that is not.
#   openai/gpt-5-mini       $0.25/$2.00 per MTok, 400,000 ctx — the cheap rung.
#   anthropic/claude-opus-5 $5.00/$25.00 per MTok, 1,000,000 ctx — the strong one,
#   deliberately the SAME model the pre-swap ADR costed, so every figure in
#   ADR-036 §d moves for exactly one reason: the cheap rung got cheaper.
# `escalate.RUNGS` names them; this module only prices and calls them.

# Pricing lives in a dated, committed artifact rather than in this file, so the
# published cost of the ladder is sourced and re-derivable (owner instruction,
# PR #58). It is read at call time from disk — never fetched — because fetching
# it would put a network module back on the seam `escalation_seam` protects.
PRICES_FILE = ROOT / "tasks" / "reviews" / "2026-08-27-openrouter-models.json"

CACHE_DIR = Path(os.environ.get("SEC10K_LLM_CACHE") or (ROOT / "evals" / "cache" / "llm"))


class EscalationUnavailable(RuntimeError):
    """The slow path cannot run: no credential, budget spent, or the API
    refused/failed.

    Raised, never swallowed into a fabricated answer. `escalate.route` catches
    exactly this class and records it verbatim in the routing record and as a
    doc-level warning — the "fail loudly and refuse" half of repo rule 4.
    """


class BudgetExceeded(EscalationUnavailable):
    """The budget's call or dollar ceiling is spent. A subclass because a
    caller that already handles "the slow path could not run" handles this."""


def _catalogue():
    """The committed OpenRouter model record. Raises if it is missing."""
    try:
        return json.loads(PRICES_FILE.read_text())
    except OSError as e:
        raise EscalationUnavailable(
            f"the OpenRouter pricing record {PRICES_FILE.name} is unreadable ({e}) — "
            "refusing to price or make a call without it") from None


def price(model):
    """(input, output) USD per 1M tokens for `model`, from the committed record.

    FAILS LOUDLY on a slug the record does not carry. There is deliberately no
    default and no fallback constant: a wrong price makes the published cost
    wrong, and a silently stale one is worse than a crash (owner instruction,
    PR #58).
    """
    models = _catalogue().get("models", {})
    if model not in models:
        raise KeyError(
            f"model {model!r} is not in {PRICES_FILE.name} (which carries "
            f"{sorted(models)}) — refusing to invent a price. Re-fetch "
            "https://openrouter.ai/api/v1/models and re-commit that artifact.")
    p = models[model].get("pricing") or {}
    try:
        # OpenRouter publishes USD per TOKEN as strings
        return float(p["prompt"]) * 1e6, float(p["completion"]) * 1e6
    except (KeyError, TypeError, ValueError) as e:
        raise KeyError(f"model {model!r} has no usable pricing in "
                       f"{PRICES_FILE.name}: {p!r} ({e})") from None


def usd(model, input_tokens, output_tokens):
    """Cost of one response in dollars, from its own reported token counts."""
    cin, cout = price(model)
    return round((input_tokens * cin + output_tokens * cout) / 1_000_000, 6)


class Budget:
    """A ceiling on paid work, enforced BEFORE the call (cost-discipline rule 3).

    **What it bounds, stated exactly, because the previous docstring said
    "per-run" and that was false (PR #58 R6).** A `Budget` instance bounds the
    calls and dollars charged THROUGH THAT INSTANCE. Its scope is therefore
    whatever the caller gives it:

      * `extract_items(path, escalate=True)` with no `budget=` creates one per
        DOCUMENT — 2 calls / $1.00 for that document and no more;
      * a caller sweeping many documents must pass ONE `Budget` to every
        `extract_items` call to get a per-sweep ceiling. `evals/snapshot.py`
        and the eval adapter never escalate at all, so neither needs one;
      * the web layer passes a single process-wide `Budget` created at import
        (`web.app.SERVER_BUDGET`), so an unauthenticated deployment cannot be
        driven past it however many requests arrive (ADR-036 §h2).

    `max_calls=0` is a hard offline mode and is what a zero-budget refusal
    looks like.
    """

    def __init__(self, max_calls=2, max_usd=1.00):
        self.max_calls = max_calls
        self.max_usd = max_usd
        self.calls = 0
        self.tokens = 0
        self.spent = 0.0

    def take(self):
        # ponytail: the dollar ceiling is checked against what has ALREADY been
        # spent, not against what this call is projected to cost, so one call
        # can overshoot `max_usd` by its own price. That overshoot is BOUNDED
        # by `escalate.EXTRACT_WINDOW` (PR #58 R12), and the bound is a derived
        # figure printed by `tasks/reviews/d11_sweep_cost.py` under "§h2 — the
        # effective deployment ceiling" rather than a number restated here —
        # this comment used to carry its own, and hand-typed dollar figures in
        # this branch have a perfect record of being wrong (PR #58 R22).
        # Upgrade path when it matters: estimate input
        # tokens from len(user)/4 and refuse before the call. Not built here
        # because that estimate is the very thing the first live run exists to
        # replace, and a wrong pre-check refuses affordable work. Debt row.
        if self.calls >= self.max_calls:
            raise BudgetExceeded(
                f"budget spent: {self.calls} of {self.max_calls} calls used")
        if self.spent >= self.max_usd:
            raise BudgetExceeded(
                f"budget spent: ${self.spent:.4f} of ${self.max_usd:.2f}")
        self.calls += 1

    def charge(self, dollars, tokens):
        self.spent = round(self.spent + dollars, 6)
        self.tokens += tokens

    def as_dict(self):
        return {"llm_calls": self.calls, "tokens": self.tokens,
                "usd": round(self.spent, 6)}


def _cache_key(model, system, user, max_tokens):
    blob = json.dumps([PROMPT_VERSION, model, system, user, max_tokens],
                      sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(blob).hexdigest()


def _credential():
    """The key, from the environment and nowhere else.

    An empty or whitespace-only value is treated as absent — that is the shape
    a half-finished `export` leaves behind, and taking it as a credential turns
    a loud refusal into a 401.
    """
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not key:
        raise EscalationUnavailable(
            "OPENROUTER_API_KEY is not set — the slow path refuses rather than "
            "degrading. The deterministic result above stands on its own; no "
            "tier ran and nothing was inferred.")
    return key


def _body(model, system, user, max_tokens, reasoning_tokens=None):
    """The OpenAI-shaped request body OpenRouter expects.

    Its own function so `_demo` can assert the SHAPE rather than text-match the
    file.

    **`reasoning` is sent when the rung asks for it (2026-08-27).** An earlier
    version of this docstring said OpenRouter's chat-completions surface "has no
    equivalent" of a reasoning knob and that the body has exactly three keys.
    That was WRONG, and the intc-2025 exam billed $0.895360 to find out:
    OpenRouter documents a `reasoning` request parameter taking `effort` OR
    `max_tokens` (mutually exclusive), and documents that **"for Anthropic
    models, `max_tokens` must be strictly higher than the reasoning budget to
    ensure there are tokens available for the final response after thinking"**.
    We sent `max_tokens: 2048` and no reasoning budget to a reasoning model; the
    allowance went entirely to thinking, `completion_tokens` came back as
    exactly 2048, and `content` was empty.

    Sending the split EXPLICITLY is what makes the outcome deterministic rather
    than dependent on a provider default: the caller states the thinking budget,
    and `max_tokens` is that budget plus room for the answer.
    """
    body = {"model": model, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}]}
    if reasoning_tokens:
        body["reasoning"] = {"max_tokens": reasoning_tokens}
    return body


def _normalize(payload, text, choice, model, max_tokens):
    """The provider response reduced to the record this repo stores and prices.

    Its own function so `_demo` can assert what the record CARRIES without a
    socket — which matters because `finish_reason` is a diagnostic, and a
    diagnostic nothing asserts is one that quietly stops being written. The
    intc-2025 exam had to be diagnosed from arithmetic precisely because this
    field was thrown away.
    """
    u = payload.get("usage") or {}
    return {
        "text": text,
        "usage": {"input_tokens": u.get("prompt_tokens", 0),
                  "output_tokens": u.get("completion_tokens", 0),
                  # TD-165. `output_tokens` counts thinking AND answer, so an
                  # empty completion at finish_reason `length` has two readings
                  # it cannot separate: the reasoning cap was not enforced and
                  # thinking ate the whole allowance, or it was enforced and the
                  # answer itself was truncated. This field separates them, and
                  # its absence is what made the 2026-08-28 run cost $0.997760
                  # and still not explain itself. None when the provider omits
                  # it — never 0, which would read as "measured, no reasoning".
                  "reasoning_tokens": (u.get("completion_tokens_details") or {}
                                       ).get("reasoning_tokens")},
        "usd": usd(model, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)),
        "model": model,
        # OpenRouter normalizes this to one of tool_calls / stop / length /
        # content_filter / error, and `length` is the documented signal that the
        # token limit was reached — so an exhausted allowance is DETECTABLE
        # rather than inferred from arithmetic.
        "finish_reason": choice.get("finish_reason"),
        "max_tokens": max_tokens,
    }


def call(model, system, user, max_tokens, budget, timeout=120,
         reasoning_tokens=None):
    """One OpenRouter chat-completions request.

    Returns {"text", "usage", "usd", "model", "cached"}.

    Cache first (free, and touches neither the budget nor the credential), then
    budget, then credential, then the socket — cheapest refusal wins, and a
    cached eval run needs no key at all.
    """
    key_hash = _cache_key(model, system, user, max_tokens)
    hit = CACHE_DIR / f"{key_hash}.json"
    if hit.exists():
        return {**json.loads(hit.read_text()), "cached": True}

    budget.take()
    api_key = _credential()
    body = _body(model, system, user, max_tokens, reasoning_tokens)
    base = os.environ.get("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json",
                 "authorization": f"Bearer {api_key}"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # the body may carry the provider's own error message; the key travels
        # in a header we do not echo, so it cannot appear here
        detail = e.read().decode("utf-8", "replace")[:400]
        raise EscalationUnavailable(f"API returned HTTP {e.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise EscalationUnavailable(f"API unreachable: {e}") from None

    # OpenRouter returns provider errors INSIDE a 200 body as often as not
    if payload.get("error"):
        raise EscalationUnavailable(f"API error: {payload['error']}")
    try:
        choice = payload["choices"][0]
        text = choice["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise EscalationUnavailable(
            f"unparseable response shape ({type(e).__name__}: {e}): "
            f"{json.dumps(payload)[:300]}") from None
    if choice.get("finish_reason") == "content_filter":
        raise EscalationUnavailable("provider refused: finish_reason=content_filter")

    got = _normalize(payload, text, choice, model, max_tokens)
    budget.charge(got["usd"], sum(got["usage"].values()))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    hit.write_text(json.dumps(got, indent=1, sort_keys=True))
    return {**got, "cached": False}


def _demo():
    """Every property above that can be proven without spending money.

    No network, no key, no fabricated API response. Run by CI's unit-tests job
    (PR #58 R3) — before that, deleting every guard below left both gate suites
    100% green, which is recorded in tasks/reviews/pr58-r1-red.txt.
    """
    import tempfile
    from src.sec10k.escalate import RUNGS

    # 0. the provider swap is real, not a rename
    assert "openrouter.ai" in DEFAULT_BASE_URL
    src = Path(__file__).read_text()
    # spelled in halves so this assertion is not itself the occurrence it forbids
    for gone in ("ANTHROPIC" + "_API_KEY", "x-api" + "-key"):
        assert gone not in src, f"{gone!r} is Anthropic-transport residue — swap incomplete"
    # the request body is OpenAI-shaped and carries no reasoning-effort knob —
    # asserted on the SHAPE, so a text pin cannot be satisfied by a comment
    # the record the client stores must carry the DIAGNOSTICS, not just the
    # text: `finish_reason` and the `max_tokens` it was measured against are
    # what turn "empty content" into "the allowance ran out" without a second
    # billed call (the intc-2025 exam cost $0.895360 and could not say which).
    rec = _normalize({"usage": {"prompt_tokens": 10, "completion_tokens": 2048}},
                     "", {"finish_reason": "length"}, RUNGS[1][1], 2048)
    assert rec["finish_reason"] == "length", rec
    assert rec["max_tokens"] == 2048 and rec["usage"]["output_tokens"] == 2048
    assert rec["text"] == "" and rec["usd"] == usd(RUNGS[1][1], 10, 2048)
    assert {"text", "usage", "usd", "model", "finish_reason", "max_tokens"} <= set(rec)
    # TD-165: `reasoning_tokens` is the field that separates "the reasoning cap
    # was not enforced" from "it was, and the ANSWER was truncated" — the two
    # readings of the 2026-08-28 run, which finish_reason alone cannot tell
    # apart because both surface as `length` with empty content. Asserted for
    # the same reason finish_reason is: a diagnostic nothing asserts is one
    # that quietly stops being written. Recorded as None when the provider
    # omits it, never defaulted to a number that would read as measured.
    assert "reasoning_tokens" in rec["usage"], rec
    assert rec["usage"]["reasoning_tokens"] is None, "absent must stay absent"
    deep = _normalize({"usage": {"prompt_tokens": 10, "completion_tokens": 6144,
                                 "completion_tokens_details": {"reasoning_tokens": 6144}}},
                      "", {"finish_reason": "length"}, RUNGS[1][1], 6144)
    assert deep["usage"]["reasoning_tokens"] == 6144, deep

    b = _body("m", "sys", "usr", 7)
    assert set(b) == {"model", "max_tokens", "messages"}, sorted(b)
    assert [m["role"] for m in b["messages"]] == ["system", "user"]
    assert b["messages"][0]["content"] == "sys" and b["max_tokens"] == 7
    # ...and the reasoning split is sent when a rung asks for it. OpenRouter
    # documents that for Anthropic models `max_tokens` must be strictly higher
    # than the reasoning budget; the exam proved what happens when it is not.
    assert "reasoning" not in _body("m", "s", "u", 7)
    r = _body("m", "s", "u", 6144, reasoning_tokens=4096)
    assert r["reasoning"] == {"max_tokens": 4096} and r["max_tokens"] == 6144
    assert r["max_tokens"] > r["reasoning"]["max_tokens"], "no room left to answer"

    # 1. pricing comes from the committed record, and an unknown slug RAISES
    for _, model, _think in RUNGS:
        cin, cout = price(model)
        assert cin > 0 and cout > 0, (model, cin, cout)
    # the exact figures ADR-036 §d is derived from, pinned so a re-fetch that
    # moves them cannot silently invalidate every published dollar
    assert price("openai/gpt-5-mini") == (0.25, 2.0), price("openai/gpt-5-mini")
    assert price("anthropic/claude-opus-5") == (5.0, 25.0)
    assert usd("anthropic/claude-opus-5", 1_000_000, 1_000_000) == 30.0
    assert usd("openai/gpt-5-mini", 1_000_000, 0) == 0.25
    try:
        usd("no/such-model", 1, 1)
        raise AssertionError("an unpriced model must not yield a cost figure")
    except KeyError as e:
        assert "refusing to invent a price" in str(e)

    saved = os.environ.pop("OPENROUTER_API_KEY", None)
    try:
        with tempfile.TemporaryDirectory() as td:
            global CACHE_DIR
            real_cache, CACHE_DIR = CACHE_DIR, Path(td)
            model = RUNGS[0][1]

            # 2. no credential -> refusal, raised before anything else happens
            b = Budget(max_calls=5)
            try:
                call(model, "s", "u", 64, b)
                raise AssertionError("a keyless call must refuse, not proceed")
            except EscalationUnavailable as e:
                assert "OPENROUTER_API_KEY" in str(e), e
            # the budget is decremented BEFORE the credential check, so a
            # keyless run cannot loop forever pretending it never tried
            assert b.calls == 1, b.calls

            # an exported-but-empty variable is not a credential
            os.environ["OPENROUTER_API_KEY"] = "   "
            try:
                call(model, "s", "u", 64, Budget())
                raise AssertionError("an empty key must refuse")
            except EscalationUnavailable:
                pass
            del os.environ["OPENROUTER_API_KEY"]

            # 3. a zero budget refuses before the credential is even read
            try:
                call(model, "s", "u", 64, Budget(max_calls=0))
                raise AssertionError("a zero budget must refuse")
            except BudgetExceeded as e:
                assert "budget spent" in str(e), e
            assert isinstance(BudgetExceeded("x"), EscalationUnavailable)
            # ...and so does a spent DOLLAR ceiling, which is a separate guard
            spent = Budget(max_calls=9, max_usd=0.10)
            spent.charge(0.11, 10)
            try:
                spent.take()
                raise AssertionError("a spent dollar budget must refuse")
            except BudgetExceeded as e:
                assert "$0.1100 of $0.10" in str(e), e

            # 4. a cached response is served without budget or credential. This
            #    is the CACHE under test, written through its own key function;
            #    nothing downstream of this file ever sees it.
            k = _cache_key(model, "s", "u", 64)
            (CACHE_DIR / f"{k}.json").write_text(json.dumps(
                {"text": "{}", "usage": {"input_tokens": 1, "output_tokens": 1},
                 "usd": 0.0, "model": model}))
            zero = Budget(max_calls=0)
            got = call(model, "s", "u", 64, zero)
            assert got["cached"] is True and zero.calls == 0
            # ...and a different prompt is a different key, so a reworded
            # prompt can never be answered from the old response
            try:
                call(model, "s", "u2", 64, Budget(max_calls=0))
                raise AssertionError("a different prompt must miss the cache")
            except BudgetExceeded:
                pass
            CACHE_DIR = real_cache
    finally:
        if saved is not None:
            os.environ["OPENROUTER_API_KEY"] = saved

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
