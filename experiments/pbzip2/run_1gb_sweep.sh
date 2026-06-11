#!/usr/bin/env bash
# Run the pbzip2 1GB reference benchmark, matching the methodology used for
# experiments/lbzip2/results/lbzip2_results_1gb.csv (and the stage1/2/3 sweeps):
# threads {1,2,4,8,16,32} x 3 repeats on the ~1.08GB bench_large_1g.bin input,
# default block size (900k = level 9). Round-trip verified via bunzip2.
#
# Usage (run from repo root on the Linux benchmark machine):
#   bash experiments/pbzip2/run_1gb_sweep.sh [DATA_DIR]
#
# Prerequisites: a C++ compiler with pthreads (g++) and bunzip2. No sudo/apt
# needed -- pbzip2 is statically linked against this repo's vendored libbz2
# (built via the top-level Makefile).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA_DIR="${1:-/tmp/bench_data}"
INFILE="$DATA_DIR/bench_large_1g.bin"
OUT_DIR="$REPO_ROOT/experiments/pbzip2/results"
PBZIP2="$REPO_ROOT/pbzip2-1.1.13/pbzip2"

# 1. Build pbzip2 (statically against the vendored libbz2) if needed
if [[ ! -x "$PBZIP2" ]]; then
  echo "Building vendored libbz2..."
  make -C "$REPO_ROOT" libbz2.a
  echo "Building pbzip2 (static, against vendored libbz2)..."
  cp "$REPO_ROOT/third_party/bzip2/bzlib.h" "$REPO_ROOT/pbzip2-1.1.13/"
  cp "$REPO_ROOT/libbz2.a" "$REPO_ROOT/pbzip2-1.1.13/"
  make -C "$REPO_ROOT/pbzip2-1.1.13" pbzip2-static
fi
"$PBZIP2" -V

# 2. Generate the 1.08GB input if needed
if [[ ! -f "$INFILE" ]]; then
  echo "Generating 1GB benchmark input..."
  bash "$REPO_ROOT/bench/gen_1gb_input.sh" "$DATA_DIR"
fi

# 3. Sweep
mkdir -p "$OUT_DIR"
INSIZE=$(stat -c%s "$INFILE")
{
  echo "implementation,threads,compress_seconds,throughput_mbps,compression_ratio,input_bytes,output_bytes"
  for t in 1 2 4 8 16 32; do
    for r in 1 2 3; do
      OUTFILE=$(mktemp /tmp/pbzip2_XXXXXX.bz2)
      START=$(date +%s%N)
      "$PBZIP2" -p"$t" -c -k "$INFILE" > "$OUTFILE"
      END=$(date +%s%N)
      OUTSIZE=$(stat -c%s "$OUTFILE")
      rm -f "$OUTFILE"
      SECS=$(awk -v a="$START" -v b="$END" 'BEGIN{printf "%.6f", (b-a)/1000000000}')
      TPUT=$(awk -v sz="$INSIZE" -v s="$SECS" 'BEGIN{printf "%.3f", (sz/1000000)/s}')
      RATIO=$(awk -v o="$OUTSIZE" -v i="$INSIZE" 'BEGIN{printf "%.6f", o/i}')
      echo "pbzip2,$t,$SECS,$TPUT,$RATIO,$INSIZE,$OUTSIZE" | tee /dev/stderr
    done
  done
} > "$OUT_DIR/pbzip2_results_1gb.csv"

# 4. Round-trip correctness check
CHECKFILE=$(mktemp /tmp/pbzip2_check_XXXXXX.bz2)
"$PBZIP2" -p"$(nproc)" -c -k "$INFILE" > "$CHECKFILE"
if bunzip2 -c "$CHECKFILE" | cmp -s - "$INFILE"; then
  echo "pbzip2 PASS"
else
  echo "pbzip2 FAIL"
fi
rm -f "$CHECKFILE"

echo "wrote $OUT_DIR/pbzip2_results_1gb.csv"
