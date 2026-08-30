"""10-K item-level extraction. Contract: specs/001-sec10k-contract.md.

Layers 1-9 and 11 are real: selection, normalization, candidates, TOC filter,
boundaries, status, label-free validation, confidence, assembly. Layer 10 — the
model-based slow path ADR-020 ruled NOT JUSTIFIED in 2026-08-19 — now exists as
a TRIGGERED tier behind `escalate=True` (ADR-036, which supersedes ADR-020).
It is off by default, it runs only when the D8 document-level signal fires, and
on a dev corpus where that signal fires on 2 of 38 real filings the default
cost stays exactly $0.
`success` is deliberately hard to earn — it requires the validator battery to
find nothing at all.
"""
import hashlib
import re
import time
from pathlib import Path

from src.sec10k.boilerplate import find_chrome
from src.sec10k.normalize import ACCEPTED_FORMS, COLLAPSE_FLOOR, select_and_normalize
from src.sec10k.segment import (
    assign_boundaries, classify, collective_pointer, expected_items,
    filter_candidates, footnote_pointer, item_label, find_candidates,
)
from src.sec10k import xref
from src.sec10k.validate import AMBIGUOUS_CODES, STRICT_SIM, coverage, score, validate

# 0.9 and not 0.8.1: ADR-035 (D8) adds a REQUIRED item field
# (`review_required`) and a required non-refusal `meta` key (`coverage`), which
# ADR-029/032/033's optional envelope keys were not — an old consumer's item
# loop is unaffected, but a schema check written against 0.8.x is not.
#
# 0.9.1 and not 1.0: ADR-036 (D11) adds `routing`, which is opt-in and so an
# ADR-026-class OPTIONAL key — absent unless the caller asked — plus two
# `method` values no default-flag run can emit. Nothing an existing consumer
# reads changes shape. This constant IS the one default-envelope field that
# moves; `evals/snapshot.py`, whose FIELDS predate D11, reports every other
# field identical (ADR-036 §f).
VERSION = "0.9.1-d11"  # meta.extractor_version — audits compare across runs

# ADR-042 §b. General Instruction J is the ABS instruction and nothing else is
# phrased this way; the phrase does not occur in any of the 46 other fixtures.
ABS_INSTRUCTION_J_RE = re.compile(
    r"(?i)general\s+instruction\s+J\s+(to|of)\s+form\s*10-?K")


def _item(code, cand, status, period_end=None, footnote=None):
    part, title = item_label(code, period_end)
    if cand is None:
        # no heading anywhere: the entry exists because INV-S4 says every
        # expected item must appear with some status (contract, `method`)
        return {"item": code, "part": part, "title": title,
                "heading_text": None, "start": None, "end": None,
                "status": status,
                "method": "status_keyword", "evidence": {}}
    return {
        "item": code, "part": part, "title": title,
        "heading_text": cand["heading_text"], "start": cand["start"],
        "end": cand["end"], "status": status,
        # ADR-027 §b: `method` names the heading-match tier by the SAME cut
        # that pays BASE_STRICT vs BASE_WEAK, so the envelope can no longer
        # publish "strict" on a heading the score calls weak (SD-1)
        "method": "heading_strict" if cand["similarity"] >= STRICT_SIM else "heading_lenient",
        "evidence": {"title_similarity": cand["similarity"],
                     "chars": cand["end"] - cand["start"],
                     # ADR-031: the footnote that resolved a marked, empty
                     # heading to IBR — offsets into normalized_text, the
                     # pointer sentence a human reads; the item's own span stays
                     # the heading line (INV-S1 forbids pointing it into the
                     # item that holds the footnote). Key absent otherwise.
                     **({"footnote": {"start": footnote[0], "end": footnote[1]}}
                        if footnote else {})},
    }


