# Design: Walk A — Three-Stage AI-Assisted Parallelization Experiment

**Date:** 2026-05-31
**Team:** 05
**Status:** Approved

---

## Research Question

Does the level of guidance given to an AI affect the quality of its parallelization output?
Three stages provide the same sequential bzip2 compressor to the same AI model under
increasing levels of guidance, and compare correctness, speedup, and design decision quality.

---

## Fixed Conditions (Control Variables)

| Variable | Value |
|---|---|
| Starting code | `feat/baseline-harness` sequential `pbzx` |
| AI model | Claude Sonnet 4.6, fresh conversation (zero context) |
| Platform | Linux (benchmark + profiling); macOS (development only) |
| Conversation rules | Multi-turn; clarifying questions allowed; AI not told how to fix errors; actual turn count recorded |

---

## Experiment Structure

```
sequential baseline (feat/baseline-harness)
      │
      ├── Stage 1 (naive)          → feat/parallel-naive
      │     input: code only
      │
      ├── Stage 2 (constrained)    → feat/parallel-constrained
      │     input: code + architecture constraints
      │
      └── Stage 3 (profiling)      → feat/parallel-profiling
            starting point: Stage 2 output
            input: Stage 2 code + benchmark comparison + perf data
```

---

## Stage 1 — Naive

**Goal:** Measure what an AI produces with zero guidance.

**What the AI receives:**
- Full contents of: `Makefile`, `src/args.h`, `src/block_reader.h`, `src/bz_block.h`,
  `src/bz_block.c`, `src/writer.h`, `src/main.c`
- Single prompt: "Please parallelize this bzip2 compressor using OpenMP so that
  `--threads N` actually uses N threads for compression."

**What is withheld:** All design hints, thread-safety notes, OpenMP idioms.

**Completion criteria:** Stage 1 accepts buggy output — the AI's raw result is recorded
as-is. Errors and omissions are data. If the AI asks clarifying questions, factual
answers are allowed (e.g. "Linux, GCC").

**Deliverables:**
- Full conversation saved as `docs/ai-stages/stage1-conversation.md` (with turn count)
- `docs/ai-stages/stage1-result.md`: code diff, test results, benchmark summary
- `results_stage1.csv` if the binary runs

---

## Stage 2 — Constraint-Guided

**Goal:** Measure how architecture-level constraints improve AI design decisions,
without specifying implementation details.

**What the AI receives:**
- Same sequential source files as Stage 1
- Five architecture-level constraints (no implementation specifics):
  1. Output must be a valid `.bz2` file decompressible by `bunzip2`
  2. Each block must compress independently — no inter-block dependencies
  3. The output block order must match the input order
  4. No global lock may protect the entire compression loop
  5. `--threads N` must use exactly N threads for compression

**What is withheld:** Implementation choices (scheduling strategy, buffer allocation,
atomic operations), profiling data.

**Completion criteria:** Code must pass `make test` and produce output that round-trips
correctly through `bunzip2`.

**Deliverables:**
- Full conversation saved as `docs/ai-stages/stage2-conversation.md` (with turn count)
- `docs/ai-stages/stage2-result.md`: code diff, test results, benchmark summary
- `results_stage2.csv` (threads 1/2/4/8, three input types, 3 repeats each)

---

## Stage 3 — Profiling-Guided

**Goal:** Measure whether real profiling data lets the AI identify and fix actual
bottlenecks rather than making reasoned-but-unmeasured choices.

**Pre-requisite: collect profiling data on Linux from Stage 2 binary:**

```bash
# Timing sweep
python3 bench/run_bench.py --pbzx ./pbzx \
    --inputs data/text_64.bin data/random_64.bin data/zeros_64.bin \
    --threads 1 2 4 8 --block-sizes 900000 --repeat 3 \
    --out results_stage2.csv

# CPU metrics
for t in 1 4 8; do
    perf stat -d ./pbzx -i data/text_64.bin -o /tmp/out.bz2 --threads $t
done
```

**What the AI receives:**
- Stage 2's complete final source code
- Benchmark comparison table (Stage 1 vs Stage 2 speedup by input type)
- `perf stat` output
- Prompt: "This is the constraint-guided parallel version. Based on the profiling
  data below, identify the performance bottleneck and optimize it."

**Completion criteria:** Same as Stage 2 (`make test` passes, output correct).
AI must also explain what it optimized and why.

**Starting point:** `feat/parallel-constrained` (Stage 2 output), not the sequential baseline.

**Deliverables:**
- Full conversation saved as `docs/ai-stages/stage3-conversation.md` (with turn count)
- `docs/ai-stages/stage3-result.md`: code diff vs Stage 2, test results, benchmark summary
- `results_stage3.csv`

---

## Documentation Structure (per branch)

```
docs/ai-stages/
  stageN-conversation.md   # full copy-pasted conversation + turn count
  stageN-result.md         # code diff, test output, benchmark summary

results_stageN.csv         # benchmark data (on the branch)
```

## Branch Inheritance

- `feat/parallel-naive` and `feat/parallel-constrained`: branch from `feat/baseline-harness`
- `feat/parallel-profiling`: branch from `feat/parallel-constrained`
- Each branch carries forward all previous stages' `docs/ai-stages/` files (via cherry-pick)

---

## Comparison Dimensions (for report)

| Dimension | Measurement |
|---|---|
| Correctness | `make test` pass/fail; bunzip2 round-trip |
| Speedup | compress_seconds by thread count (1T baseline) |
| Design decision quality | What AI explained, what errors it made, what it self-corrected |
| Conversation turns | Actual turns used per stage |

---

## Out of Scope

- Comparing different AI models across stages (model is fixed)
- Automated API-based conversation running
- Stages other than the three defined here
- Decompression parallelization
