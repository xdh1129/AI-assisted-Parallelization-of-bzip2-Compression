# Walk A — Three-Stage AI Parallelization Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the three-stage AI parallelization experiment: run a fresh Claude.ai conversation per stage with increasing guidance, record each conversation, benchmark the resulting code on Linux, and commit all artifacts.

**Architecture:** Each stage is an independent Claude.ai conversation (zero context) that receives the sequential bzip2 source code plus stage-specific guidance. The user runs conversations manually and records them as Markdown. Claude prepares prompt documents and organizes benchmark results. Stages 1 and 2 branch from `feat/baseline-harness`; Stage 3 branches from Stage 2's output.

**Tech Stack:** C11, OpenMP (GCC on Linux), GNU make, Python 3, pytest, perf (Linux), Claude.ai (Sonnet 4.6)

---

## File Structure

| File | Created/Modified | Purpose |
|---|---|---|
| `docs/ai-stages/stage1-prompt.md` | Create | Exact content to paste into Claude.ai for Stage 1 |
| `docs/ai-stages/stage1-conversation.md` | Create (user) | Full conversation copy-pasted from Claude.ai |
| `docs/ai-stages/stage1-result.md` | Create | Code diff, test result, benchmark summary |
| `results_stage1.csv` | Create (Linux) | Benchmark data |
| `docs/ai-stages/stage2-prompt.md` | Create | Exact content to paste for Stage 2 |
| `docs/ai-stages/stage2-conversation.md` | Create (user) | Full conversation |
| `docs/ai-stages/stage2-result.md` | Create | Code diff, test result, benchmark summary |
| `results_stage2.csv` | Create (Linux) | Benchmark data |
| `docs/ai-stages/stage3-prompt.md` | Create | Stage 2 code + profiling data, formatted for paste |
| `docs/ai-stages/stage3-conversation.md` | Create (user) | Full conversation |
| `docs/ai-stages/stage3-result.md` | Create | Code diff, test result, benchmark summary |
| `results_stage3.csv` | Create (Linux) | Benchmark data |

---

## Task 1: Prepare Stage 1 prompt and create branch

**Files:**
- Create: `docs/ai-stages/stage1-prompt.md`

- [ ] **Step 1: Create `feat/parallel-naive` branch from baseline**

```bash
git checkout feat/baseline-harness
git checkout -b feat/parallel-naive
```

- [ ] **Step 2: Write the Stage 1 prompt file**

Create `docs/ai-stages/stage1-prompt.md` with the following content (this is what the user will paste into Claude.ai):

```markdown
# Stage 1 Prompt — Paste this into a fresh Claude.ai conversation

Please parallelize the following bzip2 compressor using OpenMP so that
`--threads N` actually uses N threads for compression.

## Makefile
[paste full Makefile contents]

## src/args.h
[paste full contents]

## src/block_reader.h
[paste full contents]

## src/bz_block.h
[paste full contents]

## src/bz_block.c
[paste full contents]

## src/writer.h
[paste full contents]

## src/main.c
[paste full contents]
```

> Note: The prompt file is a template. When actually running the experiment,
> replace each `[paste full ... contents]` with the real file content from
> `feat/baseline-harness`.

- [ ] **Step 3: Commit the prompt file**

```bash
git add docs/ai-stages/stage1-prompt.md
git commit -m "Add Stage 1 naive prompt template"
```

---

## Task 2: Run Stage 1 conversation and commit code

**Files:**
- Modify: `src/main.c` (AI output)
- Modify: `Makefile` (AI output)
- Create: `docs/ai-stages/stage1-conversation.md`

- [ ] **Step 1: Run the conversation in Claude.ai**

Open a brand-new Claude.ai conversation (no prior context). Select model: **Claude Sonnet 4.6**.
Paste the contents of `docs/ai-stages/stage1-prompt.md` with all source files filled in.
Allow multi-turn conversation. Record the number of turns used.

- [ ] **Step 2: Apply the AI's code changes**

Copy the AI's modified files (`src/main.c`, `Makefile`, and any other files it changed)
into the working tree. Do not manually fix any errors — apply exactly what the AI produced.

- [ ] **Step 3: Save the conversation as Markdown**

Create `docs/ai-stages/stage1-conversation.md` with this structure:

