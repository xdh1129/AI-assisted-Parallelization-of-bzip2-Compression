# AI-assisted Parallelization of bzip2 Compression

Team 05 — final project for the parallel-programming course.

## What this project is

A study of **using AI to parallelize bzip2 compression**, guided by profiling
feedback. bzip2 processes data in independent blocks, so block-level parallelism
is possible — but doing it well requires handling output ordering, load balancing,
synchronization overhead, and I/O bottlenecks.

The project compares several versions of a block-parallel bzip2 compressor and
evaluates **whether AI-assisted parallelization improves with more guidance**
(direct prompting → design constraints → profiling feedback), while preserving
correctness. See `proposal_team05.pdf` for the full proposal.

The planned versions to compare:

1. Sequential baseline
2. An existing parallel tool (lbzip2 / pbzip2) — external reference
3. Naive AI-generated parallel version
4. Constraint-guided AI parallel version
5. Profiling-guided AI optimized version

Metrics: runtime, throughput (MB/s), speedup, parallel efficiency, compression
ratio, peak memory, and correctness.

---

## Current status

**Done — sequential baseline + measurement infrastructure.**
The parallel versions are intentionally *not* implemented yet: the baseline and
the benchmark/profiling harness are the "measuring apparatus" built first, so each
later parallel version can be measured the same way (apples-to-apples).

| Component | Status |
| --- | --- |
| `pbzx` sequential compressor (vendored libbz2) | done |
| Correctness oracle (`bench/verify.py`) | done |
| Benchmark harness (`bench/run_bench.py`) | done |
| Profiling command builders (`bench/profilers.py`) | done |
| Plotting (`bench/plot.py`) | done |
| Test data generator (`data/fetch.sh`) | done |
| **OpenMP parallel compress path** | **not started** |
| lbzip2 / pbzip2 reference runs | not started |
| Naive / constraint-guided / profiling-guided AI versions | not started |

> **Note:** `pbzx` accepts `--threads N`, but right now that value is only
> recorded in the stats line — the compression loop is still single-threaded.
> `--threads 1` and `--threads 8` currently produce identical output in identical
> time. Actual multithreading is added in the next phase (see Roadmap).

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

## Build & test

Requirements: a C compiler (`cc`), `make`, `bunzip2`, Python 3. For the harness:
`pip install -r bench/requirements.txt` (pytest, matplotlib). Profiling tools
(`perf`, `valgrind`) and GNU `/usr/bin/time -v` are **Linux-only** — the primary
benchmark target is Linux, but everything builds and the unit tests run on macOS too.

```bash
make           # builds vendored libbz2.a and the pbzx binary
make test      # builds + runs 5 C unit tests and 13 Python tests
make clean
```

## Usage

```bash
# compress (sequential today; --threads is recorded but not yet acted on)
./pbzx -i input.dat -o output.bz2 --block-size 900000 --level 9 --threads 1

# decompress with the standard tool (our output is a valid .bz2)
bunzip2 -c output.bz2 > restored.dat
```

`pbzx` prints a machine-readable stats line consumed by the harness:

```
PBZX_STATS input_bytes=.. output_bytes=.. block_size=.. threads=.. level=.. blocks=.. compress_seconds=..
```

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

On macOS, GNU time is absent; install coreutils and pass `--time-bin gtime`, or run
the sweep on the Linux target.

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

Design spec: `docs/superpowers/specs/2026-05-27-parallel-bzip2-baseline-harness-design.md`
Implementation plan: `docs/superpowers/plans/2026-05-27-parallel-bzip2-baseline-harness.md`

---

## Roadmap (planned work)

The parallelization is the actual research content. Each AI stage is one
experiment: parallelize the *same* sequential code under a *different* level of
guidance, then measure correctness and performance with the existing harness.

1. **Enable OpenMP.** Add `-fopenmp` to the build; turn the compress loop in
   `src/main.c` into a parallel loop. Two things must change first (already flagged
   in the code comment): the `break`-on-error is illegal in an OpenMP `for`, and
   `input_bytes` is summed outside the loop to avoid a loop-carried reduction.

2. **Stage 1 — Naive AI parallelization.** Give the AI only the sequential code and
   "parallelize it." Record the unguided result as the control.

3. **Stage 2 — Constraint-guided.** Provide explicit design constraints (fixed-size
   blocks, unique block IDs, worker threads + an ordered writer, no global locks).
   Measure the improvement over Stage 1.

4. **Stage 3 — Profiling-guided.** Run the result, collect profiling data (CPU
   utilization, I/O wait, lock contention, thread idle time, scalability across
   thread counts), feed it back, and ask the AI to fix the actual bottleneck.

5. **Reference comparisons.** Benchmark stock `bzip2` (sequential reference) and
   `lbzip2` / `pbzip2` (parallel references) through the same harness.

6. **Analysis & report.** Compare all versions on the metrics; analyze how AI output
   quality and performance change as guidance increases; study the effect of block
   size and thread count on speedup and compression ratio.

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
