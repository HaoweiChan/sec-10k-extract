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
can cite a file rather than a memory. Statistics the report quotes but that
are not raw per-fixture fields (R², the throughput range, the warm-up ratio,
the repeat spread, the RSS plateau index) are computed here into `derived`
rather than in prose, so "cites its inputs" means a field, not an argument.

Rulings behind the measurement design are in ADR-021; the short version:

- **Unit is the fixture, not the eval case.** Cases re-run the same fixture
  (aapl-2025 appears in several) and some carry no fixture at all, so a
  per-case population double-counts big filings and is not a corpus.
- **The timed population is the 37 DEV fixtures only.** The 5 held-out
  filings are not run: this module writes per-fixture `doc_status` and
  `normalized_chars` into a committed artifact, which would publish held-out
  extraction outcomes. Their file SIZES are read (`stat` only, no pipeline
  call) because a byte count leaks no outcome, and the §5 sweep multiplier
  needs a representative real-filing size distribution. See ADR-021 §b8.
- **Median of N repeats (default 3), single process.** Wall-clock on a shared
  laptop is noisy at the low end; the median of a small odd N is the cheapest
  estimator that ignores one scheduler hiccup. Mean, min, max and the FIRST
  (cold) repeat are recorded too so a reader can see the spread instead of
  trusting the median.
- **Throughput denominator is RAW BYTES on disk**, not normalized chars. The
  pipeline reads and normalizes the whole file, so bytes-in is the work-in;
  normalized chars are an output. Both are recorded per fixture.
- **All sizes and rates are BINARY: MiB = 1048576 B, GiB = 1073741824 B.**
  Field names say `mib`/`gib` and `units` restates it, so a reader dividing a
  quoted size by a quoted time reproduces the quoted rate.
- **Peak RSS is `resource.getrusage(RUSAGE_SELF).ru_maxrss`** — a monotone
  high-water mark for the whole process. Fixtures run in descending size
  order, so the corpus peak is reached by the FIRST (largest) filing if and
  only if peak tracks the largest document. That ordering is the measurement.
- **Refusals are separated from processed filings.** `unsupported` and
  `failed` documents return before segmentation/validation
  (`src/sec10k/extract.py`), so they time a different code path; the
  throughput range, spread and R² are computed over PROCESSED fixtures only,
  with the refusals reported alongside rather than dropped.
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
import math
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

MIB = 1024 * 1024
GIB = 1024 ** 3
HELDOUT_DIR = ROOT / "evals" / "heldout" / "fixtures"

# Statuses whose documents return before segmentation (src/sec10k/extract.py):
# a different code path, so they are excluded from the throughput statistics
# and reported separately rather than silently averaged in.
REFUSAL_STATUSES = {"unsupported", "failed"}

# Ratio statistics (warm-up first/fastest, repeat spread) are meaningless below
# about a millisecond: `truncated-download` is 1,200 bytes and runs in ~0.1 ms,
# where one scheduler tick is a 200% "spread". Rows under this floor are
# EXCLUDED from those two statistics only — never from latency, throughput,
# memory or the populations — and the excluded names are published alongside so
# the exclusion is auditable rather than a quiet filter (ADR-021 §b9).
RATIO_FLOOR_S = 0.001

DERIVED_NOTE = ("computed from `records`; the report quotes these, so they are "
                "fields here rather than arithmetic done in prose")

# Fixtures that are NOT real EDGAR documents — self-created copies/mutations of
# other members of this same corpus. Eight are marked SELF-CREATED in
# evals/fixtures/README.md; `items-stripped` has no README row and its
# provenance lives in evals/adversarial/items-stripped-escalation.json. Seven of
# the nine derive from the corpus's SMALLEST real filings, which is why they
# drag the mean filing size down and must not set the §5 sweep multiplier
# (ADR-021 §b8). `run_all` fails loudly if a name here stops existing.
SYNTHETIC = {"toc-titled", "heading-unnumbered", "malformed-html",
             "caps-cover-2016", "fy2021-item9c", "ibr-pointer-first",
             "truncated-download", "spans-transposed", "items-stripped"}

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


