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
- **The timed population is the DEV fixtures only** — every directory
  `evals.oracle.iter_fixtures` yields (one filing file each, D1); 37 at the
  artifacts of record, counted rather than quoted since. The 5 held-out
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
import re
import resource
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.oracle import iter_fixtures  # noqa: E402 — same fixture convention
from evals.run import git_sha  # noqa: E402 — same sha stamping as every report
from src.sec10k.extract import extract_items  # noqa: E402 — read-only src/ imports: the
from src.sec10k.web.fixtures import fixture_file  # noqa: E402 — extractor + the fixture rule (D1)

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
# other members of this same corpus. Twelve are marked SELF-CREATED in
# evals/fixtures/README.md; `items-stripped` has no README row and its
# provenance lives in evals/adversarial/items-stripped-escalation.json. Seven of
# the first nine derive from the corpus's SMALLEST real filings, which is why they
# drag the mean filing size down and must not set the §5 sweep multiplier
# (ADR-021 §b8). `run_all` fails loudly if a name here stops existing.
SYNTHETIC = {"toc-titled", "heading-unnumbered", "malformed-html",
             "caps-cover-2016", "fy2021-item9c", "ibr-pointer-first",
             "truncated-download", "spans-transposed", "items-stripped",
             "ibr-security-holders", "comma-cover-2016", "amended-cover-2021",
             "spaced-letter-heading"}

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
    corpus's is skewed by the `SYNTHETIC` set's self-created derivatives
    (ADR-021 §b8) — named there, not counted here, so a new fixture cannot
    re-stale this sentence (PR #28 R2).
    """
    out = {}
    if not HELDOUT_DIR.is_dir():
        return out
    for d in sorted(HELDOUT_DIR.iterdir()):
        f = fixture_file(d) if d.is_dir() else None  # same rule as iter_fixtures (D1)
        if f is not None:
            out[d.name] = f.stat().st_size
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
    def _in_ratio_pop(r):
        # ONE predicate, used for both the population and the published
        # exclusion list, so `ratio_population_n + len(excluded) == n_fixtures`
        # holds by construction rather than by coincidence (PR #12 R24).
        return r["median_s"] >= RATIO_FLOOR_S and r["min_s"] > 0

    ratio_pop = [r for r in records if _in_ratio_pop(r)]
    ratio_excluded = [r["fixture"] for r in records if not _in_ratio_pop(r)]
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
        "ratio_excluded_fixtures": ratio_excluded,
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


def build_payload(records, perf, cost):
    """Everything the artifact publishes. One place, so `_demo` can assert the
    top-level key set and a new published block cannot appear unnoticed."""
    return {"kind": "bench", "git_sha": git_sha(),
            "python": platform.python_version(), "platform": platform.platform(),
            "units": UNITS, "perf": perf, "cost": cost, "records": records}


# every top-level key of the artifact; `_demo` pins this list
PAYLOAD_KEYS = ["cost", "git_sha", "kind", "perf", "platform", "python", "records", "units"]

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



# ------------------------------------------------------- doc cross-check
#
# Why this exists (PR #12 R20). Three rounds running, prose kept quoting
# per-fixture numbers read out of a SUPERSEDED artifact while the surrounding
# text named the current one; twice the fix was "sweep the docs", and twice
# the sweep was asserted rather than performed. A claim that needs a human to
# re-read six files is not a claim, so this makes the narrow, recurring case
# mechanical: **every decimal number the docs print next to a backticked
# fixture name must be that fixture's number in the artifact of record.**
#
# Scope, stated honestly because overclaiming a check is this milestone's
# signature error: it covers FIXTURE-ATTRIBUTED decimals only. Aggregate
# figures (p95, batch throughput, the sweep projections) are not attributed to
# a fixture name and are NOT covered — they are pinned by `--self-check` in the
# artifact and swept by hand in the prose. Integers are skipped: item codes,
# years and counts share their shape.
DOC_FILES = ["specs/decisions/ADR-021-benchmark-instrument.md",
             "docs/analysis-report.md", "README.md", "tasks/TODO.md",
             "prompts/009-t13-perf-cost-scalability.md"]

# Numbers that are deliberately NOT the artifact of record's: historical values
# quoted inside a correction, a withdrawal or a v3-vs-now table. Every entry is
# a conscious citation of a superseded measurement — adding one is the point at
# which someone has to decide "this is history", not a way to silence a stale
# number. (fixture, literal) pairs.
DOC_ALLOW = {
    # (file, fixture, literal): a decimal that sits next to a fixture name but
    # is NOT that fixture's measurement in the artifact of record. Every entry
    # is a deliberate decision, which is the point — adding one is where
    # someone has to say "this is history / this is a different quantity",
    # rather than a way to quiet a stale number.
    #
    # -- historical values, quoted inside their own correction note
    ("ADR-021-benchmark-instrument.md", "ksb-2007", "42.8"),   # §c, R5's withdrawn first-draft maximum
    ("ADR-021-benchmark-instrument.md", "ksb-2007", "3.5"),    # §d1, R16's irreproducible observation
    ("ADR-021-benchmark-instrument.md", "ksb-2007", "2.5"),    # §d1, same
    ("ADR-021-benchmark-instrument.md", "ksb-2007", "44.1"),   # Verification, the stale figure choice 12 found
    ("analysis-report.md", "msft-2013", "6.6"),                # §3 v3-vs-now row; 6.6 is tgt-2002's
    ("analysis-report.md", "msft-2013", "33.8"),               # §3 v3-vs-now row; 33.8 is ibm-1997's
    # prompts/009 round-3 entry quotes the five stale values R20 found, as the
    # evidence for the finding. They are the superseded run's, deliberately.
    ("009-t13-perf-cost-scalability.md", "intc-2002", "6.8"),
    ("009-t13-perf-cost-scalability.md", "gs-2002", "7.1"),
    ("009-t13-perf-cost-scalability.md", "msft-2013", "7.5"),
    ("009-t13-perf-cost-scalability.md", "ibm-1997", "33.7"),
    ("009-t13-perf-cost-scalability.md", "ko-1997", "26.8"),
    # -- a number belonging to the NEXT fixture named on the same line
    ("ADR-021-benchmark-instrument.md", "bac-2006", "0.55"),   # §c table: max 0.55 s is jpm-2024's
    # -- cross-run ranges (§3.1): min-max over the three committed clean runs,
    #    so by construction not the single run of record's value
    ("analysis-report.md", "bac-2006", "0.500"),
    ("analysis-report.md", "bac-2006", "0.521"),
    ("analysis-report.md", "jpm-2024", "0.541"),
    ("analysis-report.md", "jpm-2024", "0.557"),
    # -- a different quantity that happens to sit beside a fixture name
    ("analysis-report.md", "truncated-download", "0.1"),       # 0.1 ms, i.e. median_s 0.0001 s
    ("TODO.md", "truncated-download", "0.1"),                  # same, in the ledger
    ("TODO.md", "axp-2008", "0.1264"),                         # ADR-019 oracle gap fraction, not a bench value
    ("TODO.md", "cvx-2015", "0.95"),                           # a confidence value, not a bench value
}

DOC_WINDOW = 60  # chars after the closing backtick, same line only


def _fixture_values(art):
    """Every number a doc could legitimately print for a given fixture."""
    out = {}
    for r in art["records"]:
        vals = [r["raw_bytes"], r["raw_bytes"] / MIB, r["normalized_chars"],
                r["median_s"], r["min_s"], r["max_s"], r["first_s"], r["mean_s"],
                r["peak_rss_mib_after"]]
        if r["mib_per_s"] is not None:
            vals.append(r["mib_per_s"])
        out[r["fixture"]] = vals
    return out


def check_docs(artifact_path):
    art = json.loads(Path(artifact_path).read_text())
    vals = _fixture_values(art)
    names = sorted(vals, key=len, reverse=True)
    name_re = re.compile("`(" + "|".join(re.escape(n) for n in names) + ")`")
    num_re = re.compile(r"(?<![\w.])(\d+\.\d+)(?![\d])")

    bad, checked = [], 0
    for rel in DOC_FILES:
        path = ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text()
        hits = list(name_re.finditer(text))
        for i, m in enumerate(hits):
            fixture = m.group(1)
            # "attributed" = same line, within WINDOW chars, and before the next
            # backticked fixture name. Wider than that and every aggregate in
            # the paragraph gets swept in; narrower and table rows are missed.
            eol = text.find("\n", m.end())
            stop = min(m.end() + DOC_WINDOW,
                       eol if eol != -1 else len(text),
                       hits[i + 1].start() if i + 1 < len(hits) else len(text))
            for nm in num_re.finditer(text, m.end(), stop):
                lit = nm.group(1)
                after = text[nm.end():nm.end() + 2]
                if text[nm.start() - 1:nm.start()] == "$" or after[:1] in ("%", "\u00d7") \
                        or after[:2] in ("x ", "\u00d7 "):
                    continue      # a ratio, a percentage or a price, not a measurement
                if (Path(rel).name, fixture, lit) in DOC_ALLOW:
                    continue
                checked += 1
                places = len(lit.split(".")[1])
                target = float(lit)
                if not any(round(v, places) == target for v in vals[fixture]):
                    line = text.count("\n", 0, nm.start()) + 1
                    bad.append(f"  {rel}:{line}  `{fixture}` {lit} "
                               f"is not a value of that fixture in {Path(artifact_path).name}")
    print(f"[bench] doc cross-check against {Path(artifact_path).name}: "
          f"{checked} fixture-attributed decimals checked, {len(bad)} unmatched")
    for b in bad:
        print(b)
    return 1 if bad else 0


# -------------------------------------------------------------- self-check
#
# THE RULE THIS SECTION ENFORCES: **no field this module publishes may be
# without an assertion pinning its value.** The rule has now been re-stated
# three times because the first two implementations of it were too narrow:
#
#   R2  (round 1) — two statistics were unasserted. Fixed by asserting them.
#   R18 (round 2) — five more were. Fixed by inverting the check: compare the
#                   whole `perf` block against a hand-derived expected dict,
#                   so a *new* field fails until someone computes its value.
#   R21/R22 (round 3) — `perf` was inverted but `cost` and `records` were not,
#                   and the golden corpus was degenerate on p95 (three fields
#                   all 0.6, slowest row == largest row), so `pct(meds, 95)`
#                   -> `max(meds)` passed while moving the published p95.
#
# So the comparison now covers the ENTIRE published payload — `perf`, `cost`,
# one full `records` row, and the artifact's top-level key set — and the
# corpus is built so that no statistic shares a value with another statistic
# that a plausible mutation could substitute for it. See ADR-021 §b10, which
# also states what this still does NOT reach.
#
# Corpus design, and what each property exists to separate:
#   * medians 0.4 / 0.6 / 0.2 / 0.01 / 0.0001 -> p50 0.2, max 0.6, and the
#     LARGEST row's median 0.4: three different numbers, so p50->largest,
#     max->largest and largest->max all go red (R21).
#   * the slowest row (nvda-2024, 0.6) is NOT the largest row (cat-2023,
#     3 MiB), so `slowest_fixture` -> `largest["fixture"]` goes red (R21).
#   * p95 == max is *structural* for any n < 20 under nearest-rank
#     (ceil(0.95n) == n), so p95 is separated in its own n=20 block below
#     rather than pretended away here.
#   * three processed rows with an exact hand-derived R² of 0.25, throughput
#     3.33 / 5.0 / 7.5 (min, median, max and spread all different values), a
#     refused row at 100 MiB/s that must not enter the range, a sub-ms row
#     that must not enter the ratio statistics, one synthetic row that must
#     not enter the sweep multiplier.
#   * chars 900,000 / 200,000 / 100,000 / 10,000 / 100 -> the median filing
#     (100,000) differs from the mean (242,020) and from the largest
#     (900,000), and the largest exceeds the cheap tier's context while the
#     median does not — so `fits_haiku_context` has both values present (R22).

def _rec(name, mib, times, chars=1000, status="success", rss=100.0):
    return make_record(name, "f", int(mib * MIB), times, chars, status, rss)


def _golden_corpus():
    """Five fixtures, descending raw size, exactly as `run_all` emits them.
    Names are real corpus names because `refused`/`synthetic` are derived from
    status and from membership of SYNTHETIC, not passed in."""
    return [
        _rec("cat-2023", 3, [0.4], 900000, rss=50.0),
        _rec("nvda-2024", 2, [0.72, 0.60, 0.60], 200000, rss=99.6),
        _rec("ko-1997", 1, [0.22, 0.20, 0.20], 100000, rss=100.0),
        _rec("aapl-2026-10q", 1, [0.01], 10000, "unsupported", 100.0),
        make_record("truncated-download", "f", 1048, [0.0004, 0.0001, 0.0001],
                    100, "failed", 100.0),
    ]


# One record, every field. Pins `make_record` itself and fails on a new key.
# times [0.30, 0.11, 0.12, 0.90, 0.13] -> median 0.13, min 0.11, first 0.30,
# max 0.90, mean 1.56/5 = 0.312; 2 MiB / 0.13 s = 15.38 MiB/s.
_GOLDEN_RECORD = {
    "fixture": "x", "file": "f", "raw_bytes": 2097152, "normalized_chars": 1000,
    "doc_status": "success", "refused": False, "synthetic": False, "repeats": 5,
    "median_s": 0.13, "min_s": 0.11, "first_s": 0.3, "mean_s": 0.312,
    "max_s": 0.9, "mib_per_s": 15.38, "peak_rss_mib_after": 100.0,
}

# Hand-derived, not blessed from a run. The load-bearing derivations, so a
# reviewer can re-check them without executing anything:
#   percentiles  sorted medians [0.0001, 0.01, 0.2, 0.4, 0.6], n=5;
#                p50 index ceil(2.5)-1 = 2 -> 0.2 (floor would give 0.01)
#   processed    rows 0-2; rates 3/0.4=7.5, 2/0.6=3.33, 1/0.2=5.0
#                -> min 3.33, median 5.0, max 7.5, spread 7.5/3.33 = 2.25
#                (with the two refusals in: max 100.0, median 7.5 — R18b/R22)
#   R²           x = 3,2,1 MiB against y = 0.4,0.6,0.2: mx=2, my=0.4, Sxx=2,
#                Sxy=0.2, a=0.1, b=0.2; residuals -0.1, 0.2, -0.1
#                -> SSR 0.06, SST 0.08, R² = 1 - 0.06/0.08 = 0.25
#   ratios       floor excludes only the 0.0001 s row; first/min per row
#                1.0, 1.2, 1.1, 1.0 -> median 1.05, max 1.2
#                spreads 0.0, 0.2, 0.1, 0.0 -> median 0.05, max 0.2
#   plateau      peak 100.0; first index whose tail stays within 0.5 is 1
#                (99.6), deliberately NOT the peak value
#   populations  total 7,341,080 B = 7.000999 MiB over batch_s 1.0 -> 7.0 MiB/s
#                real (non-synthetic) rows 0-3: 7,340,032 B = 7.0 MiB over
#                sum-of-medians 1.21 s -> 5.7851 MiB/s, mean 1.75 MiB
#                committed adds the 4 MiB held-out size: mean 11/5 = 2.2 MiB,
#                2.2 / 5.7851 = 0.3803 s per filing -> 380.3 s / 2662.0 s
#   cost         median chars 100,000 -> 25,000 tok -> $0.125 opus / $0.025
#                haiku, fits; largest 900,000 -> 225,000 tok, does NOT fit;
#                corpus 1,210,100 -> 302,525 tok -> $1.5126, does NOT fit
_GOLDEN_HELDOUT = {"spg-2019": 4 * MIB}
_GOLDEN_PAYLOAD = {
  "perf": {
    "n_fixtures": 5, "repeats": 3,
    "raw_bytes_total": 7341080, "raw_mib_total": 7.0,
    "normalized_chars_total": 1210100,
    "latency_p50_s": 0.2, "latency_p95_s": 0.6, "latency_max_s": 0.6,
    "slowest_fixture": "nvda-2024",
    "largest_fixture": "cat-2023", "largest_raw_bytes": 3145728,
    "largest_mib": 3.0, "largest_median_s": 0.4,
    "batch_seconds": 1.0, "batch_mib_per_s": 7.0,
    "median_raw_bytes": 1048576, "mean_raw_bytes": 1468216,
    "rss_mib_before_any_extraction": 20.0,
    "peak_rss_mib_corpus": 100.0,
    "peak_rss_mib_after_largest_only": 50.0,
    "derived": {
        "note": DERIVED_NOTE,
        "sum_of_medians_s": 1.21,
        "processed_n": 3, "refused_n": 2,
        "refused_fixtures": ["aapl-2026-10q", "truncated-download"],
        "processed_mib_per_s_min": 3.33,
        "processed_mib_per_s_max": 7.5,
        "processed_mib_per_s_median": 5.0,
        "processed_mib_per_s_spread": 2.25,
        "processed_size_vs_time_r2": 0.25,
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
            "mib_per_s": 5.79,
            "rate_source": "measured: sum(bytes)/sum(medians) over these fixtures",
            "seconds_per_filing": 0.3025, "n_1000_seconds": 302.5,
            "n_1000_gib_read": 1.71, "edgar_year_7000_seconds": 2117.5,
        },
        "real_edgar_committed": {
            "n": 5, "mean_raw_bytes": 2306867, "mean_mib": 2.2,
            "mib_per_s": 5.79,
            "rate_source": "sizes include held-out filings (stat only, never timed); "
                           "rate borrowed from real_edgar_dev",
            "seconds_per_filing": 0.3803, "n_1000_seconds": 380.3,
            "n_1000_gib_read": 2.15, "edgar_year_7000_seconds": 2662.0,
        },
    },
    "projection_of_record": "real_edgar_committed",
    "heldout_sizes_bytes": _GOLDEN_HELDOUT,
  },
  "cost": {
    "reported_usd_per_filing": 0.0,
    "estimate_method": "chars/4 — NOT a tokenizer count",
    "price_basis_date": "2026-06-24",
    "price_basis_source": PRICE_BASIS_SOURCE,
    "models": {"claude-opus-5": {"usd_per_mtok_input": 5.00, "context_tokens": 1_000_000},
               "claude-haiku-4-5": {"usd_per_mtok_input": 1.00, "context_tokens": 200_000}},
    "counterfactual": {
        "median_filing": {"chars": 100000, "est_tokens": 25000,
                          "usd_opus_5": 0.125, "usd_haiku_4_5": 0.025,
                          "fits_haiku_context": True},
        "largest_filing": {"chars": 900000, "est_tokens": 225000,
                           "usd_opus_5": 1.125, "usd_haiku_4_5": 0.225,
                           "fits_haiku_context": False, "fixture": "cat-2023"},
        "whole_corpus": {"chars": 1210100, "est_tokens": 302525,
                         "usd_opus_5": 1.5126, "usd_haiku_4_5": 0.3025,
                         "fits_haiku_context": False},
    },
  },
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
    # 1. ONE RECORD, EVERY FIELD, through the code path `run_all` uses.
    # Asserting `statistics.median([...]) == x` would test the stdlib; this
    # drives `make_record`, where `med` is actually computed. Five distinct
    # times so median, first, min and max are four different values — and the
    # whole dict is diffed, so a new key in a record fails here (R22).
    r = _rec("x", 2.0, [0.30, 0.11, 0.12, 0.90, 0.13])
    d = _diff(r, _GOLDEN_RECORD)
    assert not d, "make_record() drifted from the hand-derived record:\n" + "\n".join(d)
    # classification comes off the data, not off a caller's say-so
    assert _rec("toc-titled", 1.0, [0.1])["synthetic"] is True
    assert _rec("q", 1.0, [0.1], status="unsupported")["refused"] is True
    assert _rec("q", 1.0, [0.1], status="failed")["refused"] is True
    assert _rec("q", 1.0, [0.1], status="ambiguous")["refused"] is False

    # 2. THE WHOLE PUBLISHED PAYLOAD, against hand-derived values. This is the
    # assertion that makes the rule at the top of this section enforceable
    # rather than aspirational: it fails on a wrong value AND on a new field
    # nobody has computed an expected value for, in `perf` OR in `cost`.
    corpus = _golden_corpus()
    perf, cost = summarize(corpus, batch_s=1.0, rss_start=20.0, repeats=3,
                           heldout=dict(_GOLDEN_HELDOUT))
    d = _diff({"perf": perf, "cost": cost}, _GOLDEN_PAYLOAD)
    assert not d, "summarize() drifted from the hand-derived golden values:\n" + "\n".join(d)
    # every corpus row carries exactly the fields the golden record pins
    for row in corpus:
        assert set(row) == set(_GOLDEN_RECORD), sorted(set(row) ^ set(_GOLDEN_RECORD))
    # ...and the artifact grows no new top-level block unnoticed
    assert sorted(build_payload(corpus, perf, cost)) == PAYLOAD_KEYS, \
        sorted(build_payload(corpus, perf, cost))

    # 2b. PERCENTILE SEPARATION. p95 == max is structural for n < 20 under
    # nearest-rank (ceil(0.95n) == n), so the golden corpus cannot separate
    # them and this block does it instead: 20 fixtures, sizes DESCENDING while
    # medians ASCEND, so the largest row is also the fastest.
    # sorted medians 0.01..0.20 -> p50 = ceil(10)-1 = idx 9 = 0.10,
    # p95 = ceil(19)-1 = idx 18 = 0.19, max = 0.20, largest's median = 0.01.
    wide = [_rec(f"f{i}", float(20 - i), [(i + 1) / 100]) for i in range(20)]
    wperf, _ = summarize(wide, batch_s=1.0, rss_start=1.0, repeats=1)
    assert wperf["latency_p50_s"] == 0.1, wperf["latency_p50_s"]
    assert wperf["latency_p95_s"] == 0.19, wperf["latency_p95_s"]   # not max
    assert wperf["latency_max_s"] == 0.2, wperf["latency_max_s"]
    assert wperf["largest_median_s"] == 0.01, wperf["largest_median_s"]
    assert wperf["largest_fixture"] == "f0", wperf["largest_fixture"]
    assert wperf["slowest_fixture"] == "f19", wperf["slowest_fixture"]
    # four distinct values, so no one of them can stand in for another
    assert len({0.1, 0.19, 0.2, 0.01}) == 4

    # 2c. RATIO POPULATION IDENTITY. The published exclusion list is the
    # complement of the population predicate, so these always sum (R24).
    for pf in (perf, wperf):
        assert (pf["derived"]["ratio_population_n"]
                + len(pf["derived"]["ratio_excluded_fixtures"])) == pf["n_fixtures"], pf["derived"]
    # ...and specifically for the predicate the old code left out: a row whose
    # min_s rounds to 0.0 on a coarse clock is dropped from the ratio
    # statistics and MUST be named as dropped. Without this row both
    # predicates agree and the defect is unobservable, which is why R24 was
    # real but unfirable.
    coarse = [_rec("cat-2023", 2.0, [0.5, 0.0, 0.5]), _rec("ko-1997", 1.0, [0.2])]
    cperf, _ = summarize(coarse, batch_s=1.0, rss_start=1.0, repeats=3)
    cd = cperf["derived"]
    assert coarse[0]["min_s"] == 0.0 and coarse[0]["median_s"] == 0.5, coarse[0]
    assert cd["ratio_population_n"] == 1, cd
    assert cd["ratio_excluded_fixtures"] == ["cat-2023"], cd
    assert cd["ratio_population_n"] + len(cd["ratio_excluded_fixtures"]) == 2, cd

    # 2d. The same corpus with the largest row NOT first. `run_all` always
    # emits descending size, so `peak_rss_mib_after_largest_only` is only
    # meaningful under that order; out of order it must be None rather than
    # silently reporting some other fixture's high-water mark.
    shuffled = _golden_corpus()
    shuffled.append(shuffled.pop(0))
    sperf, _ = summarize(shuffled, batch_s=1.0, rss_start=20.0, repeats=3)
    assert sperf["peak_rss_mib_after_largest_only"] is None, sperf
    assert sperf["latency_p50_s"] == _GOLDEN_PAYLOAD["perf"]["latency_p50_s"]
    assert sperf["peak_rss_mib_corpus"] == _GOLDEN_PAYLOAD["perf"]["peak_rss_mib_corpus"]

    # 2e. Plateau index, other boundary. The golden corpus's plateau is at
    # index 1, so it pins a scan that always answers 0; this pins the reverse —
    # a corpus already at its peak on the first fixture must report 0, not 1.
    flat = [_rec(f"g{i}", float(4 - i), [0.1 * (4 - i)], rss=100.0) for i in range(4)]
    assert summarize(flat, 1.0, 1.0, 1)[0]["derived"]["rss_plateau_first_index"] == 0

    # 3. R² must also read 1.0 when the relationship really is perfect — the
    # golden corpus pins the 0.25 side, this pins the other, so a constant
    # `_r2` cannot satisfy both.
    perfect = [_rec(f"p{i}", float(i), [i / 10]) for i in (1, 2, 3, 4)]
    pperf, _ = summarize(perfect, batch_s=1.0, rss_start=1.0, repeats=1)
    assert pperf["derived"]["processed_size_vs_time_r2"] == 1.0, pperf["derived"]
    assert pperf["derived"]["processed_mib_per_s_spread"] == 1.0, pperf["derived"]

    # 4. No network/API surface exists in this module — the price table is
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
    ap.add_argument("--check-docs", metavar="ARTIFACT", default=None,
                    help="verify every fixture-attributed decimal in the docs "
                         "against this artifact (see check_docs)")
    args = ap.parse_args(argv[1:])

    if args.self_check:
        _demo()
        return 0
    if args.check_docs:
        return check_docs(args.check_docs)

    records, batch_s, rss_start = run_all(args.repeats)
    perf, cost = summarize(records, batch_s, rss_start, args.repeats, heldout_sizes())
    print(render(records, perf, cost))

    if args.json:
        Path(args.json).write_text(
            json.dumps(build_payload(records, perf, cost), indent=2, default=str))
        print(f"\n[bench] wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
