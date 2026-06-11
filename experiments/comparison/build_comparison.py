#!/usr/bin/env python3
"""Merge the 1GB benchmark sweeps from stage1/2/3, lbzip2 and pbzip2 into a
single comparison CSV, and render speedup / throughput / runtime charts."""
import csv
import io
import os
import subprocess
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Each source is either a plain filesystem path, or "gitref::path" to read a
# file as it exists on another branch (the stage1/2/3 1GB sweeps were
# committed on their respective stage branches, not on main).
SOURCES = {
    "stage1 (naive)":       "origin/stage/1-naive::results/stage1_results_1gb.csv",
    "stage2 (constrained)": "origin/stage/2-constrained::results/stage2_results_1gb.csv",
    "stage3 (profiling)":   "origin/stage/3-profiling::results/stage3_results_1gb.csv",
    "lbzip2 (reference)":   f"{REPO}/experiments/lbzip2/results/lbzip2_results_1gb.csv",
    "pbzip2 (reference)":   f"{REPO}/experiments/pbzip2/results/pbzip2_results_1gb.csv",
}

OUT_CSV = f"{REPO}/experiments/comparison/all_results_1gb.csv"
OUT_PLOTS = f"{REPO}/experiments/comparison/plots"


def load(source):
    if "::" in source:
        ref, path = source.split("::", 1)
        text = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout
        return list(csv.DictReader(io.StringIO(text)))
    with open(source) as f:
        return list(csv.DictReader(f))


def collect():
    """Return {impl: {threads: [compress_seconds, ...]}} and the same for throughput."""
    times = defaultdict(lambda: defaultdict(list))
    tputs = defaultdict(lambda: defaultdict(list))
    for impl, path in SOURCES.items():
        for row in load(path):
            t = int(row["threads"])
            times[impl][t].append(float(row["compress_seconds"]))
            tputs[impl][t].append(float(row["throughput_mbps"]))
    return times, tputs


def write_merged_csv(times, tputs):
    rows = []
    for impl in SOURCES:
        for t in sorted(times[impl]):
            secs = times[impl][t]
            tps = tputs[impl][t]
            mean_s = sum(secs) / len(secs)
            mean_t = sum(tps) / len(tps)
            rows.append({
                "implementation": impl,
                "threads": t,
                "mean_compress_seconds": f"{mean_s:.6f}",
                "min_compress_seconds": f"{min(secs):.6f}",
                "max_compress_seconds": f"{max(secs):.6f}",
                "mean_throughput_mbps": f"{mean_t:.3f}",
                "samples": len(secs),
            })
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT_CSV}")


def mean_by_threads(d):
    return {t: sum(v) / len(v) for t, v in d.items()}


def plot_runtime(times):
    fig, ax = plt.subplots(figsize=(7, 5))
    for impl, by_t in times.items():
        means = mean_by_threads(by_t)
        xs = sorted(means)
        ax.plot(xs, [means[x] for x in xs], marker="o", label=impl)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks([1, 2, 4, 8, 16, 32])
    ax.set_xticklabels(["1", "2", "4", "8", "16", "32"])
    ax.set_xlabel("threads")
    ax.set_ylabel("compression time (s, log scale)")
    ax.set_title("Compression time vs threads (1.08GB input)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = f"{OUT_PLOTS}/runtime_by_impl.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def plot_speedup(times):
    fig, ax = plt.subplots(figsize=(7, 5))
    thread_vals = [1, 2, 4, 8, 16, 32]
    ax.plot(thread_vals, thread_vals, linestyle="--", color="gray", label="ideal linear speedup")
    for impl, by_t in times.items():
        means = mean_by_threads(by_t)
        base = means[1]
        xs = sorted(means)
        ax.plot(xs, [base / means[x] for x in xs], marker="o", label=impl)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=2)
    ax.set_xticks(thread_vals)
    ax.set_xticklabels([str(v) for v in thread_vals])
    ax.set_yticks(thread_vals)
    ax.set_yticklabels([str(v) for v in thread_vals])
    ax.set_xlabel("threads")
    ax.set_ylabel("speedup (relative to each impl's own 1-thread time)")
    ax.set_title("Speedup vs threads (1.08GB input)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = f"{OUT_PLOTS}/speedup_by_impl.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def plot_throughput(tputs):
    fig, ax = plt.subplots(figsize=(7, 5))
    for impl, by_t in tputs.items():
        means = mean_by_threads(by_t)
        xs = sorted(means)
        ax.plot(xs, [means[x] for x in xs], marker="o", label=impl)
    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 2, 4, 8, 16, 32])
    ax.set_xticklabels(["1", "2", "4", "8", "16", "32"])
    ax.set_xlabel("threads")
    ax.set_ylabel("throughput (MB/s)")
    ax.set_title("Throughput vs threads (1.08GB input)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = f"{OUT_PLOTS}/throughput_by_impl.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def main():
    os.makedirs(OUT_PLOTS, exist_ok=True)
    times, tputs = collect()
    write_merged_csv(times, tputs)
    plot_runtime(times)
    plot_speedup(times)
    plot_throughput(tputs)


if __name__ == "__main__":
    main()