def _promote_item_headings(blocks, tables, items):
    """ADR-032 §b3: the block a span-carrying item opens with IS the heading
    the segmenter identified (`verbatim` asserts the span opens with
    `heading_text`), so it becomes a level-2 `heading` carrying the item
    code — a paragraph block, or a table block with exactly one visible row
    (jnj-2016 / spatz-2014 / wmt-2010 typeset `Item N.` | `TITLE` as a
    two-cell table). A longer table the heading merely opens (bac-2006 item
    7's MD&A index, 36 visible rows) stays a table: promoting it would swallow
    the index into an `##`. Measured 2026-08-23 over the 624 span items of
    the 34 HTML/iXBRL fixtures: 488 paragraph blocks equal to heading_text,
    135 one-row tables, 1 multi-row table."""
    at = {b["start"]: b for b in blocks}
    for it in items:
        b = at.get(it["start"])
        if b is None:
            continue
        if b["kind"] == "table":
            rows = [r for r in tables[b["table"]]["rows"] if any(c[0] < c[1] for c in r)]
            if len(rows) != 1:
                continue
            del b["table"]
        elif b["kind"] != "paragraph":
            continue
        b.pop("strong", None)
        b.update(kind="heading", level=2, item=it["item"])


def _envelope(doc_status, text="", items=None, warnings=None, meta=None,
              trace=None, t0=None, boilerplate=None, tables=None, blocks=None,
              images=None, routing=None):
    env = {
        "normalized_text": text,
        "doc_status": doc_status,
        "warnings": warnings or [],
        "meta": {"extractor_version": VERSION, **(meta or {})},
        "trace": trace or [],
        "timings": {"total_ms": round((time.monotonic() - t0) * 1000, 1) if t0 else 0},
        # ADR-036 §g: still {0, 0, 0.0} on every path where no tier ran, which
        # is every default-flag run. When the ladder does run this carries the
        # routing record's own totals, so the contract's cost field and the
        # routing record can never disagree — one is derived from the other.
        "cost": dict(routing["cost"]) if routing else
                {"llm_calls": 0, "tokens": 0, "usd": 0.0},
        "items": items or [],
    }
    if boilerplate is not None:
        # ADR-026: the key exists only when the caller asked. `[]` means "asked,
        # found none" and is not the same answer as the key being absent.
        env["boilerplate"] = boilerplate
    if tables is not None:
        env["tables"] = tables   # ADR-029: same rule — present only when asked
    if blocks is not None:
        env["blocks"] = blocks   # ADR-032: same rule again
    if images is not None:
        env["images"] = images   # ADR-033: and again
    if routing is not None:
        env["routing"] = routing  # ADR-036: and again — opt-in, never default
    return env