def peak_rss_mib():
    """ru_maxrss is bytes on macOS/BSD, kilobytes on Linux."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / MIB if sys.platform == "darwin" else raw / 1024


def pct(vals, p):
    """Nearest-rank percentile of a SORTED list: index ceil(p/100 * n) - 1.

    Textbook nearest-rank rather than interpolation — at n=37 interpolation is
    false precision — and `ceil` rather than `round`, which is banker's in
    Python and would make the index at an exact .5 depend on parity.
    """
    return vals[min(len(vals) - 1, max(0, math.ceil(p / 100 * len(vals)) - 1))]


def _round_r2(rows):
    """R² of median_s on raw_bytes, or None when it is not defined (fewer than
    three rows, or every row the same size — both real cases in `_demo`)."""
    if len(rows) < 3:
        return None
    v = _r2([r["raw_bytes"] for r in rows], [r["median_s"] for r in rows])
    return None if v is None else round(v, 4)


def _r2(xs, ys):
    """Coefficient of determination of the least-squares line y = a*x + b."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if not sxx:
        return None
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    b = my - a * mx
    sst = sum((y - my) ** 2 for y in ys)
    ssr = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    return 1 - ssr / sst if sst else None


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


def make_record(name, file, raw_bytes, times, chars, status, rss_after):
    """One fixture's row. Split out of `run_all` so `_demo` can drive the
    median/throughput arithmetic with a KNOWN list of times — otherwise the
    only test of `median_s` is a test of `statistics.median` (PR #12, R2)."""
    med = statistics.median(times)
    return {
        "fixture": name, "file": file,
        "raw_bytes": raw_bytes, "normalized_chars": chars, "doc_status": status,
        "refused": status in REFUSAL_STATUSES,
        "synthetic": name in SYNTHETIC,
        "repeats": len(times),
        "median_s": round(med, 4), "min_s": round(min(times), 4),
        # first repeat is the COLD one (page cache aside, module import is
        # already paid): first_s vs min_s is the warm-up claim, measured
        "first_s": round(times[0], 4),
        "mean_s": round(statistics.fmean(times), 4), "max_s": round(max(times), 4),
        "mib_per_s": round(raw_bytes / MIB / med, 2) if med else None,
        "peak_rss_mib_after": round(rss_after, 1),
    }


def heldout_sizes():
    """{name: bytes} for the held-out filings — `stat` ONLY.

    The held-out set is quarantined from measurement, but a file's byte count
    is not an extraction outcome and reveals nothing the pipeline decided.
    §5's sweep multiplier needs a real-filing size distribution and the dev
    corpus's is skewed by nine synthetic derivatives (ADR-021 §b8).
    """
    out = {}
    if not HELDOUT_DIR.is_dir():
        return out
    for d in sorted(HELDOUT_DIR.iterdir()):
        if not d.is_dir():
            continue
        files = [f for f in d.iterdir() if f.is_file() and f.suffix.lower() != ".md"]
        if files:
            out[d.name] = max(f.stat().st_size for f in files)
    return out


def run_all(repeats=3):
    """Per-fixture timings + one batch pass, in a single process.

    Fixtures are measured in DESCENDING raw size so the RSS high-water mark
    recorded after each one shows whether the largest document alone sets the
    peak (see module docstring).
    """
    fixtures = sorted(iter_fixtures(), key=lambda np: np[1].stat().st_size, reverse=True)
    names = {n for n, _ in fixtures}
    missing = SYNTHETIC - names
    if missing:  # fail loudly rather than silently misclassify the population
        raise SystemExit(f"[bench] SYNTHETIC names no longer exist as fixtures: {sorted(missing)}")

    rss_start = peak_rss_mib()
    records = []
    for name, path in fixtures:
        times, chars, status = time_fixture(path, repeats)
        records.append(make_record(name, str(path.relative_to(ROOT)),
                                   path.stat().st_size, times, chars, status,
                                   peak_rss_mib()))

    # batch: one sequential pass over the whole corpus, timed as a unit. This
    # is the number §5's projection divides into, not the sum of the medians —
    # a real batch pays per-file open and GC that a median-of-3 loop amortizes.
    t0 = time.perf_counter()
    for _, path in fixtures:
        extract_items(path)
    batch_s = time.perf_counter() - t0

    return records, batch_s, rss_start


