# AI-assisted Parallelization of bzip2 Compression

Team 05 — final project for the parallel-programming course.

This repository contains the implementation, experiments, benchmark data, and
report for an AI-assisted parallelization study of bzip2 compression.

## What this project is

A study of **using AI to parallelize bzip2 compression**, guided by profiling
feedback. bzip2 processes data in independent blocks, so block-level parallelism
is possible — but doing it well requires handling output ordering, load balancing,
synchronization overhead, and I/O bottlenecks.

The project evaluates **how different levels of AI guidance affect parallel
performance and code quality**: naive prompting, explicit design constraints,
and profiling feedback. Every implementation is checked for correctness and
compared against the sequential baseline and the established `lbzip2` tool.

Read the [final report](report/report.pdf) or [report draft](report/thesis-draft.md)
for the full methodology and analysis.

The completed experiment consists of:

1. A sequential `pbzx` baseline using vendored `libbz2`
2. A naive AI-generated OpenMP implementation
3. A constraint-guided pthread pipeline with ordered output
4. A profiling-guided implementation with per-thread workspace arenas
5. `lbzip2` and `pbzip2` as external reference implementations

Metrics: runtime, throughput (MB/s), speedup, parallel efficiency, compression
ratio, peak memory, and correctness.

---

### How `pbzx` works

Splits the input into fixed-size blocks (default 900 KB) and compresses each block
into an **independent `.bz2` stream** via libbz2's `BZ2_bzBuffToBuffCompress`, then
concatenates the streams in block-ID order. Concatenated bzip2 streams are a valid
`.bz2` file, so the output decompresses with the stock `bunzip2` — which is what the
correctness oracle uses as an independent check.

This per-block-independent-stream design is the basis for parallelism (each block
can be compressed on a different thread). The trade-off: on multi-block inputs the
output is slightly larger than stock `bzip2` (extra per-block stream headers/footers),
though for a single-block input it is byte-identical to `bzip2`.

---

## Results at a glance

The main sweep used a 1.08 GB input, 900 KB blocks, compression level 9, and
three repetitions at each thread count. Mean compression time was:

| Threads | Stage 1: naive | Stage 2: constrained | Stage 3: profiling | `lbzip2` |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 80.84 s | 81.77 s | 78.72 s | 67.90 s |
| 4 | 20.80 s | 20.74 s | 20.02 s | 17.58 s |
| 16 | 5.52 s | 5.50 s | 5.36 s | 4.96 s |
| 32 | 3.06 s | 3.49 s | **3.03 s** | 3.14 s |

Key findings:

- All three AI-generated implementations passed round-trip correctness at every
   tested thread count and preserved the compressed output across thread counts.
- Block-level parallelism scaled close to linearly through 16 threads. At 32
   threads, speedup plateaued around 22–26x because of block granularity and BWT
   memory bandwidth.
- Profiling feedback made Stage 3 the fastest AI-generated implementation at
   every thread count. Replacing per-block allocation with a per-thread bump
   arena reduced page faults from roughly 674K to 181K.
- Constraint guidance improved structure and ordering guarantees, but its
   pthread pipeline added enough synchronization overhead to trail the other
   implementations in absolute runtime.

![Compression time by implementation](report/runtime_by_impl.png)

![Throughput by implementation](report/throughput_by_impl.png)

![Speedup by implementation](report/speedup_by_impl.png)

More raw data and comparison plots are available under
[`experiments/comparison`](experiments/comparison/).

## Implementation stages

Each stage is preserved in its own branch so the AI guidance can be compared as
an experiment rather than inferred from a single final implementation:

| Branch | Approach | Main contribution |
| --- | --- | --- |
| `main` | Baseline and merged analysis | Sequential `pbzx`, tests, harness, results, and report |
| `stage/1-naive` | Naive AI parallelization | Direct OpenMP parallelization of independent blocks |
| `stage/2-constrained` | Constraint-guided design | Worker pipeline, block IDs, and order-preserving writer |
| `stage/3-profiling` | Profiling-guided optimization | Per-thread workspace arena and bottleneck-driven tuning |
| `bzip2-gpu` | Extension study | CUDA exploration inside the bzip2 compression pipeline |

