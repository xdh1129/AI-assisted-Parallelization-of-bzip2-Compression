#!/usr/bin/env bash
# Reproduce the ~1.08GB benchmark input used for the stage1/2/3 and lbzip2
# 1GB sweeps (results/stageN_results_1gb.csv, experiments/lbzip2/results/lbzip2_results_1gb.csv).
#
# It is the Canterbury Corpus "large" reference tarball (11,162,624 bytes)
# concatenated 97x, producing a 1,082,774,528-byte (~1.08GB) compressible file
# with compression_ratio ~0.2339 on pbzx/lbzip2 (level 9, block size 900000).
set -euo pipefail

DATA_DIR="${1:-/tmp/bench_data}"
REF="$DATA_DIR/bench_large.bin"
OUT="$DATA_DIR/bench_large_1g.bin"
COPIES=97

mkdir -p "$DATA_DIR"

if [[ ! -f "$REF" ]]; then
  echo "Fetching Canterbury Corpus reference file -> $REF"
  curl -L "https://corpus.canterbury.ac.nz/resources/large.tar.gz" \
       -o "$DATA_DIR/large.tar.gz"
  gunzip -f "$DATA_DIR/large.tar.gz"
  mv "$DATA_DIR/large.tar" "$REF"
fi

REF_SIZE=$(stat -c%s "$REF")
if [[ "$REF_SIZE" -ne 11162624 ]]; then
  echo "warning: $REF is $REF_SIZE bytes, expected 11162624 — output size will differ from the original benchmark" >&2
fi

echo "Concatenating $REF ($REF_SIZE bytes) x$COPIES -> $OUT"
rm -f "$OUT"
for _ in $(seq 1 "$COPIES"); do
  cat "$REF" >> "$OUT"
done

OUT_SIZE=$(stat -c%s "$OUT")
echo "done: $OUT ($OUT_SIZE bytes)"
if [[ "$OUT_SIZE" -ne 1082774528 ]]; then
  echo "warning: expected 1082774528 bytes, got $OUT_SIZE (reference file size differs from the original)" >&2
fi