```markdown
# Stage 1 — Naive AI Parallelization: Conversation

**Date:** YYYY-MM-DD
**Model:** Claude Sonnet 4.6
**Turns:** N

---

## Turn 1

**User:**
[paste your message]

**AI:**
[paste AI response]

---

## Turn 2
...
```

- [ ] **Step 4: Commit everything**

```bash
git add src/main.c Makefile docs/ai-stages/stage1-conversation.md
# add any other files the AI changed
git commit -m "Stage 1: apply naive AI parallelization output"
```

---

## Task 3: Test and benchmark Stage 1

**Files:**
- Create: `docs/ai-stages/stage1-result.md`
- Create: `results_stage1.csv` (on Linux)

- [ ] **Step 1: Attempt to build**

```bash
make clean && CC=gcc make
```

Record whether it builds. If it fails, record the error. Do NOT fix it — Stage 1 accepts
buggy output.

- [ ] **Step 2: Run tests if build succeeded**

```bash
make test
```

Record pass/fail. Do not fix failures.

- [ ] **Step 3: Run benchmark on Linux if binary works**

On the Linux machine (`ssh Team05@172.16.179.50`):
```bash
git checkout feat/parallel-naive && git pull
make clean && CC=gcc make
bash data/fetch.sh   # if data/ not yet populated
python3 bench/run_bench.py --pbzx ./pbzx \
    --inputs data/text_64.bin data/random_64.bin data/zeros_64.bin \
    --threads 1 2 4 8 --block-sizes 900000 --repeat 3 \
    --out results_stage1.csv
git add results_stage1.csv
git commit -m "Add Stage 1 benchmark results"
git push origin feat/parallel-naive
```

Then on Mac: `git pull origin feat/parallel-naive`

- [ ] **Step 4: Write `docs/ai-stages/stage1-result.md`**

```markdown
# Stage 1 — Naive AI Parallelization: Result

**Date:** YYYY-MM-DD
**Branch:** feat/parallel-naive

## Build status
[PASS / FAIL — paste error if failed]

## Test status
[PASS / FAIL / SKIPPED (build failed)]

## Code diff summary
[List files changed and key changes made by AI]

## Benchmark summary (if applicable)
[Paste speedup table from results_stage1.csv]

## Observations
[What did the AI get right? What did it miss or get wrong?]
```

- [ ] **Step 5: Commit result doc and push**

```bash
git add docs/ai-stages/stage1-result.md
git commit -m "Add Stage 1 result document"
git push origin feat/parallel-naive
```

---

## Task 4: Prepare Stage 2 prompt and create branch

**Files:**
- Create: `docs/ai-stages/stage2-prompt.md`

- [ ] **Step 1: Create `feat/parallel-constrained` branch from baseline**

```bash
git checkout feat/baseline-harness
git checkout -b feat/parallel-constrained
```

- [ ] **Step 2: Cherry-pick Stage 1 conversation and result docs**

```bash
# Cherry-pick the stage1-conversation and stage1-result commits from feat/parallel-naive
git log --oneline feat/parallel-naive | head -5
# find the commit hashes for stage1-prompt, stage1-conversation, stage1-result
git cherry-pick <stage1-prompt-hash> <stage1-conversation-hash> <stage1-result-hash>
```

- [ ] **Step 3: Write the Stage 2 prompt file**

Create `docs/ai-stages/stage2-prompt.md`:

```markdown
# Stage 2 Prompt — Paste this into a fresh Claude.ai conversation

Please parallelize the following bzip2 compressor using OpenMP so that
`--threads N` actually uses N threads for compression.
You must follow all architecture constraints listed below.

## Architecture Constraints

1. The output must be a valid `.bz2` file decompressible by standard `bunzip2`.
2. Each block must compress independently — the compression of block i must not
   depend on the result of any other block.
3. The output block order must match the input order exactly, regardless of thread
   scheduling.
4. No global lock may protect the entire compression loop.
5. `--threads N` must use exactly N threads for compression — no more, no fewer
   (when N <= number of blocks).

## Makefile
[paste full Makefile contents from feat/baseline-harness]

## src/args.h
[paste full contents]

## src/block_reader.h
[paste full contents]

## src/bz_block.h
[paste full contents]

## src/bz_block.c
[paste full contents]

## src/writer.h
[paste full contents]

## src/main.c
[paste full contents]
```

- [ ] **Step 4: Commit**

```bash
git add docs/ai-stages/stage2-prompt.md
git commit -m "Add Stage 2 constraint-guided prompt template"
```

