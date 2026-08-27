"""Which directories under evals/fixtures/ are filing fixtures — ONE rule (D1).

A fixture directory holds exactly one file, and that file is the filing
(`<name>/filing.htm` or `.txt`, evals/fixtures/README.md). Before D1 that
rule lived only in app.py's request-time `_fixture_file`, while `/api/meta`
listed every directory and `evals/oracle.iter_fixtures()` yielded the largest
non-.md file of every directory — so `repo_hygiene/` (UI/ledger regression
stubs, 14 files) was offered by the inspector dropdown as a dead menu entry
and would have been timed by `evals/bench.py` as a dev fixture. Listing,
request-time resolution and eval discovery now all ask `fixture_file`.

Pure stdlib, no fastapi import, so the repo_hygiene eval adapter and the
eval tooling can import it (ADR-003: the CI jobs install nothing).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "evals" / "fixtures"


def fixture_file(d: Path):
    """The filing of fixture directory `d`, or None when `d` is not a fixture
    directory — i.e. does not hold exactly one file. Subdirectories are not
    counted. ponytail: the suffix is not inspected — `_fixture_file` never
    did, and a lone non-filing file is refused by extract_items on CONTENT
    (`failed`/`unsupported`, measured on a .md and an HTML stub), never served
    as output; add a suffix test HERE, once, if such a directory ever appears."""
    files = [f for f in d.iterdir() if f.is_file()]
    return files[0] if len(files) == 1 else None


def list_fixtures(root: Path = FIXTURES):
    """Sorted names of every fixture directory under `root` — the EVAL corpus.
    D1's one rule, and what `evals.oracle.iter_fixtures` agrees with name for
    name. It is NOT what the deployment offers: see `deployed_fixtures`."""
    return sorted(d.name for d in root.iterdir()
                  if d.is_dir() and fixture_file(d) is not None)


# ADR-036 §h2 / PR #61 R1. Fixtures the DEPLOYED inspector neither lists nor
# resolves, because each one fires D8's `low_item_coverage` and the deployment
# escalates by default — so offering them makes the dropdown a paid button, and
# `?fixture=<name>&run=1` makes it a paid PAGE LOAD, with no click and no
# upload. Measured, not assumed: `tasks/reviews/d11_trigger_scan.py --rates`
# reports `low_item_coverage fires 2/44 -> ['intc-2025', 'xref-index-collapse']`
# (coverage 0.0033 and 0.0303).
#
# This is a WEB restriction only. Both are eval fixtures and stay eval
# fixtures: `list_fixtures` and `iter_fixtures` still see them, so the oracle,
# the bench and every eval case are untouched. D1 said all readers of
# evals/fixtures/ must agree on ONE predicate; they still do, and this is a
# named subtraction layered on top of it rather than a second predicate —
# `fixture-discovery` pins that relationship (deployed = single-file set minus
# this set) instead of the old plain equality.
#
# Hand-maintained HERE and derived in the GATE (PR #61 R15, which closed
# TD-160). `evals/adversarial/deployed-exclusion-derived.json` sweeps every
# fixture through `extract_items` and asserts this set EQUALS the set that
# fires `low_item_coverage`, in both directions — so adding a collapsing
# fixture and forgetting this list reds the `fast` suite instead of silently
# re-opening the hole. It is in `fast` and not `invariant` because the sweep
# costs ~4.6s and the PostToolUse hook runs `invariant` on every edit.
# ponytail: nothing derives this at RUNTIME, so the listing path stays pure
# stdlib and takes no dependency on the extractor. Surviving residue: a tree
# edited and deployed WITHOUT running the gate would still ship a stale set.
# Acceptable since TD-158's door, which makes this the second layer rather
# than the brake; the upgrade path if that ever changes is an import-time
# derivation, at the cost of a full sweep per process start.
DEPLOY_EXCLUDED = frozenset({"intc-2025", "xref-index-collapse"})


def deployed_fixtures(root: Path = FIXTURES):
    """`list_fixtures(root)` minus `DEPLOY_EXCLUDED` — what /api/meta serves,
    what the dropdown offers, and (app.py `_fixture_file`) the ONLY set
    `POST /api/extract/fixture` will resolve.

    Listing and resolution read the same function deliberately. Excluding a
    name from the menu while the resolver still finds it by name is a cosmetic
    fix: the deep link and a hand-written POST both name a fixture directly.
    """
    return [n for n in list_fixtures(root) if n not in DEPLOY_EXCLUDED]