# ------------------------------------------------------------- aggregation

def _population(label, sizes, mib_per_s, rate_source):
    mean_bytes = sum(sizes) / len(sizes)
    per_filing = mean_bytes / MIB / mib_per_s
    return label, {
        "n": len(sizes),
        "mean_raw_bytes": round(mean_bytes),
        "mean_mib": round(mean_bytes / MIB, 3),
        "mib_per_s": round(mib_per_s, 2),
        "rate_source": rate_source,
        "seconds_per_filing": round(per_filing, 4),
        "n_1000_seconds": round(per_filing * 1000, 1),
        "n_1000_gib_read": round(mean_bytes * 1000 / GIB, 2),
        "edgar_year_7000_seconds": round(per_filing * 7000, 1),
    }


def summarize(records, batch_s, rss_start, repeats, heldout=None):
    heldout = heldout or {}
    raw_total = sum(r["raw_bytes"] for r in records)
    chars_total = sum(r["normalized_chars"] for r in records)
    meds = sorted(r["median_s"] for r in records)
    sizes = sorted(r["raw_bytes"] for r in records)
    slowest = max(records, key=lambda r: r["median_s"])
    largest = max(records, key=lambda r: r["raw_bytes"])
    batch_mib_s = raw_total / MIB / batch_s
    processed = [r for r in records if not r["refused"]]

    perf = {
        "n_fixtures": len(records), "repeats": repeats,
        "raw_bytes_total": raw_total, "raw_mib_total": round(raw_total / MIB, 2),
        "normalized_chars_total": chars_total,
        "latency_p50_s": round(pct(meds, 50), 4),
        "latency_p95_s": round(pct(meds, 95), 4),
        "latency_max_s": round(max(meds), 4),
        "slowest_fixture": slowest["fixture"],
        "largest_fixture": largest["fixture"],
        "largest_raw_bytes": largest["raw_bytes"],
        "largest_mib": round(largest["raw_bytes"] / MIB, 2),
        "largest_median_s": largest["median_s"],
        "batch_seconds": round(batch_s, 3),
        "batch_mib_per_s": round(batch_mib_s, 2),
        "median_raw_bytes": pct(sizes, 50),
        "mean_raw_bytes": round(raw_total / len(records)),
        "rss_mib_before_any_extraction": round(rss_start, 1),
        "peak_rss_mib_corpus": round(max(r["peak_rss_mib_after"] for r in records), 1),
        # only meaningful under run_all's descending-size order (ADR-021 §b
        # choice 5); None rather than a wrong number if a caller reorders
        "peak_rss_mib_after_largest_only":
            records[0]["peak_rss_mib_after"] if records[0] is largest else None,
    }

    # ---- statistics the report quotes, computed here rather than in prose
    corpus_peak = perf["peak_rss_mib_corpus"]
    plateau_i = next((i for i in range(len(records))
                      if all(abs(corpus_peak - r["peak_rss_mib_after"]) <= 0.5
                             for r in records[i:])), None)
    ratio_pop = [r for r in records if r["median_s"] >= RATIO_FLOOR_S and r["min_s"] > 0]
    ratios = [r["first_s"] / r["min_s"] for r in ratio_pop]
    spreads = [(r["max_s"] - r["min_s"]) / r["median_s"] for r in ratio_pop]
    tp = sorted(r["mib_per_s"] for r in processed if r["mib_per_s"] is not None)
    perf["derived"] = {
        "note": DERIVED_NOTE,
        "sum_of_medians_s": round(sum(r["median_s"] for r in records), 3),
        "processed_n": len(processed),
        "refused_n": len(records) - len(processed),
        "refused_fixtures": [r["fixture"] for r in records if r["refused"]],
        "processed_mib_per_s_min": tp[0] if tp else None,
        "processed_mib_per_s_max": tp[-1] if tp else None,
        "processed_mib_per_s_median": round(statistics.median(tp), 2) if tp else None,
        "processed_mib_per_s_spread": round(tp[-1] / tp[0], 2) if tp and tp[0] else None,
        "processed_size_vs_time_r2": _round_r2(processed),
        "ratio_floor_s": RATIO_FLOOR_S,
        "ratio_population_n": len(ratio_pop),
        "ratio_excluded_fixtures": [r["fixture"] for r in records
                                    if r["median_s"] < RATIO_FLOOR_S],
        "warmup_first_over_min_median": round(statistics.median(ratios), 4) if ratios else None,
        "warmup_first_over_min_max": round(max(ratios), 4) if ratios else None,
        "repeat_spread_median": round(statistics.median(spreads), 4) if spreads else None,
        "repeat_spread_max": round(max(spreads), 4) if spreads else None,
        "rss_plateau_first_index": plateau_i,
        "rss_plateau_first_fixture": records[plateau_i]["fixture"] if plateau_i is not None else None,
        "rss_plateau_first_value_mib": records[plateau_i]["peak_rss_mib_after"] if plateau_i is not None else None,
    }

    # ---- §5 projections, one entry per candidate population (ADR-021 §b8).
    # Held-out filings are SIZED but never timed, so they borrow the real-dev
    # rate; `rate_source` says so on every row.
    real_dev = [r for r in records if not r["synthetic"]]
    real_dev_bytes = sum(r["raw_bytes"] for r in real_dev)
    real_dev_secs = sum(r["median_s"] for r in real_dev)
    real_dev_rate = real_dev_bytes / MIB / real_dev_secs if real_dev_secs else batch_mib_s
    pops = dict(p for p in (
        _population("all_dev_fixtures", [r["raw_bytes"] for r in records],
                    batch_mib_s, f"measured: batch pass over all {len(records)} timed fixtures"),
        _population("real_edgar_dev", [r["raw_bytes"] for r in real_dev],
                    real_dev_rate, "measured: sum(bytes)/sum(medians) over these fixtures"),
        _population("real_edgar_committed",
                    [r["raw_bytes"] for r in real_dev] + list(heldout.values()),
                    real_dev_rate,
                    "sizes include held-out filings (stat only, never timed); "
                    "rate borrowed from real_edgar_dev"),
    ))
    perf["populations"] = pops
    perf["projection_of_record"] = "real_edgar_committed"
    perf["heldout_sizes_bytes"] = heldout

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


