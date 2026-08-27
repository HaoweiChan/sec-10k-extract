# Response cache — committed on purpose, empty on purpose

`evals/cache/llm/<sha256>.json` holds one file per API response, keyed on
`sha256(PROMPT_VERSION, model, system, user, max_tokens)`
(`src/sec10k/llm._cache_key`). `llm.call` checks it **before** the budget and
before the credential, so re-running a live eval costs $0 and needs no key at
all — cost-discipline rule 2, and the reason a future `full` suite can be
reproducible offline (rule 4).

**It is committed rather than `.gitignore`d** so that the responses a paid run
produced travel with the repo that cites their numbers. It is empty today
because no call has ever been made: `OPENROUTER_API_KEY` is unset in the
development environment and ADR-036 §k records the whole live half as UNRUN.

`PROMPT_VERSION` is part of the key, so a reworded prompt cannot be answered
from an old response — bump it in `src/sec10k/llm.py` whenever a prompt in
`src/sec10k/escalate.py` changes.

The provider is OpenRouter (ADR-036 §h1); `PROMPT_VERSION` is
`d11.2-openrouter`, so nothing cached under the previous Anthropic
transport can be served for a request made through this one.

Override the location with `SEC10K_LLM_CACHE` (the module self-check does, into
a temp directory, so it never writes here).
