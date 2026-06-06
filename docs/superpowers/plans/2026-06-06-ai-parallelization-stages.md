# AI-Assisted Parallelization Stages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute three AI-assisted parallelization experiments on the pbzx baseline (naive → constraint-guided → profiling-optimized), each on its own isolated git branch. Benchmark each against the sequential baseline and lbzip2, and produce a comparison report.

**Architecture:** Each experiment stage lives on its own branch (`stage/1-naive`, `stage/2-constrained`, `stage/3-profiling`). All three branches start from the same sequential baseline (`feat/baseline-harness`). The agent for each stage opens a Claude Code session inside a git worktree on its branch. Stage 3 starts from the same source as Stage 1 and 2 — the difference is the prompt, which includes profiling data collected from Stage 2's output. The `bench/` harness evaluates all implementations uniformly using git worktrees.

**Branch lineage:**
```
feat/baseline-harness (sequential baseline)
├── stage/1-naive          (same starting source, minimal prompt)
├── stage/2-constrained    (same starting source, machine-spec prompt)
└── stage/3-profiling      (same starting source, profiling-data prompt)
```

**Tech Stack:** C11, pthreads or OpenMP (agent's choice), libbz2 1.0.8 (vendored), Python 3 + pytest (harness), perf/valgrind/gprof/`/usr/bin/time -v` (profiling, Linux), lbzip2 (reference)

---

## File Map

Each branch inherits the full baseline layout (`src/`, `bench/`, `tests/`, `Makefile`, `third_party/`).
Per-branch additions:

| Path (on each stage branch) | Purpose |
|---|---|
| `CLAUDE.md` | Agent context and permissions for that stage (root, auto-loaded by Claude Code) |
| `results/` | Benchmark CSVs committed on this branch |
| `src/*.c` / `src/*.h` | Modified by agent during session |
| `Makefile` | Agent may update CFLAGS (e.g. add `-fopenmp`) |

On `main`:
| Path | Purpose |
|---|---|
| `experiments/lbzip2/results/lbzip2_results.csv` | lbzip2 reference benchmark |
| `experiments/baseline/results/baseline_results.csv` | Sequential baseline benchmark |
| `experiments/comparison/all_results.csv` | Merged results from all branches |
| `experiments/comparison/plots/` | Speedup + throughput PNGs |

---

## Task 1: Confirm Baseline is Green

Verify the sequential baseline builds and all tests pass before creating stage branches.

**Files:** Read-only. No modifications.

- [ ] **Step 1: Build the baseline binary**

  ```bash
  make clean && make all
  ```
  Expected: `pbzx` binary in project root, no compiler errors.

- [ ] **Step 2: Run all tests**

  ```bash
  make test
  ```
  Expected: each `== tests/test_* ==` exits 0, pytest passes.

- [ ] **Step 3: Smoke-test correctness**

  ```bash
  dd if=/dev/urandom bs=1M count=10 of=/tmp/smoke.bin 2>/dev/null
  python3 bench/verify.py ./pbzx /tmp/smoke.bin
  ```
  Expected: `PASS  /tmp/smoke.bin`

- [ ] **Step 4: Commit baseline-green checkpoint**

  ```bash
  git add .
  git commit -m "chore: confirm baseline green before experiment stage branches"
  ```

---

## Task 2: Create Stage Branches and Per-Branch CLAUDE.md

Create three branches from the current HEAD and drop a `CLAUDE.md` into each that defines
the agent's context and permissions for that stage. No source changes yet — the agent does those.

**Files created (on respective branches):**
- `CLAUDE.md` on `stage/1-naive`
- `CLAUDE.md` on `stage/2-constrained`
- `CLAUDE.md` on `stage/3-profiling` (branch created later, after Stage 2 is done — see Task 7)
- `results/.gitkeep` on each stage branch (so the directory is tracked)

- [ ] **Step 1: Create branch stage/1-naive**

  ```bash
  git checkout -b stage/1-naive
  ```

- [ ] **Step 2: Write CLAUDE.md for stage/1-naive (minimal — no parallelism hints)**

  Create `CLAUDE.md` at the repo root on this branch:
  ```markdown
  # pbzx Stage 1: Naive AI Parallelization

  This is a bzip2 compression tool called pbzx.

  ## Source files you may modify
  - `src/main.c` — main entry point and compression pipeline
  - `src/writer.c` — writes compressed blocks to output
  - `src/bz_block.c` / `src/bz_block.h` — per-block bzip2 compression
  - `src/block_reader.c` / `src/block_reader.h` — reads input into fixed-size blocks
  - `src/args.c` / `src/args.h` — argument parsing (already accepts `--threads N`)
  - `Makefile` — update CFLAGS here if you need new compiler flags (e.g. `-fopenmp`, `-lpthread`)

  ## Do NOT modify
  - `third_party/bzip2/` — vendored libbz2 source
  - `libbz2.a` — prebuilt static library

  ## Build
  ```bash
  make clean && make all
  ```
  Produces: `./pbzx`

  ## Test correctness
  ```bash
  python3 bench/verify.py ./pbzx /tmp/bench_data/bench_large.bin
  ```
  Expected: `PASS  /tmp/bench_data/bench_large.bin`

  ## Interface
  ```
  ./pbzx -i input.bin -o output.bz2 [--threads N] [--block-size B] [--level L]
  ```
  The `--threads` flag is parsed but currently unused in the compression step.
  Output must be valid bzip2: `bunzip2 -c output.bz2 | cmp - input.bin` must succeed.
  ```

- [ ] **Step 3: Create results directory and commit CLAUDE.md on stage/1-naive**

  ```bash
  mkdir -p results
  touch results/.gitkeep
  git add CLAUDE.md results/.gitkeep
  git commit -m "chore: add stage1 CLAUDE.md and results dir"
  ```

- [ ] **Step 4: Create branch stage/2-constrained from main**

  ```bash
  git checkout main
  git checkout -b stage/2-constrained
  ```

- [ ] **Step 5: Write CLAUDE.md for stage/2-constrained (permits machine-spec commands)**

  Create `CLAUDE.md` at the repo root on this branch:
  ```markdown
  # pbzx Stage 2: Constraint-guided AI Parallelization

  This is a bzip2 compression tool called pbzx. Your goal is to parallelize it
  using block-level parallelism, choosing design parameters informed by the actual
  hardware this machine offers.

  ## Permitted system commands (run these to discover constraints)
  - `lscpu` — CPU topology, core count, hyperthreading
  - `nproc` — logical core count
  - `free -h` — available memory
  - `getconf -a | grep -i cache` — cache sizes
  - `cat /proc/cpuinfo | grep "cpu MHz" | head -4` — clock frequency
  - `cat /sys/devices/system/cpu/cpu0/cache/*/size` — per-level cache sizes (Linux)

  Use the output of these commands to choose thread count, block size, and queue depth.

  ## Source files you may modify
  - `src/main.c` — main entry point and compression pipeline
  - `src/writer.c` — ordered output
  - `src/bz_block.c` / `src/bz_block.h` — per-block compression (thread-safe)
  - `src/block_reader.c` / `src/block_reader.h` — block reader
  - `src/args.c` / `src/args.h` — argument parsing
  - `Makefile` — update CFLAGS as needed

  ## Do NOT modify
  - `third_party/bzip2/`
  - `libbz2.a`

  ## Build
  ```bash
  make clean && make all
  ```
  Produces: `./pbzx`

  ## Test correctness
  ```bash
  python3 bench/verify.py ./pbzx /tmp/bench_data/bench_large.bin
  ```
  Expected: `PASS  /tmp/bench_data/bench_large.bin`

  ## Interface
  ```
  ./pbzx -i input.bin -o output.bz2 [--threads N] [--block-size B] [--level L]
  ```
  `--threads 1` must still work correctly. Output must be valid bzip2.
  ```

- [ ] **Step 6: Commit CLAUDE.md on stage/2-constrained**

  ```bash
  mkdir -p results
  touch results/.gitkeep
  git add CLAUDE.md results/.gitkeep
  git commit -m "chore: add stage2 CLAUDE.md and results dir"
  ```

  (`stage/3-profiling` already exists — its CLAUDE.md is updated in Task 7 with actual
  profiling data after Stage 2's agent session is complete.)

- [ ] **Step 7: Return to main for the next setup tasks**

  ```bash
  git checkout main
  ```

---

## Task 3: Prepare Benchmark Test Data

Download or generate a representative input file used in all benchmark sweeps.

**Files created:** `/tmp/bench_data/bench_large.bin` (not committed)

- [ ] **Step 1: Create data directory**

  ```bash
  mkdir -p /tmp/bench_data
  ```

- [ ] **Step 2: Fetch Canterbury Corpus large tar (realistic, compressible)**

  ```bash
  curl -L "https://corpus.canterbury.ac.nz/resources/large.tar.gz" \
       -o /tmp/bench_data/large.tar.gz 2>/dev/null \
  && gunzip -f /tmp/bench_data/large.tar.gz \
  && mv /tmp/bench_data/large.tar /tmp/bench_data/bench_large.bin \
  && echo "Downloaded: $(ls -lh /tmp/bench_data/bench_large.bin)" \
  || echo "Download failed — see Step 3"
  ```

- [ ] **Step 3: Generate synthetic 100 MB file as fallback**

  ```bash
  # Run this if Step 2 failed OR to test incompressible data
  dd if=/dev/urandom bs=1M count=100 of=/tmp/bench_data/bench_random.bin 2>/dev/null
  echo "Generated: $(ls -lh /tmp/bench_data/bench_random.bin)"
  ```

- [ ] **Step 4: Confirm at least one usable file exists**

  ```bash
  ls -lh /tmp/bench_data/
  ```
  Use `bench_large.bin` as primary input throughout this plan (fall back to `bench_random.bin`
  if absent). Record the exact path for all `--inputs` arguments below.

---

## Task 4: lbzip2 Reference Benchmark

Install lbzip2 and benchmark it so it appears in the final comparison.

**Files created (on main):**
- `experiments/lbzip2/results/lbzip2_results.csv`

- [ ] **Step 1: Install lbzip2**

  ```bash
  sudo apt-get install -y lbzip2
  lbzip2 --version
  ```
  Expected: version string (e.g. `lbzip2 2.5`).

- [ ] **Step 2: Run lbzip2 sweep and write CSV**

  ```bash
  mkdir -p experiments/lbzip2/results
  INFILE=/tmp/bench_data/bench_large.bin
  INSIZE=$(stat -c%s "$INFILE")
  {
    echo "implementation,threads,compress_seconds,throughput_mbps,compression_ratio,input_bytes,output_bytes"
    for t in 1 2 4 8 $(nproc); do
      for r in 1 2 3; do
        OUTFILE=$(mktemp /tmp/lbzip2_XXXXXX.bz2)
        START=$(date +%s%N)
        lbzip2 -n "$t" -k -c "$INFILE" > "$OUTFILE"
        END=$(date +%s%N)
        OUTSIZE=$(stat -c%s "$OUTFILE")
        rm -f "$OUTFILE"
        SECS=$(echo "scale=6; ($END - $START) / 1000000000" | bc)
        TPUT=$(echo "scale=3; $INSIZE / 1000000 / $SECS" | bc)
        RATIO=$(echo "scale=6; $OUTSIZE / $INSIZE" | bc)
        echo "lbzip2,$t,$SECS,$TPUT,$RATIO,$INSIZE,$OUTSIZE"
      done
    done
  } > experiments/lbzip2/results/lbzip2_results.csv
  cat experiments/lbzip2/results/lbzip2_results.csv
  ```

- [ ] **Step 3: Verify lbzip2 output is valid bzip2**

  ```bash
  OUTFILE=/tmp/lbzip2_check.bz2
  lbzip2 -n "$(nproc)" -k -c /tmp/bench_data/bench_large.bin > "$OUTFILE"
  bunzip2 -c "$OUTFILE" | cmp - /tmp/bench_data/bench_large.bin \
    && echo "lbzip2 PASS" || echo "lbzip2 FAIL"
  rm -f "$OUTFILE"
  ```
  Expected: `lbzip2 PASS`

- [ ] **Step 4: Commit lbzip2 results on main**

  ```bash
  git add experiments/
  git commit -m "data: lbzip2 reference benchmark results"
  ```

---

## Task 5: Stage 1 — Run Naive AI Agent on branch stage/1-naive

Create a git worktree for `stage/1-naive`, open a Claude Code session inside it, feed a
single minimal prompt. The agent must not receive hints about parallelism strategy.

**Files modified by agent (expected, on branch stage/1-naive):**
- `src/main.c` — compression loop made parallel
- Possibly `src/writer.c`, `Makefile`
- Possibly new files `src/worker.{c,h}` or similar

**Files created by this task:**
- `results/stage1_results.csv` (committed on `stage/1-naive`)

- [ ] **Step 1: Create git worktree for stage/1-naive**

  ```bash
  git worktree add /tmp/wt_stage1 stage/1-naive
  ls /tmp/wt_stage1/src/
  ```
  Expected: same files as `src/` on main (args.c, bz_block.c, block_reader.c, writer.c, main.c).

- [ ] **Step 2: Build libbz2.a inside the worktree (needed for linking)**

  ```bash
  cd /tmp/wt_stage1
  make libbz2.a 2>/dev/null || make all
  ls -lh libbz2.a
  ```

- [ ] **Step 3: [HUMAN STEP] Launch Stage 1 agent session in the worktree**

  ```bash
  cd /tmp/wt_stage1
  claude
  ```

  When the agent starts, type **exactly this single prompt** (nothing else):
  ```
  Please parallelize this bzip2 compression program using multiple threads.
  Preserve correctness and improve performance.
  ```

  Let the agent implement, build, and verify autonomously.
  Exit the session when the agent reports completion.

- [ ] **Step 4: Build stage1 binary (clean build to confirm agent's work)**

  ```bash
  cd /tmp/wt_stage1
  make clean && make all
  ```
  Expected: `pbzx` binary, no errors.

  If the build fails because the agent used OpenMP but forgot `-fopenmp`:
  ```bash
  sed -i 's/^CFLAGS\s*?=.*/CFLAGS ?= -O2 -Wall -Wextra -std=c11 -fopenmp/' Makefile
  make clean && make all
  ```

- [ ] **Step 5: Verify round-trip correctness**

  ```bash
  python3 bench/verify.py ./pbzx /tmp/bench_data/bench_large.bin
  ```
  Expected: `PASS  /tmp/bench_data/bench_large.bin`

  If it fails, re-open the agent in `/tmp/wt_stage1` and report:
  ```
  python3 bench/verify.py ./pbzx <file> printed FAIL.
  The decompressed output does not match the original. Please fix the correctness bug.
  ```
  Do NOT proceed to benchmarking until it passes.

- [ ] **Step 6: Run benchmark sweep**

  ```bash
  cd /tmp/wt_stage1
  python3 bench/run_bench.py \
    --pbzx ./pbzx \
    --inputs /tmp/bench_data/bench_large.bin \
    --threads 1 2 4 8 $(nproc) \
    --block-sizes 900000 \
    --level 9 \
    --repeat 3 \
    --out results/stage1_results.csv \
    --time-bin /usr/bin/time
  ```

- [ ] **Step 7: Print quick speedup summary**

  ```bash
  python3 -c "
  import csv
  rows = list(csv.DictReader(open('results/stage1_results.csv')))
  by_t = {}
  for r in rows:
      by_t.setdefault(int(r['threads']), []).append(float(r['compress_seconds']))
  base = sum(by_t[1]) / len(by_t[1])
  print(f'Stage 1 (t=1 mean: {base:.3f}s):')
  for t in sorted(by_t):
      avg = sum(by_t[t]) / len(by_t[t])
      print(f'  threads={t:2d}  mean={avg:.3f}s  speedup={base/avg:.2f}x')
  "
  ```

- [ ] **Step 8: Commit stage1 work on its branch**

  ```bash
  cd /tmp/wt_stage1
  git add src/ Makefile results/
  git commit -m "feat: stage1 naive AI parallelization + benchmark results"
  ```

- [ ] **Step 9: Remove worktree (branch stays)**

  ```bash
  cd /path/to/Final_Project
  git worktree remove /tmp/wt_stage1
  ```

---

## Task 6: Stage 2 — Run Constraint-guided Agent on branch stage/2-constrained

Create a worktree for `stage/2-constrained`. The agent is permitted to run `lscpu`, `free`,
`nproc`, and related commands to discover machine constraints before designing.

**Files modified by agent (expected, on branch stage/2-constrained):**
- `src/main.c`, possibly `src/writer.c`, possibly new `src/*.c` files
- `Makefile`

**Files created by this task:**
- `results/stage2_results.csv` (committed on `stage/2-constrained`)

- [ ] **Step 1: Create git worktree for stage/2-constrained**

  ```bash
  git worktree add /tmp/wt_stage2 stage/2-constrained
  cd /tmp/wt_stage2 && make libbz2.a 2>/dev/null || make all
  ```

- [ ] **Step 2: [HUMAN STEP] Launch Stage 2 agent session**

  ```bash
  cd /tmp/wt_stage2
  claude
  ```

  Paste **exactly this prompt**:
  ```
  Please parallelize the compressor using block-level parallelism.

  Requirements:
  1. Split the input file into fixed-size blocks.
  2. Assign each block a unique block ID.
  3. Use worker threads to compress blocks independently.
  4. Use a writer thread (or equivalent ordered mechanism) to emit blocks in the original order.
  5. Avoid race conditions and unnecessary global locks.
  6. Avoid changing the compression result (decompressed output must match input exactly).
  7. Before choosing thread count, block size, and queue depth, run lscpu, nproc,
     free -h, and getconf -a | grep -i cache to understand the machine hardware,
     then use those values as constraints in your implementation.
  ```

  Let the agent run system commands, implement, build, and verify. Exit when done.

- [ ] **Step 3: Build and verify stage2**

  ```bash
  cd /tmp/wt_stage2
  make clean && make all
  python3 bench/verify.py ./pbzx /tmp/bench_data/bench_large.bin
  ```
  Expected: build succeeds, `PASS  /tmp/bench_data/bench_large.bin`.

- [ ] **Step 4: Run benchmark sweep**

  ```bash
  cd /tmp/wt_stage2
  python3 bench/run_bench.py \
    --pbzx ./pbzx \
    --inputs /tmp/bench_data/bench_large.bin \
    --threads 1 2 4 8 $(nproc) \
    --block-sizes 900000 \
    --level 9 \
    --repeat 3 \
    --out results/stage2_results.csv \
    --time-bin /usr/bin/time
  ```

- [ ] **Step 5: Print quick speedup summary**

  ```bash
  python3 -c "
  import csv
  rows = list(csv.DictReader(open('results/stage2_results.csv')))
  by_t = {}
  for r in rows:
      by_t.setdefault(int(r['threads']), []).append(float(r['compress_seconds']))
  base = sum(by_t[1]) / len(by_t[1])
  print(f'Stage 2 (t=1 mean: {base:.3f}s):')
  for t in sorted(by_t):
      avg = sum(by_t[t]) / len(by_t[t])
      print(f'  threads={t:2d}  mean={avg:.3f}s  speedup={base/avg:.2f}x')
  "
  ```

- [ ] **Step 6: Commit stage2 work on its branch**

  ```bash
  cd /tmp/wt_stage2
  git add src/ Makefile results/
  git commit -m "feat: stage2 constraint-guided AI parallelization + benchmark results"
  ```

---

## Task 7: Profile Stage 2 Output → Update stage/3-profiling CLAUDE.md

Profile the Stage 2 binary while its worktree is still available. Then add the raw
profiling files and an updated CLAUDE.md to the **existing** `stage/3-profiling` branch
(which already starts from the same sequential baseline as stages 1 and 2 — only the
prompt context differs).

**Files created/updated (on branch `stage/3-profiling`):**
- `profiling/perf_stat.txt`
- `profiling/time_v.txt`
- `profiling/perf_report.txt`
- `profiling/scaling.txt`
- `CLAUDE.md` (updated with actual bottleneck summary)

- [ ] **Step 1: perf stat -d on the stage2 binary**

  ```bash
  THREADS=$(nproc)
  INFILE=/tmp/bench_data/bench_large.bin
  perf stat -d \
    /tmp/wt_stage2/pbzx \
    -i "$INFILE" -o /tmp/prof_discard.bz2 \
    --threads "$THREADS" --block-size 900000 --level 9 \
    2> /tmp/perf_stat.txt
  cat /tmp/perf_stat.txt
  ```
  Note the `task-clock`, `cache-misses`, `LLC-load-misses`, and `context-switches` values.

- [ ] **Step 2: /usr/bin/time -v (wall time + peak RSS + CPU %)**

  ```bash
  /usr/bin/time -v \
    /tmp/wt_stage2/pbzx \
    -i /tmp/bench_data/bench_large.bin \
    -o /tmp/prof_discard.bz2 \
    --threads $(nproc) --block-size 900000 --level 9 \
    2> /tmp/time_v.txt
  cat /tmp/time_v.txt
  ```

- [ ] **Step 3: perf record + perf report (call-graph hotspots)**

  ```bash
  perf record -g -o /tmp/perf.data \
    /tmp/wt_stage2/pbzx \
    -i /tmp/bench_data/bench_large.bin \
    -o /tmp/prof_discard.bz2 \
    --threads $(nproc) --block-size 900000 --level 9

  perf report --stdio --no-children -i /tmp/perf.data \
    > /tmp/perf_report.txt 2>&1
  head -60 /tmp/perf_report.txt
  ```
  Note the top 5–10 functions and their `%` share.

- [ ] **Step 4: Collect thread-scaling data**

  ```bash
  INFILE=/tmp/bench_data/bench_large.bin
  {
    echo "threads,mean_compress_seconds"
    for t in 1 2 4 8 $(nproc); do
      python3 /tmp/wt_stage2/bench/run_bench.py \
        --pbzx /tmp/wt_stage2/pbzx \
        --inputs "$INFILE" \
        --threads "$t" \
        --repeat 3 \
        --out /tmp/scale_s2_t${t}.csv \
        --time-bin /usr/bin/time > /dev/null
      python3 -c "
  import csv
  rows = list(csv.DictReader(open('/tmp/scale_s2_t${t}.csv')))
  avg = sum(float(r['compress_seconds']) for r in rows) / len(rows)
  print(f'${t},{avg:.4f}')
  "
    done
  } > /tmp/scaling.txt
  cat /tmp/scaling.txt
  ```

- [ ] **Step 5: Add profiling files and update CLAUDE.md on stage/3-profiling**

  Create a worktree for stage/3-profiling, copy the profiling data in, and rewrite
  the CLAUDE.md with actual bottleneck numbers:

  ```bash
  git worktree add /tmp/wt_stage3 stage/3-profiling
  cp /tmp/perf_stat.txt /tmp/time_v.txt /tmp/perf_report.txt /tmp/scaling.txt \
     /tmp/wt_stage3/profiling/
  ```

  Then edit `/tmp/wt_stage3/CLAUDE.md` — replace the placeholder section under
  "Profiling data from a prior parallel implementation" with:

  ```markdown
  ## Profiling data from a prior parallel implementation (Stage 2 output)

  ### Thread scaling
  [paste contents of profiling/scaling.txt]

  ### Top CPU hotspots (perf report top 10)
  [paste top-10 lines from profiling/perf_report.txt]

  ### Hardware counters (perf stat -d)
  [paste task-clock, cache-misses, LLC-load-misses, context-switches lines]

  ### Peak memory + CPU utilization (/usr/bin/time -v)
  [paste Maximum resident set size and Percent of CPU lines]
  ```

- [ ] **Step 6: Commit profiling data on stage/3-profiling**

  ```bash
  cd /tmp/wt_stage3
  git add profiling/ CLAUDE.md
  git commit -m "chore: add stage2 profiling data to stage3 context"
  git push origin stage/3-profiling
  ```

- [ ] **Step 7: Remove worktrees**

  ```bash
  cd /path/to/Final_Project
  git worktree remove /tmp/wt_stage2
  git worktree remove /tmp/wt_stage3
  ```

---

## Task 8: Stage 3 — Run Profiling-guided Agent on branch stage/3-profiling

Open a worktree for `stage/3-profiling`. Like stages 1 and 2, it starts from the
sequential baseline source. The difference is the prompt: the CLAUDE.md embeds
profiling data from Stage 2's output so the agent knows the bottlenecks before it
starts. The agent also has full permission to run profiling tools on its own
implementation at any time.

**Files modified by agent (expected, on branch stage/3-profiling):**
- `src/main.c` and other `src/*.c` files
- `Makefile`
- Possibly new `src/*.c` files

**Files created by this task:**
- `results/stage3_results.csv` (committed on `stage/3-profiling`)

- [ ] **Step 1: Create git worktree for stage/3-profiling**

  ```bash
  git worktree add /tmp/wt_stage3 stage/3-profiling
  cd /tmp/wt_stage3 && make libbz2.a 2>/dev/null || make all
  ```

- [ ] **Step 2: Verify the starting state compiles and passes correctness**

  ```bash
  cd /tmp/wt_stage3
  make clean && make all
  python3 bench/verify.py ./pbzx /tmp/bench_data/bench_large.bin
  ```
  Expected: `PASS` (stage3 initially has stage2 source, already known-good).

- [ ] **Step 3: [HUMAN STEP] Launch Stage 3 agent session**

  ```bash
  cd /tmp/wt_stage3
  claude
  ```

  Paste this prompt (with actual bottleneck numbers filled in from Task 7's profiling output):
  ```
  The profiling results for the current parallel implementation show:

  [PASTE KEY FINDINGS — examples based on what profiling showed:]
  - Thread scaling plateaus after N threads: speedup at 8t=X.Xx, 16t=X.Xx (from profiling/scaling.txt)
  - Top CPU hotspot: BZ2_blockSort at ~XX% of samples (from profiling/perf_report.txt)
  - Lock/mutex contention appears at ~X% of samples
  - Peak RSS: XXX MB with N threads (from profiling/time_v.txt)
  - LLC cache miss rate: XX% (from profiling/perf_stat.txt)

  Please optimize the parallel design to address these bottlenecks while preserving
  correctness. You have permission to run perf, valgrind, /usr/bin/time, gprof,
  or any other profiling tool on ./pbzx at any point to guide your changes.
  ```

  Let the agent profile, modify, rebuild, re-profile, and iterate. Exit when done.

- [ ] **Step 4: Final build and correctness check**

  ```bash
  cd /tmp/wt_stage3
  make clean && make all
  python3 bench/verify.py ./pbzx /tmp/bench_data/bench_large.bin
  ```
  Expected: build succeeds, `PASS`.

  If it fails, re-open the agent:
  ```
  After your changes, python3 bench/verify.py ./pbzx <file> prints FAIL.
  The decompressed output does not match the original. Please fix the correctness issue.
  ```

- [ ] **Step 5: Run benchmark sweep**

  ```bash
  cd /tmp/wt_stage3
  python3 bench/run_bench.py \
    --pbzx ./pbzx \
    --inputs /tmp/bench_data/bench_large.bin \
    --threads 1 2 4 8 $(nproc) \
    --block-sizes 900000 \
    --level 9 \
    --repeat 3 \
    --out results/stage3_results.csv \
    --time-bin /usr/bin/time
  ```

- [ ] **Step 6: Print quick speedup summary**

  ```bash
  python3 -c "
  import csv
  rows = list(csv.DictReader(open('results/stage3_results.csv')))
  by_t = {}
  for r in rows:
      by_t.setdefault(int(r['threads']), []).append(float(r['compress_seconds']))
  base = sum(by_t[1]) / len(by_t[1])
  print(f'Stage 3 (t=1 mean: {base:.3f}s):')
  for t in sorted(by_t):
      avg = sum(by_t[t]) / len(by_t[t])
      print(f'  threads={t:2d}  mean={avg:.3f}s  speedup={base/avg:.2f}x')
  "
  ```

- [ ] **Step 7: Commit stage3 work on its branch**

  ```bash
  cd /tmp/wt_stage3
  git add src/ Makefile results/
  git commit -m "feat: stage3 profiling-guided AI optimization + benchmark results"
  ```

- [ ] **Step 8: Remove stage3 worktree**

  ```bash
  cd /path/to/Final_Project
  git worktree remove /tmp/wt_stage3
  ```

---

## Task 9: Baseline Benchmark + Final Comparison

Run the sequential baseline benchmark, pull results from all stage branches, merge into
one CSV, and generate comparison plots.

**Files created (on main):**
- `experiments/baseline/results/baseline_results.csv`
- `experiments/comparison/all_results.csv`
- `experiments/comparison/plots/speedup_by_impl.png`
- `experiments/comparison/plots/throughput_by_impl.png`

- [ ] **Step 1: Run baseline benchmark (on main)**

  ```bash
  mkdir -p experiments/baseline/results
  python3 bench/run_bench.py \
    --pbzx ./pbzx \
    --inputs /tmp/bench_data/bench_large.bin \
    --threads 1 2 4 8 $(nproc) \
    --block-sizes 900000 \
    --level 9 \
    --repeat 5 \
    --out experiments/baseline/results/baseline_results.csv \
    --time-bin /usr/bin/time
  ```

- [ ] **Step 2: Check out each stage branch to grab its results CSV**

  Each stage committed `results/*.csv` on its own branch. Use `git show` to extract
  without switching branches:
  ```bash
  mkdir -p experiments/stage1/results \
            experiments/stage2/results \
            experiments/stage3/results

  git show stage/1-naive:results/stage1_results.csv \
    > experiments/stage1/results/stage1_results.csv

  git show stage/2-constrained:results/stage2_results.csv \
    > experiments/stage2/results/stage2_results.csv

  git show stage/3-profiling:results/stage3_results.csv \
    > experiments/stage3/results/stage3_results.csv
  ```

- [ ] **Step 3: Merge all CSVs with implementation labels**

  ```bash
  mkdir -p experiments/comparison
  python3 - <<'EOF'
  import csv, os

  sources = [
      ("baseline", "experiments/baseline/results/baseline_results.csv"),
      ("stage1",   "experiments/stage1/results/stage1_results.csv"),
      ("stage2",   "experiments/stage2/results/stage2_results.csv"),
      ("stage3",   "experiments/stage3/results/stage3_results.csv"),
  ]

  all_rows, all_fields = [], set()
  for name, path in sources:
      if not os.path.exists(path):
          print(f"WARNING: missing {path}")
          continue
      with open(path) as f:
          rows = list(csv.DictReader(f))
      for r in rows:
          r["implementation"] = name
      all_rows.extend(rows)
      if rows:
          all_fields.update(rows[0].keys())

  fields = sorted(all_fields)
  with open("experiments/comparison/all_results.csv", "w", newline="") as f:
      w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
      w.writeheader()
      w.writerows(all_rows)
  print(f"Merged {len(all_rows)} rows -> experiments/comparison/all_results.csv")
  EOF
  ```

- [ ] **Step 4: Print comparison table at max thread count**

  ```bash
  python3 - <<'EOF'
  import csv
  from collections import defaultdict
  rows = list(csv.DictReader(open("experiments/comparison/all_results.csv")))
  max_t = max(int(r["threads"]) for r in rows)
  subset = [r for r in rows if int(r["threads"]) == max_t]
  by_impl = defaultdict(list)
  for r in subset:
      by_impl[r["implementation"]].append(r)
  print(f"\n=== Comparison at threads={max_t} ===")
  print(f"{'Implementation':<16} {'Mean time(s)':>12} {'Throughput MB/s':>16} {'Comp ratio':>10}")
  for impl in ["baseline", "stage1", "stage2", "stage3"]:
      if impl not in by_impl:
          continue
      rs = by_impl[impl]
      t  = sum(float(r["compress_seconds"]) for r in rs) / len(rs)
      tp = sum(float(r.get("throughput_mbps", 0)) for r in rs) / len(rs)
      cr = sum(float(r.get("compression_ratio", 0)) for r in rs) / len(rs)
      print(f"{impl:<16} {t:>12.3f} {tp:>16.1f} {cr:>10.4f}")
  EOF
  ```

- [ ] **Step 5: Generate speedup-by-implementation plot**

  ```bash
  mkdir -p experiments/comparison/plots
  python3 - <<'EOF'
  import csv, collections
  import matplotlib; matplotlib.use("Agg")
  import matplotlib.pyplot as plt

  rows = list(csv.DictReader(open("experiments/comparison/all_results.csv")))

  base = {}
  for r in rows:
      if int(r["threads"]) == 1:
          base.setdefault(r["implementation"], []).append(float(r["compress_seconds"]))
  base_avg = {k: sum(v)/len(v) for k, v in base.items()}

  by_impl = collections.defaultdict(lambda: collections.defaultdict(list))
  for r in rows:
      by_impl[r["implementation"]][int(r["threads"])].append(float(r["compress_seconds"]))

  fig, ax = plt.subplots(figsize=(8, 5))
  colors = {"baseline": "gray", "stage1": "steelblue", "stage2": "seagreen", "stage3": "tomato"}
  for impl in ["baseline", "stage1", "stage2", "stage3"]:
      if impl not in by_impl:
          continue
      td = by_impl[impl]
      threads = sorted(td.keys())
      b = base_avg.get(impl, 1.0)
      speedups = [b / (sum(td[t])/len(td[t])) for t in threads]
      ax.plot(threads, speedups, marker="o", label=impl, color=colors.get(impl))

  ax.set_xlabel("Threads")
  ax.set_ylabel("Speedup (vs own t=1)")
  ax.set_title("Speedup by AI Parallelization Stage")
  ax.legend(); ax.grid(True, linestyle="--", alpha=0.5)
  fig.savefig("experiments/comparison/plots/speedup_by_impl.png", dpi=150)
  plt.close(fig)
  print("Wrote experiments/comparison/plots/speedup_by_impl.png")
  EOF
  ```

- [ ] **Step 6: Generate throughput-by-implementation plot**

  ```bash
  python3 - <<'EOF'
  import csv, collections
  import matplotlib; matplotlib.use("Agg")
  import matplotlib.pyplot as plt

  rows = list(csv.DictReader(open("experiments/comparison/all_results.csv")))
  by_impl = collections.defaultdict(lambda: collections.defaultdict(list))
  for r in rows:
      by_impl[r["implementation"]][int(r["threads"])].append(
          float(r.get("throughput_mbps", 0)))

  fig, ax = plt.subplots(figsize=(8, 5))
  colors = {"baseline": "gray", "stage1": "steelblue", "stage2": "seagreen", "stage3": "tomato"}
  for impl in ["baseline", "stage1", "stage2", "stage3"]:
      if impl not in by_impl:
          continue
      td = by_impl[impl]
      threads = sorted(td.keys())
      tputs = [sum(td[t])/len(td[t]) for t in threads]
      ax.plot(threads, tputs, marker="s", label=impl, color=colors.get(impl))

  ax.set_xlabel("Threads")
  ax.set_ylabel("Throughput (MB/s)")
  ax.set_title("Throughput by AI Parallelization Stage")
  ax.legend(); ax.grid(True, linestyle="--", alpha=0.5)
  fig.savefig("experiments/comparison/plots/throughput_by_impl.png", dpi=150)
  plt.close(fig)
  print("Wrote experiments/comparison/plots/throughput_by_impl.png")
  EOF
  ```

- [ ] **Step 7: Commit final comparison on main**

  ```bash
  git add experiments/
  git commit -m "data: final comparison — all stages benchmarked, plots generated"
  ```

---

## Self-Review

### Spec coverage check

| Proposal requirement | Covered by |
|---|---|
| Sequential bzip2 baseline | Task 1 |
| Naive AI parallelization (Stage 1) | Task 5 — single prompt, no hints, branch `stage/1-naive` |
| Constraint-guided AI parallelization (Stage 2) | Task 6 — lscpu/nproc/free permitted, branch `stage/2-constrained` |
| Profiling-guided AI optimization (Stage 3) | Tasks 7–8 — full profiling permission, branch `stage/3-profiling` |
| lbzip2 reference comparison | Task 4 |
| Runtime, throughput, speedup, compression ratio, memory | `run_bench.py` sweeps in each task |
| Correctness verification | `bench/verify.py` round-trip in every stage |
| Scalability under different thread counts | `--threads 1 2 4 8 $(nproc)` in every sweep |
| Stage 1: single prompt only, no system tools | Task 5 Step 3 — one sentence prompt, minimal CLAUDE.md |
| Stage 2: agent discovers machine spec via lscpu etc. | Task 6 Step 2 + CLAUDE.md on `stage/2-constrained` |
| Stage 3: full profiling tool permission | Task 8 Step 3 + CLAUDE.md on `stage/3-profiling` |
| Each stage on its own branch | `stage/1-naive`, `stage/2-constrained`, `stage/3-profiling` |
| Stage 3 informed by Stage 2's profiling | Task 7 — profiling data added to `stage/3-profiling` CLAUDE.md; source starts from baseline |

### Branch lineage verified
- `stage/1-naive` ← `feat/baseline-harness` (sequential baseline source)
- `stage/2-constrained` ← `feat/baseline-harness` (sequential baseline source)
- `stage/3-profiling` ← `feat/baseline-harness` (sequential baseline source; profiling data added to CLAUDE.md in Task 7)

### No placeholders — all steps have concrete commands.

### Naming consistency
- Binary: always `pbzx` (disambiguated by worktree path during comparison)
- CSV column `compress_seconds` — matches `run_bench.py` output parser
- `throughput_mbps` — computed in `run_bench.py` as `(insize / 1e6) / cs`
- `--time-bin /usr/bin/time` — required for `max_rss_kb`; omit on macOS (field silently absent)
