# ADR-054 — DeepSeek V4 Pro is the paid-model price ceiling

Date: 2026-08-30. Status: accepted.

**Ruling**: DeepSeek V4 Pro is the default paid model; GPT-5 Mini is the owner-approved fallback exception despite its higher output list price; Claude Opus 5 remains explicitly disabled.
**Because**: the owner wants a live paid tier after rotating the key, with DeepSeek V4 Pro first and GPT-5 Mini only after it fails; the earlier blanket ceiling would disable that requested fallback.
**Enforced by**: `src/sec10k/llm.py::_enforce_model_policy` and `_demo`, plus `tasks/reviews/2026-08-30-openrouter-price-ceiling.json`.

---

## Context

The owner had required model selection from OpenRouter's popular models to
exclude anything more expensive than DeepSeek V4 Pro. That requirement was not
preserved in this repository or enforced in transport. The shipped ladder
therefore named GPT-5 Mini ($0.25/$2.00 per million input/output tokens) and
Claude Opus 5 ($5/$25), while the 2026-08-30 OpenRouter catalogue listed
`deepseek/deepseek-v4-pro` at $0.569328/$1.138656.

## Decision details

The ladder is `deepseek/deepseek-v4-pro` first, then `openai/gpt-5-mini` over
the wider fallback window. Before cache, budget, credential, or network work,
`llm.call` refuses a model whose input **or** output list price exceeds the
committed DeepSeek V4 Pro record, except the single named GPT-5 Mini fallback.
Claude Opus 5 is explicitly disabled.

DeepSeek has no billed tokenizer sample yet. Its cost proxy is an explicitly
unmeasured conservative bound of 0.25 chars/token (up to four tokens per
normalized-text character), used only on the 60,000-character first rung.
Ordinary billed traffic may replace it with the existing measured-sample rule;
no call is purchased solely for calibration.

The dated OpenRouter response subset is committed at
`tasks/reviews/2026-08-30-openrouter-price-ceiling.json`. A missing or malformed
ceiling refuses all paid work rather than falling back to a constant.

## Enforcement

`src/sec10k/llm.py::_demo` pins the rung order, GPT exception, and Opus refusal.
`token-proxy-bound` pins DeepSeek's conservative unmeasured cost bound. The
invariant and fast suites remain offline.
