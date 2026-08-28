# 029 — verify the escalation key before extraction (2026-08-28)

## Prompt decision

The owner asked to make the filing-input area less cluttered, shorten the
boilerplate/Markdown/escalation explanations, and let a visitor confirm that an
escalation key is enabled before extracting, preferably with a green check.

## Outcome

The two display-option notes became one sentence each. The key row now has a
Verify action and status. Verification calls the same `gate.paid_path_open`
decision as extraction, through `/api/extract/verify-key`; keeping that route
under the existing limited prefix prevents an unbounded credential oracle. A
key is stored and sent to extraction only after the server accepts it. Editing
the field clears both the remembered value and the green `✓ Enabled` state, and
a remembered key is reverified on load so stale deployment credentials do not
look enabled.

The existing escalation invariant was extended red-first to bind the endpoint,
shared gate/header, verification UI, and verified-only extraction path.