The core design is deliberately block-oriented: each input block is compressed
into an independent bzip2 stream, then emitted in block-ID order. This makes the
compression work parallelizable while preserving a valid concatenated `.bz2`
output that standard `bunzip2` can decode.

## Reproduce the experiment

### Requirements

Requirements: a C compiler (`cc`), `make`, `bunzip2`, Python 3. For the harness:
`pip install -r bench/requirements.txt` (pytest, matplotlib). Profiling tools
(`perf`, `valgrind`) and GNU `/usr/bin/time -v` are **Linux-oriented**. The
project builds and its tests run on macOS too; on macOS, install GNU time with
`brew install coreutils` and pass `--time-bin gtime` to the benchmark script.

```bash
make
python3 -m pip install -r bench/requirements.txt
make test
```

`make` builds the vendored `libbz2.a` and the `pbzx` executable. `make test`
runs the five C unit tests and the Python test suite. Use `make clean` to remove
generated objects, binaries, and test executables.

## Usage

```bash
# compress one input
./pbzx -i input.dat -o output.bz2 --block-size 900000 --level 9 --threads 1

# decompress with the standard tool (our output is a valid .bz2)
bunzip2 -c output.bz2 > restored.dat
```

`pbzx` prints a machine-readable stats line consumed by the harness:

```
PBZX_STATS input_bytes=.. output_bytes=.. block_size=.. threads=.. level=.. blocks=.. compress_seconds=..
```

Supported options are `-i INPUT`, `-o OUTPUT`, `--threads N`,
`--block-size BYTES`, and `--level 1..9`.

### Correctness check

```bash
python3 bench/verify.py ./pbzx file1 file2 ...
# per file: compress with pbzx -> decompress with bunzip2 -> byte-compare to original
```

### Benchmark + plot (Linux, needs GNU time)

```bash
bash data/fetch.sh        # generate synthetic inputs (+ best-effort Silesia) into data/

python3 bench/run_bench.py --pbzx ./pbzx \
    --inputs data/text_64.bin data/random_64.bin \
    --threads 1 2 4 8 --block-sizes 900000 100000 --repeat 3 \
    --out results.csv

python3 bench/plot.py --results results.csv --out speedup.png
```

The benchmark writes CSV results and removes its temporary compressed outputs.
On macOS, add `--time-bin gtime` after installing `coreutils`, or run the sweep
on the Linux target.

---

## Repository layout

```
third_party/bzip2/   # vendored official bzip2 1.0.8 -> built into libbz2.a
src/                 # the pbzx tool
  args.{c,h}         #   CLI parsing + validation
  block_reader.{c,h} #   read input into fixed-size blocks with IDs
  bz_block.{c,h}     #   compress one block into a standalone .bz2 stream
  writer.{c,h}       #   write compressed blocks in ID order (concatenation)
  main.c             #   orchestration + stats line (OpenMP seam is here)
bench/               # Python harness
  verify.py          #   round-trip correctness oracle
  run_bench.py       #   config sweep -> results.csv
  profilers.py       #   perf / valgrind massif command builders
  plot.py            #   speedup / efficiency charts
tests/               # C unit tests + pytest
data/                # test inputs (gitignored) + fetch.sh
docs/superpowers/    # design spec and the task-by-task implementation plan
```

Design spec: [`docs/superpowers/specs/2026-06-21-team05-final-presentation-design.md`](docs/superpowers/specs/2026-06-21-team05-final-presentation-design.md)

Implementation plan: [`docs/superpowers/plans/2026-06-21-team05-final-presentation.md`](docs/superpowers/plans/2026-06-21-team05-final-presentation.md)

---

### Why the baseline is `pbzx --threads 1`, not stock `bzip2`

Speedup = sequential time ÷ parallel time is only meaningful when numerator and
denominator are the *same* implementation differing only in thread count. `pbzx`
at 1 thread vs N threads isolates the effect of parallelism. Stock `bzip2` has no
N-thread mode and uses a different (single-stream) framing, so it serves as an
*external reference*, not the speedup denominator.

---

## References

- bzip2: https://gitlab.com/bzip2/bzip2
- lbzip2: https://github.com/kjn/lbzip2
- pbzip2: https://github.com/ruanhuabin/pbzip2
