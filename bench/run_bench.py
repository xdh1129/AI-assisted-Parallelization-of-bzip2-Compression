#!/usr/bin/env python3
"""Benchmark sweep: run pbzx across configs, capture metrics into results.csv."""
import argparse
import csv
import os
import re
import shutil
import subprocess
import tempfile

STATS_RE = re.compile(r"PBZX_STATS (.+)")


def parse_stats(stdout):
    m = STATS_RE.search(stdout)
    if not m:
        raise ValueError("no PBZX_STATS line found")
    out = {}
    for kv in m.group(1).split():
        k, v = kv.split("=", 1)
        out[k] = float(v) if "." in v else int(v)
    return out


def parse_time_v(stderr):
    """Parse /usr/bin/time -v output -> {'max_rss_kb', 'elapsed_s'}."""
    res = {}
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("Maximum resident set size"):
            res["max_rss_kb"] = int(line.split(":")[1])
        elif line.startswith("Elapsed (wall clock) time"):
            # Extract the actual time value (after the last colon in the key part)
            # Format: "Elapsed (wall clock) time (h:mm:ss or m:ss): 0:01.50"
            # We need to find ): and take everything after
            parts = line.split("):")
            if len(parts) == 2:
                t = parts[1].strip()
                secs = 0.0
                for p in t.split(":"):
                    secs = secs * 60 + float(p)
                res["elapsed_s"] = secs
    return res


def run_one(pbzx, infile, outfile, threads, block_size, level, time_bin):
    cmd = [time_bin, "-v", pbzx, "-i", infile, "-o", outfile,
           "--threads", str(threads), "--block-size", str(block_size),
           "--level", str(level)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"pbzx failed (rc={p.returncode}): {p.stderr}")
    return {**parse_stats(p.stdout), **parse_time_v(p.stderr)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pbzx", default="./pbzx")
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--threads", nargs="+", type=int, default=[1])
    ap.add_argument("--block-sizes", nargs="+", type=int, default=[900000])
    ap.add_argument("--level", type=int, default=9)
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--out", default="results.csv")
    ap.add_argument("--time-bin", default="/usr/bin/time")
    args = ap.parse_args()

    rows = []
    tmp = tempfile.mkdtemp()
    try:
        for inp in args.inputs:
            insize = os.path.getsize(inp)
            for bs in args.block_sizes:
                for th in args.threads:
                    for r in range(args.repeat):
                        outf = os.path.join(tmp, "o.bz2")
                        m = run_one(args.pbzx, inp, outf, th, bs,
                                    args.level, args.time_bin)
                        cs = m["compress_seconds"]
                        m["throughput_mbps"] = (insize / 1e6) / cs if cs > 0 else 0.0
                        m["compression_ratio"] = m["output_bytes"] / insize if insize else 0.0
                        m["input"] = os.path.basename(inp)
                        m["repeat"] = r
                        rows.append(m)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    fields = sorted({k for row in rows for k in row})
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