UNITS = {
    "mib": "1 MiB = 1048576 bytes (binary, not 1e6)",
    "gib": "1 GiB = 1073741824 bytes",
    "*_mib_per_s": "MiB per second, raw bytes on disk / median seconds",
    "*_s": "seconds, wall clock, time.perf_counter",
    "usd_*": "US dollars, ESTIMATE via chars/4 at the stated price_basis_date",
}


# ------------------------------------------------------------------ render

def render(records, perf, cost):
    d = perf["derived"]
    out = [f"[bench] {perf['n_fixtures']} dev fixtures, {perf['repeats']} repeats each, "
           f"single process, git={git_sha()}",
           f"        {platform.python_version()} on {platform.platform()}",
           "        sizes and rates are BINARY (MiB = 1048576 B)", ""]
    out.append(f"{'fixture':<24}{'raw bytes':>12}{'norm chars':>12}"
               f"{'median s':>10}{'MiB/s':>8}{'peak RSS':>10}  flags")
    for r in records:
        flags = ",".join(f for f, on in (("refused", r["refused"]),
                                          ("synthetic", r["synthetic"])) if on)
        out.append(f"{r['fixture']:<24}{r['raw_bytes']:>12,}{r['normalized_chars']:>12,}"
                   f"{r['median_s']:>10.4f}{(r['mib_per_s'] or 0):>8.1f}"
                   f"{r['peak_rss_mib_after']:>10.1f}  {flags}")
    out += ["",
            f"latency p50 {perf['latency_p50_s']}s  p95 {perf['latency_p95_s']}s  "
            f"max {perf['latency_max_s']}s ({perf['slowest_fixture']})",
            f"batch: {perf['raw_mib_total']} MiB in {perf['batch_seconds']}s "
            f"= {perf['batch_mib_per_s']} MiB/s (sum of medians "
            f"{d['sum_of_medians_s']}s)",
            f"processed ({d['processed_n']}): {d['processed_mib_per_s_min']}"
            f"–{d['processed_mib_per_s_max']} MiB/s, median "
            f"{d['processed_mib_per_s_median']}, spread "
            f"{d['processed_mib_per_s_spread']}x, size-vs-time R^2 "
            f"{d['processed_size_vs_time_r2']}",
            f"refused ({d['refused_n']}, different code path): "
            f"{', '.join(d['refused_fixtures'])}",
            f"warm-up first/fastest (n={d['ratio_population_n']}, "
            f">={d['ratio_floor_s']}s): median {d['warmup_first_over_min_median']}, "
            f"max {d['warmup_first_over_min_max']}; "
            f"repeat spread median {d['repeat_spread_median']}, max {d['repeat_spread_max']}; "
            f"excluded as sub-ms: {', '.join(d['ratio_excluded_fixtures']) or 'none'}",
            f"RSS: {perf['rss_mib_before_any_extraction']} MiB baseline, "
            f"{perf['peak_rss_mib_after_largest_only']} MiB after the largest filing alone, "
            f"{perf['peak_rss_mib_corpus']} MiB corpus peak; within 0.5 MiB of peak "
            f"from index {d['rss_plateau_first_index']} "
            f"({d['rss_plateau_first_fixture']}, {d['rss_plateau_first_value_mib']} MiB) onward",
            ""]
    out.append("projections (of record: " + perf["projection_of_record"] + "):")
    for label, p in perf["populations"].items():
        mark = "*" if label == perf["projection_of_record"] else " "
        out.append(f" {mark}{label:<24} n={p['n']:<3} mean={p['mean_mib']:>6.3f} MiB "
                   f"@ {p['mib_per_s']:>5.2f} MiB/s -> 1,000 in {p['n_1000_seconds']:>6.1f}s, "
                   f"7,000 in {p['edgar_year_7000_seconds'] / 60:>5.1f} min")
    out += ["",
            f"cost: reported ${cost['reported_usd_per_filing']:.2f}/filing (measured, metric 10). "
            f"counterfactual below is an ESTIMATE ({cost['estimate_method']}), "
            f"prices as of {cost['price_basis_date']}:"]
    for label, c in cost["counterfactual"].items():
        fits = "" if c["fits_haiku_context"] else "  [EXCEEDS haiku context]"
        out.append(f"  {label:<16}{c['est_tokens']:>10,} est tok  "
                   f"opus-5 ${c['usd_opus_5']:.4f}  haiku-4.5 ${c['usd_haiku_4_5']:.4f}{fits}")
    return "\n".join(out)


