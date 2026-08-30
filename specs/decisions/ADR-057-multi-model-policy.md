# ADR-057 — bounded multi-model role policy

Date: 2026-08-30. Status: accepted.

**Ruling**: one central policy assigns Flash evidence and Pro planning; deterministic verification alone publishes.
**Because**: a bounded, inspectable role split prevents a model summary or offset from becoming filing output.
**Enforced by**: D30 policy/transport evals and `src/sec10k/llm.py::_demo`.

---

Evidence uses `deepseek/deepseek-v4-flash-0731`; planning and re-planning use
`deepseek/deepseek-v4-pro`. Each role declares its input cap, completion cap,
reasoning setting and structured-response request. A verified LLM access key is
necessary before any provider call; clean and unverified-key routes make zero
calls.

Evidence is an offset/document-identity packet, never publishable text. A
planner may submit only semantic terminal `{item,status}` decisions. The
deterministic verifier rebinds a semantic omission to the existing
cross-reference entry and incorporation-by-reference to the existing pointer;
the model cannot supply or alter offsets.

Each risky document gets an independent Budget allowing at most one Flash evidence
call and three Pro planning calls, with a $0.10 live ceiling; an optional shared
Budget is charged too. The pre-call guard refuses a worst-case projected charge
that would exceed the ceiling, conservatively including system and user text;
an attempted provider call remains consumed because it may have reached the
provider. Cache keys include model,
prompt, role, completion cap, reasoning setting, response shape and images.
The public trace records role/model/calls/tokens/USD/latency/action/rejection/
next route and cache/provenance state, but never prompt bodies, filing bodies,
or the LLM access key. Filing excerpts are delimited untrusted data; the closed
evidence schema and deterministic supplied-range check discard instructions and
undeclared fields.

**Residual**: Flash evidence is currently limited to cross-reference-residual
routes. Other risky classes retain the existing bounded Pro loop pending their
own evidence packet contract.
