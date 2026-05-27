#!/usr/bin/env python3
"""Read results.csv, derive speedup/efficiency, render charts."""
import argparse
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def derive_metrics(rows):
    """Add speedup and parallel_efficiency using the threads=1 baseline
    per (input, block_size)."""
    baseline = {}
    for r in rows:
        if int(r["threads"]) == 1:
            key = (r["input"], r["block_size"])
            baseline.setdefault(key, []).append(float(r["compress_seconds"]))
    base_avg = {k: sum(v) / len(v) for k, v in baseline.items()}

    out = []
    for r in rows:
        r = dict(r)
        key = (r["input"], r["block_size"])
        th = int(r["threads"])
        cs = float(r["compress_seconds"])
        if key in base_avg and cs > 0:
            r["speedup"] = base_avg[key] / cs
            r["parallel_efficiency"] = r["speedup"] / th
        else:
            r["speedup"] = 0.0
            r["parallel_efficiency"] = 0.0
        out.append(r)
    return out


def plot_speedup(rows, outfile):
    fig, ax = plt.subplots()
    by_input = {}
    for r in rows:
        by_input.setdefault(r["input"], []).append((int(r["threads"]), r["speedup"]))
    for inp, pts in by_input.items():
        pts.sort()
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", label=inp)
    ax.set_xlabel("threads")
    ax.set_ylabel("speedup")
    ax.set_title("Speedup vs threads")
    ax.legend()
    fig.savefig(outfile)
    plt.close(fig)
    return outfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results.csv")
    ap.add_argument("--out", default="speedup.png")
    args = ap.parse_args()
    rows = derive_metrics(load(args.results))
    plot_speedup(rows, args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
