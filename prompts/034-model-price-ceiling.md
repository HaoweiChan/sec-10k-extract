# Model price ceiling and Opus shutdown

## Material request

Turn off Claude Opus 5. Preserve the owner's earlier rule that model selection
from OpenRouter's popular models must not use a model more expensive than
DeepSeek V4 Pro; identify why the current configuration did not follow it.

## Outcome — amended by owner 2026-08-30

The repository contained no durable copy or executable enforcement of that
price rule. Claude Opus 5 remains explicitly disabled. After rotating the key,
the owner directed the paid ladder to stay live as DeepSeek V4 Pro first and
GPT-5 Mini fallback. GPT-5 Mini is therefore the single explicit exception to
the DeepSeek price ceiling; no other over-ceiling model is allowed. DeepSeek's
unmeasured tokenizer cost is bounded conservatively without buying a calibration
call.