---

## Task 5: Run Stage 2 conversation and commit code

**Files:**
- Modify: `src/main.c` (AI output)
- Modify: `Makefile` (AI output)
- Possibly modify: `src/bz_block.h`, `src/bz_block.c` (AI may add helpers)
- Create: `docs/ai-stages/stage2-conversation.md`

- [ ] **Step 1: Run the conversation in Claude.ai**

Open a brand-new Claude.ai conversation. Model: **Claude Sonnet 4.6**.
Paste `docs/ai-stages/stage2-prompt.md` with all source files filled in.
Allow multi-turn. Record turn count.

- [ ] **Step 2: Apply the AI's code changes**

Copy all changed files into the working tree exactly as produced.

- [ ] **Step 3: Build and test (required for Stage 2)**

```bash
make clean && CC=gcc make
make test
```

If tests fail, return to the Claude.ai conversation and show the error message.
Do not say how to fix it. Allow the AI to diagnose and fix. Repeat until tests pass
or the conversation is exhausted.

- [ ] **Step 4: Save conversation as Markdown**

Create `docs/ai-stages/stage2-conversation.md` with the same format as Stage 1
(date, model, turn count, full turns).

- [ ] **Step 5: Commit**

```bash
git add src/ Makefile docs/ai-stages/stage2-conversation.md
git commit -m "Stage 2: apply constraint-guided AI parallelization output"
```

---

## Task 6: Benchmark Stage 2 and collect profiling data

**Files:**
- Create: `docs/ai-stages/stage2-result.md`
- Create: `results_stage2.csv` (on Linux)
- Create: `docs/ai-stages/perf_stage2.txt` (on Linux)

- [ ] **Step 1: Run benchmark on Linux**

```bash
git checkout feat/parallel-constrained && git pull
make clean && CC=gcc make
python3 bench/run_bench.py --pbzx ./pbzx \
    --inputs data/text_64.bin data/random_64.bin data/zeros_64.bin \
    --threads 1 2 4 8 --block-sizes 900000 --repeat 3 \
    --out results_stage2.csv
```

- [ ] **Step 2: Collect perf stat data (for Stage 3)**

```bash
for t in 1 4 8; do
    echo "=== text threads=$t ===" >> docs/ai-stages/perf_stage2.txt
    perf stat -d ./pbzx -i data/text_64.bin -o /tmp/out.bz2 \
        --threads $t 2>> docs/ai-stages/perf_stage2.txt
done
for t in 1 4 8; do
    echo "=== random threads=$t ===" >> docs/ai-stages/perf_stage2.txt
    perf stat -d ./pbzx -i data/random_64.bin -o /tmp/out.bz2 \
        --threads $t 2>> docs/ai-stages/perf_stage2.txt
done
```

- [ ] **Step 3: Push from Linux**

```bash
git add results_stage2.csv docs/ai-stages/perf_stage2.txt
git commit -m "Add Stage 2 benchmark results and perf data"
git push origin feat/parallel-constrained
```

Then on Mac: `git pull origin feat/parallel-constrained`

- [ ] **Step 4: Write `docs/ai-stages/stage2-result.md`**

```markdown
# Stage 2 — Constraint-guided AI Parallelization: Result

**Date:** YYYY-MM-DD
**Branch:** feat/parallel-constrained

## Build status: PASS

## Test status: PASS

## Code diff summary
[List files changed and key decisions the AI made]

## Benchmark summary

| Input | Threads | Stage 1 (s) | Stage 2 (s) | Δ |
|---|---|---|---|---|
| text_64 | 1 | ... | ... | ... |
| text_64 | 4 | ... | ... | ... |
| text_64 | 8 | ... | ... | ... |
| random_64 | 1 | ... | ... | ... |
| random_64 | 4 | ... | ... | ... |
| random_64 | 8 | ... | ... | ... |

## Observations
[What constraints did the AI follow? Which ones led to better/worse results?]
```

- [ ] **Step 5: Commit result doc and push**

```bash
git add docs/ai-stages/stage2-result.md
git commit -m "Add Stage 2 result document"
git push origin feat/parallel-constrained
```

---

## Task 7: Prepare Stage 3 prompt and create branch

**Files:**
- Create: `docs/ai-stages/stage3-prompt.md`

- [ ] **Step 1: Create `feat/parallel-profiling` branch from Stage 2**

