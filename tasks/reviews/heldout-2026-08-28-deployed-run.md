# Held-out run, 2026-08-28 — locally AND against the deployed inspector

Six cases, run **after** the two new ones' labels were committed
(`72aaeeb`), which is the whole point of the ordering. `tasks/reviews/zeabur_heldout_run.py`
is the instrument for the remote half.

## Result: the two runs agree case for case

| case | local | deployed (`c572a05`) | doc_status | coverage | cost | wall |
|---|---|---|---|---|---|---|
| `aig-2025-heldout` | **FAIL** | **FAIL** | `success` | 0.9689 | $0.00 | 2.3 s |
| `cost-2022-heldout` | PASS | PASS | `success` | 0.9584 | $0.00 | 0.8 s |
| `csco-2016-heldout` | PASS | PASS | `success` | 0.9604 | $0.00 | 1.9 s |
| `mrk-1995-heldout` | PASS | PASS | `success_with_warning` | 0.7593 | $0.00 | 0.5 s |
| `pgr-2023-heldout` | PASS | PASS | `success_with_warning` | 0.8587 | $0.00 | 0.7 s |
| `smci-2025-heldout` | PASS | PASS | `success` | 0.9763 | $0.00 | 1.0 s |

**5/6 = 0.833**, identical verdicts and the identical single failing check on
both sides. **Total spent on the deployment: $0.000000.** None of the six
fires the escalation trigger, which was measured locally *before* any request
was sent — `escalation_enabled=True` and `escalation_token_required=True` on
the deployment, so an unbudgeted trigger would have been a real bill.

### How the remote run is made comparable rather than merely similar

* Same case files, same `expect.checks`, same `eval_check` vocabulary the
  suite uses. Only the extractor is remote.
* The API returns no `normalized_text` — it is served separately so the
  offsets have one source. The runner fetches `/api/normalized/{token}` and
  **verifies its sha256 against the run's `norm_sha256`** before any check
  reads it, per the README's reproduction recipe. So every content check reads
  provably the text the deployment's own offsets index, and the API's
  40,000-char display truncation is irrelevant.
* Check types that re-invoke `extract_items` on a local path (`deterministic`
  on csco-2016 and pgr-2023) are **skipped by name and reported**, because
  running them would measure the LOCAL extractor and report it as a deployment
  fact.

## The finding: AIG's running headers cost item 1 its first page, silently

Predicted at authoring, in the case's own words, before the filing had ever
met the pipeline: *"A heading picker that takes the first match, the last
match, or the most-similar match can each land on a page header rather than on
the section start, and the failure would look like a plausible span rather
than like an error."* That is what happened.

* `is a leading global insurance organization` sits at `normalized_text`
  offset **6,670**. Item 1's span starts at **8,828**.
* Between them: the opening page of Item 1 — `ITEM 1 | Business / Sustaining
  Industry Leadership Momentum / … American International Group, Inc. (NYSE:
  AIG) is a leading global insurance organization. AIG provides insurance
  solutions that help businesses and individuals in over 200 countries…`,
  through to `Balance Sheet Strength and Financial Flexibility with
  approximately $43 billion in shareholders' equity`.
* The span instead opens at the **second** `ITEM 1 | Business` — the page-2
  running header — with `AIG's global team is both results oriented…`.
* **≈2,360 characters of item 1's own opening page are dropped.**

The part that matters is not the size, it is the silence. `doc_status`
**`success`**, `meta.coverage` **0.9689**, item 1 at confidence **0.95**,
`review_required` false, and **no warning carries item 1's code**. Every
validator in the battery is satisfied by a span that begins one page late.
`unattributed_content` does not fire because the lost region is small relative
to a 831,838-char document, and `item_span_near_empty` cannot fire on a
45,767-char span. This is the silent-partial-loss class, and the held-out set
found it unprompted — which is the second time that has happened
(`evals/heldout/README.md`).

## NOT FIXED, deliberately

Acting on this burns the case, and the case is one day old. It is recorded
here as a **ruling-free measurement**: no threshold moved, no fixture moved,
no code shipped, no case authored from it — which under
`evals/heldout/README.md`'s 2026-08-26 amendment is explicitly not influence,
so `aig-2025-heldout` **stays held out and stays unburned**.

Whoever takes it should know the shape before they start: the fix is in
candidate filtering, not in boundary assignment. AIG's first `ITEM 1 |
Business` is immediately preceded by the front-matter table of contents, so
the most likely mechanism is `segment._toc_runs` absorbing the real first
heading into the TOC run and the picker taking the next survivor. That is a
hypothesis from reading the region, not a diagnosis — confirming it means
reading `filter_candidates`' rejection list for this filing, which is
`trace.layer == "candidates"`, `rejected`.
