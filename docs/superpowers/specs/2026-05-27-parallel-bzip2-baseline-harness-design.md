# Design: Parallel bzip2 — Sequential Baseline + Benchmark/Profiling Harness

**Date:** 2026-05-27
**Team:** 05
**Status:** Approved (design phase)

## Context

The course final project (`proposal_team05.pdf`) is *AI-assisted Parallelization of
bzip2 Compression with Profiling-guided Optimization*. The full project is a study that
compares five versions of a block-parallel bzip2 compressor:

1. Sequential bzip2 baseline
2. An existing parallel implementation (lbzip2 / pbzip2)
3. A naive AI-generated parallel version
4. A constraint-guided AI parallel version
5. A profiling-guided AI optimized version

…evaluated on runtime, throughput, speedup, parallel efficiency, compression ratio,
memory usage, and correctness, across thread counts and block sizes.

This spec covers the **first deliverable only**: the sequential baseline, a correctness
oracle, and the benchmark/profiling harness. The OpenMP parallel path and the
comparison/AI-tier work are deferred but the layout leaves clean seams for them.

## Decisions (locked during brainstorming)

| Topic | Decision |
| --- | --- |
| Scope now | Sequential baseline + correctness verifier + benchmark/profiling harness. Parallel versions deferred. |
| Compression backend | Vendor the official bzip2 source (`gitlab.com/bzip2/bzip2`, which *is* libbz2), build it as a static library, call its low-level block API. No reimplementation of BWT/Huffman. |
| Target platform | Linux primary (enables `perf`, `valgrind`, `/usr/bin/time -v`, `gprof`). Must still build on macOS for development. |
| Language / threading | C + OpenMP. OpenMP is used by the *later* parallel path; the baseline is single-threaded C. |
| Code structure | One tool, `pbzx`, parameterized by `--threads`. `--threads 1` is the sequential baseline; the parallel path is added to the same code later so baseline and parallel stay apples-to-apples. |
| Output format | Standard concatenated `.bz2` streams (the pbzip2 trick), so stock `bunzip2` can decompress our output and serve as an independent correctness oracle. |

## Repository layout

```
third_party/bzip2/      # vendored official bzip2 source -> built as static libbz2.a
src/
  main.c                # CLI + orchestration
  args.{c,h}            # --threads --block-size --level -i -o, validation
  block_reader.{c,h}    # read input into fixed-size blocks, assign block IDs
  bz_block.{c,h}        # compress one block via BZ2_bzBuffToBuffCompress
  writer.{c,h}          # emit compressed blocks in ID order (concatenated .bz2)
bench/
  run_bench.py          # sweep threads x block-size x input -> results.csv
  profilers.py          # wrap perf / /usr/bin/time -v / valgrind massif
                        # (named profilers.py, not profile.py, to avoid
                        #  shadowing Python's stdlib `profile` module)
  plot.py               # speedup, throughput, efficiency, ratio charts
  verify.py             # round-trip correctness oracle
data/                   # test inputs (gitignored) + fetch/generate script
Makefile                # build libbz2 + pbzx; flags for -pg / -fopenmp (later)
docs/superpowers/specs/ # this spec; report later
```

## Components

### `pbzx` tool (first deliverable = sequential path)

- **Input splitting:** read the input into fixed-size blocks (default 900 KB, bzip2's
  maximum block size). Each block gets a monotonic block ID.
- **Per-block compression:** each block is compressed into one independent `.bz2`
  stream via `BZ2_bzBuffToBuffCompress`. Because concatenated bzip2 streams are a valid
  `.bz2` file, the output decompresses with stock `bunzip2`.
- **Ordering:** `--threads 1` runs the blocks sequentially today. The compress loop is
  written so it can later become an OpenMP-parallel loop: compress block *i* into a
  pre-allocated output slot, then emit slots in ascending ID order (via a sequential
  write pass or an `ordered` section). The `writer` interface is built now so the
  parallel stage is a drop-in.
- **Machine-readable output:** the tool prints a stats line (input bytes, output bytes,
  block size, thread count, compress-only seconds, measured with a monotonic
  high-resolution clock) for the harness to parse.
- **CLI flags:** `--threads N`, `--block-size BYTES`, `--level 1..9` (libbz2
  `blockSize100k`), `-i input`, `-o output`.

### Correctness oracle (`verify.py`)

For each test file: compress with `pbzx`, decompress with stock `bunzip2`, then `cmp`
against the original. Cases covered:

- empty file
- smaller than one block
- exactly one block
- many blocks
- incompressible (random) data

This satisfies the proposal's "decompress and compare" requirement using an *independent*
decompressor rather than self-consistency.

### Benchmark + profiling harness

- **`run_bench.py`** sweeps {thread counts} × {block sizes} × {input files}, runs each
  configuration N times, and records to `results.csv`: runtime, throughput (MB/s),
  compression ratio, peak RSS (from `/usr/bin/time -v` "Maximum resident set size"), and
  correctness pass/fail. Speedup (= seq_time / par_time) and parallel efficiency
  (= speedup / threads) are derived from the `threads=1` row.
- **`profilers.py`** (Linux): wraps `perf stat` (CPU utilization, cache behavior),
  `perf record`/`perf report` (hotspots), and `valgrind massif` (memory over time).
  Wired now; exercised mainly during the later Stage-3 profiling study.
- **`plot.py`**: produces speedup-vs-threads, throughput-vs-block-size, parallel
  efficiency, and compression-ratio charts as PNGs via matplotlib.

### Test inputs

`data/fetch.sh` downloads the Silesia corpus and generates synthetic files (highly
compressible text/zeros; incompressible random data) at a few sizes (e.g. 64 MB,
256 MB). All test data is gitignored.

## Data flow

```
input file
   -> block_reader: split into fixed-size blocks (block IDs)
   -> bz_block: BZ2_bzBuffToBuffCompress per block -> independent .bz2 stream
   -> writer: emit streams in ID order -> concatenated .bz2 output
   -> stats line to stdout

verify.py: pbzx compress -> bunzip2 decompress -> cmp vs original
run_bench.py: drive pbzx across configs -> parse stats + /usr/bin/time -> results.csv
plot.py: results.csv -> PNG charts
```

## Error handling

Validate at boundaries only: argument validation (`args`), file open/read/write errors,
`libbz2` return codes (`BZ_OK` etc.), and allocation failures. Internal code paths trust
their inputs. No speculative handling for impossible states.

## Testing

- Build test: `make` produces `libbz2.a` and `pbzx` on Linux and macOS.
- Round-trip correctness via `verify.py` across the edge cases listed above.
- A small sanity check that our output is byte-identical-on-decompress, not
  byte-identical-on-compress (compression output may differ from stock `bzip2` because
  of block boundaries — that is expected and fine).

## Out of scope (deferred)

- The OpenMP parallel compress path (the layout leaves the seam in `writer` + the
  compress loop).
- Comparison runs against lbzip2 / pbzip2.
- The three AI-tier artifacts (naive / constraint-guided / profiling-guided) and the
  comparative write-up.
- A custom decompressor (`--decompress`); we rely on stock `bunzip2` for now.
