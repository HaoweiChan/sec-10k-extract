# ADR-040 — D15: the free deterministic tier gets a GLOBAL request limit, not a per-IP one

Date: 2026-08-28. Status: accepted. Implements D15 (TD-162, promoted
2026-08-28, split out of TD-158 when the door closed the billing half). Not a
freeze exception: this is deployment protection in the web layer, not an
extraction capability — `extract_items` is untouched, default-flag digests do
not move, and no eval fixture's output changes. Amends
[ADR-036](ADR-036-tiered-escalation.md) §h2 (its two "the FREE tier has no
rate limit and no request cap" statements gain dated notes — they were true
when written and are now closed by this ADR; the door itself still carries no
rate limit of its own, which remains deliberate).

**Ruling**: one global per-process token bucket (`src/sec10k/web/limiter.py`, stdlib only: monotonic clock, `SEC10K_FREE_BURST` default 20 clamped [1, 500], `SEC10K_FREE_PER_MINUTE` default 30 clamped [1, 3000] — garbage parses to the default, so no spelling of either variable means "no limit"), consulted by ONE `@app.middleware("http")` choke point covering every `/api/extract/*` path by prefix, so refusal happens BEFORE the endpoint body: before the upload is read, before any outbound EDGAR fetch, before `extract_items`. Over-limit requests get HTTP 429 in the standard `_err` envelope with `Retry-After` and a reason naming the SHARED limit; every other path (`/`, `/api/meta`, source/normalized downloads) passes through untouched and consumes nothing.
**Because**: measured 2026-08-28, one ~25 MB request costs ~1.13 s CPU and ~138 MB peak RSS (jpm-2024 as committed: 0.59 s / 82 MB) — real load on a single-instance host, and `/api/extract/url` additionally spends an attributable EDGAR fetch per request — while per-IP identification behind Zeabur's proxy rides a forwarded header this repo cannot measure or test offline (the reason TD-158's rate-limit branch was declined), so a per-IP bucket would be a fairness claim nothing here can verify; global-and-honest beats per-IP-and-untestable, and the defaults (20 burst, one every 2 s sustained) sit far above human clicking rates — the deep link fires exactly one extraction per page load — so a demo viewer never sees a 429.
**Enforced by**: `evals/adversarial/free-tier-limit.json` (`fast`+`invariant`) — the check imports `limiter.py` and runs the decision path with an injected clock, then compiles the real middleware out of `app.py`'s tree and CALLS it (under-limit reaches `call_next`; over-limit returns the 429 + `Retry-After` on all three extract paths and never reaches `call_next`; `/api/meta` consumes nothing; service recovers when the window elapses); `src/sec10k/web/limiter.py::_demo`; red-first record, 25 MB measurement, 10/10 mutation battery and the live uvicorn over-limit run in `tasks/reviews/pr-d15-red.txt`.

---

## a) What was unbounded, measured rather than asserted

TD-162's spec said "a large filing is real CPU and real memory" without a
number. The number, measured on the dev machine (Apple M-series, Python
3.14) via `extract_items` in a fresh subprocess — the exact call `_run`
makes, `escalate=False`:

| input | bytes | CPU (s) | wall (s) | peak RSS (MB) | normalized chars |
|---|---|---|---|---|---|
| `jpm-2024` as committed | 12,849,180 | 0.591 | 0.591 | 82.1 | 1,213,284 |
| synthetic ~25 MB (2× jpm body, one HTML doc) | 25,697,079 | 1.131 | 1.132 | 137.9 | 2,426,570 |

So an unthrottled loop of maximum-size uploads costs the host on the order of
one CPU-second and ~140 MB of transient RSS per request, forever, plus one
outbound EDGAR fetch per `/api/extract/url` request under the repo's declared
fair-access User-Agent (`EDGAR_UA` names the owner's contact address, so
sustained abuse is attributable to the owner). Zeabur's host is smaller than
the dev machine; these figures are the optimistic edge, not the pessimistic
one.

## b) Global, not per-IP — the decision this ADR exists to record

TD-162's acceptance allowed "a per-IP or global request cap". Per-IP was
rejected, for the same reason TD-158 rejected a per-IP bucket on the paid
path:

1. **The IP is a header this repo cannot test.** Behind Zeabur's proxy the
   client address arrives (if at all) as `X-Forwarded-For` — a header the
   offline gate can neither exercise nor trust, and prior rows declined to
   build on it for exactly that reason. A per-IP limiter verified only
   against direct connections would ship untested on the one topology it
   runs in.
2. **Behind a proxy, per-IP may be shared anyway** — several real viewers can
   present one address, so "per-IP fairness" could throttle a classroom while
   telling each member the limit is theirs alone.
3. **The honest refusal names the real shape.** One process, one bucket, and
   the 429 reason says "shared by ALL callers" — a true statement — instead
   of implying an isolation that does not exist.

The known ceiling, stated rather than hidden: one hammering client exhausts
the shared bucket and degrades every concurrent viewer on the instance until
the window refills. Accepted — the alternative was an unverifiable key — and
bounded: recovery is automatic at the sustained rate (measured live: a 4.5 s
wait restored service), and the operator can raise the limits by env var
without a redeploy. If this ever runs multi-instance, the per-process bucket
multiplies by worker count and an external store becomes the upgrade path;
`limiter.py`'s ponytail note names it.

## c) Sizing, and why a demo viewer never notices

Defaults: burst 20, sustained 30/minute. A human working the inspector runs
single extractions seconds-to-minutes apart; the deep link
(`?fixture=…&run=1`) fires exactly one on page load; the busiest committed
self-check drives no HTTP at all (the eval suite calls the library, not the
server, so the gate cannot trip the limit by construction). Nobody clicks
Extract 20 times inside a refill window by hand — while a loop posting 25 MB
filings exhausts the burst in under a second (measured live: 20 admitted,
request #21 refused after 0.03 s of hammering) and from then on is held to
one request per 2 s, i.e. at most ~34 CPU-seconds/minute of worst-case load
on the figures in §a. The config bounds ([1, 500] and [1, 3000]) keep every
expressible configuration a real limit: the variables can tune the ceiling,
never delete it.

## d) The refusal contract

Same envelope as every other refusal (`_err`), so the UI renders it without a
special case: `doc_status: "failed"`, `warnings[0].code: "rate_limited"`,
HTTP 429, `Retry-After: <whole seconds>` — measured on the wire as
`retry-after: 2` under defaults. The reason string states the burst, the
sustained rate, that the limit is shared, the approximate wait, and that the
deterministic tier stays free — a 429 that read as a paywall would contradict
the door's own published promise that extraction is the free product.

## e) What this deliberately does not do

No per-IP state, no forwarded-header parsing, no concurrency semaphore
(requests admitted inside one burst still run concurrently — the bucket
bounds arrival rate, which bounds sustained CPU, not instantaneous
parallelism), no persistent counters (a restart refills the bucket, like
`_SERVER_BUDGET`), no limit on `/api/source`, `/api/normalized`, `/api/meta`
or the page itself (in-memory reads, no extraction cost), and no change
anywhere in the library or eval pipeline. The PAID path's own protections
(the door, the process budget, `EXTRACT_WINDOW`) are untouched; since D15 a
token holder's extract request passes the free-tier limiter first like
anyone else's, which only tightens that path.