# -------------------------------------------------------------- self-check
#
# THE RULE THIS SECTION ENFORCES (PR #12 R18, round 2): **no field this module
# publishes may be without an assertion pinning its value.** R2 caught two
# unpinned statistics in round 1; the round-1 fix pinned those two and left
# five more free, which is a correction that relocates the gap instead of
# closing it (ADR-020 §h3's shape). Pinning statistics one at a time cannot
# terminate, so the check is inverted: `summarize` is run over ONE golden
# corpus and its ENTIRE `perf` block is compared against a hand-derived
# expected dict. A new published field therefore fails `--self-check` until
# someone computes its expected value by hand and adds it here. See ADR-021
# §b10.
#
# The corpus is built so that no statistic lands on a degenerate value that
# would hide a mutation: the percentile indices are fractional before `ceil`,
# the throughput spread is not 1.0, R² is not 1.0, a refused row carries the
# extreme rate, a sub-millisecond row would poison the ratio statistics, the
# largest row is first, and one row is synthetic.

def _rec(name, mib, times, chars=1000, status="success", rss=100.0):
    return make_record(name, "f", int(mib * MIB), times, chars, status, rss)


# Five fixtures, descending raw size, exactly as `run_all` emits them.
# Names are real corpus names because `refused`/`synthetic` are derived from
# status and from membership of SYNTHETIC, not passed in.
def _golden_corpus():
    return [
        #      name                 MiB      times                     chars   status
        _rec("cat-2023",            3,     [0.6],                     300000, rss=50.0),
        _rec("nvda-2024",           2,     [0.24, 0.20, 0.20],        200000, rss=99.6),
        _rec("ko-1997",             1,     [0.11, 0.10, 0.10],        100000, rss=100.0),
        _rec("aapl-2026-10q",       1,     [0.01],                     10000, "unsupported", 100.0),
        make_record("truncated-download", "f", 1048, [0.0004, 0.0001, 0.0001],
                    100, "failed", 100.0),
    ]


