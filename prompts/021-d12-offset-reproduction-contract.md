# 021 — D12: reproducibility as a contract, because the map is refused (2026-08-26)

Interviewer-feedback gap 3 (postmortem 2026-08-25 §8): *offsets are not
raw-HTML offsets, and nothing tells the consumer.* True by design. ADR-026 §a
refuses a raw-to-normalized offset map, and D5 restated that refusal as a hard
boundary. So the task was written to close the gap **without** the thing that
would obviously close it, which is the only interesting constraint in it.

## The prompt decisions that mattered

- **The refusal is the design, not an obstacle to route around.** The first
  instinct on "make offsets reproducible" is a map, and a map is available in
  approximate form — track a delta through normalization, accept drift at the
  entity and whitespace rewrites. That is worse than none: an approximate
  provenance chain that is right most of the time is a chain nobody can use as
  evidence, which is what provenance is for. The task named the boundary and
  it was not tested. What replaces the map is a contract with three moving
  parts — serve the exact string the offsets index, publish a sha that binds
  that string to the run, write the slicing recipe down — and none of the
  three needs to know anything about the raw bytes.

- **One token, two representations.** The compare pane already caches the raw
  filing under an opaque token (`/api/source/{token}`). The normalized text
  went into the *same* cache entry rather than a second cache, and the reason
  is not tidiness: two caches can hand out a raw filing from one run and a
  normalized text from another, and the consumer's sha check would then fail
  for a reason that has nothing to do with the offsets. One token makes "same
  run" true by construction. The cost is named where it lands — an entry now
  costs roughly twice what it did, the ceiling is 3 × 2 × `MAX_BYTES`.

- **The second copy of the recipe is the endpoint's own docstring, and that is
  the whole reason there is no `docs/api.md`.** The task asked for the recipe
  in "README and API docs". This repo has no API doc and did not need one: the
  service is FastAPI, so the handler's docstring *is* the OpenAPI description
  and it is served at `/docs` by the deployed instance. A consumer with no
  access to this repo — the exact reader the gap names — reads the warning at
  the endpoint they are about to call, not in a markdown file they would have
  to find. A new file would have been a third copy to drift; this is a second
  copy that ships with the code. `check_offset_reproduction_contract` pins
  both copies line by line, whitespace-free, so they cannot drift apart.

- **`norm_sha256` went on the VIEW, not in the envelope.** `extract_items` is
  out of scope for D12, and it stays out: the sha is derived in `build_view`
  from the text it already holds, exactly like every other field there, so no
  second copy exists to drift. It also sits deliberately next to
  `meta.input_sha256`, which pins the *raw file* — the two shas are the
  distinction the recipe exists to teach, and having both on one response is
  what makes step 3 a check rather than a ritual. Verified rather than
  asserted: `evals/snapshot.py` over all 61 committed filings (56 dev + 5
  held-out), before and after, digests byte-identical.

- **What the red-first run actually proved, written down honestly.** The new
  case went red with 17 failures, but only some of them were about this
  change. Two of its halves were green *before* implementation: that
  `normalized_text[start:end]` equals the text the API serves (INV-S2 restated
  at the API boundary) and that the raw-bytes slice differs (a property of
  normalization). They are in the case for the future — the first goes red the
  day the view serves a second copy instead of a slice, the second the day
  normalization becomes the identity and the docs get to stop shouting. The
  half this change made true is the **served** half: before it there was no
  endpoint to perform step 2 against and no sha to perform step 3 with, so the
  recipe was unwritable rather than merely unwritten. A case whose triage note
  claims more than that would be the kind of decoration hard rule 2 exists to
  prevent.

- **The gate cannot issue an HTTP request, and the hand-walk is evidence, not
  a gate.** The eval harness is stdlib-only and importing `app.py` drags
  fastapi into the dependency-free unit job, so the endpoint is pinned by the
  same allow-list shape `check_boilerplate_plumbing` uses: the route
  decorator plus four whole expressions on the wire. That proves the code is
  there; it cannot prove FastAPI binds it. So the recipe was walked end to end
  over real HTTP once, by hand, against `fastapi.testclient.TestClient` —
  aapl-2025, 23 items, 209,227 bytes served, body sha256 and the
  `X-Normalized-SHA256` header both equal to the run's `norm_sha256`, every
  spanned item reproduced from the download, the raw slice differing, a bad
  token returning a plain 404, the recipe present in `/openapi.json`. That
  walk is in the PR's evidence pack and in a debt row, labelled as a
  measurement without a regression gate rather than quietly counted as one.

- **No button.** The obvious next move is a download link in the compare pane.
  It was not built: D12's reader is an API consumer who already holds
  `source.token`, and a button is another hop for the wire allow-list and
  another element for the S3 layout cases to agree about, bought for a reader
  the gap did not name. Logged as debt with the trigger written down — the
  next time the compare pane changes for another reason.
