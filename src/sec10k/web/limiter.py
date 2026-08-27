"""A global request limit on the FREE deterministic tier (TD-162 / D15).

The door (`gate.py`, TD-158) closed the PAID path and deliberately left
extraction open — the product, free and unauthenticated. What that left
unbounded is everything the free path costs: measured 2026-08-28, one
~25 MB request is ~1.1 s CPU and ~138 MB peak RSS (`tasks/reviews/
pr-d15-red.txt`), and `/api/extract/url` additionally spends an outbound
EDGAR fetch per request under this repo's attributable fair-access
User-Agent. A caller in a loop is a denial-of-service and hosting-cost
surface, not a billing one.

**Global per process, not per IP, deliberately** (ADR-040). Zeabur's proxy
means per-IP identification rides a forwarded header this repo cannot
measure or test offline — the same reason TD-158's rate-limit branch was
declined — and behind that proxy a per-IP key may be shared between real
callers anyway. One shared bucket is the honest version: the refusal says
so ("shared by ALL callers") instead of implying fairness that does not
exist. The known ceiling: one hammering client degrades everyone on the
instance until the window recovers — accepted, because the alternative is
a key nothing here can verify.

**Token bucket on the monotonic clock.** Burst allowance + sustained
per-minute refill, stdlib only, no external store, deterministic given the
clock (injectable, which is how the eval check runs the real decision path
red/green). Sized so a human demo viewer never notices — the deep link
fires exactly one extraction per page load, and nobody clicks Extract 20
times in a burst — while a loop is refused in seconds with an honest 429
and Retry-After.

**Config is BOUNDED.** Two env vars, both clamped into [1, max]; garbage
parses to the default, never to infinity and never to zero. There is no
spelling of either variable that turns the limit off — the failure mode of
a typo is "the default limit", not "no limit" (the `gate.py` property,
applied here).

Stdlib only and no fastapi import, deliberately: `repo_hygiene`'s
`free_tier_limit` check IMPORTS this module and exercises the decision
path for real, the way `escalation_door` runs `gate.py`'s table instead of
reading its shape.

Self-check: python3 -m src.sec10k.web.limiter
"""
import os
import threading
import time

BURST_VAR = "SEC10K_FREE_BURST"
RATE_VAR = "SEC10K_FREE_PER_MINUTE"
DEFAULT_BURST = 20
DEFAULT_PER_MINUTE = 30
# Ceilings on the CONFIG, so every configurable value is still a real limit.
MAX_BURST = 500
MAX_PER_MINUTE = 3000
# The one path prefix the middleware limits; covers all three extract routes
# (and any future one) by construction rather than by enumeration.
LIMITED_PREFIX = "/api/extract/"


def _bounded_int(raw, default, hi):
    """An operator-supplied limit: garbage means the DEFAULT, never infinity,
    and any parsed value is clamped into [1, hi]."""
    try:
        v = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return max(1, min(hi, v))


class Limiter:
    """Token bucket: `burst` requests immediately, refilled at
    `per_minute / 60` tokens per second, never holding more than `burst`.

    `clock` is injectable for the eval check and the self-check; production
    uses `time.monotonic`. Thread-safe because uvicorn runs sync endpoints
    on a threadpool.
    """

    def __init__(self, burst=None, per_minute=None, clock=time.monotonic):
        self.burst = _bounded_int(
            os.environ.get(BURST_VAR) if burst is None else burst,
            DEFAULT_BURST, MAX_BURST)
        self.per_minute = _bounded_int(
            os.environ.get(RATE_VAR) if per_minute is None else per_minute,
            DEFAULT_PER_MINUTE, MAX_PER_MINUTE)
        self.clock = clock
        self._lock = threading.Lock()
        self._tokens = float(self.burst)
        self._last = clock()

    def allow(self):
        """`(allowed, retry_after_seconds, reason)` — the ONE decision.

        The reason is written for the envelope: it names the shared limit and
        the wait honestly, and says the tier stays free — a refusal that reads
        as a paywall or an outage would be a lie in either direction.
        """
        rate = self.per_minute / 60.0
        with self._lock:
            now = self.clock()
            self._tokens = min(float(self.burst),
                               self._tokens + max(0.0, now - self._last) * rate)
            self._last = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True, 0.0, "within the free-tier limit"
            wait = (1.0 - self._tokens) / rate
            return False, wait, (
                f"free-tier limit: this deployment serves at most "
                f"{self.burst} extractions in a burst and {self.per_minute} "
                f"per minute, shared by ALL callers — wait about "
                f"{int(wait) + 1}s and retry. The deterministic tier stays "
                f"free and open; this is a load ceiling, not a paywall")

    def reset(self):
        """Refill to a full burst — the documented seam a self-check or test
        harness uses instead of an env kill-switch that could ship off."""
        with self._lock:
            self._tokens = float(self.burst)
            self._last = self.clock()


# The one process-wide bucket `app.py`'s middleware consults. Module-level on
# purpose: one process, one limit, the same shape as `_SERVER_BUDGET`.
# ponytail: per-process state, so N uvicorn workers mean N x the limit and a
# restart refills it — fine for the single-instance inspector; an external
# store is the upgrade path if this ever scales out.
LIMITER = Limiter()


def _demo():
    t = [0.0]
    lim = Limiter(burst=3, per_minute=60, clock=lambda: t[0])
    assert [lim.allow()[0] for _ in range(3)] == [True] * 3
    ok, wait, why = lim.allow()
    assert ok is False and wait > 0 and len(why) > 40, (ok, wait, why)
    t[0] += 1.0                       # 60/min == one token per second
    assert lim.allow()[0] is True
    assert lim.allow()[0] is False    # refill is elapsed x rate, no more
    t[0] += 3600.0                    # a long idle never banks past the burst
    assert [lim.allow()[0] for _ in range(4)] == [True, True, True, False]
    lim.reset()
    assert lim.allow()[0] is True
    # bounded config: no spelling of the env vars means "no limit"
    assert _bounded_int("banana", 20, 500) == 20
    assert _bounded_int(None, 20, 500) == 20
    assert _bounded_int("0", 20, 500) == 1
    assert _bounded_int("-7", 20, 500) == 1
    assert _bounded_int("999999999", 20, 500) == 500
    assert 1 <= DEFAULT_BURST <= MAX_BURST
    assert 1 <= DEFAULT_PER_MINUTE <= MAX_PER_MINUTE
    for route in ("fixture", "upload", "url"):
        assert f"/api/extract/{route}".startswith(LIMITED_PREFIX)
    # PR #65 R1: the PRODUCTION singleton, by behavior and exact type — an
    # isinstance pin accepted an always-allow subclass that admitted
    # 1000/1000 while this self-check printed ok
    assert type(LIMITER) is Limiter
    LIMITER.reset()
    admitted = sum(1 for _ in range(LIMITER.burst + 3) if LIMITER.allow()[0])
    assert admitted <= LIMITER.burst + 1, admitted   # it must actually refuse
    LIMITER.reset()
    print("limiter: ok")


if __name__ == "__main__":
    _demo()
