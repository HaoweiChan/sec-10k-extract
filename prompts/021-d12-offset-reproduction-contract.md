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

## Round 1 repair (PR #54) — the pin named the variable, not the value

The reviewer falsified the central claim of the whole PR with a one-character
mutation. `WIRE_NORMALIZED` pinned `return Response(content=norm, …)` and
`hashlib.sha256(norm).hexdigest()`, both of which mention `norm` and neither of
which says where `norm` comes from — so `norm = hit[1]` made the endpoint serve
the **raw filing** under a matching sha header, and the case that exists to
make exactly that impossible stayed green, 60/60. The check's own comment
called it impossible. That is worse than an unpinned behaviour: it is a pin
that reads as coverage.

Three things are worth keeping from it:

- **An allow-list pin is only as strong as the narrowest expression it names.**
  `check_boilerplate_plumbing`'s comment already says a question can always be
  answered by a broken hop; the same is true one level down — an expression can
  be present while the value flowing through it is wrong. The repair pins the
  *binding* as well as the *use*, on both hops, and adds `NORM_BINDERS`, which
  requires each of the two functions to bind `norm` exactly once, because
  `norm = hit[2]` followed by `norm = hit[1]` satisfies every pin and wins at
  runtime. That is UNIQUE_UI's argument, in Python.

- **The repair had the same class of defect inside it, for one run.**
  `NORM_BINDERS` was first keyed on the route decorator; the end-of-function
  scan stops at the next `\ndef `, which is the handler's own `def` line, so it
  measured an empty slice and reported "0 bindings" for every possible body.
  It was red — for the wrong reason, and it would have been green the moment
  anyone wrote the expected count as 0. Caught only because the mutation's red
  output was read instead of counted. The reason is now written into the
  constant.

- **The prose was right and the code under it was wrong** (R2). README's worked
  snippet asserted `slice == item["text"]`, false for any item over
  `DISPLAY_MAX`, with a parenthetical one line below correctly saying to
  compare prefixes. aapl-2025 item 1 is 16,053 characters, so the printed
  example passed; item 1A of the same fixture is 68,162 and raises. A snippet a
  reader will paste is not documentation, it is code, and it is now pinned in
  its correct form.

## Round 2 repair (PR #54) — the same overclaim, one level down, twice

Round 1 fixed R1 and then made two smaller versions of the same mistake:
claiming in committed prose that a guard enforces more than it does. Round 2
found both. The pattern is worth naming, because it is the failure mode of
this whole style of checking and it recurred inside the repair for it.

- **R4 — a regex guard is always one spelling behind.** `NORM_BINDERS` was
  `^\s*norm\s*=[^=]`, which counts a rebind only when it starts a physical
  line. `norm = hit[2]; norm = hit[1]` and `norm, _unused = hit[1], 0` are both
  valid Python, both serve the raw filing, and both were green — the R1 defect
  restored, under a guard four committed artifacts described as "binds `norm`
  exactly once". Patching the pattern would have bought the next spelling.
  Replaced by an `ast` walk counting `Name(id="norm", ctx=Store)` inside the
  function node, which is not a better pattern but the property itself: every
  binding form Python has is one Store node. It also deleted the text-window
  scan and, with it, the off-by-one that shipped in round 1.

- **R5 — a check implied by the line above it has no falsification power.**
  Round 1 added `slice_[:len(it["text"])] != it["text"]` to back the claim that
  README's snippet was "executed, not just spell-checked", plus a guard
  requiring a truncated item so the execution could not be vacuous. But
  `build_view` sets `it["text"] = slice_[:DISPLAY_MAX]`, so that comparison is
  the same expression as the `slice_[:DISPLAY_MAX] != it["text"]` line directly
  above it — it could never fail alone, and the vacuity guard therefore guarded
  nothing. Both deleted; the four artifacts now say R2 is protected by a text
  pin, full stop. The lazier fix was also the honest one: `eval`-ing a README
  line to manufacture falsification power would have been machinery built to
  make a sentence true.

The rule both findings point at: **a check's claim must be measured the same
way its subject is.** R1, R4 and R5 were all found by mutating the thing the
claim was about and watching the gate stay green — the only test of a check
that is worth anything, and cheap enough that it should have been run on the
repair as readily as on the code.
