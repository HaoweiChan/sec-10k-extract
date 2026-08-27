"""The door on the PAID path (TD-158, ADR-036 §h2, owner decision 2026-08-27).

ADR-036 §h2 made the deployed inspector escalate by DEFAULT, and PR #61 R10
showed that excluding the two collapsing fixtures did not close the money path:
`POST /api/extract/url` takes any `https://www.sec.gov/Archives/…` URL, and
`intc-2025` is a real Intel EDGAR filing whose own Archives URL still bills.
Fixture exclusion cannot fix that — the service extracts arbitrary EDGAR URLs
by design, so ANY collapsing filing on EDGAR was a paid call for an anonymous
caller. The owner's decision was to close it at the door instead.

**What is closed and what is not.** Extraction is the product and stays open,
free and unauthenticated: a viewer with no secret gets the full deterministic
run, every item, every span, the compare pane, all of it. The only thing behind
the door is the paid tier, and when it does not open the envelope says WHY
(`view["escalation"]`, rendered by the routing strip) rather than going quiet.

**Safe when unset, which is the property that matters.** With no
`SEC10K_ESCALATION_TOKEN` on the host the door is CLOSED, not open — the
failure mode of a forgotten variable is "the demo is free", never "the demo is
free to bill me". `MIN_TOKEN_CHARS` is why a token is a bounded default rather
than an open one: a one-character secret configured by accident is refused in
the same words an absent one is, so there is no value of the variable that is
worse than leaving it unset.

**One decision, not three guards.** `web.app._run` is the single point all
three input modes converge on, and it is the only caller of `extract_items` in
the web layer; this function is called there exactly once. A new endpoint that
forgets to pass its `Request` gets `presented=None` and therefore the free
path — the fail-safe direction — which is what makes the choke point structural
rather than a convention three call sites have to remember (PR #61 R13 is the
same defect class: a per-line guard a second endpoint walked around).

Stdlib only and no fastapi import, deliberately: `repo_hygiene`'s
`escalation_door` check IMPORTS this module and exercises the decision table
for real, instead of reading its shape out of `app.py` with `ast` — which is
what every previous money pin had to do, and is why they were evadable.

Self-check: python3 -m src.sec10k.web.gate
"""
import hmac
import os

# The request header a caller presents. Lower-case because that is how
# Starlette's case-insensitive header mapping is keyed and how curl sends it.
HEADER = "x-escalation-token"
TOKEN_VAR = "SEC10K_ESCALATION_TOKEN"
# A floor on the secret, not a policy about its shape. 16 characters is what
# `secrets.token_urlsafe(12)` produces; anything shorter is treated as absent.
MIN_TOKEN_CHARS = 16


def configured_token():
    """The deployment's escalation secret, or "" when there is none."""
    return os.environ.get(TOKEN_VAR, "").strip()


def paid_path_open(presented, armed, token=None):
    """`(may_escalate, reason)` — the ONE decision that lets a request spend.

    `presented` is the request's `X-Escalation-Token` header (None when the
    caller sent none, or when the call site had no request to read — the
    fail-safe direction). `armed` is `app.ESCALATION_ENABLED`, the operator's
    off-switch. `token` overrides the configured secret and exists for the
    check that exercises this table; production passes nothing.

    The reason is returned even on the happy path because it is published in
    the envelope either way, and a viewer who is told nothing cannot tell
    "escalation ran and the trigger stayed quiet" from "escalation never ran".
    """
    token = configured_token() if token is None else token.strip()
    if not armed:
        return False, ("the operator disarmed this deployment "
                       "(SEC10K_ESCALATION_ENABLED) — no model tier can run")
    if len(token) < MIN_TOKEN_CHARS:
        return False, (f"this deployment has no {TOKEN_VAR} of at least "
                       f"{MIN_TOKEN_CHARS} characters configured, so the paid "
                       f"tier is closed to everyone including the operator")
    if not _same(presented, token):
        return False, (f"no valid {HEADER} header on this request — the "
                       f"deterministic extraction above is complete and free; "
                       f"only the paid model tier is behind the header")
    return True, (f"a valid {HEADER} header was presented, so the model tier "
                  f"was allowed to run if the trigger fired")


def _same(presented, token):
    """Constant-time compare, tolerant of the ways a header can be absent."""
    if not presented:
        return False
    try:
        return hmac.compare_digest(presented.strip().encode("utf-8"),
                                   token.encode("utf-8"))
    except (AttributeError, UnicodeError):
        return False


def _demo():
    good = "x" * MIN_TOKEN_CHARS
    open_ = lambda p, a=True, t=good: paid_path_open(p, a, token=t)[0]  # noqa: E731

    # UNSET is CLOSED. The whole point: a host nobody configured cannot bill.
    assert open_(good, True, "") is False
    assert open_(None, True, "") is False
    # a too-short secret is treated as no secret, in both directions
    assert open_("abc", True, "abc") is False
    assert open_(good, True, good[:MIN_TOKEN_CHARS - 1]) is False
    # the operator's off-switch still wins, even with a valid token
    assert open_(good, False) is False
    # no header, empty header, wrong header
    assert open_(None) is False and open_("") is False
    assert open_("y" * MIN_TOKEN_CHARS) is False
    # and the one case that opens
    assert open_(good) is True
    assert open_(f"  {good}  ") is True          # header whitespace is trimmed
    # every refusal explains itself, and never leaks the secret
    for args in ((good, True, ""), (None, True, good), (good, False, good)):
        ok, why = paid_path_open(args[0], args[1], token=args[2])
        assert ok is False and len(why) > 40 and good not in why, why
    # HEADER is what app.py reads off the request; keep it lower-case so the
    # ASGI header mapping and a hand-written curl agree
    assert HEADER == HEADER.lower() and MIN_TOKEN_CHARS >= 16
    print("gate: ok")


if __name__ == "__main__":
    _demo()
