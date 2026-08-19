#!/usr/bin/env python3
"""evals/bench.py — T13 performance / cost / scalability BENCHMARK.

Dev instrument only, stdlib only. Same shape and same rules as
`evals/oracle.py`: `src/` must NEVER import this module, it changes no
pipeline behaviour, no eval case, and no baseline. Its single `src/` import
is the public entry point `extract_items`, used read-only.

It exists because the analysis report's §3/§4/§5 numbers had no committed
input. `evals/run.py` records a per-case `seconds`, but that is one run per
*case* at 2-decimal precision, with no size, throughput or memory data
attached — enough for metric 9's p50/p95 and nothing else. Every figure this
module prints is written to `evals/report/<stamp>-bench.json` so the report
can cite a file rather than a memory.

Rulings behind the measurement design are in ADR-021; the short version:

- **Unit is the fixture, not the eval case.** Cases re-run the same fixture
  (aapl-2025 appears in several) and some carry no fixture at all, so a
  per-case population double-counts big filings and is not a corpus.
- **Median of N repeats (default 3), single process.** Wall-clock on a shared
  laptop is noisy at the low end; the median of a small odd N is the cheapest
  estimator that ignores one scheduler hiccup. Mean and min are recorded too
  so a reader can see the spread instead of trusting the median.
- **Throughput denominator is RAW BYTES on disk**, not normalized chars. The
  pipeline reads and normalizes the whole file, so bytes-in is the work-in;
  normalized chars are an output. Both are recorded per fixture.
- **Peak RSS is `resource.getrusage(RUSAGE_SELF).ru_maxrss`** — a monotone
  high-water mark for the whole process. Recorded after every fixture in
  descending size order, so the corpus peak is reached by the FIRST (largest)
  filing if and only if peak tracks the largest document. That ordering is
  the measurement: no separate per-filing memory probe is needed.
- **Nothing here is a scored eval check.** A wall-clock assertion in the
  `fast` suite would be flaky on CI hardware and would gate correctness on a
  laptop's thermal state (CLAUDE.md hard rule 2's "do not add a flaky timing
  assertion"). Regressions are read off the committed artifact history.
- **Cost is an estimate and is labelled as one.** No tokenizer is available
  without a new dependency or a network call (checked: neither `anthropic`
  nor `tiktoken` is importable, and neither is in `requirements.txt`), so
  token counts are the chars/4 approximation ADR-020 §d used, carried
  forward with its caveat rather than silently upgraded. NO CODE PATH HERE
  CAN MAKE AN API CALL — the price table is three constants.

CLI:
    python3 -m evals.bench                      # print the tables
    python3 -m evals.bench --json out.json      # also dump the artifact
    python3 -m evals.bench --repeats 5          # more repeats per fixture
    python3 -m evals.bench --self-check         # assert-based proof of the math
"""
import argparse
import ast
import json
import platform
import resource
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.oracle import iter_fixtures  # noqa: E402 — same fixture convention
from evals.run import git_sha  # noqa: E402 — same sha stamping as every report
from src.sec10k.extract import extract_items  # noqa: E402 — the only src/ import; read-only

MB = 1024 * 1024

# ---------------------------------------------------------------- cost basis
# Anthropic first-party API list price, AS OF 2026-06-24, carried forward from
# ADR-020 §d. NOT re-verified at T13: re-checking the published list requires
# a network call, which this milestone is forbidden to make. Treat the date,
# not the number, as the fact. Input price only — a locate-an-item fallback's
# spend is dominated by pushing the whole filing in; output is a span offset.
PRICE_BASIS_DATE = "2026-06-24"
PRICE_BASIS_SOURCE = "ADR-020 §d (Anthropic API list price, not re-verified at T13)"
MODELS = {
    # name: (usd per million input tokens, context window in tokens)
    "claude-opus-5": (5.00, 1_000_000),
    "claude-haiku-4-5": (1.00, 200_000),
}
CHARS_PER_TOKEN = 4  # chars/4 approximation; see module docstring


def est_tokens(chars):
    """chars/4. An ESTIMATE — the name says so, and every caller labels it."""
    return chars / CHARS_PER_TOKEN


