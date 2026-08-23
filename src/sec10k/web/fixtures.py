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
    """Sorted names of the fixture directories under `root` — what /api/meta
    serves and the inspector dropdown offers."""
    return sorted(d.name for d in root.iterdir()
                  if d.is_dir() and fixture_file(d) is not None)