# Hand-derived, not blessed from a run. The load-bearing derivations, so a
# reviewer can re-check them without executing anything:
#   percentiles  n=5, sorted medians [0.0001, 0.01, 0.1, 0.2, 0.6];
#                p50 index ceil(2.5)-1 = 2 -> 0.1  (floor would give 0.01)
#                p95 index ceil(4.75)-1 = 4 -> 0.6 (floor would give 0.2)
#   processed    rows 0-2 only; rates 3/0.6=5, 2/0.2=10, 1/0.1=10
#                -> min 5, max 10, median 10, spread 2.0
#                (with the two refusals in: max 100, spread 20 — R18b)
#   R²           x = 1,2,3 MiB against y = 0.1,0.2,0.6: mx=2, my=0.3,
#                Sxx=2, Sxy=0.5, a=0.25, b=-0.2; residuals 0.05,-0.1,0.05
#                -> SSR 0.015, SST 0.14, R² = 1 - 0.015/0.14 = 0.892857
#   ratios       floor excludes only the 0.0001 s row; first/min per row
#                1.0, 1.2, 1.1, 1.0 -> median 1.05, max 1.2
#                spreads 0.0, 0.2, 0.1, 0.0 -> median 0.05, max 0.2
#   plateau      peak 100.0; first index whose tail stays within 0.5 is 1
#                (99.6), which is deliberately NOT the peak value
#   populations  total 7,341,080 B = 7.000999 MiB over batch_s 1.0 -> 7.0 MiB/s
#                real (non-synthetic) rows 0-3: 7,340,032 B = 7.0 MiB over
#                sum-of-medians 0.91 s -> 7.6923 MiB/s, mean 1.75 MiB
#                committed adds the 4 MiB held-out size: mean 11/5 = 2.2 MiB,
#                2.2 / 7.6923 = 0.286 s per filing -> 286 s / 2002 s
_GOLDEN_HELDOUT = {"spg-2019": 4 * MIB}
_GOLDEN_PERF = {
    "n_fixtures": 5, "repeats": 3,
    "raw_bytes_total": 7341080, "raw_mib_total": 7.0,
    "normalized_chars_total": 610100,
    "latency_p50_s": 0.1, "latency_p95_s": 0.6, "latency_max_s": 0.6,
    "slowest_fixture": "cat-2023",
    "largest_fixture": "cat-2023", "largest_raw_bytes": 3145728,
    "largest_mib": 3.0, "largest_median_s": 0.6,
    "batch_seconds": 1.0, "batch_mib_per_s": 7.0,
    "median_raw_bytes": 1048576, "mean_raw_bytes": 1468216,
    "rss_mib_before_any_extraction": 20.0,
    "peak_rss_mib_corpus": 100.0,
    "peak_rss_mib_after_largest_only": 50.0,
    "derived": {
        "note": DERIVED_NOTE,
        "sum_of_medians_s": 0.91,
        "processed_n": 3, "refused_n": 2,
        "refused_fixtures": ["aapl-2026-10q", "truncated-download"],
        "processed_mib_per_s_min": 5.0,
        "processed_mib_per_s_max": 10.0,
        "processed_mib_per_s_median": 10.0,
        "processed_mib_per_s_spread": 2.0,
        "processed_size_vs_time_r2": 0.8929,
        "ratio_floor_s": 0.001,
        "ratio_population_n": 4,
        "ratio_excluded_fixtures": ["truncated-download"],
        "warmup_first_over_min_median": 1.05,
        "warmup_first_over_min_max": 1.2,
        "repeat_spread_median": 0.05,
        "repeat_spread_max": 0.2,
        "rss_plateau_first_index": 1,
        "rss_plateau_first_fixture": "nvda-2024",
        "rss_plateau_first_value_mib": 99.6,
    },
    "populations": {
        "all_dev_fixtures": {
            "n": 5, "mean_raw_bytes": 1468216, "mean_mib": 1.4,
            "mib_per_s": 7.0,
            "rate_source": "measured: batch pass over all 5 timed fixtures",
            "seconds_per_filing": 0.2, "n_1000_seconds": 200.0,
            "n_1000_gib_read": 1.37, "edgar_year_7000_seconds": 1400.0,
        },
        "real_edgar_dev": {
            "n": 4, "mean_raw_bytes": 1835008, "mean_mib": 1.75,
            "mib_per_s": 7.69,
            "rate_source": "measured: sum(bytes)/sum(medians) over these fixtures",
            "seconds_per_filing": 0.2275, "n_1000_seconds": 227.5,
            "n_1000_gib_read": 1.71, "edgar_year_7000_seconds": 1592.5,
        },
        "real_edgar_committed": {
            "n": 5, "mean_raw_bytes": 2306867, "mean_mib": 2.2,
            "mib_per_s": 7.69,
            "rate_source": "sizes include held-out filings (stat only, never timed); "
                           "rate borrowed from real_edgar_dev",
            "seconds_per_filing": 0.286, "n_1000_seconds": 286.0,
            "n_1000_gib_read": 2.15, "edgar_year_7000_seconds": 2002.0,
        },
    },
    "projection_of_record": "real_edgar_committed",
    "heldout_sizes_bytes": _GOLDEN_HELDOUT,
}


