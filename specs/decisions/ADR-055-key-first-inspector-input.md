# ADR-055 — Put LLM access before filing inputs

Date: 2026-08-30. Status: accepted.

**Ruling**: when configured, the existing LLM access-key verification row appears first inside filing input, before every extraction mode.
**Because**: interviewers should see and verify the paid-tier prerequisite before choosing a filing and starting extraction.
**Enforced by**: `escalation-key-ui-behavior.json` requires `#esc-key-row` to precede `.modes` while retaining the existing verification state-machine probe.

---

The row remains hidden when the server has no configured key. No verification,
storage, request-header, or extraction behavior changes.