def usd(tokens, model):
    return tokens / 1_000_000 * MODELS[model][0]


def peak_rss_mb():
    """ru_maxrss is bytes on macOS/BSD, kilobytes on Linux."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / MB if sys.platform == "darwin" else raw / 1024


# ------------------------------------------------------------- measurement

def time_fixture(path, repeats):
    """(list of seconds, normalized chars, doc_status) for one fixture."""
    times, chars, status = [], 0, None
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = extract_items(path)
        times.append(time.perf_counter() - t0)
        chars, status = len(out["normalized_text"]), out["doc_status"]
    return times, chars, status


def run_all(repeats=3):
    """Per-fixture timings + one batch pass, in a single process.

    Fixtures are measured in DESCENDING raw size so the RSS high-water mark
    recorded after each one shows whether the largest document alone sets the
    peak (see module docstring).
    """
    fixtures = sorted(iter_fixtures(), key=lambda np: np[1].stat().st_size, reverse=True)
    rss_start = peak_rss_mb()
    records = []
    for name, path in fixtures:
        raw = path.stat().st_size
        times, chars, status = time_fixture(path, repeats)
        med = statistics.median(times)
        records.append({
            "fixture": name, "file": str(path.relative_to(ROOT)),
            "raw_bytes": raw, "normalized_chars": chars, "doc_status": status,
            "repeats": repeats,
            "median_s": round(med, 4), "min_s": round(min(times), 4),
            # first repeat is the COLD one (page cache aside, module import is
            # already paid): first_s vs min_s is the warm-up claim, measured
            "first_s": round(times[0], 4),
            "mean_s": round(statistics.fmean(times), 4), "max_s": round(max(times), 4),
            "mb_per_s": round(raw / MB / med, 2) if med else None,
            "peak_rss_mb_after": round(peak_rss_mb(), 1),
        })

    # batch: one sequential pass over the whole corpus, timed as a unit. This
    # is the number §5's projection divides into, not the sum of the medians —
    # a real batch pays per-file open and GC that a median-of-3 loop amortizes.
    t0 = time.perf_counter()
    for _, path in fixtures:
        extract_items(path)
    batch_s = time.perf_counter() - t0

    return records, batch_s, rss_start


def summarize(records, batch_s, rss_start, repeats):
    raw_total = sum(r["raw_bytes"] for r in records)
    chars_total = sum(r["normalized_chars"] for r in records)
    meds = sorted(r["median_s"] for r in records)
    sizes = sorted(r["raw_bytes"] for r in records)
    slowest = max(records, key=lambda r: r["median_s"])
    largest = max(records, key=lambda r: r["raw_bytes"])
    batch_mb_s = raw_total / MB / batch_s

    def pct(vals, p):
        # nearest-rank; n=37 makes interpolation false precision
        return vals[min(len(vals) - 1, max(0, round(p / 100 * len(vals) + 0.5) - 1))]

    perf = {
        "n_fixtures": len(records), "repeats": repeats,
        "raw_bytes_total": raw_total, "normalized_chars_total": chars_total,
        "latency_p50_s": round(pct(meds, 50), 4),
        "latency_p95_s": round(pct(meds, 95), 4),
        "latency_max_s": round(max(meds), 4),
        "slowest_fixture": slowest["fixture"],
        "largest_fixture": largest["fixture"],
        "largest_raw_bytes": largest["raw_bytes"],
        "largest_median_s": largest["median_s"],
        "batch_seconds": round(batch_s, 3),
        "batch_mb_per_s": round(batch_mb_s, 2),
        "median_raw_bytes": pct(sizes, 50),
        "mean_raw_bytes": round(raw_total / len(records)),
        "rss_mb_before_any_extraction": round(rss_start, 1),
        "peak_rss_mb_corpus": round(max(r["peak_rss_mb_after"] for r in records), 1),
        # only meaningful under run_all's descending-size order (ADR-021 §b
        # choice 5); None rather than a wrong number if a caller reorders
        "peak_rss_mb_after_largest_only":
            records[0]["peak_rss_mb_after"] if records[0] is largest else None,
    }

    # §5 projection: batch throughput × mean filing size. Stated in filings,
    # because "MB/s" is not what an operator schedules.
    mean_mb = perf["mean_raw_bytes"] / MB
    per_filing_s = mean_mb / batch_mb_s
    perf["projection"] = {
        "basis": "batch_mb_per_s over the committed corpus, mean filing size",
        "seconds_per_filing_batch_mean": round(per_filing_s, 4),
        "n_1000_seconds": round(per_filing_s * 1000, 1),
        "n_1000_gb_read": round(perf["mean_raw_bytes"] * 1000 / (1024 ** 3), 2),
        "edgar_year_7000_seconds": round(per_filing_s * 7000, 1),
    }

    med_chars = statistics.median(r["normalized_chars"] for r in records)
    cost = {
        "reported_usd_per_filing": 0.0,  # metric 10; no paid dependency exists
        "estimate_method": f"chars/{CHARS_PER_TOKEN} — NOT a tokenizer count",
        "price_basis_date": PRICE_BASIS_DATE,
        "price_basis_source": PRICE_BASIS_SOURCE,
        "models": {k: {"usd_per_mtok_input": v[0], "context_tokens": v[1]}
                   for k, v in MODELS.items()},
        "counterfactual": {},
    }
    for label, chars in (("median_filing", med_chars),
                         ("largest_filing", largest["normalized_chars"]),
                         ("whole_corpus", chars_total)):
        tok = est_tokens(chars)
        cost["counterfactual"][label] = {
            "chars": int(chars), "est_tokens": round(tok),
            "usd_opus_5": round(usd(tok, "claude-opus-5"), 4),
            "usd_haiku_4_5": round(usd(tok, "claude-haiku-4-5"), 4),
            "fits_haiku_context": tok <= MODELS["claude-haiku-4-5"][1],
        }
    cost["counterfactual"]["largest_filing"]["fixture"] = largest["fixture"]
    return perf, cost


# ------------------------------------------------------------------ render

def render(records, perf, cost):
    out = [f"[bench] {perf['n_fixtures']} fixtures, {perf['repeats']} repeats each, "
           f"single process, git={git_sha()}",
           f"        {platform.python_version()} on {platform.platform()}", ""]
    out.append(f"{'fixture':<24}{'raw bytes':>12}{'norm chars':>12}"
               f"{'median s':>10}{'MB/s':>8}{'peak RSS':>10}")
    for r in records:
        out.append(f"{r['fixture']:<24}{r['raw_bytes']:>12,}{r['normalized_chars']:>12,}"
                   f"{r['median_s']:>10.4f}{(r['mb_per_s'] or 0):>8.1f}"
                   f"{r['peak_rss_mb_after']:>10.1f}")
    out += ["",
            f"latency p50 {perf['latency_p50_s']}s  p95 {perf['latency_p95_s']}s  "
            f"max {perf['latency_max_s']}s ({perf['slowest_fixture']})",
            f"batch: {perf['raw_bytes_total'] / MB:.1f} MB in {perf['batch_seconds']}s "
            f"= {perf['batch_mb_per_s']} MB/s",
            f"RSS: {perf['rss_mb_before_any_extraction']} MB before any extraction, "
            f"{perf['peak_rss_mb_after_largest_only']} MB after the largest filing alone, "
            f"{perf['peak_rss_mb_corpus']} MB peak over the corpus",
            f"projection: {perf['projection']['n_1000_seconds']}s for 1,000 filings, "
            f"{perf['projection']['edgar_year_7000_seconds']}s for ~7,000",
            "",
            f"cost: reported ${cost['reported_usd_per_filing']:.2f}/filing (measured, metric 10). "
            f"counterfactual below is an ESTIMATE ({cost['estimate_method']}), "
            f"prices as of {cost['price_basis_date']}:"]
    for label, c in cost["counterfactual"].items():
        fits = "" if c["fits_haiku_context"] else "  [EXCEEDS haiku context]"
        out.append(f"  {label:<16}{c['est_tokens']:>10,} est tok  "
                   f"opus-5 ${c['usd_opus_5']:.4f}  haiku-4.5 ${c['usd_haiku_4_5']:.4f}{fits}")
    return "\n".join(out)


# -------------------------------------------------------------- self-check

def _demo():
    # 1. the estimator: median must ignore one outlier repeat, and the
    # recorded min/mean/max must expose that it was there.
    times = [0.10, 0.11, 0.90]
    assert statistics.median(times) == 0.11
    assert max(times) == 0.90  # spread stays visible in the artifact

    # 2. throughput and projection must be reciprocal — a projection that does
    # not round-trip back to the measured batch time is arithmetic, not data.
    recs = [{"fixture": "big", "file": "f", "raw_bytes": 8 * MB, "normalized_chars": 400_000,
             "doc_status": "success", "repeats": 3, "median_s": 0.4, "min_s": 0.4,
             "mean_s": 0.4, "max_s": 0.4, "mb_per_s": 20.0, "peak_rss_mb_after": 100.0},
            {"fixture": "small", "file": "f", "raw_bytes": 2 * MB, "normalized_chars": 100_000,
             "doc_status": "success", "repeats": 3, "median_s": 0.1, "min_s": 0.1,
             "mean_s": 0.1, "max_s": 0.1, "mb_per_s": 20.0, "peak_rss_mb_after": 100.0}]
    perf, cost = summarize(recs, batch_s=0.5, rss_start=30.0, repeats=3)
    assert perf["batch_mb_per_s"] == 20.0, perf["batch_mb_per_s"]
    # 10 MB / 2 fixtures = 5 MB mean; 5 MB at 20 MB/s = 0.25 s/filing
    assert abs(perf["projection"]["seconds_per_filing_batch_mean"] - 0.25) < 1e-6
    assert abs(perf["projection"]["n_1000_seconds"] - 250.0) < 0.5
    # 1000 filings × 5 MB = 5000 MB ≈ 4.88 GB
    assert abs(perf["projection"]["n_1000_gb_read"] - 4.88) < 0.02

    # 3. peak RSS must be the high-water mark, and the descending-size order
    # must make "the largest filing alone set it" a readable fact.
    assert perf["peak_rss_mb_corpus"] == 100.0
    assert perf["peak_rss_mb_after_largest_only"] == 100.0
    assert perf["rss_mb_before_any_extraction"] == 30.0

    # 4. the cost model must price the corpus, not one filing, and must FLAG a
    # filing that does not fit the cheap tier's context — that flag is the
    # whole of ADR-020 §d consequence 1 and must not be a prose claim.
    assert cost["reported_usd_per_filing"] == 0.0
    corpus = cost["counterfactual"]["whole_corpus"]
    assert corpus["est_tokens"] == 125_000, corpus  # 500,000 chars / 4
    assert abs(corpus["usd_opus_5"] - 0.625) < 1e-9  # 0.125 MTok × $5.00
    assert abs(corpus["usd_haiku_4_5"] - 0.125) < 1e-9
    big = {"est_tokens": est_tokens(1_600_000)}
    assert big["est_tokens"] > MODELS["claude-haiku-4-5"][1]
    assert est_tokens(400_000) <= MODELS["claude-haiku-4-5"][1]
    # and the per-fixture flag itself, computed by summarize:
    assert cost["counterfactual"]["largest_filing"]["fits_haiku_context"] is True

    # 5. no network/API surface exists in this module — the price table is
    # data, and nothing here can be talked into spending money.
    # (parsed, not grepped — a string search would match its own banned list)
    imported = set()
    for node in ast.walk(ast.parse(Path(__file__).read_text())):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {"urllib", "http", "socket", "ssl", "requests",
                           "httpx", "anthropic", "openai"}, imported

    print("[bench self-check] ok")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None, help="also dump the machine-readable artifact")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args(argv[1:])

    if args.self_check:
        _demo()
        return 0

    records, batch_s, rss_start = run_all(args.repeats)
    perf, cost = summarize(records, batch_s, rss_start, args.repeats)
    print(render(records, perf, cost))

    if args.json:
        payload = {"kind": "bench", "git_sha": git_sha(),
                   "python": platform.python_version(), "platform": platform.platform(),
                   "perf": perf, "cost": cost, "records": records}
        Path(args.json).write_text(json.dumps(payload, indent=2, default=str))
        print(f"\n[bench] wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