def _diff(got, want, path=""):
    """Every leaf that differs, so a red self-check names the field."""
    out = []
    if isinstance(want, dict) and isinstance(got, dict):
        for k in sorted(set(want) | set(got)):
            out += _diff(got.get(k, "<MISSING>"), want.get(k, "<UNASSERTED FIELD>"),
                         f"{path}.{k}" if path else k)
    elif got != want:
        out.append(f"  {path}: got {got!r}, expected {want!r}")
    return out


def _demo():
    # 1. THE ESTIMATOR, through the code path `run_all` uses. Asserting
    # `statistics.median([...]) == x` tests the stdlib; this drives
    # `make_record`, where `med` is actually computed. Five distinct times so
    # median, first, min and max are four different values.
    r = _rec("x", 2.0, [0.30, 0.11, 0.12, 0.90, 0.13])
    assert r["median_s"] == 0.13, r          # not first (0.30), not min, not max
    assert r["first_s"] == 0.30, r           # cold repeat, NOT the fastest
    assert r["min_s"] == 0.11 and r["max_s"] == 0.90, r
    assert r["mib_per_s"] == round(2.0 / 0.13, 2), r   # throughput uses the MEDIAN
    assert r["repeats"] == 5 and r["refused"] is False and r["synthetic"] is False
    # refusal + synthetic classification must come off the data, not a guess
    assert _rec("toc-titled", 1.0, [0.1])["synthetic"] is True
    assert _rec("q", 1.0, [0.1], status="unsupported")["refused"] is True
    assert _rec("q", 1.0, [0.1], status="failed")["refused"] is True
    assert _rec("q", 1.0, [0.1], status="ambiguous")["refused"] is False

    # 2. THE WHOLE PUBLISHED SURFACE, against hand-derived values. This is the
    # assertion that makes the rule at the top of this section enforceable
    # rather than aspirational: it fails on a wrong value AND on a new field
    # nobody has computed an expected value for.
    perf, _ = summarize(_golden_corpus(), batch_s=1.0, rss_start=20.0, repeats=3,
                        heldout=dict(_GOLDEN_HELDOUT))
    d = _diff(perf, _GOLDEN_PERF)
    assert not d, "summarize() drifted from the hand-derived golden values:\n" + "\n".join(d)

    # 2b. The same corpus with the largest row NOT first. `run_all` always
    # emits descending size, so `peak_rss_mib_after_largest_only` is only
    # meaningful under that order; out of order it must be None rather than
    # silently reporting some other fixture's high-water mark. (The golden
    # corpus alone cannot catch a dropped guard — its largest row is first.)
    shuffled = _golden_corpus()
    shuffled.append(shuffled.pop(0))
    sperf, _ = summarize(shuffled, batch_s=1.0, rss_start=20.0, repeats=3)
    assert sperf["peak_rss_mib_after_largest_only"] is None, sperf
    # everything order-independent must be untouched by the reorder
    assert sperf["latency_p50_s"] == _GOLDEN_PERF["latency_p50_s"]
    assert sperf["peak_rss_mib_corpus"] == _GOLDEN_PERF["peak_rss_mib_corpus"]

    # 2c. Plateau index, other boundary. The golden corpus's plateau is at
    # index 1, so it pins a scan that always answers 0; this pins the reverse —
    # a corpus already at its peak on the first fixture must report 0, not 1.
    flat = [_rec(f"f{i}", float(4 - i), [0.1 * (4 - i)], rss=100.0) for i in range(4)]
    assert summarize(flat, 1.0, 1.0, 1)[0]["derived"]["rss_plateau_first_index"] == 0

    # 3. R² must also read 1.0 when the relationship really is perfect —
    # the golden corpus pins the 0.8929 side, this pins the other, so a
    # constant-returning `_r2` cannot satisfy both.
    perfect = [_rec(f"p{i}", float(i), [i / 10]) for i in (1, 2, 3, 4)]
    pperf, _ = summarize(perfect, batch_s=1.0, rss_start=1.0, repeats=1)
    assert pperf["derived"]["processed_size_vs_time_r2"] == 1.0, pperf["derived"]
    assert pperf["derived"]["processed_mib_per_s_spread"] == 1.0, pperf["derived"]

    # 4. THE COST MODEL must price the corpus, not one filing, and must FLAG a
    # filing that does not fit the cheap tier's context — that flag is the
    # whole of ADR-020 §d consequence 1 and must not be a prose claim.
    _, cost = summarize([_rec("a", 1.0, [0.1], chars=500_000)],
                        batch_s=1.0, rss_start=1.0, repeats=1)
    assert cost["reported_usd_per_filing"] == 0.0
    corpus = cost["counterfactual"]["whole_corpus"]
    assert corpus["est_tokens"] == 125_000, corpus          # 500,000 chars / 4
    assert abs(corpus["usd_opus_5"] - 0.625) < 1e-9         # 0.125 MTok x $5.00
    assert abs(corpus["usd_haiku_4_5"] - 0.125) < 1e-9
    assert corpus["fits_haiku_context"] is True
    _, big = summarize([_rec("b", 1.0, [0.1], chars=1_600_000)],
                       batch_s=1.0, rss_start=1.0, repeats=1)
    assert big["counterfactual"]["whole_corpus"]["fits_haiku_context"] is False

    # 5. No network/API surface exists in this module — the price table is
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
    perf, cost = summarize(records, batch_s, rss_start, args.repeats, heldout_sizes())
    print(render(records, perf, cost))

    if args.json:
        payload = {"kind": "bench", "git_sha": git_sha(),
                   "python": platform.python_version(), "platform": platform.platform(),
                   "units": UNITS, "perf": perf, "cost": cost, "records": records}
        Path(args.json).write_text(json.dumps(payload, indent=2, default=str))
        print(f"\n[bench] wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