```bash
git checkout feat/parallel-constrained
git checkout -b feat/parallel-profiling
```

- [ ] **Step 2: Write the Stage 3 prompt file**

Create `docs/ai-stages/stage3-prompt.md`. This prompt includes Stage 2's code,
the benchmark comparison, and the perf data. Fill in the actual numbers:

```markdown
# Stage 3 Prompt — Paste this into a fresh Claude.ai conversation

This is a constraint-guided parallel bzip2 compressor. Based on the profiling
data below, identify the performance bottleneck and optimize it.
Explain what you changed and why.

## Benchmark: Stage 1 (naive) vs Stage 2 (constrained)

[Paste the comparison table from stage2-result.md]

## perf stat output (Stage 2 binary, text_64.bin)

[Paste contents of docs/ai-stages/perf_stage2.txt]

## Current source code (Stage 2)

### Makefile
[paste]

### src/args.h
[paste]

### src/block_reader.h
[paste]

### src/bz_block.h
[paste]

### src/bz_block.c
[paste]

### src/writer.h
[paste]

### src/main.c
[paste]
```

- [ ] **Step 3: Commit**

```bash
git add docs/ai-stages/stage3-prompt.md
git commit -m "Add Stage 3 profiling-guided prompt template"
```

---

## Task 8: Run Stage 3 conversation and commit code

**Files:**
- Modify: `src/main.c` (AI output)
- Possibly: `src/bz_block.h`, `src/bz_block.c`, `Makefile`
- Create: `docs/ai-stages/stage3-conversation.md`

- [ ] **Step 1: Run the conversation in Claude.ai**

Open a brand-new Claude.ai conversation. Model: **Claude Sonnet 4.6**.
Paste `docs/ai-stages/stage3-prompt.md` with all data filled in.
Allow multi-turn. Record turn count.

- [ ] **Step 2: Apply AI's changes**

Copy all changed files into the working tree exactly as produced.

- [ ] **Step 3: Build and test (required)**

```bash
make clean && CC=gcc make
make test
```

If tests fail, show error to AI and let it fix. Do not fix manually.

- [ ] **Step 4: Save conversation**

Create `docs/ai-stages/stage3-conversation.md` (same format as Stages 1 and 2).

- [ ] **Step 5: Commit**

```bash
git add src/ Makefile docs/ai-stages/stage3-conversation.md
git commit -m "Stage 3: apply profiling-guided AI optimization output"
```

---

## Task 9: Benchmark Stage 3 and write final results

**Files:**
- Create: `docs/ai-stages/stage3-result.md`
- Create: `results_stage3.csv` (on Linux)

- [ ] **Step 1: Run benchmark on Linux**

```bash
git checkout feat/parallel-profiling && git pull
make clean && CC=gcc make
python3 bench/run_bench.py --pbzx ./pbzx \
    --inputs data/text_64.bin data/random_64.bin data/zeros_64.bin \
    --threads 1 2 4 8 --block-sizes 900000 --repeat 3 \
    --out results_stage3.csv
git add results_stage3.csv
git commit -m "Add Stage 3 benchmark results"
git push origin feat/parallel-profiling
```

Then on Mac: `git pull origin feat/parallel-profiling`

- [ ] **Step 2: Write `docs/ai-stages/stage3-result.md`**

```markdown
# Stage 3 — Profiling-guided AI Optimization: Result

**Date:** YYYY-MM-DD
**Branch:** feat/parallel-profiling

## Build status: PASS

## Test status: PASS

## Code diff summary (vs Stage 2)
[List what changed from Stage 2]

## AI's stated optimization rationale
[Quote the AI's explanation of what bottleneck it found and what it changed]

## Benchmark summary

| Input | Threads | Stage 2 (s) | Stage 3 (s) | Δ |
|---|---|---|---|---|
| text_64 | 1 | ... | ... | ... |
| text_64 | 4 | ... | ... | ... |
| text_64 | 8 | ... | ... | ... |
| random_64 | 4 | ... | ... | ... |
| random_64 | 8 | ... | ... | ... |

## Observations
[Did profiling guidance lead to measurable improvement over Stage 2?
 Did the AI correctly identify the bottleneck from the perf data?]
```

- [ ] **Step 3: Commit result doc and push**

```bash
git add docs/ai-stages/stage3-result.md
git commit -m "Add Stage 3 result document"
git push origin feat/parallel-profiling
```
