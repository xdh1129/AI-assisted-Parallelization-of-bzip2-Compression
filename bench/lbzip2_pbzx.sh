#!/usr/bin/env bash
# Adapter: expose the pbzx benchmark interface on top of vendored lbzip2 so the
# existing harness (bench/run_bench.py, bench/verify.py) can drive lbzip2 with
# zero changes.
#
#   pbzx interface : -i IN -o OUT [--threads N] [--block-size B] [--level L]
#   lbzip2 flags   : -z -c -k -n N -<level>   (level = block size / 100000)
#
# Emits the PBZX_STATS stdout line the harness parses. lbzip2 is a streaming
# read/compress/write pipeline, so compress_seconds is the end-to-end wall time
# of the lbzip2 process (I/O overlaps compression and cannot be separated).
set -euo pipefail

# Resolve the lbzip2 binary (override with LBZIP2_BIN=/path env var).
# NOTE: lbzip2 reads the LBZIP2/BZIP2/BZIP environment variables as *prepended
# command-line options* (bzip2 compatibility, see main.c ev_name[]). We must NOT
# name our selector var LBZIP2, and we unset all three so no hidden options leak
# into the benchmark and skew results.
unset LBZIP2 BZIP2 BZIP
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LBZIP2_BIN="${LBZIP2_BIN:-$SCRIPT_DIR/../lbzip2/build/lbzip2}"

in_path=""; out_path=""; threads=1; block_size=900000; level=""
while [ $# -gt 0 ]; do
  case "$1" in
    -i)            in_path="$2";    shift 2 ;;
    -o)            out_path="$2";   shift 2 ;;
    --threads)     threads="$2";    shift 2 ;;
    --block-size)  block_size="$2"; shift 2 ;;
    --level)       level="$2";      shift 2 ;;
    *) echo "lbzip2_pbzx: unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -n "$in_path" ]  || { echo "lbzip2_pbzx: -i input required"  >&2; exit 1; }
[ -n "$out_path" ] || { echo "lbzip2_pbzx: -o output required" >&2; exit 1; }

# Level: prefer explicit --level, else derive from block size (bzip2 blocks are
# multiples of 100K; clamp to 1..9).
if [ -z "$level" ]; then
  level=$(( (block_size + 99999) / 100000 ))
fi
[ "$level" -lt 1 ] && level=1
[ "$level" -gt 9 ] && level=9

input_bytes=$(stat -c%s "$in_path")

start=$(date +%s.%N)
"$LBZIP2_BIN" -z -c -k -n "$threads" "-$level" < "$in_path" > "$out_path"
end=$(date +%s.%N)

compress_seconds=$(awk "BEGIN{printf \"%.6f\", $end - $start}")
output_bytes=$(stat -c%s "$out_path")
# blocks: number of (block_size-sized) input chunks, matching pbzx's accounting.
blocks=$(( (input_bytes + block_size - 1) / block_size ))
[ "$blocks" -lt 1 ] && blocks=1

printf 'PBZX_STATS input_bytes=%s output_bytes=%s block_size=%s threads=%s level=%s blocks=%s compress_seconds=%s\n' \
  "$input_bytes" "$output_bytes" "$block_size" "$threads" "$level" "$blocks" "$compress_seconds"
