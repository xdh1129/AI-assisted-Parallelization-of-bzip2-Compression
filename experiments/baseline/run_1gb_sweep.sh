#!/usr/bin/env bash
# Run the sequential pbzx baseline 1GB benchmark (pre-parallelization, on main),
# matching the methodology used for the stage1/2/3 and lbzip2/pbzip2 1GB sweeps:
# threads {1,2,4,8,16,32} x 3 repeats on the ~1.08GB bench_large_1g.bin input,
# block size 900000, level 9. Round-trip verified via bench/verify.py.
#
# Note: --threads is recorded but not yet acted on by this baseline pbzx, so
# all thread settings should produce ~identical compress_seconds -- the sweep
# documents this empirically (and gives a flat reference line for plots).
#
# Usage (run from repo root on the Linux benchmark machine, on main):
#   bash experiments/baseline/run_1gb_sweep.sh [DATA_DIR]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA_DIR="${1:-/tmp/bench_data}"
INFILE="$DATA_DIR/bench_large_1g.bin"
OUT_DIR="$REPO_ROOT/experiments/baseline/results"
PBZX="$REPO_ROOT/pbzx"

# 1. Build pbzx if needed
if [[ ! -x "$PBZX" ]]; then
  echo "Building pbzx..."
  make -C "$REPO_ROOT"
fi

# 2. Generate the 1.08GB input if needed
if [[ ! -f "$INFILE" ]]; then
  echo "Generating 1GB benchmark input..."
  bash "$REPO_ROOT/bench/gen_1gb_input.sh" "$DATA_DIR"
fi

# 3. Sweep
mkdir -p "$OUT_DIR"
python3 "$REPO_ROOT/bench/run_bench.py" \
  --pbzx "$PBZX" \
  --inputs "$INFILE" \
  --threads 1 2 4 8 16 32 \
  --block-sizes 900000 \
  --level 9 \
  --repeat 3 \
  --out "$OUT_DIR/baseline_results_1gb.csv"

# 4. Round-trip correctness check
python3 "$REPO_ROOT/bench/verify.py" "$PBZX" "$INFILE"

echo "wrote $OUT_DIR/baseline_results_1gb.csv"