def extract_items(path, exclude_boilerplate=False, tables=False, blocks=False,
                  images=False, escalate=False, budget=None, source_url=None):
    """Extract items from a 10-K filing.

    Returns {"normalized_text": str, "doc_status": str, "items": [...], ...}
    per specs/001-sec10k-contract.md.

    `exclude_boilerplate=True` adds ONE key, `boilerplate` — the chrome runs
    found in `normalized_text` (ADR-026). It is a pure annotation: nothing else
    in the envelope moves, so INV-S2 offsets mean the same thing either way.

    `tables=True` adds ONE key, `tables` — every HTML <table> as offsets into
    `normalized_text` (ADR-029), the same annotation-not-edit rule. The
    Markdown view is derived by `src/sec10k/tables.to_markdown`, never stored.

    `blocks=True` adds `blocks` (and implies `tables`) — the document's block
    structure as offsets into `normalized_text` (ADR-032): headings,
    paragraphs, list items, tables (pointing at the `tables` record), or one
    `pre` block for a txt-era filing. The whole-document / per-item Markdown
    view is derived by `src/sec10k/markdown.to_markdown`, never stored.

    `images=True` adds ONE key, `images` — every HTML <img> as
    `{offset, src, alt, width, height}`, the offset into `normalized_text`
    (ADR-033). Same annotation-not-edit rule; the image BYTES are not
    fetched, by ruling (ADR-033 §c).

    `escalate=True` adds ONE key, `routing` — the tiered slow path's record
    (ADR-036): whether the trigger fired, which tiers were attempted, each
    tier's outcome and cost, and which items a tier resolved. Unlike the four
    flags above this one is NOT a pure annotation: when the trigger fires AND a
    tier's answer survives `escalate.verify`, the resolved items' spans,
    `method` and `heading_text` move, with the deterministic answer preserved
    under `evidence.deterministic`. When the trigger does NOT fire — 50 of 53
    dev fixtures, and 36 of the 38 real EDGAR filings among them — nothing
    moves, nothing is spent, and the only difference from a default run is the
    presence of the `routing` key itself. The exception is `intc-2025`, the
    collapsed real filing the live exam burned to the dev side: this line said
    "every real EDGAR filing in the set" until 2026-08-28 (PR #61 R21), eight
    lines below a module header the same commit had already corrected.

    THE SLOW PATH REFUSES RATHER THAN DEGRADES. With no `OPENROUTER_API_KEY` in
    the environment, or with a spent `budget`, a fired trigger produces a
    `routing` record whose tier outcome is `unavailable` plus an
    `escalation_unavailable` warning. It never invents an item, never quietly
    falls back to the deterministic answer without saying so, and never reports
    a cost it did not incur.

    `budget` is an `llm.Budget` (calls and dollars, both enforced before each
    call). Default: at most 2 calls and $1.00 for one document.
    """
    t0 = time.monotonic()
    raw_bytes = Path(path).read_bytes()
    sha = hashlib.sha256(raw_bytes).hexdigest()
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # 1990s filings carry Word's cp1252 smart quotes as raw bytes, not
        # entities; errors="replace" would silently mangle them to U+FFFD.
        # All 13 committed fixtures are pure ASCII — this is for held-out input.
        raw = raw_bytes.decode("cp1252", errors="replace")

    trace = [{"layer": "acquisition", "path": str(path), "bytes": len(raw_bytes)}]
    text, meta, warnings, tabs, blks, imgs = select_and_normalize(
        raw, tables=tables, blocks=blocks, images=images or escalate)
    emit_imgs = imgs if images else None
    meta["input_sha256"] = sha
    trace.append({"layer": "select+normalize", **meta})
    # ADR-026 layer 3b, opt-in. Computed here, off the normalized text, and
    # then carried untouched to whichever envelope this run returns — including
    # the `failed`/`unsupported` refusals, which still have readable text a
    # caller who asked for chrome is entitled to. Nothing downstream reads it.
    chrome = find_chrome(text) if exclude_boilerplate else None

    # ORDER IS THE CONTRACT'S, NOT A PREFERENCE (001-sec10k-contract, envelope
    # rules): collapse is tested BEFORE form identity. A truncated download
    # normalizes to nothing AND sniffs no form, and the two statuses are
    # different diagnoses to a user — "we could not read this" sends them to
    # re-download, "this is not a 10-K" sends them to check the wrong thing.
    if len(text) < COLLAPSE_FLOOR:
        warnings.append({
            "code": "normalization_collapse", "item": None,
            "message": f"{len(raw)} raw chars normalized to {len(text)}"})
        return _envelope("failed", text, meta=meta, warnings=warnings,
                         trace=trace, t0=t0, boilerplate=chrome, tables=tabs,
                         blocks=blks, images=emit_imgs)

    # ADR-042 §b: an asset-backed issuer's annual report. Legally a 10-K, and
    # `sniff_form` correctly says so — but General Instruction J to Form 10-K
    # REPLACES Items 1-16 of Regulation S-K with Items 1112(b)/1114/1117/1119/
    # 1122/1123 of Regulation AB, a taxonomy this pipeline does not model. Left
    # to the ordinary path, Bridgecrest Trust 2024-1 returned
    # `success_with_warning` over 18 `extracted` items, including a 96-char
    # "Item 7 MD&A" at 0.80 — a plausible-looking item set over a document we
    # cannot identify, which is the one thing the README promises never
    # happens. The document names the instruction itself, twice, so this reads
    # the filing's own words rather than inferring from the filer's name.
    # Tested BEFORE the form check for the same reason collapse is: "this is
    # not the kind of 10-K we read" is a different diagnosis from "this is not
    # a 10-K", and only the first is true here.
    if ABS_INSTRUCTION_J_RE.search(text):
        warnings.append({
            "code": "abs_general_instruction_j", "item": None,
            "message": "asset-backed issuer report under General Instruction J "
                       "to Form 10-K — its items are Regulation AB 1112-1123, "
                       "not Regulation S-K Items 1-16"})
        return _envelope("unsupported", text, meta=meta, warnings=warnings,
                         trace=trace, t0=t0, boilerplate=chrome, tables=tabs,
                         blocks=blks, images=emit_imgs)

    if meta["form_type"] not in ACCEPTED_FORMS:
        # refusal, not a best-effort parse (contract v2 envelope rules)
        found = meta["form_type"] or "none"
        warnings.append({"code": "unsupported_form", "item": None,
                         "message": f"not an accepted 10-K form (detected: {found})"})
        return _envelope("unsupported", text, meta=meta, warnings=warnings,
                         trace=trace, t0=t0, boilerplate=chrome, tables=tabs,
                         blocks=blks, images=emit_imgs)

    expected = expected_items(meta.get("period_end"))
    # taxonomy era is the item set the filing's date implies, not its file
    # format: a 2002 HTML filing is as legacy as a 1994 txt one
    meta["taxonomy_era"] = "modern" if "1A" in expected else "legacy"
    cands = find_candidates(text, expected)
    survivors, manifest, rejected = filter_candidates(cands)
    accepted = assign_boundaries(survivors, expected, text)
    meta["toc_manifest"] = manifest
    trace.append({"layer": "candidates", "found": len(cands),
                  "survived": len(survivors), "toc_manifest": manifest,
                  "rejected": [{"item": r["item"], "start": r["start"],
                                "why": r["why"]} for r in rejected]})

    # ADR-042 §c: a Part addressed collectively, with no per-item heading.
    # Read BEFORE statuses are assigned, off the codes segmentation left
    # unassigned, so it can only ever upgrade a `missing` — it cannot displace
    # a heading the filing actually carries.
    collective = collective_pointer(text, [c for c in expected if c not in accepted])
    if collective:
        trace.append({"layer": "collective_pointer",
                      "items": sorted(collective), "at": min(collective.values())[0]})

    items = []
    for code in expected:
        c = accepted.get(code)
        body = text[c["heading_end"]:c["end"]] if c else ""
        status = classify(code, body, c is not None)
        foot = None
        if c is not None and status == "extracted":
            # ADR-031 (D4): a marked heading over an empty body, resolved by a
            # footnote elsewhere that names this item and an external document
            foot = footnote_pointer(code, c["heading_text"], body, text)
            if foot:
                status = "incorporated_by_reference"
        it = _item(code, c, status, meta.get("period_end"), footnote=foot)
        if c is None and code in collective:
            # null offsets stay null — INV-S1 forbids five items sharing the
            # pointer sentence's range, so the sentence travels as evidence
            it["status"] = "incorporated_by_reference"
            lo, hi = collective[code]
            it["evidence"]["collective_reference"] = {"start": lo, "end": hi}
        items.append(it)
    trace.append({"layer": "status",
                  "counts": {s: sum(1 for i in items if i["status"] == s)
                             for s in {i["status"] for i in items}}})

    for i in items:
        if i["status"] == "missing":
            warnings.append({"code": "expected_item_missing", "item": i["item"],
                             "message": f"item {i['item']} expected in this era, no heading found"})
    if meta.get("period_end") is None:
        warnings.append({"code": "period_end_unknown", "item": None,
                         "message": "no period of report found; expected item set is a guess"})

    # ADR-035 §d: the coverage figure is PUBLISHED, not only thresholded — it
    # is the number interviewer feedback found undisclosed at the API level
    # (postmortem §8 gap 1), and `unattributed_content`'s message is not it
    # (that one is preamble + tail, ADR-019 §d). Non-refusal path only, beside
    # `toc_manifest` and `taxonomy_era`, which are normative in `meta` the same
    # way. 4 dp: enough to separate near-identical derivative fixtures
    # (sandston-2021 0.7352 vs fy2021-item9c 0.7354) without float noise.
    meta["coverage"] = round(coverage(text, items), 4)

    # layer 8: label-free validation, then layer 9 confidence from what it found
    findings = validate(text, items, accepted, manifest)
    prior_findings = findings
    warnings += findings
    trace.append({"layer": "validate",
                  "checks_fired": [w["code"] for w in findings]})

    # ADR-042 §d: the cross-reference index. Entered on the SAME document-level
    # signals ADR-036's paid tier uses, and deliberately before it: on the one
    # filing where that tier was ever measured (intc-2025, $0.997760, ADR-036
    # §k) it resolved nothing, and this resolves the same filing
    # deterministically at $0 by reading the index's own page references
    # against the filing's own pagination.
    #
    # Spans do NOT move for an item that already has one — Intel's page ranges
    # overlap and nest, so no assignment of them can satisfy INV-S1, and what
    # the index points at travels as evidence instead (the shape ADR-031 chose
    # for the footnote case). The ONE exception is a filing where segmentation
    # found no heading at ALL (Citi FY2025: 1,163,303 chars, coverage 0.0000,
    # 23 items `missing`, because its index writes `1. Business` with no
    # "Item"). There the index's own rows become the spans: rows partition the
    # index region, so they are ordered and disjoint by construction, which is
    # exactly what INV-S1 asks of them, and the result is the same shape Intel
    # already produces rather than a second kind of answer.
    COLLAPSE_CODES = ("low_item_coverage", "expected_items_mostly_missing")
    promoted = set()
    if any(w["code"] in COLLAPSE_CODES for w in findings):
        ix, entries, refs = xref.resolve(text, expected)
        if refs:
            pointers = xref.pointer_entries(text, ix, entries,
                                            {i["item"]: i["part"] for i in items})
            total_collapse = all(i["start"] is None for i in items)
            for i in items:
                code = i["item"]
                if code in entries:
                    a, b = entries[code]
                    i["evidence"]["cross_reference_entry"] = {"start": a, "end": b}
                if code in pointers:
                    i["evidence"]["cross_reference_pointer"] = pointers[code]
                if code in refs:
                    i["evidence"]["cross_reference"] = refs[code]
                if total_collapse and code in entries and code in refs:
                    a, b = entries[code]
                    head = text[a:b].strip().split("\n")[0].strip()
                    i.update(start=a, end=b, status="extracted",
                             heading_text=head, method="cross_reference_index")
                    promoted.add(code)
            reached = sum(r["end"] - r["start"]
                          for rs in refs.values() for r in rs)
            warnings.append({
                "code": "cross_reference_index", "item": None,
                "message": f"the filing answers its items through a "
                           f"cross-reference index at {ix[0]}; "
                           f"{len(refs)} items' page references resolved to "
                           f"{reached:,} chars of content published under "
                           f"evidence.cross_reference"
                           + (f", and {len(promoted)} items whose heading the "
                              f"filing never writes take that index's own rows "
                              f"as their spans" if promoted else "")})
            trace.append({"layer": "cross_reference", "index": list(ix),
                          "resolved": sorted(refs), "promoted": sorted(promoted),
                          "chars": reached})
    if promoted:
        # spans moved, so everything derived from them is stale — the same
        # re-derivation the escalation tier does below, and for the same reason
        warnings = [w for w in warnings
                    if not (w["code"] == "expected_item_missing"
                            and w["item"] in promoted)]
        accepted = {**accepted,
                    **{c: {"heading_end": next(i["start"] + len(i["heading_text"])
                                               for i in items if i["item"] == c)}
                       for c in promoted}}
        meta["coverage"] = round(coverage(text, items), 4)
        findings = validate(text, items, accepted, manifest)
        warnings = [w for w in warnings if w not in prior_findings] + findings
        prior_findings = findings
        trace.append({"layer": "validate", "after": "cross_reference",
                      "checks_fired": [w["code"] for w in findings]})

    # layer 10 (ADR-036, D11): the tiered slow path. Opt-in, and even then it
    # reads the warnings layer 8 just produced and returns immediately unless
    # the D8 document-level code is among them. This is the ONLY place in the
    # pipeline that can spend money, and on every dev fixture but one it spends
    # nothing at all.
    routing = None
    if escalate:
        from src.sec10k.escalate import route   # NOT at module scope: keeping
        # the import here is what makes `python3 -m evals.run` load no network
        # module at all (ADR-036 §h, pinned by repo_hygiene's escalation_seam)
        routing, extra = route(text, items, warnings, budget=budget, images=imgs,
                               source_url=source_url, raw=raw_bytes)
        warnings += extra
        trace.append({"layer": "escalate", "trigger": routing["trigger"]["fired"],
                      "tiers": [f"{t['tier']}:{t['outcome']}" for t in routing["tiers"]],
                      "resolved": routing["resolved"],
                      "dispositions": routing.get("dispositions", []),
                      "routing": routing["trigger"], "cost": routing["cost"]})
        if routing["resolved"] or routing.get("dispositions"):
            # spans moved, so EVERY number derived from them is now stale.
            # Re-deriving is not optional politeness: `envelope_shape`
            # recomputes `meta.coverage` from the items the envelope publishes
            # and refuses an envelope where the two disagree.
            resolved = set(routing["resolved"])
            by_code = {i["item"]: i for i in items}
            # a resolved span has no heading line — its whole extent is body,
            # so the fingerprint's heading cut moves with it. The key stays in
            # `accepted` so check 1 does not read the item as unresolved.
            accepted = {c: ({**v, "heading_end": by_code[c]["start"]}
                            if c in resolved else v)
                        for c, v in accepted.items()}
            findings = validate(text, items, accepted, manifest)
            warnings = [w for w in warnings if w not in prior_findings] + findings
            trace.append({"layer": "validate", "after": "escalate",
                          "checks_fired": [w["code"] for w in findings]})

    if blks is not None:
        _promote_item_headings(blks, tabs, items)

    # doc_status ladder (contract v2, fixed order). Only validators in
    # AMBIGUOUS_CODES may reach `ambiguous`, except ADR-045's resolved
    # cross-reference alternative content qualifies low coverage alone. The
    # warning remains published; the other ambiguity codes still escalate.
    # Decided BEFORE scoring: an `ambiguous` verdict caps every item
    # (ADR-027 §a) before a document-level warning reaches an item's number.
    extracted = [i for i in items if i["status"] == "extracted"]
    codes = {w["code"] for w in warnings}
    if "cross_reference_index" in codes:
        codes.discard("low_item_coverage")
    ambiguous = not extracted or bool(codes & set(AMBIGUOUS_CODES))
    graph_routes = {(x.get("item"), x.get("next_route"))
                    for x in ((routing or {}).get("graph", {}).get("items", []))}
    for i in items:
        # A short primary index row remains a document diagnostic, but once
        # the verifier attached local cross-reference content it is no longer
        # an unresolved item failure. Keep that resolution on the evidence so
        # callers can distinguish it from a validator that never fired.
        resolved = [w for w in warnings
                    if (w.get("code") == "item_span_near_empty"
                        and w.get("item") == i["item"]
                        and (i.get("evidence") or {}).get("cross_reference"))]
        resolved_ids = {id(w) for w in resolved}
        i["confidence"], i["evidence"] = score(
            i, [w for w in warnings if id(w) not in resolved_ids], doc_ambiguous=ambiguous)
        if resolved:
            i["evidence"]["resolved_warnings"] = [w["code"] for w in resolved]
        # ADR-035 §e: the consumer-facing half. A validator that fires on an
        # item must not leave that item reading like any other `extracted` one
        # (postmortem §8 gap 2) — `status` still answers "what did the filing
        # do with this item", so the review signal is its own boolean rather
        # than a fifth status. Derived from the same item-targeted hits that
        # already move the confidence, so the two can never disagree.
        i["review_required"] = (bool(i["evidence"]["warnings"])
                                or (i["item"], "review_required") in graph_routes)
    if ambiguous:
        doc_status = "ambiguous"
    elif warnings:
        doc_status = "success_with_warning"
    else:
        doc_status = "success"
    # ADR-036 §g: recomputed here rather than only above, because a resolved
    # tier moves spans and `meta.coverage` must describe the items this
    # envelope actually publishes. On every non-escalated run this is the same
    # arithmetic over the same spans and the same value.
    meta["coverage"] = round(coverage(text, items), 4)
    return _envelope(doc_status, text, items=items, meta=meta,
                     warnings=warnings, trace=trace, t0=t0, boilerplate=chrome,
                     tables=tabs, blocks=blks, images=emit_imgs, routing=routing)
