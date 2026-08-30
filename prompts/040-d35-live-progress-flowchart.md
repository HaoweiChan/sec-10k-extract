# D35 — live progress flowchart

## Material prompt

Replace the text-only extraction wait state with a connected flow for filing
preparation, classify, plan, route, verify, and decide. The active node must be
driven by live backend work, final nodes must retain the response routing
outcomes, and polling must disclose no filing text, prompts, credentials, or
model reasoning.

## Outcome

The inspector opts into a process-local asynchronous extraction while existing
API callers remain synchronous. Extraction and routing emit fixed stage names;
the polling endpoint exposes only those names and bounded statuses, and a
separate result endpoint returns the unchanged extraction envelope. The browser
renders native connected nodes, announces the active backend stage through the
existing live region, honors reduced motion, and rebuilds the completed graph
from `routing.stages` so skipped and failed outcomes cannot be invented by the
frontend.
