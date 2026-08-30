# D37 — readable live progress detail

## Material prompt

After PR #93, the flowchart still does not make a long route or a failed verify
easy to understand. Keep the visual flow, but show some plain text that tells
the user what the active stage is doing and whether it is still making visible
progress.

## Outcome

The existing sanitized stage and status drive a fixed human-readable title and
description. The browser displays total elapsed time and time since the last
visible stage/status change. At 30 seconds without a change it explicitly says
the request is still running and may be waiting on the model/provider; a failed
verification is explained while safe finalization continues. No new backend
event or model content is exposed.
