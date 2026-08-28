# Prompt records

The assignment reviewers read this folder. One layer:

- `YYYY-MM-DD-<topic>.md` (this directory) — curated records, written after
  each meaningful chunk of work. Only interactions that materially changed
  architecture, evaluation methodology, failure handling, an output contract,
  or another major implementation decision (CLAUDE.md rule 6). Routine coding,
  formatting and trivial debugging are deliberately not curated.

There is deliberately no `raw/` layer. An earlier SessionEnd hook dumped every
user prompt here verbatim, which is the "raw transcript dump" rule 6 forbids —
the hook was unregistered and its one surviving dump removed on 2026-08-28
(the owner decision it held, "R25–R31 as enumerated debt", was already carried
where such decisions belong, in `tasks/DONE.md`). Session exhaust is not a
prompt record; a curated file with a correction chain is.

## Curated file format

The valuable artifact is not the final polished prompt — it is the correction
chain. Every curated file ends with:

```
## Assumption → Eval contradiction → Correction
- Assumed: <what we believed when writing the prompt/code>
- Eval said: <the case/run that contradicted it, with case id>
- Corrected: <what changed — prompt, code, invariant, or ADR>
```

One chain entry per real correction. If a curated file has no chain entries,
it probably wasn't worth curating.
